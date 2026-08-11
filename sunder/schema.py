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


def _approved_tags() -> set[str]:
    """Approved tag ids (governance gate for tag-bearing cards)."""
    from .registry import approved_tags
    return set(approved_tags())


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
    tag: str | None = None          # X_COUNT_OF_TAG_ON_BOARD payload
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
    tags: list[str] = field(default_factory=list)
    atk: int = 0
    def_: int = 0
    fuse: int | None = None
    flavor: str = ""

    def rules_text(self) -> str:
        from .lore import rules_text as _rules_text
        return _rules_text(self)


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
        tag=raw.get("tag"),
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

    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        raise SchemaError(f"card {raw.get('id')}: tags must be a list")
    if len(tags) > 4:
        raise SchemaError(f"card {raw.get('id')}: {len(tags)} tags (need 0–4)")
    if len(set(tags)) != len(tags):
        raise SchemaError(f"card {raw.get('id')}: duplicate tags")
    for t in tags:
        if not isinstance(t, str) or not t:
            raise SchemaError(f"card {raw.get('id')}: malformed tag {t!r}")
        if t not in _approved_tags():
            raise SchemaError(f"card {raw.get('id')}: unknown tag {t!r}")

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
        tags=tags,
        atk=atk,
        def_=def_,
        fuse=int(raw["fuse"]) if raw.get("fuse") is not None else None,
        flavor=str(raw.get("flavor", "")),
    )


def load_card_file(path: str | Path) -> list[Card]:
    cards = json.loads(Path(path).read_text())
    return [parse_card(raw) for raw in cards]

