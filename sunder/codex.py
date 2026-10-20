"""SUNDER — codex: read cards without opening JSON.

Usage:
  python -m sunder codex                list every card
  python -m sunder codex <query>        card details (name or id, partial ok)
  python -m sunder codex <query> -j     raw card JSON
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from .budget import check_budget
from .keywords import display, remind
from .lore import rules_text
from .primitives import CardType
from .schema import Card, load_card_file

CARDS_DIR = Path(__file__).parent / "cards"


def all_cards() -> list[Card]:
    cards = []
    for f in sorted(CARDS_DIR.glob("*.json")):
        if f.name in ("registry.json", "sleeves.json", "avatars.json"):
            continue
        cards.extend(load_card_file(f))
    return cards


def find(query: str) -> list[Card]:
    q = query.lower()
    return [c for c in all_cards() if q in c.id.lower() or q in c.name.lower()]


def _card_line(c: Card) -> str:
    stats = f"{c.atk}/{c.def_}" if c.type is CardType.BROADCAST else " — "
    return (f"  {c.id:<8} {c.cost:>2} BW  {c.type.value.lower():<9} "
            f"{c.rarity.value:<9} {stats} {c.name}")


def list_all() -> str:
    out = ["SUNDER CODEX"]
    by_set: dict[str, list[Card]] = {}
    for c in all_cards():
        by_set.setdefault(c.set, []).append(c)
    for key, cards in by_set.items():
        out.append(f"\n[{key}]")
        for c in sorted(cards, key=lambda x: x.id):
            out.append(_card_line(c))
    return "\n".join(out)


def format_card(c: Card, live: dict | None = None) -> str:
    lines = [f"{c.name} — {c.rarity.value} {c.type.value.lower()}",
             f"Set {c.set} · {c.id} · Cost {c.cost} BW"]
    if c.type is CardType.BROADCAST:
        lines.append(f"Stats: {c.atk}/{c.def_}")
    if c.keywords:
        lines.append("Keywords: " + ", ".join(f"{display(k)} — {remind(k)}" for k in c.keywords))
    if c.tags:
        lines.append("Tags: " + ", ".join(f"#{t}" for t in c.tags))
    if c.fuse:
        lines.append(f"FUSE: detonates {c.fuse} of your turns after airing.")
    text = rules_text(c, live)
    if text and text != "(no text)":
        lines.append("Ability: " + text)
    if c.flavor:
        lines.append(f'"{c.flavor}"')
    b = check_budget(c)
    mark = "OK" if b["ok"] else "OFF-BUDGET"
    lines.append(f"Budget: score {b['score']} -> suggested {b['suggested']} "
                 f"(cost {b['cost']}, tol {b['tolerance']}) {mark}")
    return "\n".join(lines)


def to_json(c: Card) -> str:
    def conv(v):
        if hasattr(v, "value"):
            return v.value
        if isinstance(v, list):
            return [conv(x) for x in v]
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        return v

    return json.dumps({k: conv(v) for k, v in asdict(c).items()}, indent=2, default=str)


def main(argv: list[str]) -> int:
    if not argv:
        print(list_all())
        return 0
    as_json = "-j" in argv or "--json" in argv
    hits = find(argv[0])
    if not hits:
        print(f"codex: no card matches {argv[0]!r}")
        return 1
    for c in hits:
        print(to_json(c) if as_json else format_card(c))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
