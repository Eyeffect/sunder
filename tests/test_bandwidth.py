from .conftest import card, make_gs, put_hand


def test_bandwidth_ramps_one_per_own_turn():
    gs = make_gs()
    gs.start_game()
    assert gs.players[0].max_bandwidth == 1
    gs.end_turn()
    assert gs.players[1].max_bandwidth == 1
    assert gs.players[1].bandwidth == 1
    gs.end_turn()
    assert gs.players[0].max_bandwidth == 2
    assert gs.players[0].bandwidth == 2


def test_gain_bandwidth_generates_this_turn():
    gs = make_gs()
    gen = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "GAIN_BANDWIDTH", "target": "SELF", "value": 2}])
    put_hand(gs, 0, gen)
    gs.cur.bandwidth = 3
    gs.play_card(0)
    assert gs.cur.bandwidth == 5


def test_uncap_bandwidth_removes_cap():
    gs = make_gs()
    uncap = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "UNCAP_BANDWIDTH", "target": "SELF", "value": 1}])
    put_hand(gs, 0, uncap)
    gs.cur.bandwidth = 1
    gs.play_card(0)
    assert gs.players[0].uncapped
    gs.players[0].turns_taken = 12
    gs.players[0].bandwidth_bonus = 0
    assert gs.players[0].current_max_bandwidth() == 12
    # the capped rival stays at the 10 cap
    gs.players[1].turns_taken = 12
    assert gs.players[1].current_max_bandwidth() == 10


def test_bandwidth_bonus_raises_cap():
    gs = make_gs()
    gs.players[0].bandwidth_bonus = 2
    gs.players[0].turns_taken = 3
    assert gs.players[0].current_max_bandwidth() == 5


def test_second_station_gets_coin():
    gs = make_gs()
    gs.start_game()
    hand = gs.players[1].hand
    assert len(hand) == 1
    assert hand[0].card.name == "Signal Spike"
    assert gs.players[0].hand == []


def test_coin_grants_one_bandwidth_this_turn_only():
    gs = make_gs()
    gs.start_game()
    gs.end_turn()  # Station 2's turn
    p = gs.cur
    assert gs.current == 1
    before = p.bandwidth
    idx = next(i for i, c in enumerate(p.hand) if c.card.id == "SIGNAL_SPIKE")
    gs.play_card(idx)
    assert p.bandwidth == before + 1
    assert "generates 1 Bandwidth" in gs.log[-1]
    gs.end_turn()
    # the spike never raised the cap and is gone by the next refill
    assert p.max_bandwidth == min(10, p.turns_taken)
    gs.end_turn()
    gs.end_turn()  # Station 2's next turn: refilled exactly to max, no spike
    assert p.bandwidth == p.max_bandwidth
