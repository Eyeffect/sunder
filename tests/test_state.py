from .conftest import card, make_gs, put_board, put_hand


def test_snapshot_shape():
    from pathlib import Path
    from sunder.schema import load_card_file
    from sunder.state import snapshot
    here = Path(__file__).parent.parent / "sunder" / "cards"
    gs = make_gs()
    for idx, deck in ((0, "neon_frequency.json"), (1, "cinderworks.json")):
        gs.players[idx].playlist.clear()
        for c in load_card_file(here / deck):
            gs.players[idx].playlist.append(gs.make_instance(c, idx))
    gs.start_game()
    s = snapshot(gs)
    assert s["turn"] == 1 and s["current"] == 0 and s["winner"] is None
    assert len(s["hand"]) == 5
    assert s["me"]["hand_count"] == 5
    assert s["foe"]["hand_count"] == 5  # 4 opening cards + Signal Spike
    assert s["me"]["sleeve"] == "ember"
    assert s["foe"]["sleeve"] == "static"
    assert set(s) >= {"turn", "current", "phase", "winner", "status",
                      "viewer", "can_act", "players", "me", "foe", "hand", "log"}


def test_bside_masked():
    from sunder.state import snapshot
    gs = make_gs()
    put_board(gs, 1, card(type="LOOP", keywords=["B_SIDE"]))
    inst = gs.players[1].board[0]
    inst.hidden = True
    s = snapshot(gs)
    foe_card = s["foe"]["board"][0]
    assert foe_card["hidden"] is True
    assert foe_card["name"] == "???"
    assert "id" not in foe_card
    assert foe_card["keywords"] == ["B_SIDE"]


def test_hand_has_playability_data():
    from sunder.state import snapshot
    gs = make_gs()
    put_board(gs, 1, card(type="BROADCAST", stats={"atk": 1, "def": 1}))
    track = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "CHOSEN", "value": 2}])
    put_hand(gs, 0, track)
    gs.cur.bandwidth = 2
    s = snapshot(gs)
    h = s["hand"][0]
    assert h["needs_target"] is True
    assert h["legal_targets"] == [gs.players[1].board[0].serial]
    assert h["is_playable"] is True


def test_can_act_flips():
    from sunder.state import snapshot
    gs = make_gs()
    assert snapshot(gs)["can_act"] is True
    gs.end_turn()
    assert snapshot(gs)["can_act"] is False
    gs.players[0].signal = -5
    gs.check_win()
    assert snapshot(gs)["can_act"] is False
    assert snapshot(gs)["winner"] == 1


def test_attack_targets_serialized():
    from sunder.state import snapshot
    gs = make_gs()
    put_board(gs, 0, card(type="BROADCAST", stats={"atk": 2, "def": 2}))
    put_board(gs, 1, card(type="BROADCAST", stats={"atk": 1, "def": 1}))
    s = snapshot(gs)
    me_card = s["me"]["board"][0]
    assert me_card["can_attack"] is True  # never aired this turn
    assert {"kind": "broadcast", "serial": gs.players[1].board[0].serial} in me_card["attack_targets"]
    assert {"kind": "face"} in me_card["attack_targets"]
    gs.players[0].board[0].aired_this_turn = True
    assert snapshot(gs)["me"]["board"][0]["can_attack"] is False
