import json

from sunder.avatars import AVATAR_PATH, load_avatars


def test_manifest_is_well_formed():
    data = json.loads(AVATAR_PATH.read_text())
    avatars = data["avatars"]
    ids = [a["id"] for a in avatars]
    assert len(ids) == len(set(ids))
    assert avatars[0]["id"] == "frequency"
    assert avatars[0]["glyph"] == "◉"
    glyphs = {a["glyph"] for a in avatars}
    assert {"≈", "⌁", "◍", "◎", "❋", "▤", "⏵", "◬", "‖"} <= glyphs
    for a in avatars:
        assert isinstance(a["label"], str) and a["label"]
        assert isinstance(a["glyph"], str) and a["glyph"]


def test_load_avatars_indexes_by_id():
    avatars = load_avatars()
    assert avatars["cinder"]["glyph"] == "⌁"
    assert avatars["callsign"]["label"] == "Call Sign"


def test_missing_manifest_keeps_a_default(tmp_path):
    avatars = load_avatars(tmp_path / "nope.json")
    assert list(avatars) == ["frequency"]
    assert avatars["frequency"]["glyph"] == "◉"
