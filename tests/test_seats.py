"""Phase 0 (multiplayer groundwork): winner-0 regression + seat-aware rooms."""

import asyncio

import pytest

from sunder import ai
from sunder.game import GameState
from sunder.server.app import default_decks
from sunder.server.match import BotSeat, MatchRoom, Seat
from tests.conftest import card, put_board, put_hand

# ---------------------------------------------------------------- winner == 0


def _won_by_station_0():
    gs = GameState(*default_decks(), seed=1)
    gs.start_game()
    gs.players[1].signal = 0
    gs.check_win()
    assert gs.winner == 0
    return gs


def test_station_0_win_logged_once():
    gs = _won_by_station_0()
    gs.check_win()
    gs.check_win()
    assert sum(e["kind"] == "win" for e in gs.history) == 1
    assert gs.game_over


def test_station_0_win_freezes_turns():
    gs = _won_by_station_0()
    turn, cur = gs.turn, gs.current
    gs.end_turn()
    assert (gs.turn, gs.current) == (turn, cur)


def test_station_0_win_blocks_actions():
    gs = _won_by_station_0()
    with pytest.raises(ValueError, match="game over"):
        gs.play_card(0)
    assert not any(gs.is_playable(i) for i in gs.cur.hand)
    attacker = card(name="A", keywords=["LOUD"])
    put_board(gs, gs.current, attacker)
    assert not gs.can_attack(gs.cur.board[-1])


def test_station_1_win_unchanged():
    gs = GameState(*default_decks(), seed=1)
    gs.start_game()
    gs.players[0].signal = 0
    gs.check_win()
    gs.end_turn()
    assert gs.winner == 1 and gs.turn == 1


def test_ai_does_nothing_after_station_0_won():
    gs = _won_by_station_0()
    gs.current = 1  # even if it were the bot's turn
    hand, log_len = len(gs.players[1].hand), len(gs.log)
    assert list(ai.iter_turn(gs)) == []
    assert len(gs.players[1].hand) == hand and len(gs.log) == log_len


# ---------------------------------------------------------------- rooms


class FakeSeat(Seat):
    def __init__(self, index):
        super().__init__(index)
        self.inbox = []

    async def send(self, payload):
        self.inbox.append(payload)

    @property
    def last(self):
        return [m for m in self.inbox if m["type"] == "state"][-1]["snapshot"]


SLEEVES = {"ember": {}, "default": {}}
AVATARS = {"frequency": {}}


def _pvp(seed=1):
    gs = GameState(*default_decks(), seed=seed)
    gs.start_game()
    a, b = FakeSeat(0), FakeSeat(1)
    return gs, MatchRoom(gs, [a, b]), a, b


def _run(coro):
    return asyncio.run(coro)


def test_room_requires_one_seat_per_station():
    gs = GameState(*default_decks(), seed=1)
    with pytest.raises(ValueError):
        MatchRoom(gs, [FakeSeat(0), FakeSeat(0)])


def test_each_seat_gets_its_own_viewer():
    gs, room, a, b = _pvp()

    async def go():
        await room.broadcast()
    _run(go())
    assert a.last["viewer"] == 0 and a.last["can_act"] is True
    assert b.last["viewer"] == 1 and b.last["can_act"] is False
    # Hidden information: each seat sees only its own hand.
    assert [c["serial"] for c in a.last["hand"]] == [i.serial for i in gs.players[0].hand]
    assert [c["serial"] for c in b.last["hand"]] == [i.serial for i in gs.players[1].hand]
    assert "hand" not in a.last["foe"] and a.last["foe"]["hand_count"] == len(gs.players[1].hand)


def test_seat_cannot_act_out_of_turn():
    gs, room, a, b = _pvp()

    async def go():
        assert await room.handle(b, {"type": "play", "hand": 0},
                                 sleeves=SLEEVES, avatars=AVATARS) == "not your turn"
        await room.handle(b, {"type": "end_turn", "turn": gs.turn},
                          sleeves=SLEEVES, avatars=AVATARS)
    _run(go())
    assert gs.current == 0 and gs.turn == 1


def test_turn_passes_between_two_humans():
    gs, room, a, b = _pvp()

    async def go():
        await room.handle(a, {"type": "end_turn", "turn": 1}, sleeves=SLEEVES, avatars=AVATARS)
        assert gs.current == 1 and b.last["can_act"] and not a.last["can_act"]
        # station 1 now plays a real move through its own seat
        idx = next(i for i, c in enumerate(b.last["hand"])
                   if c["is_playable"] and not c["needs_target"])
        err = await room.handle(b, {"type": "play", "hand": idx},
                                sleeves=SLEEVES, avatars=AVATARS)
        assert err is None
        await room.handle(b, {"type": "end_turn", "turn": 2}, sleeves=SLEEVES, avatars=AVATARS)
    _run(go())
    assert gs.current == 0 and gs.turn == 3


def test_cosmetics_apply_to_sender_seat():
    gs, room, a, b = _pvp()

    async def go():
        assert await room.handle(b, {"type": "set_sleeve", "sleeve": "default"},
                                 sleeves=SLEEVES, avatars=AVATARS) is None
    _run(go())
    assert gs.players[1].sleeve == "default"
    assert a.last["foe"]["sleeve"] == "default"


def _buff_track():
    return card(id="buff", name="Boost", type="TRACK", stats=None, cost=0, abilities=[
        {"trigger": "ON_PLAY", "effect": "BUFF_STAT", "target": "CHOSEN",
         "scaling": "FLAT", "value": 2, "value_def": 2}])


def test_friendly_targeted_track_resolves():
    """Regression: CHOSEN buffs used to look the target up on the enemy board only."""
    gs, room, a, b = _pvp()
    put_board(gs, 0, card(id="mine", name="Mine", stats={"atk": 1, "def": 1}))
    mine = gs.players[0].board[-1]
    gs.players[0].hand.clear()
    put_hand(gs, 0, _buff_track())

    async def go():
        return await room.handle(a, {"type": "play", "hand": 0, "target": mine.serial},
                                 sleeves=SLEEVES, avatars=AVATARS)
    assert _run(go()) is None
    assert gs.effective_atk(mine) == 3


def test_illegal_target_rejected_without_state_change():
    gs, room, a, b = _pvp()
    gs.players[0].hand.clear()
    put_hand(gs, 0, _buff_track())

    async def go():
        return await room.handle(a, {"type": "play", "hand": 0, "target": 99999},
                                 sleeves=SLEEVES, avatars=AVATARS)
    assert _run(go()) == "bad target"
    assert len(gs.players[0].hand) == 1


def test_stray_target_on_untargeted_card_is_ignored():
    gs, room, a, b = _pvp()
    gs.players[0].hand.clear()
    put_hand(gs, 0, card(id="plain", name="Plain", cost=0))

    async def go():
        return await room.handle(a, {"type": "play", "hand": 0, "target": 424242},
                                 sleeves=SLEEVES, avatars=AVATARS)
    assert _run(go()) is None
    assert gs.players[0].board[-1].card.name == "Plain"


def test_bot_vs_bot_room_finishes():
    gs = GameState(*default_decks(), seed=3)
    gs.start_game()
    room = MatchRoom(gs, [BotSeat(0, 0, 0), BotSeat(1, 0, 0)])

    async def go():
        room.kick()
        await asyncio.wait_for(room._bot_task, timeout=20)
    _run(go())
    assert gs.game_over and gs.winner in (0, 1)


def test_human_vs_bot_room_returns_turn():
    gs = GameState(*default_decks(), seed=1)
    gs.start_game()
    human = FakeSeat(0)
    room = MatchRoom(gs, [human, BotSeat(1, 0, 0)])

    async def go():
        await room.handle(human, {"type": "end_turn", "turn": 1},
                          sleeves=SLEEVES, avatars=AVATARS)
        await asyncio.wait_for(room._bot_task, timeout=10)
    _run(go())
    assert gs.current == 0 and gs.turn == 3 and human.last["can_act"]
