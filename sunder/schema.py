"""SUNDER — card schema: dataclasses + validation.

Cards are plain data. Any conforming card is executable by the engine.
`value_def` is the defence half of a BUFF_STAT (+atk/+def); `count_type`
feeds X_COUNT_OF_TYPE_ON_BOARD when it differs from the source card's type.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .primitives import CardType, Effect, Rarity, Scaling, Target, Trigger

_KNOWN_KEYWORDS = {
    "LOUD", "RUSH", "ECHO", "AMP", "CARRIER", "BEACON", "DISTORT",
    "FILTER", "DRAIN", "FEEDBACK", "MASKED", "FUSE", "B_SIDE",
}


@dataclass
class Ability:
    trigger: Trigger
    effect: Effect
    target: Target
    scaling: Scaling = Scaling.FLAT
    value: int = 0
    value_def: int = 0
    condition: dict | None = None
    count_type: CardType | None = None
    keyword: str | None = None      # GRANT_KEYWORD payload
    ref: int | None = None          # stable ability index for THIS_TRIGGERED counts


@dataclass
class Card:
    id: str
    name: str
    set: str
    plane: str
    rarity: Rarity
    cost: int
    type: CardType
    abilities: list[Ability] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    atk: int = 0
    def_: int = 0
    fuse: int | None = None
    flavor: str = ""

    def rules_text(self) -> str:
        from .lore import remind

        parts = []
        if self.keywords:
            parts.append(" ".join(remind(k) for k in self.keywords))
        for ab in self.abilities:
            parts.append(describe_ability(self, ab))
        text = " ".join(p for p in parts if p)
        return text or "(no text)"


# ---------------------------------------------------------------- validation

class SchemaError(ValueError):
    pass


def _enum(name: str, cls, value: str):
    try:
        return cls(value)
    except ValueError:
        raise SchemaError(f"{name}: unknown value {value!r} for {cls.__name__}")


def _as_enum_list(name: str, cls, values):
    if values is None:
        return []
    if not isinstance(values, list):
        raise SchemaError(f"{name}: expected a list, got {values!r}")
    return [_enum(name, cls, v) for v in values]


def parse_ability(raw: dict, index: int) -> Ability:
    try:
        trigger = _enum("trigger", Trigger, raw["trigger"])
        effect = _enum("effect", Effect, raw["effect"])
        target = _enum("target", Target, raw["target"])
        scaling = _enum("scaling", Scaling, raw.get("scaling", "FLAT"))
    except KeyError as exc:
        raise SchemaError(f"ability {index}: missing key {exc.args[0]!r}")

    count_type = None
    if raw.get("count_type"):
        count_type = _enum("count_type", CardType, raw["count_type"])

    return Ability(
        trigger=trigger,
        effect=effect,
        target=target,
        scaling=scaling,
        value=int(raw.get("value", 0)),
        value_def=int(raw.get("value_def", 0)),
        condition=raw.get("condition"),
        count_type=count_type,
        keyword=raw.get("keyword"),
        ref=index,
    )


def parse_card(raw: dict) -> Card:
    try:
        ctype = _enum("type", CardType, raw["type"])
        rarity = _enum("rarity", Rarity, raw["rarity"])
    except KeyError as exc:
        raise SchemaError(f"card {raw.get('id')}: missing key {exc.args[0]!r}")

    stats = raw.get("stats") or {}
    abilities = [parse_ability(a, i) for i, a in enumerate(raw.get("abilities", []))]

    if not 0 <= len(abilities) <= 3:
        raise SchemaError(f"card {raw.get('id')}: {len(abilities)} abilities (need 0–3)")

    keywords = raw.get("keywords") or []
    for k in keywords:
        if k not in _KNOWN_KEYWORDS:
            raise SchemaError(f"card {raw.get('id')}: unknown keyword {k!r}")

    if ctype is CardType.BROADCAST:
        atk = int(stats.get("atk", 0))
        def_ = int(stats.get("def", 0))
    else:
        atk = def_ = 0

    return Card(
        id=str(raw["id"]),
        name=str(raw["name"]),
        set=str(raw.get("set", "")),
        plane=str(raw.get("plane", "")),
        rarity=rarity,
        cost=int(raw["cost"]),
        type=ctype,
        abilities=abilities,
        keywords=keywords,
        atk=atk,
        def_=def_,
        fuse=int(raw["fuse"]) if raw.get("fuse") is not None else None,
        flavor=str(raw.get("flavor", "")),
    )


def load_card_file(path: str | Path) -> list[Card]:
    cards = json.loads(Path(path).read_text())
    return [parse_card(raw) for raw in cards]


# ---------------------------------------------------------------- display

def describe_ability(card: Card, ab: Ability) -> str:
    """Deterministic rules text from the ability tuple (lore-flavoured)."""
    num = _num(card, ab)
    trig = _TRIGGER_WORDS.get(ab.trigger, ab.trigger.value)
    target = _TARGET_WORDS.get(ab.target, ab.target.value)
    effect = _EFFECT_WORDS.get(ab.effect, ab.effect.value)
    return f"{trig}: {effect} {num} to {target}."


def _num(card: Card, ab: Ability) -> int:
    return _scaled_value(card, ab, ab.value)


def _scaled_value(card: Card, ab: Ability, base: int) -> int:
    s = ab.scaling
    if s is Scaling.X_TURN_NUMBER:
        return base  # placeholder — live value applied by the engine
    if s is not Scaling.FLAT:
        return base
    return base


_TRIGGER_WORDS = {
    Trigger.ON_PLAY: "When this enters play",
    Trigger.ON_ATTACK: "When this attacks",
    Trigger.ON_DEATH: "When this goes silent",
    Trigger.ON_TURN_START: "At the start of your turn",
    Trigger.ON_TURN_END: "At the end of your turn",
    Trigger.ON_CAST_TRACK: "When a Track is played",
    Trigger.ON_ANY_BROADCAST_PLAYED: "Whenever a Broadcast is aired",
    Trigger.ON_FUSE_EXPIRED: "When the fuse expires",
    Trigger.STATIC: "Always on",
}

_TARGET_WORDS = {
    Target.SELF: "self",
    Target.ENEMY_FACE: "the rival station",
    Target.ENEMY_BROADCAST: "an enemy Broadcast",
    Target.ALL_ENEMY_BROADCASTS: "all enemy Broadcasts",
    Target.ALL_YOUR_BROADCASTS: "your Broadcasts",
    Target.ALL_BROADCASTS: "all Broadcasts",
    Target.RANDOM: "a random Broadcast",
    Target.CHOSEN: "a chosen Broadcast",
}

_EFFECT_WORDS = {
    Effect.DEAL_DAMAGE: "deal {n} Noise",
    Effect.GAIN_LIFE: "boost your Signal by {n}",
    Effect.DRAW_CARD: "cue {n}",
    Effect.BUFF_STAT: "+{n}/+{nd}",
    Effect.SUMMON_TOKEN: "summon {n} 1/1 Echo",
    Effect.RETURN_FROM_DISCARD: "return {n} card from Static",
    Effect.COPY_LAST_TRACK: "replay the last Track {n} time(s)",
    Effect.COUNTER_TRACK: "cut the Track",
    Effect.DESTROY: "jam {t}",
    Effect.GRANT_KEYWORD: "grant {kw} to {t}",
    Effect.DOUBLE_NEXT_TRIGGER: "double {t}'s next trigger",
}


def keyword_display(key: str) -> str:
    from .keywords import KEYWORD_REGISTRY
    return KEYWORD_REGISTRY.get(key, (key, "")).display
