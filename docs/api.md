# Server API

`sunder/server/app.py` — FastAPI; interactive docs at **`/api/docs`** when
running. `create_app()` is the testable factory (pass `decks=`, and
`ai_think`/`ai_delay` in seconds for the rival's pacing; `0` = instant, used
by the test suite). The module also exposes a ready `app = create_app()` for
`uvicorn sunder.server.app:app`.

## REST

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/cards` | all cards in the loaded decks (rules text pre-rendered) |
| GET | `/api/keywords` | the 13 keywords (key, display, meaning, kind) |
| GET | `/api/tags` | approved tags only |
| GET | `/api/registry` | full registry — tags + keywords with status/mechanic |
| POST | `/api/registry` | propose a tag/keyword: `{kind, id, definition, reminder?, mechanic?}` → `201` |
| POST | `/api/registry/{kind}/{id}/approve` | approve a review-queue proposal (404 for unknown ids) |
| POST | `/api/generate` | run [generation](generation.md): `{theme, count?, seed?}` |
| GET | `/api/health` | `{"ok": true}` |
| GET | `/api/sleeves` | card-back manifest from `sunder/cards/sleeves.json` |

The built SPA is served at `/` **iff `web/dist` exists** (StaticFiles, html
mode). Rails: dev frontend via `npm run dev` in `web/` proxies `/api` + `/ws`.

## WebSocket `/ws`

One match per connection; client-driven request/response; every mutation
answers with a full `state` snapshot. Protocol:

| Client → | Payload | Effect |
|---|---|---|
| `start` / `restart` | `{seed?}` | new GameState + deal; answers a fresh state |
| `play` | `{hand: <index>, target?: <serial>}` | play hand card (indexes into *your* hand); `target` auto-looked up on the enemy board |
| `attack` | `{board: <index>, target: <serial> \| "face"}` | attack (indexes into your board) |
| `end_turn` | `{turn: <n>}` | guarded — a stale turn number is ignored; then the AI's turn is **staged**: before it speaks (director pause), then one snapshot per AI action, paced by the jitter windows |
| `set_sleeve` | `{sleeve: "<id>"}` | set your station's card back; id validated against the sleeve manifest (invalid → error, no state change); the opponent sees the new sleeve in `players.{}.sleeve` |
| `ping` | — | answers `{"type": "pong"}` |

Server →:

* `{"type": "state", "snapshot": {...}}`
* `{"type": "error", "message": "…"}` — never closes the socket

## Snapshot shape (`state.py`)

Viewer-aware (`viewer = 0` for the human station):

```jsonc
{
  "turn": 1, "current": 0, "phase": "MAIN",
  "winner": null, "status": "Turn 1 | …",
  "viewer": 0,
  "can_act": true,          // winner is None AND it is your turn
  "players": {"0": {...}, "1": {...}},
  "me": {...}, "foe": {...},
  "hand": [ ... ],          // your hand, with legality precomputed
  "log": [ ... ], "log_offset": <count>,
  "history": [ ... ]        // structured play/damage/death events for the UI feed
}
```

Per-player view: `signal`, `max_signal`, `bandwidth`, `max_bandwidth`,
`hand_count` (foe = count only), `static_count`, `playlist_count`, `board`.

Board cards: effective `atk`/`def`, `damage`, fuse progress, `rules`,
`flavor` — plus, **for your own cards**, `can_attack` and the resolved
`attack_targets` (`{"kind":"face"}` / `{"kind":"broadcast","serial":n}`).

Hand cards carry playability: `is_playable`, `needs_target`, and the exact
serial `legal_targets` list where a chosen target is required — the client
never re-implements legality.

Hidden B-SIDEs (opponent view) collapse to `name: "???"`, `type: null`,
keywords `["B_SIDE"]`.

## AI pacing windows (from `create_app`)

* `ai_think` — the rival's first pause after your `end_turn`
  (`uniform(0.8, 1.2) × 1.4 s`)
* `ai_delay` — per-action spacing (`uniform(0.6, 1.3) × 1.4 s`)

`ai.iter_turn` yields exactly once per discrete action, which is what makes
staging (and instant-mode test runs) possible.
