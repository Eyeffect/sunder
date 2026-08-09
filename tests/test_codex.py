import json

from sunder.codex import all_cards, find, format_card, list_all, to_json


def test_list_covers_all_starter_sets():
    text = list_all()
    assert "[neon_frequency]" in text
    assert "[cinderworks]" in text
    for c in all_cards():
        assert c.name in text


def test_find_by_partial_name_and_id():
    assert [c.id for c in find("vinyl")] == ["vg_001"]
    assert [c.id for c in find("replay")] == ["cw_011"]
    assert find("does not exist") == []


def test_format_card_renders():
    c = find("juggernaut")[0]
    text = format_card(c)
    assert "Juggernaut" in text
    assert "5/5" in text
    assert "FEEDBACK" in text
    assert "Budget:" in text


def test_to_json_is_valid_and_uses_enum_values():
    c = find("final")[0]
    raw = json.loads(to_json(c))
    assert raw["type"] == "TRACK"
    assert raw["rarity"] == "SUNDERED"
    assert raw["abilities"][0]["effect"] == "DEAL_DAMAGE"
