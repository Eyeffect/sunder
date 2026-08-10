"""SUNDER — tag + keyword registry (shared governance lifecycle).

Tags are the connective tissue the generation system introduces: cards carry
2–4 tags (0–1 load-bearing, 1–3 flavor) and payoffs reference them via
`condition: {"has_tag": …}` or `X_COUNT_OF_TAG_ON_BOARD`. Nothing but the
registry decides which tags exist and whether one is usable.

Both TAG_REGISTRY and KEYWORD_REGISTRY share the same lifecycle:

    proposed  →  approved    (sampler may draw it)
             ↘  rejected

The theme-profile step may *propose* up to two tags per theme; they land in
the review queue and the web REGISTRY panel approves them. The sampler only
ever draws from `approved_*`. Keyword entries are seeded from the engine's
hardcoded KEYWORD_REGISTRY so the two never drift.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROPOSED = "proposed"
APPROVED = "approved"
REJECTED = "rejected"

REGISTRY_DIR = Path(__file__).parent / "cards"
REGISTRY_PATH = REGISTRY_DIR / "registry.json"

_KNOWN_KINDS = ("tag", "keyword")
_VALID_STATUSES = (PROPOSED, APPROVED, REJECTED)
_SECTION = {"tag": "tags", "keyword": "keywords"}

# Starter tags are deliberately theme-neutral so generation works out of the
# box; theme-specific tags arrive through the propose → approve flow.
_STARTER_TAGS: list[dict[str, str]] = [
    {"id": "vinyl", "definition": "records, grooves, needle, analog",
     "reminder": "Old-school media — records, tapes, film."},
    {"id": "chrome", "definition": "metal, neon, machines, polished surfaces",
     "reminder": "Machines and polished metal."},
    {"id": "ghost", "definition": "unseen, memory, residual, spectral",
     "reminder": "Something that was there — or was never there."},
    {"id": "static", "definition": "interference, noise, broken signal, hiss",
     "reminder": "Interference in the signal."},
    {"id": "ember", "definition": "heat, fire, slow burning, warmth",
     "reminder": "Slow heat that keeps going."},
    {"id": "tide", "definition": "water, waves, cycles, ebb and flow",
     "reminder": "Things that come and go in cycles."},
]

_CACHE: dict[str, Any] | None = None


@dataclass
class RegistryEntry:
    kind: str
    id: str
    definition: str
    reminder: str
    status: str


# ---------------------------------------------------------------- storage

def _default_data() -> dict[str, Any]:
    from .keywords import KEYWORD_REGISTRY
    keywords = [
        {"id": k, "definition": v.reminder, "reminder": v.reminder, "status": APPROVED}
        for k, v in KEYWORD_REGISTRY.items()
    ]
    return {
        "schema_version": 1,
        "tags": [_with_status(t, APPROVED) for t in _STARTER_TAGS],
        "keywords": keywords,
    }


def _with_status(entry: dict[str, str], status: str) -> dict[str, str]:
    return {**entry, "status": status}


def load_registry(force_reload: bool = False) -> dict[str, Any]:
    """Return the registry data, re-syncing keywords from the engine."""
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE
    if REGISTRY_PATH.exists():
        try:
            data = json.loads(REGISTRY_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            data = _default_data()
    else:
        data = _default_data()
    _sync_keywords(data)
    _CACHE = data
    return data


def save_registry(data: dict[str, Any] | None = None) -> None:
    """Persist the registry atomically (and refresh the module cache)."""
    global _CACHE
    data = data if data is not None else (_CACHE or load_registry())
    fd, tmp = tempfile.mkstemp(dir=str(REGISTRY_DIR), prefix="registry.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, REGISTRY_PATH)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    _CACHE = data


def _sync_keywords(data: dict[str, Any]) -> None:
    """Mirror the engine's KEYWORD_REGISTRY so governance never drifts."""
    from .keywords import KEYWORD_REGISTRY
    known = {e["id"]: e for e in data.get("keywords", [])}
    for k, v in KEYWORD_REGISTRY.items():
        if k not in known:
            data.setdefault("keywords", []).append(
                {"id": k, "definition": v.reminder, "reminder": v.reminder,
                 "status": APPROVED}
            )


# ---------------------------------------------------------------- queries

def _entries(kind: str, data: dict[str, Any] | None = None) -> list[dict[str, str]]:
    data = data if data is not None else load_registry()
    return list(data.get(_SECTION.get(kind, kind), []))


def approved_ids(kind: str) -> frozenset[str]:
    return frozenset(e["id"] for e in _entries(kind) if e.get("status") == APPROVED)


def approved_tags() -> frozenset[str]:
    return approved_ids("tags")


def approved_keywords() -> frozenset[str]:
    return approved_ids("keywords")


def tag_definition(tag_id: str) -> str:
    for e in _entries("tags"):
        if e["id"] == tag_id:
            return e.get("definition", "") or e.get("reminder", "")
    return ""


def all_entries(kind: str) -> list[RegistryEntry]:
    return [
        RegistryEntry(kind=kind, id=e["id"], definition=e.get("definition", ""),
                      reminder=e.get("reminder", ""), status=e.get("status", PROPOSED))
        for e in _entries(kind)
    ]


# ---------------------------------------------------------------- mutations

def propose(kind: str, entry_id: str, definition: str = "", reminder: str = "") -> RegistryEntry:
    """Add an entry to the review queue, or re-open a rejected one."""
    if kind not in _KNOWN_KINDS:
        raise ValueError(f"unknown registry kind {kind!r}")
    if not entry_id or not entry_id.islower() or not entry_id.replace("_", "").isalnum():
        raise ValueError("entry id must be lowercase snake_case")
    data = load_registry()
    for e in _entries(kind, data):
        if e["id"] == entry_id:
            e["definition"] = definition or e.get("definition", "")
            e["reminder"] = reminder or e.get("reminder", "")
            if e.get("status") == REJECTED:
                e["status"] = PROPOSED
            save_registry(data)
            return RegistryEntry(kind, entry_id, e["definition"], e["reminder"], e["status"])
    entry = {"id": entry_id, "definition": definition, "reminder": reminder,
             "status": PROPOSED}
    data.setdefault(_SECTION[kind], []).append(entry)
    save_registry(data)
    return RegistryEntry(kind, entry_id, definition, reminder, PROPOSED)


def set_status(kind: str, entry_id: str, status: str) -> RegistryEntry | None:
    if kind not in _KNOWN_KINDS:
        raise ValueError(f"unknown registry kind {kind!r}")
    if status not in _VALID_STATUSES:
        raise ValueError(f"unknown status {status!r}")
    data = load_registry()
    for e in _entries(kind, data):
        if e["id"] == entry_id:
            e["status"] = status
            save_registry(data)
            return RegistryEntry(kind, entry_id, e["definition"], e["reminder"], status)
    return None


def approve(kind: str, entry_id: str) -> RegistryEntry | None:
    return set_status(kind, entry_id, APPROVED)


def reject(kind: str, entry_id: str) -> RegistryEntry | None:
    return set_status(kind, entry_id, REJECTED)
