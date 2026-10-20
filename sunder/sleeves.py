"""SUNDER — card-back sleeve manifest (server side).

Backed by `cards/sleeves.json`, mirroring `web/src/sleeves.ts`. Owns the
deck→plane sleeve mapping and the seat fallback (ember / static).
"""

from __future__ import annotations

import json
from pathlib import Path

CARDS_DIR = Path(__file__).parent / "cards"
SLEEVE_PATH = CARDS_DIR / "sleeves.json"

_FALLBACK_SLEEVES = [
    {"id": "default", "label": "Frequency",
     "palette": {"ink": "amber", "glow": "amber", "paper": "voidDeep"}},
    {"id": "ember", "label": "Ember",
     "palette": {"ink": "amber", "glow": "amber", "paper": "voidDeep"}},
    {"id": "static", "label": "Static",
     "palette": {"ink": "magenta", "glow": "magenta", "paper": "voidDeep"}},
]


def load_manifest(path: Path | None = None) -> dict[str, dict]:
    """Parse sleeves.json → {id: sleeve}. Minimally forgiving: a missing
    or malformed file keeps a hardcoded 3-sleeve fallback live."""
    target = Path(path) if path else SLEEVE_PATH
    try:
        data = json.loads(target.read_text())
        sleeves = [s for s in data.get("sleeves", [])
                   if isinstance(s, dict) and isinstance(s.get("id"), str)]
    except (OSError, AttributeError, json.JSONDecodeError):
        sleeves = []
    if not sleeves:
        sleeves = _FALLBACK_SLEEVES
    return {s["id"]: s for s in sleeves}


def deck_plane(deck) -> str | None:
    """The plane a playlist broadcasts from (first card that has one)."""
    for card in deck:
        plane = getattr(card, "plane", None)
        if plane:
            return plane
    return None


def _plane_sleeves(manifest: dict[str, dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in manifest.values():
        plane = s.get("plane")
        if isinstance(plane, str):
            out.setdefault(plane, s["id"])
    return out


def seat_sleeve(manifest: dict[str, dict], deck, index: int) -> str:
    """Deck's plane default, else the legacy seat colors."""
    plane = deck_plane(deck)
    if plane:
        sleeve_id = _plane_sleeves(manifest).get(plane)
        if sleeve_id:
            return sleeve_id
    return "ember" if index == 0 else "static"
