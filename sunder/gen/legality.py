"""SUNDER — legality tables + mechanic validation for the generation system.

The sampler and the profile prompt both need to know which trigger/effect/
target/scaling combinations are legal for each card type. Keeping the tables
here (instead of in `sampler.py`) lets the profile step validate LLM-proposed
mechanics against exactly the same rules the sampler applies.

`validate_mechanic` is structural (enum membership, legal target for the
effect, value ranges, scaling payloads). Reference checks that need the
registry (a `tag`/`keyword`/`condition` must be an approved id) live in the
caller so this module stays registry-free.
"""

from ..primitives import CardType, Effect, Scaling, Target, Trigger

_ALL_TRIGGERS = ["ON_PLAY", "ON_ATTACK", "ON_DEATH", "ON_TURN_START",
                 "ON_TURN_END", "ON_CAST_TRACK", "ON_ANY_BROADCAST_PLAYED",
                 "STATIC"]

_TRIGGERS_BY_TYPE = {
    "BROADCAST": _ALL_TRIGGERS,
    "TRACK": ["ON_PLAY"],
    "LOOP": ["STATIC", "ON_TURN_START", "ON_TURN_END",
             "ON_ANY_BROADCAST_PLAYED", "ON_CAST_TRACK"],
}

_EFFECTS_BY_TYPE = {
    "BROADCAST": ["DEAL_DAMAGE", "GAIN_LIFE", "DRAW_CARD", "BUFF_STAT",
                  "SUMMON_TOKEN", "DESTROY", "GRANT_KEYWORD",
                  "DOUBLE_NEXT_TRIGGER", "GAIN_BANDWIDTH"],
    "TRACK": ["DEAL_DAMAGE", "DRAW_CARD", "GAIN_LIFE", "SUMMON_TOKEN",
              "DESTROY", "COPY_LAST_TRACK"],
    "LOOP": ["BUFF_STAT", "GAIN_BANDWIDTH", "GRANT_KEYWORD",
             "RETURN_FROM_DISCARD", "UNCAP_BANDWIDTH"],
}

_EFFECT_TARGETS = {
    "DEAL_DAMAGE": ["ENEMY_FACE", "ENEMY_BROADCAST", "ALL_ENEMY_BROADCASTS",
                    "RANDOM", "CHOSEN"],
    "GAIN_LIFE": ["SELF"],
    "DRAW_CARD": ["SELF"],
    "BUFF_STAT": ["SELF", "ALL_YOUR_BROADCASTS", "CHOSEN"],
    "SUMMON_TOKEN": ["SELF"],
    "RETURN_FROM_DISCARD": ["SELF"],
    "COPY_LAST_TRACK": ["SELF"],
    "COUNTER_TRACK": ["SELF"],
    "DESTROY": ["ENEMY_BROADCAST", "ALL_ENEMY_BROADCASTS", "RANDOM", "CHOSEN"],
    "GRANT_KEYWORD": ["SELF", "ALL_YOUR_BROADCASTS", "CHOSEN"],
    "DOUBLE_NEXT_TRIGGER": ["SELF"],
    "GAIN_BANDWIDTH": ["SELF"],
    "UNCAP_BANDWIDTH": ["SELF"],
}

_KEYWORDS_BY_TYPE = {
    "BROADCAST": ["LOUD", "RUSH", "ECHO", "AMP", "CARRIER", "BEACON",
                  "DISTORT", "FILTER", "DRAIN", "FEEDBACK", "MASKED", "B_SIDE"],
    "TRACK": [],
    "LOOP": ["CARRIER", "B_SIDE"],
}

_VALUE_RANGE: dict[str, tuple[int, int]] = {
    "DEAL_DAMAGE": (1, 4), "GAIN_LIFE": (2, 5), "DRAW_CARD": (1, 2),
    "BUFF_STAT": (1, 2), "SUMMON_TOKEN": (1, 2),
    "RETURN_FROM_DISCARD": (1, 2), "COPY_LAST_TRACK": (1, 2),
    "GAIN_BANDWIDTH": (1, 3),
}

# Every scaling the engine can resolve (`engine._scaled`). The sampler only
# *samples* a subset; LLM mechanics may use any of these.
SCALINGS = [s.value for s in Scaling]

_TRIGGER_VALUES = {t.value for t in Trigger}
_EFFECT_VALUES = {e.value for e in Effect}
_TARGET_VALUES = {t.value for t in Target}
_TYPE_VALUES = {c.value for c in CardType}

_HOSTED_EFFECTS = {e for effs in _EFFECTS_BY_TYPE.values() for e in effs}
_HOSTED_TRIGGERS = {t for trigs in _TRIGGERS_BY_TYPE.values() for t in trigs}


def validate_mechanic(m) -> tuple[bool, str]:
    """Structural validation of a proposed mechanic.

    Returns (ok, reason). Reference checks (approved tag/keyword ids) are the
    caller's job because they need the registry.
    """
    if not isinstance(m, dict):
        return False, "mechanic is not an object"
    trigger = m.get("trigger")
    effect = m.get("effect")
    target = m.get("target")
    scaling = m.get("scaling") or "FLAT"

    if trigger not in _TRIGGER_VALUES:
        return False, f"unknown trigger {trigger!r}"
    if effect not in _EFFECT_VALUES:
        return False, f"unknown effect {effect!r}"
    if scaling not in SCALINGS:
        return False, f"unknown scaling {scaling!r}"
    if target not in _EFFECT_TARGETS.get(effect, ["SELF"]):
        return False, f"target {target!r} is illegal for {effect}"

    # a mechanic must be hostable by at least one card type, else it can
    # never resolve on a real card
    if effect not in _HOSTED_EFFECTS:
        return False, f"effect {effect} has no legal card type"
    if trigger not in _HOSTED_TRIGGERS:
        return False, f"trigger {trigger} has no legal card type"

    if scaling == "X_COUNT_OF_TAG_ON_BOARD" and not m.get("tag"):
        return False, "X_COUNT_OF_TAG_ON_BOARD requires a tag"
    if scaling == "X_COUNT_OF_TYPE_ON_BOARD":
        ct = m.get("count_type")
        if ct is not None and ct not in _TYPE_VALUES:
            return False, f"unknown count_type {ct!r}"
    if effect == "GRANT_KEYWORD" and not m.get("keyword"):
        return False, "GRANT_KEYWORD requires a keyword"

    condition = m.get("condition")
    if condition is not None:
        if not isinstance(condition, dict) or not condition.get("has_tag"):
            return False, "condition must be {\"has_tag\": ...}"

    try:
        value = int(m.get("value", 1))
        value_def = int(m.get("value_def", 0))
    except (TypeError, ValueError):
        return False, "value must be an integer"

    if scaling == "FLAT":
        lo, hi = _VALUE_RANGE.get(effect, (1, 1))
        if not lo <= value <= hi:
            return False, f"value {value} outside {lo}..{hi} for {effect}"
        if not 0 <= value_def <= value:
            return False, f"value_def {value_def} outside 0..{value}"
    return True, ""


def normalize_mechanic(m: dict) -> dict:
    """Coerce a validated mechanic to its stored form (ints, value for X)."""
    out = dict(m)
    if out.get("scaling") in (None, "FLAT"):
        out["scaling"] = "FLAT"
        out["value"] = int(out.get("value", 1))
        out["value_def"] = int(out.get("value_def", 0))
    else:
        out["value"] = 1
        out["value_def"] = 0
    return out


def mechanic_legal(mechanic: dict, ctype: str) -> bool:
    """True when `ctype` may host this mechanic's trigger + effect."""
    return (mechanic.get("trigger") in _TRIGGERS_BY_TYPE.get(ctype, [])
            and mechanic.get("effect") in _EFFECTS_BY_TYPE.get(ctype, []))


def value_range(effect: str) -> tuple[int, int]:
    return _VALUE_RANGE.get(effect, (1, 1))
