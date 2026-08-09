# Phase 1 — Core Engine (no UI, no LLM)  ✅ COMPLETE

Goal: a provably-correct engine that plays a complete duel with the starter set, verified by
tests + a scripted AI-vs-AI match. TUI, generation, and economy come in P2–P4.

## Setup

- Python 3.14 venv at `.venv` in this repo · pytest. (textual added in P2.)
- Layout:

```
sunder/
  primitives.py  schema.py  engine.py  game.py  ai.py
  budget.py  keywords.py  lore.py  cli.py  codex.py  state.py
  server/{__init__.py, app.py, serve.py}  __main__.py
  cards/{neon_frequency.json, cinderworks.json}
web/
  (Vite + React + TypeScript UI — see PHASE3.md)
tests/
  conftest.py  test_schema.py  test_engine.py  test_combat.py  test_keywords.py
  test_budget.py  test_bandwidth.py  test_codex.py  test_b_side.py  test_match.py
  test_state.py  test_web.py
pyproject.toml  DESIGN.md  PHASE1.md  PHASE2.md  PHASE3.md
```

## Deliverables

1. **primitives.py** — closed enums: card types, rarities, triggers, effects, scalings, targets.
2. **schema.py** — Card/Ability dataclasses + validator (schema conformance, known vocabulary).
3. **keywords.py** — seeded registry (13 entries incl. B-SIDE macro) with display + reminder text.
4. **engine.py** — ability resolver: trigger firing, effects, modifiers (DRAIN/DISTORT/FILTER/BEACON),
   FUSE ticking, COPY semantics, token spawning.
5. **game.py** — GameState, zones, turn loop, combat resolution, win/loss, event log.
6. **budget.py** — budget_score(card) → suggested cost + validator tolerance.
7. **ai.py** — heuristic opponent: play best affordable card, Tracks at biggest threat/face,
   attack allocation honoring BEACON.
8. **cards/** — 20 starter cards (roster below), two planes.
9. **cli.py** — print-based battle loop: play, choose targets (CHOSEN), attack, log.
   Commands: `p <n> [face|b<k>]` · `a <n> face|b<k>` · `h` · `b` · `l` · `e` · `q`.
   (P2 added a Textual TUI; P3 replaced the TUI with a web UI — see PHASE3.md.)
10. **tests** — unit coverage + integration (AI vs AI full match).

## Starter roster (all 12 keywords covered)

| # | Card | Type | Cost | Stats | Rules | Rarity |
|---|---|---|---|---|---|---|
| 1 | Vinyl Golem | B | 4 | 3/5 | ON_DEATH: +3 Signal | C |
| 2 | Neon Drifter | B | 3 | 3/2 | RUSH | C |
| 3 | Disco Inferno | T | 2 | — | deal 3 Noise (CHOSEN) | U |
| 4 | Roller Rink Serenade | B | 2 | 1/1 | ON_TURN_END: +1/+1 self | C |
| 5 | Static Bloom | L | 3 | — | CARRIER: your Broadcasts +1/+0 | U |
| 6 | Laser Harp | B | 4 | 3/4 | DRAIN | R |
| 7 | The Mixer | B | 5 | 3/4 | AMP | R |
| 8 | Midnight Request | L | 2 | — | B-SIDE: when a Broadcast is aired, deal 1 Noise to rival | C |
| 9 | Echo Chamber | B | 6 | 2/6 | ECHO: summon 1/1 on death | U |
| 10 | Final Wave | T | 5 | — | deal 5 to all enemy Broadcasts + rival | S |
| 11 | Scrapheap | B | 1 | 0/3 | BEACON | C |
| 12 | Cinder Hound | B | 2 | 2/2 | LOUD | C |
| 13 | Molten Core | T | 3 | — | deal 2 Noise to all enemy Broadcasts | U |
| 14 | Covert Recorder | B | 2 | 2/2 | MASKED | C |
| 15 | Furnace Vent | L | 4 | — | ON_TURN_START: deal 1 Noise to rival | U |
| 16 | Juggernaut | B | 6 | 5/5 | FEEDBACK | R |
| 17 | Filtered Capacitor | B | 3 | 1/4 | FILTER | U |
| 18 | Jamming Tower | B | 3 | 2/4 | DISTORT | U |
| 19 | The Foundry Never Sleeps | B | 3 | 1/1 | +X per Broadcast aired (TIMES TRIGGERED) | R |
| 20 | Static Replay | L | 2 | — | B-SIDE: ON_TURN_END return last Track from Static | U |

## B-SIDE (P1/P2 split)

P1: the `hidden` flag on CardInstance (hidden board state) + the registry entry.
P2 (PHASE2.md): reveal-on-trigger, untargetability while hidden, `not_self`
condition, reveal UX in the TUI, and the two starter B-SIDE loops above.

## Verification

`pytest` green · scripted AI-vs-AI match runs to completion with deterministic results ·
replays give identical outcomes (seed-aware).

## Out of scope

TUI, LLM generation, economy/collection, stream, deck-builder UI.
