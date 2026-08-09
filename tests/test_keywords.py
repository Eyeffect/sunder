from sunder.keywords import KEYWORD_REGISTRY, display, remind, resolve_key
from sunder.lore import rules_text

from .conftest import card


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
