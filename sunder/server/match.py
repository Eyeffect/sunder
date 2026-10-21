"""SUNDER — match rooms: one GameState, two seats, server-authoritative actions.

A `MatchRoom` owns a `GameState` and the seats that play it. Every action
names the seat that sent it, and the room checks it against that seat's
station, never against a hard-coded `0`. Seats are pluggable:

* `HumanSeat` — a WebSocket (detachable: a dropped socket leaves the seat
  empty until the player resumes). Receives viewer-aware snapshots.
* `BotSeat`   — the heuristic AI (`ai.iter_turn`), run as a background task
  so the room (and any human socket) stays responsive during its turn.

PvP rooms (two `HumanSeat`s) also run clocks — see docs/multiplayer.md:

* turn timer: `turn_seconds` per turn; on expiry the turn is ended for the
  player, and `afk_limit` consecutive expiries forfeit (`"timeout"`).
* disconnect grace: a seat that stays detached for `grace_seconds` while
  the game is live forfeits (`"disconnect"`).

All `GameState` mutation happens under `room.lock`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import time
from typing import Awaitable, Callable

from .. import ai as ai_mod
from ..game import GameState
from ..primitives import Target
from ..state import snapshot

log = logging.getLogger(__name__)


def _needs_target(inst) -> bool:
    # Mirrors state.hand_view's `needs_target`.
    return any(ab.target in (Target.CHOSEN, Target.ENEMY_BROADCAST)
               for ab in inst.card.abilities)


class Seat:
    """A participant controlling one station (`index` is 0 or 1)."""

    is_bot = False

    def __init__(self, index: int):
        if index not in (0, 1):
            raise ValueError("seat index must be 0 or 1")
        self.index = index

    @property
    def connected(self) -> bool:
        return True

    async def send(self, payload: dict) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class HumanSeat(Seat):
    """A seat backed by a WebSocket. Sends are serialized per seat, so the
    bot task, clocks and the receive loop never interleave a frame."""

    def __init__(self, index: int, ws=None):
        super().__init__(index)
        self.ws = ws
        self._send_lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self.ws is not None

    async def send(self, payload: dict) -> None:
        ws = self.ws
        if ws is None:
            return
        async with self._send_lock:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:  # socket gone mid-send; its receive loop will detach
                if self.ws is ws:
                    self.ws = None


class BotSeat(Seat):
    """The heuristic AI. `think`/`delay` are base seconds (0 = instant)."""

    is_bot = True

    def __init__(self, index: int, think: float = 1.4, delay: float = 1.4):
        super().__init__(index)
        self.think = think
        self.delay = delay

    async def send(self, payload: dict) -> None:
        return None  # the bot reads the GameState directly

    async def play_turn(self, room: "MatchRoom") -> None:
        gs = room.gs
        await asyncio.sleep(self.think * random.uniform(0.8, 1.2))
        steps = ai_mod.iter_turn(gs)
        while True:
            async with room.lock:
                if gs.game_over or gs.current != self.index:
                    return
                try:
                    next(steps)
                    done = False
                except StopIteration:  # iter_turn ended the turn (or the game)
                    done = True
                room._after_change()
                await room.broadcast()
            if done:
                return
            await asyncio.sleep(self.delay * random.uniform(0.6, 1.3))


OnEnd = Callable[["MatchRoom"], Awaitable[None] | None]


class MatchRoom:
    def __init__(self, gs: GameState, seats: list[Seat], *, code: str | None = None,
                 turn_seconds: float | None = None, grace_seconds: float | None = None,
                 afk_limit: int = 3, on_end: OnEnd | None = None):
        if sorted(s.index for s in seats) != [0, 1]:
            raise ValueError("a room needs exactly one seat per station")
        self.gs = gs
        self.seats: dict[int, Seat] = {s.index: s for s in seats}
        self.code = code
        self.turn_seconds = turn_seconds
        self.grace_seconds = grace_seconds
        self.afk_limit = max(1, afk_limit)
        self.on_end = on_end
        self.lock = asyncio.Lock()
        self._bot_task: asyncio.Task | None = None
        self._clock_task: asyncio.Task | None = None
        self._clock_key: tuple[int, int] | None = None
        self._deadline: float | None = None  # time.monotonic()
        self._grace: dict[int, asyncio.Task] = {}
        self._timeouts = {0: 0, 1: 0}
        self._ended = False
        self.closed = False

    @property
    def mode(self) -> str:
        return "bot" if any(s.is_bot for s in self.seats.values()) else "pvp"

    # ------------------------------------------------------------ output

    def meta(self, seat: Seat) -> dict:
        """Per-seat match info that rides next to each snapshot."""
        foe = self.seats[1 - seat.index]
        remaining = None
        if self._deadline is not None and not self.gs.game_over:
            remaining = round(max(0.0, self._deadline - time.monotonic()), 2)
        return {
            "mode": self.mode,
            "code": self.code,
            "seat": seat.index,
            "opponent_connected": foe.connected,
            "turn_seconds": self.turn_seconds if self.mode == "pvp" else None,
            "turn_remaining": remaining,
        }

    async def send_state(self, seat: Seat) -> None:
        await seat.send({"type": "state",
                         "snapshot": snapshot(self.gs, viewer=seat.index),
                         "match": self.meta(seat)})

    async def broadcast(self) -> None:
        for seat in self.seats.values():
            await self.send_state(seat)

    # ------------------------------------------------------------ lifecycle

    def start(self) -> None:
        """Arm clocks and start the bot if it moves first. Call once, after
        the initial state has been sent."""
        self._after_change()
        self.kick()

    def kick(self) -> None:
        """Start the bot if it is a bot's turn and it isn't already running."""
        if self.gs.game_over or self.closed:
            return
        seat = self.seats[self.gs.current]
        if seat.is_bot and (self._bot_task is None or self._bot_task.done()):
            self._bot_task = asyncio.create_task(self._run_bot())

    async def _run_bot(self) -> None:
        # Loop so bot-vs-bot rooms (tests, future spectating) keep going.
        gs = self.gs
        while not gs.game_over and not self.closed:
            seat = self.seats[gs.current]
            if not seat.is_bot:
                return
            before = (gs.turn, gs.current)
            try:
                await seat.play_turn(self)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("bot turn crashed")
                return
            if (gs.turn, gs.current) == before:  # no progress — never spin
                return

    def _after_change(self) -> None:
        """Call under the lock after any mutation: re-arms the turn clock on
        a new turn, and fires `on_end` exactly once when the game ends."""
        gs = self.gs
        if gs.game_over:
            self._stop_clock()
            for st in list(self._grace):
                self._cancel_grace(st)
            if not self._ended:
                self._ended = True
                if self.on_end is not None:
                    res = self.on_end(self)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
            return
        # Clocks are a PvP courtesy to the rival; practice vs the bot is untimed.
        if not self.turn_seconds or self.mode != "pvp":
            self._stop_clock()
            return
        key = (gs.turn, gs.current)
        if key != self._clock_key:
            self._stop_clock()
            self._clock_key = key
            self._deadline = time.monotonic() + self.turn_seconds
            self._clock_task = asyncio.create_task(self._turn_clock(key))

    def _stop_clock(self) -> None:
        task, self._clock_task = self._clock_task, None
        self._clock_key = None
        self._deadline = None
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()

    async def _turn_clock(self, key: tuple[int, int]) -> None:
        await asyncio.sleep(self.turn_seconds)
        async with self.lock:
            gs = self.gs
            if gs.game_over or (gs.turn, gs.current) != key:
                return
            st = gs.current
            self._timeouts[st] += 1
            if self._timeouts[st] >= self.afk_limit:
                gs.forfeit(st, "timeout")
            else:
                gs.log_line(f"Station {st + 1} ran out of time.", kind="system", station=st)
                gs.end_turn()
            self._after_change()
            await self.broadcast()
        self.kick()

    # ------------------------------------------------------------ connections

    async def attach(self, index: int, ws) -> None:
        seat = self.seats[index]
        if not isinstance(seat, HumanSeat):
            raise ValueError("not a human seat")
        seat.ws = ws
        self._cancel_grace(index)
        await self.broadcast()

    async def detach(self, index: int, ws=None) -> None:
        """Drop seat `index`'s socket unless a different socket is attached.
        In a live PvP game this starts the disconnect grace clock."""
        seat = self.seats[index]
        if not isinstance(seat, HumanSeat):
            return
        if ws is not None and seat.ws is not None and seat.ws is not ws:
            return
        seat.ws = None
        if self.mode == "pvp" and not self.gs.game_over and self.grace_seconds is not None:
            self._cancel_grace(index)
            self._grace[index] = asyncio.create_task(self._grace_clock(index))
        await self.broadcast()

    def _cancel_grace(self, index: int) -> None:
        task = self._grace.pop(index, None)
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()

    async def _grace_clock(self, index: int) -> None:
        await asyncio.sleep(self.grace_seconds)
        async with self.lock:
            self._grace.pop(index, None)
            if self.gs.game_over or self.seats[index].connected:
                return
            self.gs.forfeit(index, "disconnect")
            self._after_change()
            await self.broadcast()

    async def close(self) -> None:
        """Cancel every background task (bot, clocks). Idempotent."""
        self.closed = True
        tasks = [self._bot_task, self._clock_task, *self._grace.values()]
        self._bot_task = self._clock_task = None
        self._grace.clear()
        self._deadline = None
        me = asyncio.current_task()
        for task in tasks:
            if task and task is not me and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    # ------------------------------------------------------------ input

    def _my_turn(self, seat: Seat) -> bool:
        return not self.gs.game_over and self.gs.current == seat.index

    async def concede(self, seat: Seat) -> str | None:
        async with self.lock:
            if self.gs.game_over:
                return "game over"
            self.gs.forfeit(seat.index, "concede")
            self._after_change()
            await self.broadcast()
        return None

    async def handle(self, seat: Seat, msg: dict, *, sleeves: dict, avatars: dict) -> str | None:
        """Apply one client message for `seat`. Returns an error message for
        that seat only, or None on success (state is then broadcast)."""
        mtype = msg.get("type")
        if mtype == "concede":
            return await self.concede(seat)
        async with self.lock:
            gs = self.gs
            me = gs.players[seat.index]

            if mtype == "play":
                if not self._my_turn(seat):
                    return "not your turn"
                try:
                    idx = int(msg["hand"])
                    if not 0 <= idx < len(me.hand):
                        return "no such card in hand"
                    chosen = None
                    target = msg.get("target")
                    if target is not None and _needs_target(me.hand[idx]):
                        # Server-side legality: friendly or enemy, whatever the
                        # card allows — never a raw board lookup. (A target sent
                        # for an untargeted card is ignored, as before.)
                        legal = gs.legal_track_targets(me.hand[idx])
                        chosen = next((t for t in legal if t.serial == target), None)
                        if chosen is None:
                            return "bad target"
                    gs.play_card(idx, chosen)
                except (KeyError, TypeError, ValueError, IndexError) as exc:
                    return str(exc) or "bad play"
                self._timeouts[seat.index] = 0

            elif mtype == "attack":
                if not self._my_turn(seat):
                    return "not your turn"
                try:
                    attacker = me.board[int(msg["board"])]
                    target = msg.get("target")
                    if target == "face":
                        t: tuple = ("FACE", None)
                    else:
                        inst = next((i for i in me.opponent.board if i.serial == target), None)
                        if inst is None:
                            return "bad target"
                        t = ("BROADCAST", inst)
                    gs.attack(attacker, t)
                except (KeyError, TypeError, ValueError, IndexError) as exc:
                    return str(exc) or "bad attack"
                self._timeouts[seat.index] = 0

            elif mtype == "end_turn":
                # Stale/duplicate end_turns are ignored but still answered with
                # a fresh state, so the client can resync.
                if self._my_turn(seat) and msg.get("turn") == gs.turn:
                    gs.end_turn()
                    self._timeouts[seat.index] = 0

            elif mtype == "set_sleeve":
                sid = msg.get("sleeve")
                if not isinstance(sid, str) or sid not in sleeves:
                    return "unknown sleeve"
                me.sleeve = sid

            elif mtype == "set_avatar":
                aid = msg.get("avatar")
                if not isinstance(aid, str) or aid not in avatars:
                    return "unknown avatar"
                me.avatar = aid

            else:
                return f"unknown type {mtype!r}"

            self._after_change()
            await self.broadcast()
        self.kick()
        return None
