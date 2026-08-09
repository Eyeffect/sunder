from pathlib import Path

import pytest

from sunder.budget import check_budget
from sunder.schema import SchemaError, load_card_file

CARDS = Path(__file__).parent.parent / "sunder" / "cards"


def test_starter_sets_parse():
    neon = load_card_file(CARDS / "neon_frequency.json")
    cw = load_card_file(CARDS / "cinderworks.json")
    assert len(neon) == 10
    assert len(cw) == 10


def test_all_starter_cards_pass_budget():
    for f in ("neon_frequency.json", "cinderworks.json"):
        for c in load_card_file(CARDS / f):
            result = check_budget(c)
            assert result["ok"], f"{c.name}: {result}"


def test_unknown_effect_rejected():
    from .conftest import card
    with pytest.raises(SchemaError):
        card(abilities=[{"trigger": "ON_PLAY", "effect": "TELEPORT", "target": "SELF"}])


def test_too_many_abilities_rejected():
    from .conftest import card
    ab = {"trigger": "ON_PLAY", "effect": "GAIN_LIFE", "target": "SELF"}
    with pytest.raises(SchemaError):
        card(abilities=[ab, ab, ab, ab])


def test_zero_abilities_is_valid_for_vanilla():
    from .conftest import card
    c = card(type="LOOP", abilities=[])
    assert c.type.value == "LOOP"


def test_unknown_keyword_rejected():
    from .conftest import card
    with pytest.raises(SchemaError):
        card(keywords=["TURBO"])
