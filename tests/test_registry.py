"""Registry governance: lifecycle, persistence, schema gating."""

import json

import pytest

import sunder.registry as registry
from sunder.registry import (
    APPROVED,
    PROPOSED,
    REJECTED,
    approve,
    approved_tags,
    load_registry,
    propose,
    reject,
    save_registry,
)


@pytest.fixture
def reg(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "REGISTRY_DIR", tmp_path)
    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "registry.json")
    registry._CACHE = None
    yield tmp_path / "registry.json"
    registry._CACHE = None


def test_seed_loaded(reg):
    data = load_registry()
    assert APPROVED in {t["status"] for t in data["tags"]}
    assert "vinyl" in approved_tags()
    assert len(data["keywords"]) >= 12


def test_propose_approve_reject_roundtrip(reg):
    e = propose("tag", "neon", "glowing signs", "Bright and loud.")
    assert e.status == PROPOSED
    e = approve("tag", "neon")
    assert e.status == APPROVED
    assert "neon" in approved_tags()
    e = reject("tag", "neon")
    assert e.status == REJECTED
    assert "neon" not in approved_tags()


def test_propose_persists_to_disk(reg):
    propose("tag", "neon", "glowing signs", "Bright.")
    data = json.loads(reg.read_text())
    assert any(t["id"] == "neon" and t["status"] == PROPOSED for t in data["tags"])


def test_propose_with_mechanic_roundtrips(reg):
    from sunder.registry import all_entries, tag_mechanic
    mech = {"trigger": "ON_PLAY", "effect": "DRAW_CARD", "target": "SELF",
            "scaling": "FLAT", "value": 1}
    e = propose("tag", "probe", "a scan", "derived reminder", mechanic=mech)
    assert e.mechanic == mech
    # persisted on disk
    data = json.loads(reg.read_text())
    saved = next(t for t in data["tags"] if t["id"] == "probe")
    assert saved["mechanic"] == mech
    # readable back through the public query
    assert tag_mechanic("probe") == mech
    entry = next(x for x in all_entries("tags") if x.id == "probe")
    assert entry.mechanic == mech
    assert all(x.mechanic is None for x in all_entries("tags") if x.id != "probe")


def test_mechanic_survives_approval(reg):
    from sunder.registry import approve, tag_mechanic
    mech = {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE",
            "scaling": "FLAT", "value": 2}
    propose("tag", "probe", "a scan", "derived reminder", mechanic=mech)
    e = approve("tag", "probe")
    assert e.mechanic == mech
    assert tag_mechanic("probe") == mech


def test_repropose_without_mechanic_clears_it(reg):
    from sunder.registry import tag_mechanic
    propose("tag", "probe", "a scan", "derived reminder",
            mechanic={"trigger": "ON_PLAY", "effect": "DRAW_CARD",
                      "target": "SELF", "scaling": "FLAT", "value": 1})
    propose("tag", "probe", "a scan", "just flavor now")
    assert tag_mechanic("probe") is None


def test_repropose_reopens_rejected(reg):
    reject("tag", "vinyl")
    e = propose("tag", "vinyl")
    assert e.status == PROPOSED


def test_bad_id_rejected(reg):
    with pytest.raises(ValueError):
        propose("tag", "Not Lower Case")
    with pytest.raises(ValueError):
        propose("nonsense", "x")


def test_approve_unknown_returns_none(reg):
    assert approve("tag", "nope") is None


def test_schema_gate_follows_approval(reg):
    from sunder.schema import SchemaError, parse_card

    def with_tag(t):
        return {"id": "t", "name": "T", "set": "test", "plane": "test",
                "rarity": "COMMON", "cost": 0, "type": "BROADCAST",
                "stats": {"atk": 1, "def": 1}, "tags": [t],
                "abilities": [], "keywords": [], "flavor": ""}

    with pytest.raises(SchemaError):
        parse_card(with_tag("neon"))
    propose("tag", "neon", "glowing signs", "Bright.")
    with pytest.raises(SchemaError):  # proposed, not yet approved
        parse_card(with_tag("neon"))
    approve("tag", "neon")
    c = parse_card(with_tag("neon"))
    assert c.tags == ["neon"]


def test_keywords_auto_sync(reg):
    # an engine keyword missing from the registry file is re-seeded approved
    data = load_registry()
    data["keywords"] = [k for k in data["keywords"] if k["id"] != "LOUD"]
    save_registry(data)
    registry._CACHE = None
    data = load_registry()
    loud = next(k for k in data["keywords"] if k["id"] == "LOUD")
    assert loud["status"] == APPROVED
