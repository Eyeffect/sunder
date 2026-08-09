import pytest

from sunder.game import GameState
from sunder.schema import parse_card


def card(**kw):
    base = {
        "id": "t", "name": "T", "set": "test", "plane": "test",
        "rarity": "COMMON", "cost": 0, "type": "BROADCAST",
        "stats": {"atk": 1, "def": 1},
        "abilities": [], "keywords": [], "flavor": "",
    }
    base.update(kw)
    return parse_card(base)


def put_hand(gs, pidx, c, n=1):
    pl = gs.players[pidx]
    for _ in range(n):
        inst = gs.make_instance(c, pidx)
        inst.zone = "HAND"
        pl.hand.append(inst)


def put_board(gs, pidx, c, n=1):
    pl = gs.players[pidx]
    for _ in range(n):
        inst = gs.make_instance(c, pidx)
        inst.zone = "AIRWAVES"
        pl.board.append(inst)


def put_static(gs, pidx, c):
    pl = gs.players[pidx]
    inst = gs.make_instance(c, pidx)
    inst.zone = "STATIC"
    pl.static.append(inst)
    return inst


def make_gs(seed=None):
    return GameState([], [], seed=seed)


@pytest.fixture
def gs():
    return make_gs()
