"""SUNDER — LLM-assisted card generation (doc §1–3).

Pipeline: theme profile (cached, clamped, fallback-marked) → deterministic
seeded sampler (rarity/type/keywords/ability tuple/cost + load-bearing tag +
flavor-tag menu) → novelty ledger (codex-seeded) → one batched humanizer
call per pack (names/flavour/menu picks) → schema-valid card dicts.

`mode` reports `llm` when the humanizer ran, `deterministic` on any fallback.
"""

from __future__ import annotations

import json
import random
import sys
from typing import Any

from ..schema import parse_card
from .client import LLMClient, LLMError
from .humanizer import deterministic_fill, humanize_pack
from .ledger import Ledger
from .profile import profile_for
from .sampler import build_card_raw, sample_pack

MAX_COUNT = 10


def generate_pack(theme: str, count: int = 5, seed: int | None = None,
                  client=None, use_llm: bool = True) -> dict[str, Any]:
    """Return `{cards, theme, seed, mode}` for one pack of `count` cards."""
    theme = (theme or "").strip()
    if not theme:
        raise ValueError("theme is required")
    count = max(1, min(int(count), MAX_COUNT))
    rng = random.Random(seed)
    client = client or LLMClient()
    profile = profile_for(theme, client, use_llm=use_llm)
    ledger = Ledger.seeded()
    skeletons = sample_pack(theme, profile, rng, ledger, count)

    mode = "deterministic"
    if use_llm and not profile.fallback:
        try:
            human = humanize_pack(theme, profile, skeletons, client)
            mode = "llm"
        except LLMError:
            human = deterministic_fill(skeletons, profile)
            mode = "deterministic"
    else:
        human = deterministic_fill(skeletons, profile)

    cards = [
        build_card_raw(sk, h["name"], h["flavor"], h["flavor_tags"])
        for sk, h in zip(skeletons, human)
    ]
    for c in cards:
        parse_card(c)  # guarantee schema-valid output
    return {"cards": cards, "theme": theme, "seed": seed, "mode": mode}


def cli_main(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="sunder gen",
                                description="Generate a SUNDER card pack.")
    p.add_argument("theme")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--json", action="store_true", help="print raw card JSON")
    p.add_argument("--no-llm", action="store_true", help="deterministic only")
    args = p.parse_args(argv)

    result = generate_pack(args.theme, count=args.count, seed=args.seed,
                           use_llm=not args.no_llm)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    from ..budget import check_budget
    from ..lore import rules_text

    print(f"THEME: {result['theme']}   seed={result['seed']}   "
          f"mode={result['mode']}")
    for c in result["cards"]:
        parsed = parse_card(c)
        stats = f"{c['stats']['atk']}/{c['stats']['def']}" if \
            c["type"] == "BROADCAST" else " — "
        tags = f"  tags: {', '.join('#' + t for t in c['tags'])}" if c["tags"] else ""
        b = check_budget(parsed)
        print(f"\n{c['id']}  {c['name']}  ({c['rarity']} {c['type']}, "
              f"cost {c['cost']} BW, {stats})")
        if c["keywords"]:
            print("  keywords: " + ", ".join(c["keywords"]))
        if tags:
            print(tags)
        print("  " + rules_text(parsed))
        if c["flavor"]:
            print(f'  "{c["flavor"]}"')
        mark = "OK" if b["ok"] else "OFF-BUDGET"
        print(f"  budget score {b['score']} -> suggested {b['suggested']} "
              f"(cost {b['cost']}) {mark}")
    return 0


if __name__ == "__main__":
    sys.exit(cli_main(sys.argv[1:]))
