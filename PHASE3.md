# Phase 3 — Web UI (React + TypeScript)

Goal: replace the Textual TUI with a real browser UI — mouse + keyboard — over the
same deterministic engine, plus a web codex. Single-player human-vs-AI.

## Deliverables

1. **Backend** (`sunder/state.py`, `sunder/server/`):
   - `state.py` — pure `snapshot(gs)` serializer: players (signal, bandwidth), board
     cards (effective atk/def, damage, fuse, B-SIDE `hidden` masking), hand cards with
     `is_playable` / `needs_target` / `legal_targets`, per-creature `attack_targets`,
     turn/current/winner/status/log. Everything the UI needs, computed server-side.
   - `server/app.py` — FastAPI: `GET /api/cards` (codex data), `GET /api/health`,
     `WS /ws` (start / restart / play / attack / end_turn / ping), full state snapshot
     replied after every action; serves the built SPA from `web/dist` when present.
   - `server/serve.py` — uvicorn launcher (`python -m sunder`).
2. **Frontend** (`web/` — Vite + React 18 + TypeScript):
   - Battle view: rival station + your station (signal bars, bandwidth, board), clickable
     hand, colored log, status bar, hover inspector (full rules + flavor), end-of-game
     overlay with Play again.
   - Card faces with cost badges, type accents, rarity borders, keywords; B-SIDE renders
     as a mystery card; damage-flash and reveal animations.
   - Interaction: click to air cards (CHOSEN Tracks enter targeting mode — legal targets
     pulse), click creature → click target or RIVAL TRANSMITTER to attack; keys `1–9`
     air hand card, `e` end turn, `c` codex, `Esc` cancel.
   - Codex view: live search over `/api/cards`.
3. **Cleanup**: Textual TUI and its dependency removed; `python -m sunder` now boots the
   web server; `python -m sunder cli` keeps the headless print battle.

## Run

```
npm --prefix web install
npm --prefix web run build          # or: npm --prefix web run dev (Vite proxy)
python -m sunder                    # → http://localhost:8000
```

## Verification

`pytest` (incl. `test_state.py`, `test_web.py` WebSocket round-trips) ·
`npm --prefix web test` (Vitest + Testing Library: App interaction/keys) ·
`npm --prefix web run build` · live smoke: start server, play a full match.

## Out of scope

LLM generation (P4), economy/collection/stream/deck-builder (P5).
