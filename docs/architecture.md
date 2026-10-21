# Architecture

The repo is two halves over one rules core:

```
sunder/
  primitives.py   closed vocabularies (the whole grammar)
  schema.py       Card/Ability dataclasses + parse_card() validation
  engine.py       data-driven ability resolver ("the interpreter")
  game.py         GameState: zones, turn loop, combat, win check
  keywords.py     13-keyword registry (display names + reminder text)
  lore.py         rules-text templating, reskin vocabulary
  budget.py       clause-scored cost model
  state.py        snapshot serializer (viewer-aware) for the web UI
  ai.py           greedy heuristic opponent
  registry.py     tag + keyword governance (proposed → approved/rejected)
  codex.py        CLI card browser
  cards/          JSON sets + registry.json
  server/         FastAPI app (REST + WS) + uvicorn launcher
    match.py      MatchRoom + seats (HumanSeat / BotSeat), clocks
    lobby.py      versus rooms: invite codes, seat tokens, resume
  gen/            LLM card-generation pipeline
web/              React + TypeScript + Vite SPA (served from web/dist)
tests/            ~20 Python modules + vitest suite in web/
```

## Design principles

**1. Closed grammar — no card is ever special-cased.**
`engine.py` executes *any* schema-conforming card by reading its data.
Everything an ability can possibly do comes from closed enums in
`primitives.py`: 3 card types, 4 rarities, **9 triggers, 13 effects,
8 targets, 6 scalings**. Adding a new generated card never means editing the
engine; growing the *game* means adding enum values (a documented, tested
extension path).

**2. The LLM never invents mechanics.**
Generation (see [generation.md](generation.md)) lets the model pick weights,
names, and flavor — inside vocabulary tables. Legality lives in
`sunder/gen/legality.py`, mirrored between the sampler and the validation
tables, so every generated card is schema-valid, in-budget, and executable
by the same engine that runs starter cards.

**3. Clients are dumb.**
The server owns legality (`is_playable`, `attack_targets`,
`legal_targets`, `legal_track_targets`) and pre-computes it into each
snapshot (`state.py`). Opponent hands are counts; hidden B-SIDEs stay
masked in every view but their owner's.

**4. Deterministic and seed-driven.**
All randomness flows from one `random.Random(seed)` on the GameState
(machine-per-instance makes shards reproducible); AI-vs-AI matches finish
and replay identically across seeds (test-guaranteed).

## Core data flow

```
Card JSON ──parse_card()──▶ Card ──▶ CardInstance (zone-aware runtime copy)
                                   │
      turn event ──▶ game.py ──▶ engine.fire / resolve_ability ──▶ log + history
                                     │
                             state.snapshot(gs, viewer) ──▶ web client
```

* `CardInstance` (`game.py`) wraps a `Card` with runtime state: serial, zone,
  base + permanent buffs, `damage_taken`, keyword-related flags
  (`filter_spent`, `mask_broken`, `fuse_ticks`), `pending_doubles`
  (`DOUBLE_NEXT_TRIGGER`), `trigger_counts` (X_TIMES scaling), `hidden`
  (B-SIDE).
* `engine.fire(gs, inst, trigger, event, chosen)` resolves all matching
  abilities of one card (expanded keywords included); `fire_global` sweeps
  both boards; `process_deaths` runs to quiescence after every step.
* Tracks resolve through a **pre-scan stack** (`last_track_stack`): the
  server looks for `ON_CAST_TRACK`/`COUNTER_TRACK` before resolving, so
  counter effects can CUT a track mid-cast; `resolving` guards re-entrancy
  (`COPY_LAST_TRACK` can't copy itself).

## Match rooms

`game.py` has no notion of sockets or players-as-people; the server wraps
each `GameState` in a `MatchRoom` with one **seat** per station. Seats are
pluggable — `HumanSeat` (a WebSocket) or `BotSeat` (the heuristic AI run
as a background task) — so practice and versus share one code path. The
room validates every action against the sender's station, serializes
mutations behind one lock, and broadcasts a per-viewer snapshot to each
seat. Versus rooms add a turn clock, AFK strikes and a disconnect grace;
the in-memory `Lobby` pairs connections via invite codes. Details:
[multiplayer.md](multiplayer.md).

Game end is always `winner` (0/1) + `end_reason`; use `gs.game_over`,
never truthiness of `winner` (station 0 winning is `winner == 0`).

## Snapshot masks

* Viewer's own board: full — `atk`/`def` are *effective* values, `damage`,
  fuse progress, rules text.
* Hidden B-SIDE (opponent view): name `???`, type `None`, only the B-SIDE
  keyword. The owner additionally sees its resolved rules text.
* Rival hand: a count only.
* Log/history text: a hidden B-SIDE is named "Hidden B-SIDE" until revealed
  (`CardInstance.label()`), so damage/death lines can't leak it.

## Resource model

`budget.py` derives a suggested cost from clause scores — every effect has a
weighted value (repeating triggers ×3, group targets ×2, delayed FUSE payoff
×0.5); `suggested_cost = round(score / 2)`. The fairness check allows a
deviation that widens with rarity (COMMON 2 … SUNDERED 4). Generation goes
one step further and *sets* cost = suggestion, clamped by a per-rarity
budget cap (see [generation.md](generation.md)).

## Governance

`registry.py` owns what exists: tags (6 approved starters + whatever the
review queue accumulates) and the 13 keywords (auto-synced from
`keywords.py`). Lifecycle is `proposed → approved` or `rejected`; approved
tags are the only ones cards and the sampler may use; a tag may carry a
structured `mechanic` that the sampler can load onto carrier cards.
All registry writes share one lock (web generation runs in asyncio worker
threads) and persist atomically to `cards/registry.json`.
