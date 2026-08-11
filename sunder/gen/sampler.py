"""SUNDER — deterministic card sampler.

The sampler turns a theme profile into card skeletons: everything mechanical
(type, rarity, keywords, stats, ability tuples, cost) plus the load-bearing
tag and the flavor-tag menu the humanizer picks from. A seeded
`random.Random` makes skeletons reproducible; the LLM only ever touches
names, flavour text, and menu choices.

Costs are set to `suggested_cost`, so every generated card is in-budget by
construction — and because `budget.py` never discounts conditions, a
conditional ability costs the same as an unconditional one (a condition is
not a discount).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..budget import _KEYWORD_COST, budget_score, suggested_cost
from ..primitives import Rarity
from ..registry import approved_ids, tag_mechanic
from ..schema import parse_card
from .ledger import Ledger, signature_from_skeleton
from .legality import (_EFFECT_TARGETS, _EFFECTS_BY_TYPE, _KEYWORDS_BY_TYPE,
                       _TRIGGERS_BY_TYPE, _VALUE_RANGE, mechanic_legal)
from .profile import ThemeProfile

log = logging.getLogger("sunder.gen")

MAX_NOVELTY_ATTEMPTS = 5
BUDGET_ATTEMPTS = 6

# Ceiling budget per rarity keeps generated costs inside the playable band
# (roughly cost 2–6) so a pack feels draftable, not theoretical.
_SCORE_CAP = {"COMMON": 6, "UNCOMMON": 8, "RARE": 11, "SUNDERED": 14}

_RARITY_ORDER = [r.value for r in Rarity]


@dataclass
class CardSkeleton:
    id: str
    set: str
    plane: str
    type: str
    rarity: str
    cost: int
    keywords: list[str]
    stats: dict
    abilities: list[dict]
    load_bearing_tag: str | None = None
    subject_tag: str | None = None
    flavor_tag_menu: list[str] = field(default_factory=list)
    n_flavor: int = 0


# ---------------------------------------------------------------- public

def sample_pack(theme: str, profile: ThemeProfile, rng, ledger: Ledger,
                count: int) -> list[CardSkeleton]:
    """Sample `count` skeletons. Rarity caps + novelty re-rolls handled here."""
    slug = profile.slug if hasattr(profile, "slug") else _slug(theme)
    approved_kw = sorted(approved_ids("keywords"))
    approved_tags = sorted(approved_ids("tags"))
    used: dict[str, int] = {}
    out: list[CardSkeleton] = []
    for i in range(count):
        allowed = _allowed_rarities(used)
        cand: CardSkeleton | None = None
        for _ in range(MAX_NOVELTY_ATTEMPTS):
            cand = _sample_card(slug, theme, i, profile, rng, approved_kw,
                                approved_tags, allowed)
            if not ledger.collides(signature_from_skeleton(cand)):
                break
        assert cand is not None
        if ledger.collides(signature_from_skeleton(cand)) \
                and ledger.relaxed_collides(signature_from_skeleton(cand)):
            log.warning("novelty relax: accepted near-duplicate %s "
                        "(narrow theme)", cand.id)
        ledger.add(signature_from_skeleton(cand))
        used[cand.rarity] = used.get(cand.rarity, 0) + 1
        out.append(cand)
    return out


def build_card_raw(sk: CardSkeleton, name: str, flavor: str,
                   flavor_tags: list[str]) -> dict:
    tags = []
    for t in (sk.load_bearing_tag, sk.subject_tag):
        if t and t not in tags:
            tags.append(t)
    tags.extend(flavor_tags)
    return {
        "id": sk.id, "name": name, "set": sk.set, "plane": sk.plane,
        "rarity": sk.rarity, "cost": sk.cost, "type": sk.type,
        "stats": {"atk": sk.stats.get("atk", 0), "def": sk.stats.get("def", 0)},
        "keywords": sk.keywords, "tags": tags,
        "abilities": sk.abilities, "flavor": flavor,
    }


def skeleton_to_card(sk: CardSkeleton, name: str = "…", flavor: str = "",
                     flavor_tags: list[str] | None = None) -> object:
    return parse_card(build_card_raw(sk, name, flavor, flavor_tags or []))


# ---------------------------------------------------------------- internals

def _slug(theme: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", theme.lower()).strip("-")
    return slug or "theme"


def _allowed_rarities(used: dict[str, int]) -> list[str]:
    allowed = list(_RARITY_ORDER)
    if used.get("SUNDERED", 0) >= 1:
        allowed.remove("SUNDERED")
    if used.get("RARE", 0) >= 2:
        allowed.remove("RARE")
    return allowed


def _pick(rng, items: list, affinity: dict, default: float = 0.5):
    if not items:
        return None
    weights = [max(0.0, float(affinity.get(i, default))) for i in items]
    total = sum(weights)
    if total <= 0:
        return rng.choice(items)
    r = rng.uniform(0.0, total)
    acc = 0.0
    for item, w in zip(items, weights):
        acc += w
        if r <= acc:
            return item
    return items[-1]


def _sample_card(slug, theme, index, profile, rng, approved_kw, approved_tags,
                 allowed_rarities) -> CardSkeleton:
    rarity = _pick(rng, allowed_rarities, profile.rarity_affinity)
    cap = _SCORE_CAP.get(rarity, 8)
    sk: CardSkeleton | None = None
    for _ in range(BUDGET_ATTEMPTS):
        sk = _build_skeleton(slug, theme, index, profile, rng, approved_kw,
                             approved_tags, rarity)
        if budget_score(skeleton_to_card(sk)) <= cap:
            break
    assert sk is not None
    if budget_score(skeleton_to_card(sk)) > cap:
        _downgrade_to_budget(sk, cap, rng, approved_tags, profile)
    sk.cost = suggested_cost(skeleton_to_card(sk))
    return sk


def _downgrade_to_budget(sk, cap, rng, approved_tags, profile) -> None:
    """Cut content until the skeleton fits `cap`, never re-rolling stats.

    Ladder: drop the second ability first (the RARE/SUNDERED overflow case),
    then keywords, then stats, then shave the remaining ability's values.
    If even that can't land under the cap the card is accepted over-budget
    with a detailed log line (the true floor — reachable only if the budget
    cost table changes under us).
    """
    original = budget_score(skeleton_to_card(sk))
    cuts: list[str] = []
    while budget_score(skeleton_to_card(sk)) > cap:
        if len(sk.abilities) > 1:
            # the subject is the card's identity — when it carries a mechanic
            # (abilities[0]) keep it fixed through the ladder
            force = sk.subject_tag if tag_mechanic(sk.subject_tag) else None
            sk.abilities = sk.abilities[:1]
            _assign_tags(sk, _load_bearing(sk.abilities, approved_tags), rng,
                         approved_tags, profile, ctype=sk.type,
                         force_subject=force)
            cuts.append("2nd-ability")
        elif sk.keywords:
            _drop_costliest_keyword(sk)
            cuts.append("keyword")
        elif sk.type == "BROADCAST" and (sk.stats["def"] > 0 or sk.stats["atk"] > 0):
            if sk.stats["def"] > 0:
                sk.stats["def"] -= 1
                cuts.append("def")
            else:
                sk.stats["atk"] -= 1
                cuts.append("atk")
        elif _shave_ability_value(sk):
            cuts.append("value")
        else:
            break
    final = budget_score(skeleton_to_card(sk))
    if final > cap:
        ab = sk.abilities[0] if sk.abilities else {}
        log.warning(
            "budget accept-over rarity=%s type=%s effect=%s trigger=%s "
            "target=%s scaling=%s value=%s value_def=%s keywords=%s "
            "stats=%s score=%d cap=%d",
            sk.rarity, sk.type, ab.get("effect"), ab.get("trigger"),
            ab.get("target"), ab.get("scaling"), ab.get("value"),
            ab.get("value_def"), sk.keywords, sk.stats, final, cap,
        )
    else:
        log.warning("budget clamp rarity=%s score=%d cap=%d cuts=%s "
                    "-> final_score=%d", sk.rarity, original, cap,
                    ",".join(cuts), final)


def _drop_costliest_keyword(sk) -> None:
    costly = sorted(sk.keywords, key=lambda k: -_KEYWORD_COST.get(k, 0))
    if _KEYWORD_COST.get(costly[0], 0) <= 0:
        sk.keywords = []  # only free keywords remain — drop them all
    else:
        sk.keywords.remove(costly[0])


def _shave_ability_value(sk) -> bool:
    """Reduce the surviving ability's value/value_def by one step.

    Returns False when there is nothing left to shave (fixed-value effects,
    X-scaling abilities, or already at the floor).
    """
    if not sk.abilities:
        return False
    ab = sk.abilities[0]
    if ab.get("value", 0) > 1:
        ab["value"] = ab["value"] - 1
        return True
    if ab.get("value_def", 0) > 0:
        ab["value_def"] = ab["value_def"] - 1
        return True
    return False


def _build_skeleton(slug, theme, index, profile, rng, approved_kw,
                    approved_tags, rarity) -> CardSkeleton:
    ctype = _pick(rng, ["BROADCAST", "TRACK", "LOOP"], profile.type_affinity)
    keywords = _sample_keywords(rng, ctype, approved_kw, profile.keyword_affinity)
    abilities = _sample_abilities(rng, ctype, rarity, approved_kw, approved_tags,
                                  profile)
    stats = _sample_stats(rng, ctype, rarity)
    sk = CardSkeleton(
        id=f"{slug}_{index + 1:03d}", set=slug, plane=theme,
        type=ctype, rarity=rarity, cost=0, keywords=keywords, stats=stats,
        abilities=abilities, n_flavor=rng.choice([0, 0, 1, 1]),
    )
    _assign_tags(sk, _load_bearing(abilities, approved_tags), rng,
                 approved_tags, profile, ctype=ctype)
    _inject_subject_mechanic(sk)
    return sk


def _inject_subject_mechanic(sk) -> None:
    """A mechanical subject tag becomes the card's primary (identity) ability.

    The mechanic is only attached when the card's type can legally host its
    trigger + effect; the reminder is derived from the same mechanic, so a
    card that carries the tag actually does what the tag promises.
    """
    if not sk.subject_tag:
        return
    mech = tag_mechanic(sk.subject_tag)
    if not mech:
        return
    if mechanic_legal(mech, sk.type):
        sk.abilities.insert(0, dict(mech))
    else:
        log.warning("tag mechanic skipped for %s (#%s illegal on %s)",
                    sk.id, sk.subject_tag, sk.type)


def _assign_tags(sk, load_tag, rng, approved_tags, profile, ctype=None,
                 force_subject=None) -> CardSkeleton:
    """Set load-bearing + subject tags and the offered flavor menu.

    A load-bearing card's subject *is* its load-bearing tag; otherwise the
    subject is a seeded draw from the card's own affinity-weighted menu (so a
    pack clusters on the theme's top few tags without collapsing the pool).
    Mechanical tags that can't legally attach to this card type are skipped
    for subject selection, so a subject never promises a mechanic the card
    can't have. The offered menu excludes the subject, so the humanizer never
    re-picks it.
    """
    menu = _flavor_menu(rng, approved_tags, profile.tag_affinity, load_tag)
    sk.load_bearing_tag = load_tag
    subject = force_subject
    if subject is None:
        if load_tag:
            subject = load_tag
        elif menu:
            subject = _pick_subject(rng, menu, ctype, profile.tag_affinity)
    sk.subject_tag = subject
    sk.flavor_tag_menu = [t for t in menu if t != subject] if subject else menu
    return sk


def _pick_subject(rng, menu: list[str], ctype: str | None,
                  affinity: dict) -> str:
    """Affinity-weighted subject draw, skipping mechanical tags illegal on
    this type. Weighted (not uniform) so a theme's own tags dominate the
    card's identity without ever being guaranteed."""
    legal = [t for t in menu if not _mechanic_illegal(t, ctype)] \
        if ctype else list(menu)
    return _pick(rng, legal, affinity) if legal else rng.choice(menu)


def _mechanic_illegal(tag_id: str, ctype: str) -> bool:
    mech = tag_mechanic(tag_id)
    return bool(mech) and not mechanic_legal(mech, ctype)


def _sample_keywords(rng, ctype, approved_kw, affinity) -> list[str]:
    allow = _KEYWORDS_BY_TYPE.get(ctype)
    if not allow:
        return []
    pool = [k for k in approved_kw if k in allow]
    n = rng.choice([0, 0, 1, 1, 2]) if ctype == "BROADCAST" \
        else rng.choice([0, 0, 1])
    chosen: list[str] = []
    for _ in range(n):
        if not pool:
            break
        kw = _pick(rng, pool, affinity)
        if kw is None:
            break
        pool.remove(kw)
        chosen.append(kw)
    return chosen


def _sample_abilities(rng, ctype, rarity, approved_kw, approved_tags,
                      profile) -> list[dict]:
    n_ab = 1
    if ctype == "TRACK":
        n_ab = 1
    elif rarity in ("RARE", "SUNDERED"):
        n_ab = 2
    elif rng.random() < 0.35:
        n_ab = 2
    triggers = _TRIGGERS_BY_TYPE[ctype]
    effects = _EFFECTS_BY_TYPE[ctype]
    return [_sample_ability(rng, triggers, effects, approved_kw, approved_tags,
                            profile) for _ in range(n_ab)]


def _sample_ability(rng, triggers, effects, approved_kw, approved_tags,
                    profile) -> dict:
    trigger = _pick(rng, triggers, profile.trigger_affinity)
    effect = _pick(rng, effects, profile.effect_affinity)
    target = _pick(rng, _EFFECT_TARGETS.get(effect, ["SELF"]),
                   profile.target_affinity)
    scaling = _pick_scaling(rng, bool(approved_tags))
    value, value_def = _value_for(rng, effect, scaling)
    ab = {"trigger": trigger, "effect": effect, "target": target,
          "scaling": scaling, "value": value, "value_def": value_def}
    if scaling == "X_COUNT_OF_TAG_ON_BOARD" and approved_tags:
        ab["tag"] = _pick(rng, approved_tags, profile.tag_affinity)
    if effect == "GRANT_KEYWORD" and approved_kw:
        kw = _pick(rng, approved_kw, profile.keyword_affinity)
        if kw is not None:
            ab["keyword"] = kw
    if trigger == "ON_ANY_BROADCAST_PLAYED" and approved_tags \
            and rng.random() < 0.30:
        tag = _pick(rng, approved_tags, profile.tag_affinity)
        if tag is not None:
            ab["condition"] = {"has_tag": tag}
    return ab


def _pick_scaling(rng, tags_available: bool) -> str:
    opts = [("FLAT", 0.72), ("X_TURN_NUMBER", 0.12)]
    if tags_available:
        opts.append(("X_COUNT_OF_TAG_ON_BOARD", 0.16))
    return _pick(rng, [o[0] for o in opts], dict(opts))


def _value_for(rng, effect: str, scaling: str) -> tuple[int, int]:
    if scaling != "FLAT":
        return (1, 0)
    lo, hi = _VALUE_RANGE.get(effect, (1, 1))
    value = rng.randint(lo, hi)
    value_def = rng.randint(0, value) if effect == "BUFF_STAT" else 0
    return value, value_def


def _sample_stats(rng, ctype: str, rarity: str) -> dict:
    if ctype != "BROADCAST":
        return {"atk": 0, "def": 0}
    boost = 1 if rarity in ("RARE", "SUNDERED") else 0
    return {"atk": min(8, rng.randint(1, 3 + boost)),
            "def": min(8, rng.randint(1, 5 + boost))}


def _load_bearing(abilities: list[dict], approved_tags) -> str | None:
    for ab in abilities:
        cond = ab.get("condition") or {}
        tag = cond.get("has_tag")
        if tag in approved_tags:
            return tag
    return None


def _flavor_menu(rng, approved_tags, affinity, exclude: str | None) -> list[str]:
    pool = [t for t in approved_tags if t != exclude]
    menu: list[str] = []
    work = list(pool)
    while work and len(menu) < 8:
        tag = _pick(rng, work, affinity)
        if tag is None:
            break
        work.remove(tag)
        menu.append(tag)
    return menu
