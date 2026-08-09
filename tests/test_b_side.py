from .conftest import card, make_gs, put_board, put_hand, put_static
from sunder.state import snapshot


def test_bside_owner_hover_reveals_real_card():
    gs = make_gs()
    secret = card(name="Deep Secret", type="BROADCAST",
                  stats={"atk": 2, "def": 2}, keywords=["B_SIDE"])
    put_board(gs, 1, secret)
    inst = gs.players[1].board[0]
    inst.hidden = True

    own = snapshot(gs, viewer=1)
    foe = snapshot(gs, viewer=0)
    own_inst = [c for c in own["players"][1]["board"] if c["serial"] == inst.serial][0]
    foe_inst = [c for c in foe["players"][1]["board"] if c["serial"] == inst.serial][0]

    assert own_inst["hidden"] is True
    assert own_inst["name"] == "Deep Secret"
    assert own_inst["type"] == "BROADCAST"
    assert own_inst["rules"] != ""
    assert foe_inst["name"] == "???"
    assert foe_inst["type"] is None
    assert "rules" not in foe_inst


def test_bside_hidden_on_play():
    gs = make_gs()
    mr = card(type="LOOP", keywords=["B_SIDE"], abilities=[
        {"trigger": "ON_ANY_BROADCAST_PLAYED", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE",
         "value": 1, "condition": {"not_self": True}}])
    put_hand(gs, 0, mr)
    gs.cur.bandwidth = 2
    gs.play_card(0)
    inst = gs.players[0].board[0]
    assert inst.hidden
    assert gs.players[1].signal == 20


def test_bside_reveals_when_another_broadcast_airs():
    gs = make_gs()
    mr = card(name="X", type="LOOP", keywords=["B_SIDE"], abilities=[
        {"trigger": "ON_ANY_BROADCAST_PLAYED", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE",
         "value": 1, "condition": {"not_self": True}}])
    put_hand(gs, 0, mr)
    gs.play_card(0)
    inst = gs.players[0].board[0]
    assert inst.hidden
    hound = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    put_hand(gs, 0, hound)
    gs.play_card(0)
    assert not inst.hidden
    assert gs.players[1].signal == 19
    assert any("B-SIDE" in line for line in gs.log)


def test_bside_untargetable_while_hidden():
    gs = make_gs()
    secret = card(type="BROADCAST", stats={"atk": 2, "def": 2}, keywords=["B_SIDE"])
    put_board(gs, 1, secret)
    sec_inst = gs.players[1].board[0]
    sec_inst.hidden = True
    put_board(gs, 0, card(type="BROADCAST", stats={"atk": 3, "def": 3}))
    attacker = gs.players[0].board[0]
    assert ("BROADCAST", sec_inst) not in gs.legal_attack_targets(attacker)
    sec_inst.hidden = False
    assert ("BROADCAST", sec_inst) in gs.legal_attack_targets(attacker)


def test_static_replay_reveals_and_returns_track():
    gs = make_gs()
    track = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE", "value": 2}])
    put_static(gs, 0, track)
    replay = card(type="LOOP", keywords=["B_SIDE"], abilities=[
        {"trigger": "ON_TURN_END", "effect": "RETURN_FROM_DISCARD", "target": "SELF", "value": 1}])
    put_hand(gs, 0, replay)
    gs.cur.bandwidth = 2
    gs.play_card(0)
    inst = gs.players[0].board[0]
    assert inst.hidden
    gs.end_turn()
    assert not inst.hidden
    assert len(gs.players[0].hand) == 1
