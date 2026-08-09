from .conftest import card, make_gs, put_board


def test_distort_does_not_one_shot_station():
    """DISTORT only affects Broadcasts — face damage is plain atk."""
    gs = make_gs()
    tower = card(type="BROADCAST", stats={"atk": 2, "def": 4}, keywords=["DISTORT"])
    put_board(gs, 0, tower)
    inst = gs.players[0].board[0]
    gs.attack(inst, ("FACE", None))
    assert gs.players[1].signal == 18  # 2 noise, not lethal


def test_distort_one_shots_broadcast_ignoring_def():
    """DISTORT is lethal to a Broadcast even when def > atk."""
    gs = make_gs()
    tower = card(type="BROADCAST", stats={"atk": 2, "def": 4}, keywords=["DISTORT"])
    wall = card(type="BROADCAST", stats={"atk": 0, "def": 5})
    put_board(gs, 0, tower)
    put_board(gs, 1, wall)
    t, w = gs.players[0].board[0], gs.players[1].board[0]
    gs.attack(t, ("BROADCAST", w))
    assert w not in gs.players[1].board


def test_filter_blocks_one_distort_hit():
    """FILTER's shield is checked before DISTORT's lethality."""
    gs = make_gs()
    tower = card(type="BROADCAST", stats={"atk": 3, "def": 4}, keywords=["DISTORT"])
    cap = card(type="BROADCAST", stats={"atk": 1, "def": 4}, keywords=["FILTER"])
    put_board(gs, 0, tower)
    put_board(gs, 1, cap)
    t, c = gs.players[0].board[0], gs.players[1].board[0]

    gs.attack(t, ("BROADCAST", c))
    assert c in gs.players[1].board
    assert c.damage_taken == 0 and c.filter_spent

    t.attacked_this_turn = 0
    gs.attack(t, ("BROADCAST", c))
    assert c not in gs.players[1].board  # shield gone → lethal
