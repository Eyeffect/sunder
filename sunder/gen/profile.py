"""SUNDER — theme profiles: the LLM's one-shot read on a frequency.

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
from ..registry import approved_ids, propose as registry_propose
from .client import LLMError

log = logging.getLogger("sunder.gen")

SCHEMA_VERSION = 1

CACHE_DIR = Path(__file__).parent / "cache"

_DEFAULT_POOL = [
    "Silent Track", "Copper Signal", "Polar Tape", "Glass Antenna",
    "Hollow Echo", "Night Frequency", "Rust Parade", "Bass Tide",
    "Distant Station", "Velvet Static",
]

_DEFAULT_BRIEF = "A fresh SUNDER frequency — musical, weird, and vivid."


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
    """Load (or build) a profile for `theme`. `client` may be a FakeLLM."""
    profile = _load_cached(theme)
    if profile is not None:
        return profile
    if not use_llm:
        profile = default_profile(theme)
        _save_cached(theme, profile)
        return profile
    try:
        profile = _fetch_profile(theme, client)
    except (LLMError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
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
             "You shape the flavor of a card theme for SUNDER, a procedural "
             "music-duel game. Affinity weights steer an automatic card "
             "sampler. Reply with ONLY valid JSON, no commentary, matching "
             "this exact shape:\n"
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
             '  "proposed_tags": [{"id": "lowercase_snake", "definition": "short", '
             '"reminder": "one sentence"}] — at most 2, can be []\n'
             "}"
         )},
        {"role": "user",
         "content": (
             f"THEME: {theme}\n\n"
             "Write the profile. Higher weight = that dimension is more "
             "common for this theme. Include every key from the lists below; "
             "weights must be numbers between 0 and 1.\n\n"
             f"types: {types}\n"
             f"rarities: {rarities}\n"
             f"triggers: {triggers}\n"
             f"effects: {effects}\n"
             f"targets: {targets}\n"
             f"keywords: {approved_keywords}\n"
             f"approved tags: {approved_tags}\n"
         )},
    ]


def _fetch_profile(theme: str, client) -> ThemeProfile:
    data = client.chat_json(_build_prompt(theme), temperature=0.8, max_tokens=8000)
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
        tag_affinity=_clamp(data.get("tag_affinity"), sorted(approved_ids("tags"))),
        proposed_tags=[],
    )
    _register_proposals(data.get("proposed_tags"))
    return profile


def _register_proposals(raw) -> None:
    if not isinstance(raw, list):
        return
    for item in raw[:2]:
        if not isinstance(item, dict):
            continue
        entry_id = str(item.get("id") or "").strip().lower()
        definition = str(item.get("definition") or "")
        reminder = str(item.get("reminder") or "")
        if not entry_id:
            continue
        try:
            registry_propose("tag", entry_id, definition, reminder)
        except ValueError as exc:
            log.warning("skipping proposed tag %r: %s", entry_id, exc)


def _clamp(raw, keys: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for key in keys:
        v = raw.get(key, 0.5)
        try:
            out[key] = max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            out[key] = 0.5
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
            tag_affinity=_clamp(prof.get("tag_affinity"), sorted(approved_ids("tags"))),
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
