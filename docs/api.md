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
| GET | `/api/avatars` | profile-icon manifest from `sunder/cards/avatars.json` |
| GET | `/api/rooms/{code}` | versus room status: `{code, status: "waiting" \| "live" \| "over"}`, `404` if unknown — never exposes seat tokens ([multiplayer](multiplayer.md)) |

The built SPA is served at `/` **iff `web/dist` exists** (StaticFiles, html
mode). Rails: dev frontend via `npm run dev` in `web/` proxies `/api` + `/ws`.

## WebSocket `/ws`

Every connection is routed through a `MatchRoom` (`sunder/server/match.py`).
A practice match is Human(seat 0) vs `BotSeat`; a versus match is two
`HumanSeat`s created by the lobby (see [multiplayer.md](multiplayer.md)).
Actions are validated against **the sender's seat**, and every mutation is
answered with a `state` to **each** seat, built for that seat's viewpoint.

| Client → | Payload | Effect |
|---|---|---|
| `start` / `restart` | `{seed?}` | new practice match vs the bot (refused while a live PvP match is running) |
| `play` | `{hand: <index>, target?: <serial>}` | play a card from *your* hand; `target` must be one of the card's `legal_targets` (friendly or enemy), else `bad target`. A target sent for an untargeted card is ignored |
| `attack` | `{board: <index>, target: <serial> \| "face"}` | attack (indexes into your board) |
| `end_turn` | `{turn: <n>}` | guarded — a stale turn number or out-of-turn request is ignored (answered with a fresh state). Against the bot, its turn then runs as a background task: a think pause, then one `state` per AI action, paced by the jitter windows |
| `concede` | — | forfeit the current match (`end_reason: "concede"`) |
| `create_room` / `join_room {code}` / `resume {code, token}` / `leave_room` | | versus lobby — see [multiplayer.md](multiplayer.md#protocol) |
| `set_sleeve` | `{sleeve: "<id>"}` | set your station's card back; id validated against the sleeve manifest (invalid → error, no state change); the opponent sees the new sleeve in `players.{}.sleeve` |
| `set_avatar` | `{avatar: "<id>"}` | set your station's profile icon; id validated against `avatars.json` (invalid → error, no state change); glyph + sleeve ink ride the snapshot |
| `ping` | — | answers `{"type": "pong"}` |

Server →:

* `{"type": "state", "snapshot": {...}, "match": {...}}` — `match` is
  per-seat: `mode` (`"bot"`/`"pvp"`), `code`, `seat`,
  `opponent_connected`, `turn_seconds`, `turn_remaining`
* `{"type": "room", ...}` / `{"type": "room_closed", "reason": ...}` — versus lobby
* `{"type": "error", "message": "…"}` — never closes the socket

While the bot is playing, the socket stays responsive: a `play` sent during
its turn gets `not your turn` immediately, and `restart` cancels the bot's
turn cleanly.

## Snapshot shape (`state.py`)

Viewer-aware — each seat gets `snapshot(gs, viewer=<its station>)`:

```jsonc
{
  "turn": 1, "current": 0, "phase": "MAIN",
  "winner": null, "end_reason": null,   // "signal" | "concede" | "timeout" | "disconnect"
  "status": "Turn 1 | …",
  "viewer": 0,
  "can_act": true,          // winner is None AND it is your turn
  "players": {"0": {...}, "1": {...}},
  "me": {...}, "foe": {...},
  "hand": [ ... ],          // your hand, with legality precomputed
  "log": [ ... ], "log_offset": <count>,
  "history": [ ... ]        // structured play/damage/death events for the UI feed
}
```

Per-player view: `sleeve`, `sleeve_ink` (palette channel name), `avatar`
(icon id), `avatar_glyph` (resolved glyph), `signal`, `max_signal`,
`bandwidth`, `max_bandwidth`, `hand_count` (foe = count only),
`static_count`, `playlist_count`, `board`. The client tints the glyph with
`sleeve_ink`, so profile icons recolour with the sleeve.

Board cards: effective `atk`/`def`, `damage`, fuse progress, `rules`,
`flavor`, `rarity` — plus, **for your own cards**, `can_attack` and the
resolved `attack_targets` (`{"kind":"face"}` /
`{"kind":"broadcast","serial":n}`).

Hand cards carry `rarity` (for the face badge) and playability:
`is_playable`, `needs_target`, and the exact serial `legal_targets` list
where a chosen target is required — the client never re-implements
legality.

Hidden B-SIDEs (opponent view) collapse to `name: "???"`, `type: null`,
keywords `["B_SIDE"]`.

## AI pacing windows (from `create_app`)

* `ai_think` — the rival's first pause after your `end_turn`
  (`uniform(0.8, 1.2) × 1.4 s`)
* `ai_delay` — per-action spacing (`uniform(0.6, 1.3) × 1.4 s`)

`ai.iter_turn` yields exactly once per discrete action, which is what makes
staging (and instant-mode test runs) possible.
