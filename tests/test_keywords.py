from sunder.keywords import KEYWORD_REGISTRY, display, remind, resolve_key
from sunder.lore import rules_text

from .conftest import card, make_gs


def test_registry_has_all_seeded_keywords():
    expected = {
        "LOUD", "RUSH", "ECHO", "AMP", "CARRIER", "BEACON", "DISTORT",
        "FILTER", "DRAIN", "FEEDBACK", "MASKED", "FUSE", "B_SIDE",
    }
    assert expected <= set(KEYWORD_REGISTRY)


def test_legacy_static_maps_to_carrier():
    assert resolve_key("STATIC") == "CARRIER"
    assert display("STATIC") == "CARRIER"
    assert "always" in remind("STATIC").lower()


def test_every_keyword_has_display_and_reminder():
    for key, kw in KEYWORD_REGISTRY.items():
        assert kw.display
        assert kw.reminder


def test_rules_text_renders():
    c = card(type="BROADCAST", stats={"atk": 2, "def": 2}, keywords=["BEACON"])
    text = rules_text(c)
    assert "BEACON" in text


def test_echo_cards_without_on_death_rejected():
    import pytest
    with pytest.raises(Exception):
        card(type="BROADCAST", keywords=["ECHO"], abilities=[])


def test_echo_with_on_death_is_valid():
    c = card(type="BROADCAST", keywords=["ECHO"], abilities=[
        {"trigger": "ON_DEATH", "effect": "GAIN_LIFE", "target": "SELF", "value": 1}])
    assert c.keywords == ["ECHO"]


def test_amp_buffs_itself_when_broadcast_aired():
    from .conftest import put_board, put_hand
    gs = make_gs()
    amp = card(type="BROADCAST", keywords=["AMP"], stats={"atk": 1, "def": 1})
    other = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    put_board(gs, 0, amp)
    put_hand(gs, 0, other)
    gs.play_card(0)
    assert gs.players[0].board[0].buff_atk == 1
    assert gs.players[0].board[0].buff_def == 1


def test_amp_buffs_both_stations_broadcasts():
    from .conftest import put_board, put_hand
    gs = make_gs(seed=0)
    amp_mine = card(type="BROADCAST", keywords=["AMP"], stats={"atk": 1, "def": 1})
    amp_foe = card(type="BROADCAST", keywords=["AMP"], stats={"atk": 1, "def": 1})
    played = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    put_board(gs, 0, amp_mine)
    put_board(gs, 1, amp_foe)
    put_hand(gs, 0, played)
    gs.play_card(0)
    assert gs.players[0].board[0].buff_atk == 1
    assert gs.players[1].board[0].buff_atk == 1
