"""Legality tables + mechanic validation: the closed grammar is enforced
here, so an LLM-proposed mechanic can never reach a card invalidly."""

from sunder.gen.legality import (normalize_mechanic, mechanic_legal,
                                 validate_mechanic)


def _ok(mechanic):
    ok, reason = validate_mechanic(mechanic)
    assert ok, reason
    return True


def _bad(mechanic, why=None):
    ok, reason = validate_mechanic(mechanic)
    assert not ok
    if why:
        assert why in reason
    return True


FLAT_DAMAGE = {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE",
               "target": "ENEMY_FACE", "scaling": "FLAT", "value": 2}


def test_valid_flat_mechanic():
    _ok(FLAT_DAMAGE)


def test_unknown_enum_values_rejected():
    _bad({**FLAT_DAMAGE, "trigger": "BOGUS"})
    _bad({**FLAT_DAMAGE, "effect": "BOGUS"})
    _bad({**FLAT_DAMAGE, "scaling": "BOGUS"})
    _bad({**FLAT_DAMAGE, "target": "BOGUS"})


def test_target_illegal_for_effect_rejected():
    _bad({**FLAT_DAMAGE, "target": "SELF"}, "illegal")


def test_value_out_of_range_rejected():
    _bad({**FLAT_DAMAGE, "value": 9}, "outside")
    _bad({**FLAT_DAMAGE, "value": 0}, "outside")


def test_value_def_range():
    buff = {"trigger": "ON_PLAY", "effect": "BUFF_STAT", "target": "SELF",
            "scaling": "FLAT", "value": 2, "value_def": 3}
    _bad(buff, "outside")
    _ok({**buff, "value_def": 1})


def test_effect_with_no_host_type_rejected():
    # COUNTER_TRACK exists in the grammar but no card type may host it
    _bad({"trigger": "ON_CAST_TRACK", "effect": "COUNTER_TRACK",
          "target": "SELF", "scaling": "FLAT"}, "no legal card type")


def test_tag_scaling_needs_tag():
    ab = {**FLAT_DAMAGE, "scaling": "X_COUNT_OF_TAG_ON_BOARD"}
    _bad(ab, "requires a tag")
    _ok({**ab, "tag": "vinyl"})


def test_count_type_scaling():
    ab = {"trigger": "ON_TURN_START", "effect": "DEAL_DAMAGE",
          "target": "RANDOM", "scaling": "X_COUNT_OF_TYPE_ON_BOARD"}
    _ok(ab)
    _ok({**ab, "count_type": "LOOP"})
    _bad({**ab, "count_type": "BOGUS"}, "count_type")


def test_grant_keyword_needs_keyword():
    ab = {"trigger": "ON_PLAY", "effect": "GRANT_KEYWORD", "target": "SELF",
          "scaling": "FLAT", "value": 1}
    _bad(ab, "requires a keyword")
    _ok({**ab, "keyword": "LOUD"})


def test_condition_must_be_has_tag_dict():
    ab = {**FLAT_DAMAGE, "trigger": "ON_ANY_BROADCAST_PLAYED",
          "condition": {"has_tag": "vinyl"}}
    _ok(ab)
    _bad({**ab, "condition": {"nope": 1}}, "condition")
    _bad({**ab, "condition": "vinyl"}, "condition")


def test_non_flat_scalings_accepted_without_value():
    for scaling in ("X_TURN_NUMBER", "X_CARDS_PLAYED_THIS_TURN",
                    "X_TIMES_THIS_TRIGGERED_THIS_GAME"):
        _ok({**FLAT_DAMAGE, "scaling": scaling, "value": 5})


def test_normalize_mechanic():
    flat = normalize_mechanic({**FLAT_DAMAGE})
    assert flat["value"] == 2 and flat["value_def"] == 0
    x = normalize_mechanic({**FLAT_DAMAGE,
                            "scaling": "X_TURN_NUMBER", "value": 7})
    assert x["value"] == 1 and x["value_def"] == 0


def test_mechanic_legal_by_type():
    ab = {"trigger": "ON_ATTACK", "effect": "DEAL_DAMAGE",
          "target": "ENEMY_BROADCAST", "scaling": "FLAT", "value": 2}
    assert mechanic_legal(ab, "BROADCAST")
    assert not mechanic_legal(ab, "TRACK")
    assert not mechanic_legal(ab, "LOOP")


def test_loop_only_effect():
    ab = {"trigger": "STATIC", "effect": "GAIN_BANDWIDTH", "target": "SELF",
          "scaling": "FLAT", "value": 1}
    assert mechanic_legal(ab, "LOOP")
    assert mechanic_legal(ab, "BROADCAST")
    assert not mechanic_legal(ab, "TRACK")
