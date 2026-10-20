"""Deck-bound sleeve defaults + seat override plumbing."""

from __future__ import annotations

import json
from pathlib import Path

from sunder.game import GameState
from sunder.schema import load_card_file, parse_card
from sunder.sleeves import (
    _FALLBACK_SLEEVES,
    SLEEVE_PATH,
    deck_plane,
    load_manifest,
    seat_sleeve,
)

from .conftest import card

CARDS_DIR = Path(__file__).parent.parent / "sunder" / "cards"


def _planeless_card():
    return parse_card({"id": "p_1", "name": "Planeless", "set": "t",
                       "rarity": "COMMON", "cost": 1, "type": "TRACK",
                       "abilities": []})


def test_deck_plane_from_playlist():
    deck = load_card_file(CARDS_DIR / "cinderworks.json")
    assert deck_plane(deck) == "cinderworks"
    assert deck_plane([]) is None
    assert deck_plane([_planeless_card()]) is None


def test_deck_bound_defaults():
    manifest = load_manifest()
    neon = load_card_file(CARDS_DIR / "neon_frequency.json")
    cinder = load_card_file(CARDS_DIR / "cinderworks.json")
    assert seat_sleeve(manifest, neon, 0) == "neonfreq"
    assert seat_sleeve(manifest, cinder, 1) == "cinderworks"


def test_unknown_plane_falls_back_to_seat():
    manifest = load_manifest()
    alien = [card(id="alien_1", name="Alien", type="TRACK", plane="atmos_9")]
    assert seat_sleeve(manifest, alien, 1) == "static"
    assert seat_sleeve(manifest, [_planeless_card()], 0) == "ember"


def test_state_uses_deck_bound_sleeves():
    gs = GameState(
        load_card_file(CARDS_DIR / "neon_frequency.json"),
        load_card_file(CARDS_DIR / "cinderworks.json"),
        seed=1,
    )
    assert gs.players[0].sleeve == "neonfreq"
    assert gs.players[1].sleeve == "cinderworks"


def test_load_manifest_fallback_on_missing(tmp_path):
    manifest = load_manifest(tmp_path / "nowhere.json")
    assert set(manifest) == {s["id"] for s in _FALLBACK_SLEEVES}


def test_load_manifest_recovers_from_malformed(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    manifest = load_manifest(bad)
    assert set(manifest) == {s["id"] for s in _FALLBACK_SLEEVES}
    assert SLEEVE_PATH.name == "sleeves.json"  # default path untouched


def test_manifest_round_trip_with_plane(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"schema_version": 1, "sleeves": [
        {"id": "spore", "label": "Sporewake", "pattern": "wavelength",
         "palette": {"ink": "green", "glow": "green", "paper": "voidDeep"},
         "plane": "sporewake"},
    ]}))
    manifest = load_manifest(p)
    # no sporewake.json deck ships yet — synthesize one from its plane id
    deck = [parse_card({"id": "sp_1", "name": "Spore", "set": "t",
                        "plane": "sporewake", "rarity": "COMMON", "cost": 1,
                        "type": "TRACK", "abilities": []})]
    assert seat_sleeve(manifest, deck, 1) == "spore"
    # planes outside this manifest still fall back to the seat color
    assert seat_sleeve(manifest, [card(id="a", name="A")], 1) == "static"
