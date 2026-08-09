# Phase 2 — B-SIDE completion + Textual TUI

> Superseded: P3 replaced the Textual TUI with a web app (`web/`). This file
> documents P2's engine work (still live) and its now-removed TUI. Run the
> game with `python -m sunder` → browse to localhost:8000.

Goal: make the hidden B-SIDE mechanic fully real (reveal, untargetability, reveal UX)
and replace the print CLI with a clickable Textual interface — human vs the heuristic AI.
Generation and economy remain P3/P4.

## Deliverables

1. **Engine — B-SIDE completion** (`engine.py`, `game.py`):
   - Playing a `B_SIDE` card sets `hidden=True`.
   - `fire()` reveals a hidden card the moment one of its listed triggers would fire
     (condition ok) → logs `Station N reveals a B-SIDE: <name>` → resolves normally.
   - Hidden cards are untargetable: excluded from direct targeting
     (`_collect_targets`, `legal_attack_targets`, `legal_track_targets`); mass effects
     still hit them and they die hidden without revealing.
   - New condition key `not_self` (e.g. ON_ANY that ignores its own airing).

2. **Cards** — two starter B-SIDE loops (replacing Encore! / Sleeper Cache):
   - **Midnight Request** (Neon, Common Loop, 2): *"When a Broadcast is aired, deal
     1 Noise to the rival station."* — reveals the first time another Broadcast airs.
   - **Static Replay** (Cinderworks, Uncommon Loop, 2): *"At the end of your turn,
     return the last Track from Static to your hand."* — reveals at first turn end.

3. **game.py validation helpers** (shared by TUI and future AI work):
   `is_playable(inst)` and `legal_track_targets(inst)`.

4. **Textual TUI** (`tui.py`):
   - Battle screen: title/turn, dual Signal + Bandwidth readouts, enemy board
     (B-SIDE renders as `??? [B-SIDE]`), your board, clickable hand, log panel,
     End Turn / Codex / Quit buttons, status line.
   - Mouse + keys: click a hand card to air it (CHOSEN Tracks enter target mode with
     legal targets highlighted); click a creature then a target to attack; `e` end turn,
     `c` codex, `q` quit, `Esc` cancel.
   - Codex screen: live search over cards reusing the CLI codex.
   - `python -m sunder` launches the TUI; `sunder.cli` stays for headless use.
   - Dependency: `textual` (added to `pyproject.toml`).

5. **Docs**: this file; PHASE1.md reconciled (final roster, layout, CLI commands,
   corrected B-SIDE split); DESIGN.md §11 roadmap updated.

## Verification

`pytest` green (incl. `test_b_side.py` + `test_tui.py` smoke via `App.run_test`) ·
manual TUI match vs the AI · AI-vs-AI determinism unchanged.

## Out of scope

LLM generation (P3), economy/collection/stream/deck-builder (P4).
