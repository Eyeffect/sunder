"""SUNDER — station profile-icon registry.

Glyphs live in `cards/avatars.json` and are independent of sleeve picks:
the player chooses an icon id, and the UI tints it with the station's
sleeve ink. Served at `GET /api/avatars`; validated on WS `set_avatar`.
"""

from __future__ import annotations

import json
from pathlib import Path

CARDS_DIR = Path(__file__).parent / "cards"
AVATAR_PATH = CARDS_DIR / "avatars.json"

_FALLBACK_AVATARS = [
    {"id": "frequency", "label": "Frequency", "glyph": "◉"},
]


def load_avatars(path: Path | None = None) -> dict[str, dict]:
    """Parse avatars.json → {id: avatar}. Malformed/missing files keep a
    single default icon live so the station dial always has something."""
    target = Path(path) if path else AVATAR_PATH
    try:
        data = json.loads(target.read_text())
        avatars = [a for a in data.get("avatars", [])
                   if isinstance(a, dict)
                   and isinstance(a.get("id"), str)
                   and isinstance(a.get("glyph"), str)]
    except (OSError, AttributeError, json.JSONDecodeError):
        avatars = []
    if not avatars:
        avatars = _FALLBACK_AVATARS
    return {a["id"]: a for a in avatars}
