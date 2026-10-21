"""SUNDER — match rooms: one GameState, N seats, server-authoritative actions.

A `MatchRoom` owns a `GameState` and the seats that play it. Every action
names the seat that sent it, and the room checks it against that seat's
station, never against a hard-coded `0`. Seats are pluggable:

* `HumanSeat` — a WebSocket. Receives viewer-aware snapshots for its station.
* `BotSeat`   — the heuristic AI (`ai.iter_turn`), run as a background task
  so the room (and any human socket) stays responsive during its turn.

Today the server builds a room as Human(0) vs Bot(1). A PvP room is the same
class with two `HumanSeat`s; no engine or snapshot changes needed.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random

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

    async def send(self, payload: dict) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class HumanSeat(Seat):
    """A seat backed by a WebSocket. Sends are serialized per socket, so the
    bot task and the receive loop never interleave a frame."""

    def __init__(self, index: int, ws):
        super().__init__(index)
        self.ws = ws
        self.connected = True
        self._send_lock = asyncio.Lock()

    async def send(self, payload: dict) -> None:
        if not self.connected:
            return
        async with self._send_lock:
            try:
                await self.ws.send_text(json.dumps(payload))
            except Exception:  # socket gone mid-send; the receive loop will notice
                self.connected = False


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
                if room.gs is not gs or gs.game_over or gs.current != self.index:
                    return
                try:
                    next(steps)
                    done = False
                except StopIteration:  # iter_turn ended the turn (or the game)
                    done = True
                await room.broadcast()
            if done:
                return
            await asyncio.sleep(self.delay * random.uniform(0.6, 1.3))


class MatchRoom:
    def __init__(self, gs: GameState, seats: list[Seat]):
        if sorted(s.index for s in seats) != [0, 1]:
            raise ValueError("a room needs exactly one seat per station")
        self.gs = gs
        self.seats: dict[int, Seat] = {s.index: s for s in seats}
        self.lock = asyncio.Lock()
        self._bot_task: asyncio.Task | None = None

    # ------------------------------------------------------------ output

    async def send_state(self, seat: Seat) -> None:
        await seat.send({"type": "state", "snapshot": snapshot(self.gs, viewer=seat.index)})

    async def broadcast(self) -> None:
        for seat in self.seats.values():
            await self.send_state(seat)

    # ------------------------------------------------------------ lifecycle

    def kick(self) -> None:
        """Start the bot if it is a bot's turn and it isn't already running."""
        if self.gs.game_over:
            return
        seat = self.seats[self.gs.current]
        if seat.is_bot and (self._bot_task is None or self._bot_task.done()):
            self._bot_task = asyncio.create_task(self._run_bot(seat))

    async def _run_bot(self, seat: BotSeat) -> None:
        # Loop so bot-vs-bot rooms (tests, future spectating) keep going.
        gs = self.gs
        while not gs.game_over and self.gs is gs:
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

    async def close(self) -> None:
        task, self._bot_task = self._bot_task, None
        if task and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    # ------------------------------------------------------------ input

    def _my_turn(self, seat: Seat) -> bool:
        return not self.gs.game_over and self.gs.current == seat.index

    async def handle(self, seat: Seat, msg: dict, *, sleeves: dict, avatars: dict) -> str | None:
        """Apply one client message for `seat`. Returns an error message for
        that seat only, or None on success (state is then broadcast)."""
        mtype = msg.get("type")
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

            elif mtype == "end_turn":
                # Stale/duplicate end_turns are ignored but still answered with
                # a fresh state, so the client can resync.
                if self._my_turn(seat) and msg.get("turn") == gs.turn:
                    gs.end_turn()

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

            await self.broadcast()
        self.kick()
        return None
