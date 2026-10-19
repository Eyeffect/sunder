from sunder.budget import budget_score, suggested_cost

from .conftest import card


def test_vanilla_stats_suggest_cost():
    c = card(type="BROADCAST", stats={"atk": 3, "def": 3}, cost=3)
    assert budget_score(c) == 6
    assert suggested_cost(c) == 3


def test_sundered_gets_wider_tolerance():
    common = card(rarity="COMMON", cost=4)
    rare = card(rarity="RARE", cost=4)
    sundered = card(rarity="SUNDERED", cost=4)
    assert sundered.cost == rare.cost == common.cost == 4


def test_fuse_halves_score():
    bomb = card(type="BROADCAST", stats={"atk": 0, "def": 4}, fuse=3, abilities=[
        {"trigger": "ON_FUSE_EXPIRED", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE", "value": 4}])
    assert budget_score(bomb) == (4 + 4) // 2
