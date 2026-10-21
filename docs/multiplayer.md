# Multiplayer (versus)

Two humans, one server-authoritative match. This page covers how live PvP
works today (Phase 1: invite rooms, in-memory) and what's planned next.

> **Status:** Phase 1. Rooms live in server memory: a server restart ends
> every live match, and there are no accounts, ratings or saved history yet.
> Those land in Phase 2 (Postgres + username/password accounts) and
> Phase 3 (ratings, leaderboards, stats). See [Roadmap](#roadmap).

## Playing

1. Open the **VERSUS** tab and press **CREATE ROOM**. You get a six-character
   code (e.g. `K7QM2X`) and a **COPY INVITE LINK** button
   (`https://<host>/?room=K7QM2X`).
2. Your rival opens the link, or types the code under **JOIN**.
3. The match starts right away. Seats are random, so the host doesn't always
   go first. Station 2 still gets the Signal Spike.

During the match, the bar above the board shows the room code, whether your
rival is connected, and the turn clock. **CONCEDE** asks for confirmation.

| Rule | Default | What happens |
|---|---|---|
| Turn timer | 75 s | When it runs out, your turn ends for you. |
| AFK limit | 3 strikes | Three timeouts in a row with no action forfeit the match (`timeout`). Any play, attack or end-turn resets your strikes. |
| Reconnect grace | 60 s | If you disconnect, your seat waits for you. Stay away longer than the grace period and you forfeit (`disconnect`). |
| Concede / leave | — | Ends the match at once (`concede`). Leaving the room during a live match counts as a concede. |

Practice matches against the bot have no clocks.

**Refreshing the page** brings you back to your seat (see
[Resume](#resume-and-seat-tokens)). Opening the same match in a second tab
moves your seat there, and the first tab drops back to practice.

## Architecture

```
browser ──WS /ws──▶ Connection ──▶ Lobby ──▶ MatchRoom ──▶ GameState
                                     │          ├─ HumanSeat(0, ws)
                                     │          └─ HumanSeat(1, ws)   (or BotSeat)
                                     └─ pending rooms (code → host)
```

| Module | Owns |
|---|---|
| `sunder/game.py` | Rules. `forfeit(station, reason)` and `end_reason` cover endings that aren't Signal. No I/O. |
| `sunder/server/match.py` | `MatchRoom`: one `GameState` plus two seats. It checks every action against the seat that sent it, sends each seat its own snapshot, and runs the turn clock, AFK strikes and grace clocks. All mutations happen under `room.lock`. |
| `sunder/server/lobby.py` | `Lobby`: invite codes, seat tokens, join, resume, leave, and cleanup of finished rooms. |
| `sunder/server/app.py` | `/ws` routing. A practice `start` builds a Human-vs-Bot `MatchRoom`; the lobby messages build Human-vs-Human ones. |

The bot is just another seat (`BotSeat`). It runs as a background task, so
sockets stay responsive during its turn, and the same `MatchRoom` code paths
serve practice and versus.

### Server authority

* Clients send intents (`play`, `attack`, `end_turn`), and the room checks
  them against the **sender's** station. A seat can't act out of turn or
  aim at an illegal target: chosen targets must be in
  `legal_track_targets()`.
* Each seat gets `snapshot(gs, viewer=seat)`. The rival's hand is a count,
  and hidden B-SIDEs are masked.
* Log and history text never name a hidden B-SIDE. `CardInstance.label()`
  returns "Hidden B-SIDE" while the card is hidden, so area damage or a death
  can't leak it. This is covered by `tests/test_pvp.py`.
* The server picks the match seed (`secrets.randbits`) and never sends it to
  clients. Knowing the seed would reveal both shuffled playlists.

### Resume and seat tokens

When a match goes live, each seat receives a **seat token**
(`secrets.token_urlsafe(16)`) in its `room` message. The token is a bearer
secret: whoever holds it can play that seat.

* The client keeps `{code, token}` in `sessionStorage` under `sunder-pvp`.
  That's per tab and cleared when the tab closes. The token is never shown in
  the UI and never appears in URLs.
* After a reconnect the client sends `resume {code, token}`. The server
  compares tokens in constant time (`hmac.compare_digest`), reattaches the
  socket and cancels the grace clock.
* Room codes are shareable but are **not** credentials. `GET /api/rooms/{code}`
  only returns `waiting` / `live` / `over`.

### Lifecycle

```
create_room ─▶ waiting ──join_room──▶ live ──signal | concede | timeout | disconnect──▶ over
     │                                  ▲                                                 │
     └─ leave_room / socket closes      └──── resume (within grace) ◀── socket drops      └─ reaped after 5 min
        → room deleted                                                                       (or when both leave)
```

A server holds at most `max_rooms` rooms (200 by default, pending and live
combined). Past that, `create_room` fails with "server is full".

## Protocol

These messages extend the existing [WebSocket protocol](api.md#websocket-ws).

| Client → | Payload | Effect |
|---|---|---|
| `create_room` | — | Host a room. Answers `room {status: "waiting", code}`. Ends any practice match. |
| `join_room` | `{code}` | Join a waiting room (case-insensitive). Both seats get `room {status: "live", seat, token}` and then a `state`. |
| `resume` | `{code, token}` | Reattach to your seat. Answers `room` + `state`, and the rival sees `opponent_connected: true`. |
| `leave_room` | — | Cancel a waiting room, or concede and leave a live one. Answers `room_closed {reason: "left"}`. |
| `concede` | — | Forfeit the current match (versus or practice). |

| Server → | Payload |
|---|---|
| `room` | `{mode: "pvp", code, seat, token, status}`. `seat` and `token` are `null` while waiting. |
| `room_closed` | `{reason}`: `"left"` or `"resumed elsewhere"`. |
| `state` | `{snapshot, match}` (see below). |
| `error` | `{message}`, e.g. `no such room`, `room is full`, `not your turn`, `that match is no longer running`, `you're in a PvP match — concede or leave first`. |

Every `state` now carries `match`:

```jsonc
{
  "mode": "pvp",              // or "bot"
  "code": "K7QM2X",           // null for practice
  "seat": 1,                  // your station
  "opponent_connected": true,
  "turn_seconds": 75,         // null when untimed (practice, or clock disabled)
  "turn_remaining": 41.37     // seconds left on the current turn, or null
}
```

The snapshot also gains `end_reason`: `null` while the match is live, then
one of `"signal" | "concede" | "timeout" | "disconnect"`.

`start` / `restart` are refused during a live PvP match. You have to concede
or leave first, so a stray key press can't throw away a ranked game later on.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `SUNDER_TURN_SECONDS` | `75` | Turn length in versus. Set to `0` or `off` for untimed versus. |
| `SUNDER_GRACE_SECONDS` | `60` | Reconnect window before a disconnect forfeits. `0` / `off` disables it (a dropped seat then waits forever). |

`create_app()` takes the same settings as keyword arguments (`turn_seconds`,
`grace_seconds`, `afk_limit`, `finished_ttl`). Tests pass `0` to switch the
clocks off, or tiny values to exercise them.

**Single process only.** Rooms live in one Python process, so run uvicorn
with **one worker** (the Docker image already does). Running several workers
would need shared room state, for example Redis, which is out of scope until
it's actually needed.

## Testing

* `tests/test_pvp.py`: forfeits and end reasons; the hidden-B-SIDE log
  regression; turn timer, AFK strikes, grace and reconnect; and, over
  WebSockets: create/join, alternating turns, a full PvP match to completion,
  join errors, full rooms, resume (including bad tokens and "resumed
  elsewhere"), concede, leave, disconnect forfeit.
* `tests/test_seats.py`: seat-aware rooms, per-seat views, out-of-turn
  rejection, the station-0 `winner` regression.
* `web/src/pvp.test.ts`, `components/MatchBar.test.tsx`,
  `components/LobbyView.test.tsx`, and the "App — versus" suite in
  `App.test.tsx`: session storage, invite links, resume/join on connect,
  the stale-resume fallback, hosting, concede confirmation, end-of-match text.

## Roadmap

| Phase | Scope |
|---|---|
| 0 ✅ | Fix for the `winner == 0` bug; seat-aware `MatchRoom`; bot as a seat. |
| 1 ✅ | Invite rooms, server-side clocks, concede, resume, the VERSUS UI. |
| 2 | Postgres (async SQLAlchemy 2 + Alembic), username/password accounts (argon2, httpOnly session cookie), profiles (avatar/sleeve stored server-side), match + action log (seed + actions = replay). Seat tokens become "the logged-in user owns this seat". |
| 3 | Glicko-2 ratings, ranked matchmaking queue, leaderboard, per-deck stats, match history. |
| 4 | Deck choice/building, replays, spectating, admin roles for `/api/registry` approve + `/api/generate`, rate limits. |
