"""Tag mechanic: engine conditions/scaling, schema governance, rules text."""

import pytest

from sunder import engine
from sunder.lore import rules_text
from sunder.primitives import Scaling
from sunder.schema import SchemaError, parse_card

from .conftest import card, make_gs, put_board, put_hand


def test_card_tags_round_trip():
    c = card(tags=["ember", "vinyl"])
    assert c.tags == ["ember", "vinyl"]


def test_unknown_tag_rejected():
    with pytest.raises(SchemaError):
        card(tags=["flimflam"])


def test_too_many_tags_rejected():
    with pytest.raises(SchemaError):
        card(tags=["vinyl", "chrome", "ghost", "static", "ember", "tide"])


def test_duplicate_tags_rejected():
    with pytest.raises(SchemaError):
        card(tags=["ember", "ember"])


# ---------------------------------------------------------------- has_tag

def _payoff():
    return card(type="BROADCAST", stats={"atk": 1, "def": 1}, tags=["ember"],
                abilities=[{
                    "trigger": "ON_ANY_BROADCAST_PLAYED",
                    "effect": "DEAL_DAMAGE",
                    "target": "ENEMY_FACE",
                    "value": 1,
                    "condition": {"has_tag": "ember"},
                }])


def test_has_tag_fires_only_on_matching_event():
    gs = make_gs()
    put_board(gs, 0, _payoff())
    put_hand(gs, 0, card(type="BROADCAST", tags=["ember"],
                         stats={"atk": 1, "def": 1}))
    put_hand(gs, 0, card(type="BROADCAST", tags=["vinyl"],
                         stats={"atk": 1, "def": 1}))
    gs.cur.bandwidth = 10
    gs.play_card(0)  # ember broadcast airs -> payoff fires
    assert gs.players[1].signal == 29
    gs.play_card(0)  # vinyl broadcast airs -> no fire
    assert gs.players[1].signal == 29


def test_has_tag_condition_missing_event_never_fires():
    gs = make_gs()
    put_board(gs, 0, _payoff())
    assert gs.players[1].signal == 30  # nothing played, nothing happens


def test_has_tag_rules_text():
    text = rules_text(_payoff())
    assert "ember" in text
    assert "Whenever a Broadcast with the ember tag is aired" in text


# ---------------------------------------------------------------- scaling

def test_x_count_of_tag_on_board():
    gs = make_gs()
    booster = card(type="BROADCAST", stats={"atk": 1, "def": 1}, tags=["ember"],
                   abilities=[{
                       "trigger": "ON_PLAY",
                       "effect": "DEAL_DAMAGE",
                       "target": "ENEMY_FACE",
                       "scaling": "X_COUNT_OF_TAG_ON_BOARD",
                       "tag": "ember",
                       "value": 0,
                   }])
    put_board(gs, 0, card(type="BROADCAST", tags=["ember"], stats={"atk": 1, "def": 1}))
    put_board(gs, 0, card(type="BROADCAST", tags=["ember"], stats={"atk": 1, "def": 1}))
    put_hand(gs, 0, booster)
    gs.cur.bandwidth = 10
    gs.play_card(0)
    # booster (ember) + 2 ember broadcasts already on board = 3
    assert gs.players[1].signal == 27


def test_x_count_of_tag_counts_both_stations():
    gs = make_gs()
    booster = card(type="BROADCAST", stats={"atk": 1, "def": 1}, tags=["ember"],
                   abilities=[{
                       "trigger": "ON_PLAY",
                       "effect": "DEAL_DAMAGE",
                       "target": "ENEMY_FACE",
                       "scaling": "X_COUNT_OF_TAG_ON_BOARD",
                       "tag": "ember",
                       "value": 0,
                   }])
    put_board(gs, 1, card(type="BROADCAST", tags=["ember"], stats={"atk": 1, "def": 1}))
    put_hand(gs, 0, booster)
    gs.cur.bandwidth = 10
    gs.play_card(0)
    # booster + 1 rival ember = 2
    assert gs.players[1].signal == 28


def test_x_count_tag_scaling_rules_text():
    booster = card(type="BROADCAST", stats={"atk": 1, "def": 1}, tags=["ember"],
                   abilities=[{
                       "trigger": "ON_PLAY",
                       "effect": "DEAL_DAMAGE",
                       "target": "ENEMY_FACE",
                       "scaling": "X_COUNT_OF_TAG_ON_BOARD",
                       "tag": "ember",
                       "value": 0,
                   }])
    text = rules_text(booster)
    assert "ember" in text
    assert "X" in text


def test_ability_tag_payload_parsed():
    c = card(type="BROADCAST", tags=["ember"],
             abilities=[{"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE",
                         "target": "ENEMY_FACE",
                         "scaling": "X_COUNT_OF_TAG_ON_BOARD",
                         "tag": "ember", "value": 0}])
    assert c.abilities[0].tag == "ember"
    assert c.abilities[0].scaling is Scaling.X_COUNT_OF_TAG_ON_BOARD


# ------------------------------------------------------- target rendering

def _ab(abilities, **kw):
    base = {"type": "BROADCAST", "stats": {"atk": 1, "def": 1},
            "abilities": abilities}
    base.update(kw)
    return card(**base)


def test_deal_damage_renders_face_target():
    text = rules_text(_ab([{
        "trigger": "ON_TURN_END", "effect": "DEAL_DAMAGE",
        "target": "ENEMY_FACE", "value": 1}]))
    assert text == "At the end of your turn: deal 1 Noise to the rival station."


def test_deal_damage_renders_all_enemy_broadcasts_target():
    text = rules_text(_ab([{
        "trigger": "ON_PLAY", "effect": "DEAL_DAMAGE",
        "target": "ALL_ENEMY_BROADCASTS", "value": 1}]))
    assert text == "When this enters play: deal 1 Noise to all enemy Broadcasts."


def test_deal_damage_renders_random_target():
    text = rules_text(_ab([{
        "trigger": "ON_PLAY", "effect": "DEAL_DAMAGE",
        "target": "RANDOM", "value": 1}]))
    assert text == "When this enters play: deal 1 Noise to a random Broadcast."


def test_buff_stat_renders_your_broadcasts_target():
    text = rules_text(_ab([{
        "trigger": "STATIC", "effect": "BUFF_STAT",
        "target": "ALL_YOUR_BROADCASTS", "value": 1, "value_def": 1}]))
    assert text == "Always on: +1/+1 to your Broadcasts."


def test_self_effects_stay_bare():
    text = rules_text(_ab([{
        "trigger": "ON_PLAY", "effect": "DRAW_CARD", "target": "SELF",
        "value": 1}]))
    assert text == "When this enters play: cue 1."
    assert "self" not in text


def test_template_targets_unchanged():
    jam = rules_text(_ab([{
        "trigger": "ON_PLAY", "effect": "DESTROY",
        "target": "ENEMY_BROADCAST"}]))
    assert jam == "When this enters play: jam an enemy Broadcast."
    grant = rules_text(_ab([{
        "trigger": "ON_PLAY", "effect": "GRANT_KEYWORD",
        "target": "CHOSEN", "keyword": "LOUD"}]))
    assert grant == "When this enters play: grant LOUD to a chosen Broadcast."


def test_schema_and_lore_renderers_agree():
    from sunder.schema import Card
    c = _ab([{"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE",
              "target": "ENEMY_FACE", "value": 1}])
    assert isinstance(c, Card)
    assert c.rules_text() == rules_text(c)

