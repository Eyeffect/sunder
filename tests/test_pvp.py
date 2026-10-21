"""Phase 1 — live PvP: forfeits, clocks, hidden-info, lobby + WS protocol."""

import asyncio
import contextlib
import time

import pytest
from fastapi.testclient import TestClient

from sunder.game import GameState
from sunder.server.app import create_app, default_decks
from sunder.server.lobby import CODE_ALPHABET, CODE_LENGTH
from sunder.server.match import HumanSeat, MatchRoom, Seat
from sunder.state import snapshot
from tests.conftest import card, make_gs, put_board, put_hand

# ---------------------------------------------------------------- engine


def _gs(seed=1):
    gs = GameState(*default_decks(), seed=seed)
    gs.start_game()
    return gs


def test_forfeit_sets_winner_and_reason():
    gs = _gs()
    gs.forfeit(0, "concede")
    assert gs.winner == 1 and gs.end_reason == "concede" and gs.game_over
    gs.forfeit(1, "timeout")  # no-op once over
    assert gs.winner == 1 and gs.end_reason == "concede"
    assert snapshot(gs, 0)["end_reason"] == "concede"


def test_signal_win_reason():
    gs = _gs()
    gs.players[1].signal = 0
    gs.check_win()
    assert gs.end_reason == "signal"


def test_forfeit_rejects_bad_station():
    with pytest.raises(ValueError):
        _gs().forfeit(2, "concede")


def test_hidden_bside_name_never_logged():
    """Regression: AoE damage/death lines used to print a hidden B-SIDE's name."""
    gs = make_gs()
    put_board(gs, 1, card(name="Deep Secret", stats={"atk": 1, "def": 1}, keywords=["B_SIDE"]))
    gs.players[1].board[0].hidden = True
    put_hand(gs, 0, card(name="Wipe", type="TRACK", stats=None, abilities=[
        {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "ALL_ENEMY_BROADCASTS",
         "value": 2}]))
    gs.cur.bandwidth = 5
    gs.play_card(0)
    s = snapshot(gs, viewer=0)
    text = " ".join(s["log"]) + " ".join(e["text"] for e in s["history"])
    assert "Deep Secret" not in text
    assert "Hidden B-SIDE goes silent." in s["log"]


def test_revealed_bside_is_named_again():
    gs = make_gs()
    put_board(gs, 1, card(name="Deep Secret", keywords=["B_SIDE"]))
    inst = gs.players[1].board[0]
    inst.hidden = True
    assert inst.label() == "Hidden B-SIDE"
    inst.hidden = False
    assert inst.label() == "Deep Secret"


# ---------------------------------------------------------------- room clocks


class FakeSeat(HumanSeat):
    """A HumanSeat with an in-memory 'socket'."""

    def __init__(self, index):
        super().__init__(index, ws=object())
        self.inbox = []

    async def send(self, payload):
        if self.ws is not None:
            self.inbox.append(payload)

    @property
    def last(self):
        return [m for m in self.inbox if m["type"] == "state"][-1]


def _room(**kw):
    gs = _gs()
    a, b = FakeSeat(0), FakeSeat(1)
    return gs, MatchRoom(gs, [a, b], **kw), a, b


def test_meta_rides_with_each_state():
    gs, room, a, b = _room(code="ABCDEF", turn_seconds=30)

    async def go():
        room.start()
        await room.broadcast()
        await room.close()
    asyncio.run(go())
    m = a.last["match"]
    assert m["mode"] == "pvp" and m["code"] == "ABCDEF" and m["seat"] == 0
    assert m["opponent_connected"] is True and m["turn_seconds"] == 30
    assert 0 < m["turn_remaining"] <= 30
    assert b.last["match"]["seat"] == 1


def test_turn_timer_ends_turn_then_forfeits_afk():
    gs, room, a, b = _room(turn_seconds=0.1, afk_limit=2)

    async def go():
        room.start()
        await asyncio.sleep(0.15)   # t=0.10 seat 0 times out once → turn passes
        assert gs.current == 1 and not gs.game_over
        await asyncio.sleep(0.10)   # t=0.20 seat 1 times out once
        assert gs.current == 0 and not gs.game_over
        await asyncio.sleep(0.10)   # t=0.30 seat 0's second strike → forfeit
        await room.close()
    asyncio.run(go())
    assert gs.winner == 1 and gs.end_reason == "timeout"


def test_acting_resets_afk_strikes():
    gs, room, a, b = _room(turn_seconds=0.1, afk_limit=2)

    async def go():
        room.start()
        await asyncio.sleep(0.25)   # seat 0 strike 1 (t=.1), seat 1 strike 1 (t=.2)
        assert gs.current == 0 and room._timeouts == {0: 1, 1: 1}
        await room.handle(a, {"type": "end_turn", "turn": gs.turn}, sleeves={}, avatars={})
        assert room._timeouts[0] == 0
        await room.handle(b, {"type": "end_turn", "turn": gs.turn}, sleeves={}, avatars={})
        await asyncio.sleep(0.15)   # seat 0 times out — strike 1 again, not 2
        assert room._timeouts[0] == 1
        await room.close()
    asyncio.run(go())
    assert not gs.game_over


def test_turn_clock_restarts_each_turn():
    gs, room, a, b = _room(turn_seconds=10)

    async def go():
        room.start()
        first = room._deadline
        await asyncio.sleep(0.02)
        await room.handle(a, {"type": "end_turn", "turn": 1}, sleeves={}, avatars={})
        assert room._deadline > first
        await room.close()
    asyncio.run(go())


def test_disconnect_grace_forfeits():
    gs, room, a, b = _room(grace_seconds=0.05)

    async def go():
        await room.detach(1)
        assert a.last["match"]["opponent_connected"] is False
        await asyncio.sleep(0.12)
        await room.close()
    asyncio.run(go())
    assert gs.winner == 0 and gs.end_reason == "disconnect"


def test_reconnect_within_grace_keeps_game():
    gs, room, a, b = _room(grace_seconds=0.1)

    async def go():
        await room.detach(1)
        await asyncio.sleep(0.03)
        await room.attach(1, object())
        await asyncio.sleep(0.15)
        await room.close()
    asyncio.run(go())
    assert not gs.game_over
    assert a.last["match"]["opponent_connected"] is True


def test_concede_any_time_and_on_end_once():
    ended = []
    gs, room, a, b = _room(on_end=lambda r: ended.append(r.gs.winner))

    async def go():
        assert await room.handle(b, {"type": "concede"}, sleeves={}, avatars={}) is None
        assert await room.handle(a, {"type": "concede"}, sleeves={}, avatars={}) == "game over"
    asyncio.run(go())
    assert gs.winner == 0 and gs.end_reason == "concede" and ended == [0]


def test_no_clocks_in_bot_rooms():
    from sunder.server.match import BotSeat
    gs = _gs()
    human = FakeSeat(0)
    room = MatchRoom(gs, [human, BotSeat(1, 0, 0)], turn_seconds=0.01, grace_seconds=0.01)

    async def go():
        room.start()
        await room.detach(0)
        await asyncio.sleep(0.05)
        await room.close()
    asyncio.run(go())
    assert not gs.game_over and gs.current == 0 and room._deadline is None


def test_plain_seat_is_always_connected():
    assert Seat(0).connected is True


# ---------------------------------------------------------------- WS protocol


def _client(**kw):
    kw.setdefault("ai_think", 0)
    kw.setdefault("ai_delay", 0)
    kw.setdefault("turn_seconds", 0)
    kw.setdefault("grace_seconds", 0)
    return TestClient(create_app(**kw))


def _close(ws):
    """Simulate a dropped connection for one side of a `_pair`."""
    ws.close()


def _recv(ws, mtype):
    """Read until a message of `mtype` arrives (skips interleaved states)."""
    for _ in range(50):
        m = ws.receive_json()
        if m["type"] == mtype:
            return m
    raise AssertionError(f"no {mtype}")


@contextlib.contextmanager
def _pair(tc):
    """Open two sockets, host creates, guest joins.

    Yields ({seat: (ws, room_msg, first_state)}, code). Sockets are always
    closed on exit, so a failing assertion can't hang the TestClient."""
    with tc.websocket_connect("/ws") as h, tc.websocket_connect("/ws") as g:
        h.send_json({"type": "create_room"})
        room = _recv(h, "room")
        assert room["status"] == "waiting" and room["token"] is None
        code = room["code"]
        assert len(code) == CODE_LENGTH and set(code) <= set(CODE_ALPHABET)
        g.send_json({"type": "join_room", "code": code.lower()})  # case-insensitive
        rh, rg = _recv(h, "room"), _recv(g, "room")
        assert rh["status"] == rg["status"] == "live"
        assert {rh["seat"], rg["seat"]} == {0, 1} and rh["token"] != rg["token"]
        sh, sg = _recv(h, "state"), _recv(g, "state")
        yield {rh["seat"]: (h, rh, sh), rg["seat"]: (g, rg, sg)}, code


def test_ws_create_join_and_viewer_snapshots():
    with _client() as tc:
        with _pair(tc) as (seats, code):
            for seat, (_ws, _room, state) in seats.items():
                assert state["snapshot"]["viewer"] == seat
                assert state["match"]["mode"] == "pvp" and state["match"]["code"] == code
                assert state["snapshot"]["can_act"] is (seat == 0)
            assert tc.get(f"/api/rooms/{code}").json() == {"code": code, "status": "live"}


def test_ws_turns_alternate_and_out_of_turn_rejected():
    with _client() as tc:
        with _pair(tc) as (seats, _):
            p0, p1 = seats[0][0], seats[1][0]
            p1.send_json({"type": "end_turn", "turn": 1})
            s = _recv(p1, "state")  # out-of-turn end_turn just resyncs (both seats)
            assert s["snapshot"]["current"] == 0
            _recv(p0, "state")
            p1.send_json({"type": "play", "hand": 0})
            assert _recv(p1, "error")["message"] == "not your turn"
            p0.send_json({"type": "end_turn", "turn": 1})
            s0, s1 = _recv(p0, "state"), _recv(p1, "state")
            assert s1["snapshot"]["can_act"] and not s0["snapshot"]["can_act"]


def test_ws_full_pvp_match_terminates():
    """Both seats play the same simple policy until someone wins."""
    with _client() as tc:
        with _pair(tc) as (seats, code):
            latest = {0: seats[0][2]["snapshot"], 1: seats[1][2]["snapshot"]}
            socks = {0: seats[0][0], 1: seats[1][0]}
            final = None
            for _ in range(600):
                cur = latest[0]["current"]
                s = latest[cur]
                if s["winner"] is not None:
                    final = s
                    break
                ws = socks[cur]
                idx = next((i for i, c in enumerate(s["hand"]) if c["is_playable"]
                            and (not c["needs_target"] or c["legal_targets"])), None)
                if idx is not None:
                    c = s["hand"][idx]
                    ws.send_json({"type": "play", "hand": idx,
                                  "target": c["legal_targets"][0] if c["needs_target"] else None})
                else:
                    att = next((b for b in s["me"]["board"]
                                if b.get("can_attack") and b.get("attack_targets")), None)
                    if att:
                        t = att["attack_targets"][0]
                        ws.send_json({"type": "attack", "board": s["me"]["board"].index(att),
                                      "target": "face" if t["kind"] == "face" else t["serial"]})
                    else:
                        ws.send_json({"type": "end_turn", "turn": s["turn"]})
                for seat in (0, 1):
                    msg = _recv(socks[seat], "state")
                    latest[seat] = msg["snapshot"]
            assert final is not None and final["winner"] in (0, 1)
            assert final["end_reason"] == "signal"
            assert tc.get(f"/api/rooms/{code}").json()["status"] == "over"


def test_ws_join_errors():
    with _client() as tc:
        with tc.websocket_connect("/ws") as h, tc.websocket_connect("/ws") as x:
            x.send_json({"type": "join_room", "code": "ZZZZZZ"})
            assert _recv(x, "error")["message"] == "no such room"
            h.send_json({"type": "create_room"})
            code = _recv(h, "room")["code"]
            h.send_json({"type": "join_room", "code": code})
            assert "your own room" in _recv(h, "error")["message"]
        assert tc.get("/api/rooms/ZZZZZZ").status_code == 404


def test_ws_room_full():
    with _client() as tc:
        with _pair(tc) as (seats, code):
            with tc.websocket_connect("/ws") as third:
                third.send_json({"type": "join_room", "code": code})
                assert _recv(third, "error")["message"] == "room is full"


def test_ws_pending_room_vanishes_on_disconnect_or_leave():
    with _client() as tc:
        with tc.websocket_connect("/ws") as h:
            h.send_json({"type": "create_room"})
            code = _recv(h, "room")["code"]
            h.send_json({"type": "leave_room"})
            assert _recv(h, "room_closed")["reason"] == "left"
        assert tc.get(f"/api/rooms/{code}").status_code == 404
        with tc.websocket_connect("/ws") as h:
            h.send_json({"type": "create_room"})
            code = _recv(h, "room")["code"]
        time.sleep(0.05)
        assert tc.get(f"/api/rooms/{code}").status_code == 404


def test_ws_resume_after_drop():
    with _client(grace_seconds=30) as tc:
        with _pair(tc) as (seats, code):
            p0, room0, _ = seats[0]
            p1 = seats[1][0]
            _close(p0)
            assert _recv(p1, "state")["match"]["opponent_connected"] is False
            with tc.websocket_connect("/ws") as back:
                back.send_json({"type": "resume", "code": code, "token": "nope"})
                assert "no longer running" in _recv(back, "error")["message"]
                back.send_json({"type": "resume", "code": code, "token": room0["token"]})
                r = _recv(back, "room")
                assert r["seat"] == 0 and r["status"] == "live"
                s = _recv(back, "state")
                assert s["snapshot"]["viewer"] == 0 and s["snapshot"]["turn"] == 1
                assert _recv(p1, "state")["match"]["opponent_connected"] is True
                back.send_json({"type": "end_turn", "turn": 1})
                assert _recv(p1, "state")["snapshot"]["can_act"] is True


def test_ws_resume_elsewhere_kicks_old_socket():
    with _client(grace_seconds=30) as tc:
        with _pair(tc) as (seats, code):
            p0, room0, _ = seats[0]
            with tc.websocket_connect("/ws") as tab2:
                tab2.send_json({"type": "resume", "code": code, "token": room0["token"]})
                assert _recv(tab2, "room")["seat"] == 0
                assert _recv(p0, "room_closed")["reason"] == "resumed elsewhere"
                p0.send_json({"type": "end_turn", "turn": 1})
                assert _recv(p0, "error")["message"] == "send {type:start} first"


def test_ws_concede_and_start_guard():
    with _client() as tc:
        with _pair(tc) as (seats, _):
            p0, p1 = seats[0][0], seats[1][0]
            p1.send_json({"type": "start"})
            assert "concede or leave" in _recv(p1, "error")["message"]
            p1.send_json({"type": "concede"})
            s = _recv(p0, "state")["snapshot"]
            assert s["winner"] == 0 and s["end_reason"] == "concede"
            p1.send_json({"type": "start", "seed": 1})  # allowed once the match is over
            s = _recv(p1, "state")
            while s["match"]["mode"] == "pvp":  # skip the concede broadcast
                s = _recv(p1, "state")
            assert s["match"]["mode"] == "bot" and s["snapshot"]["turn"] == 1


def test_ws_leave_live_match_concedes():
    with _client() as tc:
        with _pair(tc) as (seats, _):
            p0, p1 = seats[0][0], seats[1][0]
            p0.send_json({"type": "leave_room"})
            s = _recv(p1, "state")["snapshot"]
            assert s["winner"] == 1 and s["end_reason"] == "concede"


def test_ws_disconnect_grace_forfeit_end_to_end():
    with _client(grace_seconds=0.1) as tc:
        with _pair(tc) as (seats, _):
            p0, p1 = seats[0][0], seats[1][0]
            _close(p1)
            time.sleep(0.3)
            s = None
            for _ in range(10):
                s = _recv(p0, "state")["snapshot"]
                if s["winner"] is not None:
                    break
            assert s["winner"] == 0 and s["end_reason"] == "disconnect"


def test_ws_bot_mode_carries_match_meta():
    with _client() as tc, tc.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s = _recv(ws, "state")
        assert s["match"]["mode"] == "bot" and s["match"]["code"] is None
        assert s["match"]["turn_seconds"] is None
