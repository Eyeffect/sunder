from .conftest import card, make_gs, put_board


def test_summoning_sickness_prevents_attack():
    gs = make_gs()
    b = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    put_board(gs, 0, b)
    inst = gs.players[0].board[0]
    inst.aired_this_turn = True
    assert not gs.can_attack(inst)
    inst.aired_this_turn = False
    assert gs.can_attack(inst)


def test_loud_attacks_same_turn():
    gs = make_gs()
    b = card(type="BROADCAST", stats={"atk": 2, "def": 2}, keywords=["LOUD"])
    put_board(gs, 0, b)
    inst = gs.players[0].board[0]
    inst.aired_this_turn = True
    assert gs.can_attack(inst)


def test_attack_face_reduces_signal():
    gs = make_gs()
    put_board(gs, 0, card(type="BROADCAST", stats={"atk": 3, "def": 3}))
    gs.attack(gs.players[0].board[0], ("FACE", None))
    assert gs.players[1].signal == 27


def test_trade_kills_both():
    gs = make_gs()
    a = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    d = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    put_board(gs, 0, a)
    put_board(gs, 1, d)
    gs.attack(gs.players[0].board[0], ("BROADCAST", gs.players[1].board[0]))
    assert gs.players[0].board == []
    assert gs.players[1].board == []


def test_masked_cannot_be_targeted_until_it_attacks():
    gs = make_gs()
    recorder = card(type="BROADCAST", stats={"atk": 2, "def": 2}, keywords=["MASKED"])
    put_board(gs, 1, recorder)
    put_board(gs, 0, card(type="BROADCAST", stats={"atk": 3, "def": 3}))
    attacker = gs.players[0].board[0]
    recorder_inst = gs.players[1].board[0]
    targets = gs.legal_attack_targets(attacker)
    assert targets == [("FACE", None)]
    # after it attacks, it's revealed
    recorder_inst.attacked_this_turn = 1
    recorder_inst.mask_broken = True
    targets = gs.legal_attack_targets(attacker)
    assert ("BROADCAST", recorder_inst) in targets


def test_beacon_forces_block_and_blocks_face():
    gs = make_gs()
    heap = card(type="BROADCAST", stats={"atk": 0, "def": 3}, keywords=["BEACON"])
    put_board(gs, 1, heap)
    put_board(gs, 1, card(type="BROADCAST", stats={"atk": 1, "def": 1}))
    put_board(gs, 0, card(type="BROADCAST", stats={"atk": 3, "def": 3}))
    attacker = gs.players[0].board[0]
    targets = gs.legal_attack_targets(attacker)
    assert all(k == "BROADCAST" for k, _ in targets)
    assert all(i.has("BEACON") for _, i in targets)


def test_feedback_attacks_twice():
    gs = make_gs()
    jugg = card(type="BROADCAST", stats={"atk": 2, "def": 5}, keywords=["FEEDBACK"])
    put_board(gs, 0, jugg)
    inst = gs.players[0].board[0]
    gs.attack(inst, ("FACE", None))
    assert gs.players[1].signal == 28
    assert gs.can_attack(inst)
    gs.attack(inst, ("FACE", None))
    assert gs.players[1].signal == 26
    assert not gs.can_attack(inst)


def test_win_by_signal_zero():
    gs = make_gs()
    b = card(type="BROADCAST", stats={"atk": 35, "def": 5})
    put_board(gs, 0, b)
    gs.attack(gs.players[0].board[0], ("FACE", None))
    assert gs.winner == 0
    before = gs.players[1].signal
    gs.attack(gs.players[0].board[0], ("FACE", None))
    assert gs.players[1].signal == before
