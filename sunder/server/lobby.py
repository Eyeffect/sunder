"""SUNDER — PvP lobby: invite-code rooms, seat tokens, resume.

In-memory and single-process by design (Phase 1). Each WebSocket gets a
`Connection`; the lobby moves connections between three places:

  nothing ──create──▶ PendingRoom (host waiting, has an invite code)
  PendingRoom ──join──▶ LiveEntry (MatchRoom with two HumanSeats)
  LiveEntry ──resume(code, token)──▶ re-attach a dropped seat

Seat tokens are bearer secrets (`secrets.token_urlsafe`) handed only to the
seat's owner; anyone holding one can play that seat, so the client keeps it
in `sessionStorage` (per tab) and never shows it. Codes are short and
shareable, tokens are not. See docs/multiplayer.md.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import secrets
from dataclasses import dataclass, field

from ..game import GameState
from .match import HumanSeat, MatchRoom

# No 0/O/1/I/L — codes get read aloud and typed on phones.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


class LobbyError(Exception):
    """A user-facing lobby failure (message is safe to send to the client)."""


@dataclass(eq=False)
class Connection:
    """Per-socket routing state. Exactly one of `room`/`pending` (or neither)."""

    ws: object
    room: MatchRoom | None = None
    seat: int | None = None
    pending: "PendingRoom | None" = None
    entry: "LiveEntry | None" = None

    @property
    def in_live_pvp(self) -> bool:
        return (self.entry is not None and self.room is not None
                and not self.room.gs.game_over)

    def clear(self) -> None:
        self.room = self.seat = self.pending = self.entry = None


@dataclass(eq=False)
class PendingRoom:
    code: str
    host: Connection
    host_token: str


@dataclass(eq=False)
class LiveEntry:
    code: str
    room: MatchRoom
    tokens: dict[int, str]
    conns: dict[int, Connection | None] = field(default_factory=dict)
    reaper: asyncio.Task | None = None


class Lobby:
    def __init__(self, decks, *, sleeves: dict, avatars: dict,
                 turn_seconds: float | None = 75, grace_seconds: float | None = 60,
                 afk_limit: int = 3, finished_ttl: float = 300, max_rooms: int = 200):
        self.decks = decks
        self.sleeves = sleeves
        self.avatars = avatars
        self.turn_seconds = turn_seconds
        self.grace_seconds = grace_seconds
        self.afk_limit = afk_limit
        self.finished_ttl = finished_ttl
        self.max_rooms = max_rooms
        self.pending: dict[str, PendingRoom] = {}
        self.live: dict[str, LiveEntry] = {}

    # ------------------------------------------------------------ helpers

    def _new_code(self) -> str:
        for _ in range(100):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self.pending and code not in self.live:
                return code
        raise LobbyError("could not allocate a room code")  # pragma: no cover

    @staticmethod
    def normalize(code) -> str:
        return str(code or "").strip().upper()

    @staticmethod
    def room_msg(code: str, seat: int | None, token: str | None, status: str) -> dict:
        return {"type": "room", "mode": "pvp", "code": code, "seat": seat,
                "token": token, "status": status}

    # ------------------------------------------------------------ create / join

    def create(self, conn: Connection) -> PendingRoom:
        if len(self.pending) + len(self.live) >= self.max_rooms:
            raise LobbyError("server is full — try again in a bit")
        self.cancel_pending(conn)
        pr = PendingRoom(self._new_code(), conn, secrets.token_urlsafe(16))
        self.pending[pr.code] = pr
        conn.pending = pr
        return pr

    def cancel_pending(self, conn: Connection) -> None:
        pr = conn.pending
        if pr is not None and self.pending.get(pr.code) is pr:
            del self.pending[pr.code]
        conn.pending = None

    def check_joinable(self, conn: Connection, code) -> str:
        """Validate a join without side effects; returns the normalized code."""
        code = self.normalize(code)
        pr = self.pending.get(code)
        if pr is None:
            raise LobbyError("no such room" if code not in self.live else "room is full")
        if pr.host is conn:
            raise LobbyError("that's your own room — share the code with a rival")
        return code

    async def join(self, conn: Connection, code) -> LiveEntry:
        code = self.check_joinable(conn, code)
        pr = self.pending[code]
        del self.pending[code]
        pr.host.pending = None

        # Seat order is random so the host doesn't always move first. The
        # seed is server-only: a client-chosen seed would leak the shuffle.
        host_seat = secrets.randbelow(2)
        guest_seat = 1 - host_seat
        gs = GameState(*self.decks, seed=secrets.randbits(64),
                       sleeves=self.sleeves, avatars=self.avatars)
        gs.start_game()
        tokens = {host_seat: pr.host_token, guest_seat: secrets.token_urlsafe(16)}
        entry = LiveEntry(code, None, tokens)  # type: ignore[arg-type]
        room = MatchRoom(
            gs,
            [HumanSeat(host_seat, pr.host.ws), HumanSeat(guest_seat, conn.ws)],
            code=code, turn_seconds=self.turn_seconds, grace_seconds=self.grace_seconds,
            afk_limit=self.afk_limit, on_end=lambda _room: self._schedule_reap(entry),
        )
        entry.room = room
        entry.conns = {host_seat: pr.host, guest_seat: conn}
        self.live[code] = entry
        for seat, c in entry.conns.items():
            c.clear()
            c.room, c.seat, c.entry = room, seat, entry
            await room.seats[seat].send(self.room_msg(code, seat, tokens[seat], "live"))
        await room.broadcast()
        room.start()
        return entry

    # ------------------------------------------------------------ resume / leave

    async def resume(self, conn: Connection, code, token) -> LiveEntry:
        code = self.normalize(code)
        entry = self.live.get(code)
        if entry is None or not isinstance(token, str):
            raise LobbyError("that match is no longer running")
        seat = next((s for s, t in entry.tokens.items()
                     if hmac.compare_digest(t, token)), None)
        if seat is None:
            raise LobbyError("that match is no longer running")
        old = entry.conns.get(seat)
        if old is not None and old is not conn:
            # Same seat opened in another tab/device: last one wins.
            old_ws = old.ws
            old.clear()
            with contextlib.suppress(Exception):
                await old_ws.send_text(json.dumps(
                    {"type": "room_closed", "reason": "resumed elsewhere"}))
        conn.clear()
        conn.room, conn.seat, conn.entry = entry.room, seat, entry
        entry.conns[seat] = conn
        status = "over" if entry.room.gs.game_over else "live"
        seat_obj = entry.room.seats[seat]
        seat_obj.ws = conn.ws
        await seat_obj.send(self.room_msg(code, seat, entry.tokens[seat], status))
        await entry.room.attach(seat, conn.ws)
        return entry

    async def leave(self, conn: Connection) -> None:
        """Leave whatever PvP state `conn` is in. A live match is conceded."""
        if conn.pending is not None:
            self.cancel_pending(conn)
        entry, seat = conn.entry, conn.seat
        if entry is not None and seat is not None:
            room = entry.room
            if not room.gs.game_over:
                await room.concede(room.seats[seat])
            await self._drop(entry, seat, conn)
        conn.clear()

    async def disconnect(self, conn: Connection) -> None:
        """Socket closed. Pending rooms vanish; live seats start their grace."""
        if conn.pending is not None:
            self.cancel_pending(conn)
        entry, seat = conn.entry, conn.seat
        if entry is not None and seat is not None:
            await self._drop(entry, seat, conn)
        conn.clear()

    async def _drop(self, entry: LiveEntry, seat: int, conn: Connection) -> None:
        if entry.conns.get(seat) is not conn:
            return
        entry.conns[seat] = None
        await entry.room.detach(seat, conn.ws)
        if entry.room.gs.game_over and not any(entry.conns.values()):
            await self._reap(entry)

    # ------------------------------------------------------------ cleanup

    def _schedule_reap(self, entry: LiveEntry) -> None:
        if entry.reaper is None:
            entry.reaper = asyncio.create_task(self._reap_later(entry))

    async def _reap_later(self, entry: LiveEntry) -> None:
        await asyncio.sleep(self.finished_ttl)
        await self._reap(entry)

    async def _reap(self, entry: LiveEntry) -> None:
        if self.live.get(entry.code) is entry:
            del self.live[entry.code]
        for c in entry.conns.values():
            if c is not None and c.entry is entry:
                c.clear()
        task, entry.reaper = entry.reaper, None
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()
        await entry.room.close()

    async def shutdown(self) -> None:
        for entry in list(self.live.values()):
            await self._reap(entry)
        self.pending.clear()
