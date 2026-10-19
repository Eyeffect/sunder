"""SUNDER — theme profiles: the LLM's one-shot read on a theme.

A profile steers the sampler. It is fetched once per theme (then cached on
disk keyed by the theme slug + schema version) and carries affinity weights
for every closed vocabulary dimension plus a name pool and a flavour brief.

Every weight field is range-clamped to [0, 1]; a malformed or unreachable
profile degrades to `DEFAULT_PROFILE` with `fallback=True` (logged, and the
cache entry is marked so the degradation is visible).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..primitives import CardType, Effect, Rarity, Target, Trigger
from ..registry import (APPROVED, REJECTED, all_entries, approved_ids,
                        propose as registry_propose)
from ..schema import parse_card
from .client import LLMError
from .legality import (SCALINGS, _EFFECTS_BY_TYPE, _EFFECT_TARGETS,
                       _TRIGGERS_BY_TYPE, _VALUE_RANGE, normalize_mechanic,
                       validate_mechanic)

log = logging.getLogger("sunder.gen")

SCHEMA_VERSION = 3

# Timeout for the fresh LLM probe fired on a fallback cache hit. Measured
# profile latency for the reasoning default model is ~55-70s, so the bound
# must clear that; a dead gateway still fails instantly via
# connection-refused, so this only ever binds against a slow-but-alive model.
PROBE_TIMEOUT = 120.0

# Affinity floor for approved tags a theme's profile never ranked. The
# approved-tag pool is open and grows as themes are fetched, so unranked
# (usually foreign) tags must not sit at the neutral 0.5 — a small floor keeps
# them possible as rare connective tissue without crowding out theme tags.
_TAG_FLOOR = 0.15

CACHE_DIR = Path(__file__).parent / "cache"

_DEFAULT_POOL = [
    "Folded Horizon", "Ember Court", "Glass Petal", "Quiet Thunder",
    "Iron Bloom", "Mirror Tide", "Cinder Halo", "Hollow Crown",
    "Solar Echo", "Ash Requiem",
]

_DEFAULT_BRIEF = "A card from a far corner of the multiverse — vivid, strange, and true to its world."


@dataclass
class ThemeProfile:
    theme: str
    flavor_brief: str
    name_pool: list[str]
    type_affinity: dict[str, float] = field(default_factory=dict)
    rarity_affinity: dict[str, float] = field(default_factory=dict)
    trigger_affinity: dict[str, float] = field(default_factory=dict)
    effect_affinity: dict[str, float] = field(default_factory=dict)
    target_affinity: dict[str, float] = field(default_factory=dict)
    keyword_affinity: dict[str, float] = field(default_factory=dict)
    tag_affinity: dict[str, float] = field(default_factory=dict)
    proposed_tags: list[dict] = field(default_factory=list)
    fallback: bool = False
    from_cache: bool = False


def default_profile(theme: str) -> ThemeProfile:
    return ThemeProfile(
        theme=theme,
        flavor_brief=_DEFAULT_BRIEF,
        name_pool=list(_DEFAULT_POOL),
        type_affinity={t.value: 0.5 for t in CardType},
        rarity_affinity={r.value: 0.5 for r in Rarity},
        trigger_affinity={t.value: 0.5 for t in Trigger},
        effect_affinity={e.value: 0.5 for e in Effect},
        target_affinity={t.value: 0.5 for t in Target},
        keyword_affinity={},
        tag_affinity={},
        fallback=True,
    )


def slugify(theme: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", theme.lower()).strip("-")
    return slug or "theme"


def profile_for(theme: str, client, use_llm: bool = True) -> ThemeProfile:
    """Load (or build) a profile for `theme`. `client` may be a FakeLLM.

    A genuine (non-fallback) cache hit is returned as-is. A fallback cache
    hit is treated as a miss-with-fallback: we attempt one fresh LLM call
    (bounded probe timeout) and only fall through to the stale fallback if
    that fails — a transient outage must not pin a theme to deterministic
    mode forever.
    """
    cached = _load_cached(theme)
    if cached is not None and not cached.fallback:
        return cached
    if not use_llm:
        if cached is not None:
            return cached
        profile = default_profile(theme)
        _save_cached(theme, profile)
        return profile
    try:
        # Fresh themes use the client's full timeout; only the fallback
        # re-probe is bounded so a slow-but-alive model can't hang forever.
        profile = _fetch_profile(theme, client,
                                 timeout=None if cached is None else PROBE_TIMEOUT)
        _save_cached(theme, profile)  # overwrites any stale fallback
        return profile
    except (LLMError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        if cached is not None:
            log.warning("reusing stale fallback for %r (probe failed): %s",
                        theme, exc)
            return cached  # left stale so the next request retries
        log.warning("profile fallback for %r: %s", theme, exc)
        profile = default_profile(theme)
        _save_cached(theme, profile)
        return profile


# ---------------------------------------------------------------- LLM fetch

def _build_prompt(theme: str) -> list[dict]:
    from ..registry import approved_ids as _approved
    approved_tags = sorted(_approved("tags"))
    approved_keywords = sorted(_approved("keywords"))
    types = [t.value for t in CardType]
    rarities = [r.value for r in Rarity]
    triggers = [t.value for t in Trigger]
    effects = [e.value for e in Effect]
    targets = [t.value for t in Target]
    return [
        {"role": "system",
         "content": (
             "You shape the flavor of a card theme for SUNDER, a multiverse "
             "card game. You play a broadcast station battling another "
             "across a shared spectrum, and every card is a transmission "
             "bleeding in from some world — any world. The radio-station "
             "frame is the game's shell, not its subject matter: a theme "
             "may be anything and must be true to itself. Affinity weights "
             "steer an automatic card sampler. Reply with ONLY valid JSON, "
             "no commentary, matching this exact shape:\n"
             "{\n"
             '  "flavor_brief": "one short evocative paragraph",\n'
             '  "name_pool": ["up to 12 punchy card names"],\n'
             '  "type_affinity": {each type: weight 0..1},\n'
             '  "rarity_affinity": {each rarity: weight 0..1},\n'
             '  "trigger_affinity": {each trigger: weight 0..1},\n'
             '  "effect_affinity": {each effect: weight 0..1},\n'
             '  "target_affinity": {each target: weight 0..1},\n'
             '  "keyword_affinity": {each keyword: weight 0..1},\n'
             '  "tag_affinity": {each tag: weight 0..1},\n'
             '  "proposed_tags": [{"id": "lowercase_snake", "definition": '
             '"short subject-matter phrase", "reminder": "one thematic '
             'sentence — only when there is no mechanic", "mechanic": '
             '{"trigger": "…", "effect": "…", "target": "…", "scaling": '
             '"FLAT", "value": 1, "value_def": 0, "tag": "…", "keyword": '
             '"…", "count_type": "…", "condition": {"has_tag": "…"}}}] — '
             "at most 2, can be []\n"
             "}"
         )},
        {"role": "user",
         "content": (
             f"THEME: {theme}\n\n"
             "The theme is a world from the multiverse — a planet, era, "
             "culture, or abstraction — write it true to itself, not to the "
             "game's radio shell. Higher weight = that dimension is more "
             "common for this theme. Include every key from the lists below; "
             "weights must be numbers between 0 and 1.\n\n"
             f"types: {types}\n"
             f"rarities: {rarities}\n"
             f"triggers: {triggers}\n"
             f"effects: {effects}\n"
             f"targets: {targets}\n"
             f"scalings: {SCALINGS}\n"
             f"keywords: {approved_keywords}\n"
             f"approved tags: {approved_tags}\n"
             f"legal targets per effect: {_EFFECT_TARGETS}\n"
             f"value ranges per effect (FLAT only): {_VALUE_RANGE}\n"
             f"triggers per card type: {_TRIGGERS_BY_TYPE}\n"
             f"effects per card type: {_EFFECTS_BY_TYPE}\n\n"
             "MECHANIC RULES:\n"
             "- 'mechanic' must be composed ONLY from the lists and tables "
             "above; anything unsupported is discarded (the tag still "
             "becomes a plain flavor tag).\n"
             "- 'value' matters only for FLAT and must sit inside the value "
             "range; for any X-scaling set value to 1.\n"
             "- X_COUNT_OF_TAG_ON_BOARD requires 'tag' from the approved "
             "tags.\n"
             "- X_COUNT_OF_TYPE_ON_BOARD may set 'count_type' to a card "
             "type (omit it to count the card's own type).\n"
             "- GRANT_KEYWORD requires 'keyword' from the keywords list.\n"
             "- 'condition' (optional) is {\"has_tag\": \"an approved "
             "tag\"}.\n"
             "- A mechanic is what a card does when this tag is its subject "
             "tag; keep it to one lane and modest.\n"
             "- The reminder is auto-derived from the mechanic and will be "
             "exact — do NOT write a reminder when a mechanic is present.\n"
         )},
    ]


def _fetch_profile(theme: str, client, timeout: float | None = None) -> ThemeProfile:
    data = client.chat_json(_build_prompt(theme), temperature=0.8,
                            max_tokens=24000, timeout=timeout)
    if not isinstance(data, dict):
        raise ValueError("profile is not a JSON object")
    if data.get("schema_version") is not None and data["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"profile schema version {data['schema_version']} unsupported")
    expected = ("flavor_brief", "name_pool", "type_affinity", "rarity_affinity",
                "trigger_affinity", "effect_affinity", "target_affinity",
                "keyword_affinity", "tag_affinity")
    if not any(k in data for k in expected):
        raise ValueError("profile lacks any expected fields")

    profile = ThemeProfile(
        theme=theme,
        flavor_brief=str(data.get("flavor_brief") or _DEFAULT_BRIEF),
        name_pool=_clean_pool(data.get("name_pool")),
        type_affinity=_clamp(data.get("type_affinity"), [t.value for t in CardType]),
        rarity_affinity=_clamp(data.get("rarity_affinity"), [r.value for r in Rarity]),
        trigger_affinity=_clamp(data.get("trigger_affinity"), [t.value for t in Trigger]),
        effect_affinity=_clamp(data.get("effect_affinity"), [e.value for e in Effect]),
        target_affinity=_clamp(data.get("target_affinity"), [t.value for t in Target]),
        keyword_affinity=_clamp(data.get("keyword_affinity"),
                                sorted(approved_ids("keywords"))),
        tag_affinity=_clamp(data.get("tag_affinity"), sorted(approved_ids("tags")),
                            default=_TAG_FLOOR),
        proposed_tags=[],
    )
    own_tags = _register_proposals(data.get("proposed_tags"))
    for tag_id in own_tags:
        profile.tag_affinity[tag_id] = 1.0
    return profile


def _register_proposals(raw) -> list[str]:
    """Propose tags from the LLM response into the review queue.

    Returns the ids of every proposal (used by the caller to boost the
    theme's own tags in `tag_affinity` once approved). Proposals land as
    `proposed` — the web REGISTRY panel approves them and only then does
    the sampler draw them and attach mechanics. A tag the user explicitly
    rejected is re-opened to `proposed` but stays unapproved — a rejection
    is respected until the user acts again.
    """
    accepted: list[str] = []
    if not isinstance(raw, list):
        return accepted
    approved_tags = approved_ids("tags")
    approved_keywords = approved_ids("keywords")
    existing = {e.id: e.status for e in all_entries("tags")}
    for item in raw[:2]:
        if not isinstance(item, dict):
            continue
        entry_id = str(item.get("id") or "").strip().lower()
        definition = str(item.get("definition") or "")
        if not entry_id:
            continue
        mechanic = item.get("mechanic")
        if mechanic is not None:
            ok, reason = _valid_mechanic(mechanic, entry_id, approved_tags,
                                         approved_keywords)
            if ok:
                reminder = _mechanic_reminder(mechanic)
            else:
                log.warning("rejecting mechanic for proposed tag %r: %s",
                            entry_id, reason)
                mechanic = None
                reminder = str(item.get("reminder") or "")
        else:
            reminder = str(item.get("reminder") or "")
        try:
            registry_propose("tag", entry_id, definition, reminder,
                             mechanic=mechanic)
        except ValueError as exc:
            log.warning("skipping proposed tag %r: %s", entry_id, exc)
            continue
        if existing.get(entry_id) == REJECTED:
            log.info("proposed tag %r stays unapproved — earlier rejection "
                     "is respected", entry_id)
        elif existing.get(entry_id) != APPROVED:
            log.info("proposed tag %r queued for review", entry_id)
        accepted.append(entry_id)
    return accepted


def _valid_mechanic(mechanic, entry_id: str, approved_tags, approved_keywords) \
        -> tuple[bool, str]:
    ok, reason = validate_mechanic(mechanic)
    if not ok:
        return False, reason
    if mechanic.get("scaling") == "X_COUNT_OF_TAG_ON_BOARD":
        tag = mechanic.get("tag")
        if tag not in approved_tags and tag != entry_id:
            return False, f"tag {tag!r} is not approved"
    if mechanic.get("effect") == "GRANT_KEYWORD":
        kw = mechanic.get("keyword")
        if kw not in approved_keywords:
            return False, f"keyword {kw!r} is not approved"
    cond = mechanic.get("condition") or {}
    if cond.get("has_tag") and cond["has_tag"] not in approved_tags:
        return False, f"condition tag {cond['has_tag']!r} is not approved"
    return True, ""


def _mechanic_reminder(mechanic: dict) -> str:
    """Deterministic, engine-true reminder derived from a validated mechanic."""
    from ..lore import rules_text
    raw = {
        "id": "mechanic", "name": "", "set": "", "plane": "",
        "rarity": "COMMON", "cost": 0, "type": "BROADCAST",
        "stats": {"atk": 0, "def": 0}, "keywords": [],
        "abilities": [normalize_mechanic(mechanic)], "flavor": "",
    }
    return rules_text(parse_card(raw))


def _clamp(raw, keys: list[str], default: float = 0.5) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for key in keys:
        v = raw.get(key, default)
        try:
            out[key] = max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            out[key] = default
    return out


def _clean_pool(raw) -> list[str]:
    if not isinstance(raw, list):
        return list(_DEFAULT_POOL)
    names = []
    for n in raw:
        if isinstance(n, str) and n.strip() and "\n" not in n and len(n.strip()) <= 48:
            if n.strip() not in names:
                names.append(n.strip())
    return names[:40] or list(_DEFAULT_POOL)


# ---------------------------------------------------------------- cache

def _cache_path(theme: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{slugify(theme)}.json"


def _load_cached(theme: str) -> ThemeProfile | None:
    path = _cache_path(theme)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if raw.get("schema_version") != SCHEMA_VERSION:
        return None
    prof = raw.get("profile")
    if not isinstance(prof, dict):
        return None
    try:
        return ThemeProfile(
            theme=theme,
            flavor_brief=str(prof.get("flavor_brief") or _DEFAULT_BRIEF),
            name_pool=_clean_pool(prof.get("name_pool")),
            type_affinity=_clamp(prof.get("type_affinity"), [t.value for t in CardType]),
            rarity_affinity=_clamp(prof.get("rarity_affinity"), [r.value for r in Rarity]),
            trigger_affinity=_clamp(prof.get("trigger_affinity"), [t.value for t in Trigger]),
            effect_affinity=_clamp(prof.get("effect_affinity"), [e.value for e in Effect]),
            target_affinity=_clamp(prof.get("target_affinity"), [t.value for t in Target]),
            keyword_affinity=_clamp(prof.get("keyword_affinity"),
                                    sorted(approved_ids("keywords"))),
            tag_affinity=_clamp(prof.get("tag_affinity"), sorted(approved_ids("tags")),
                                default=_TAG_FLOOR),
            proposed_tags=[],
            fallback=bool(prof.get("fallback")),
            from_cache=True,
        )
    except (TypeError, ValueError):
        return None


def _save_cached(theme: str, profile: ThemeProfile) -> None:
    path = _cache_path(theme)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "profile": {
            "theme": profile.theme,
            "flavor_brief": profile.flavor_brief,
            "name_pool": profile.name_pool,
            "type_affinity": profile.type_affinity,
            "rarity_affinity": profile.rarity_affinity,
            "trigger_affinity": profile.trigger_affinity,
            "effect_affinity": profile.effect_affinity,
            "target_affinity": profile.target_affinity,
            "keyword_affinity": profile.keyword_affinity,
            "tag_affinity": profile.tag_affinity,
            "fallback": profile.fallback,
        },
    }
    path.write_text(json.dumps(payload, indent=2))
