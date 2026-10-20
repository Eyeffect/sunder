import re

from fastapi.testclient import TestClient

from sunder.server.app import create_app

client = TestClient(create_app(ai_think=0, ai_delay=0))


def test_health():
    r = client.get("/api/health")
    assert r.json()["ok"] is True


def test_cards_endpoint():
    r = client.get("/api/cards")
    cards = r.json()["cards"]
    assert len(cards) == 20
    assert all("rules" in c and "flavor" in c for c in cards)


def test_keywords_endpoint():
    r = client.get("/api/keywords")
    kws = r.json()["keywords"]
    keys = {k["key"] for k in kws}
    assert "RUSH" in keys and "B_SIDE" in keys
    assert all("display" in k and "meaning" in k and "kind" in k for k in kws)


def test_tags_endpoint():
    r = client.get("/api/tags")
    tags = r.json()["tags"]
    ids = {t["id"] for t in tags}
    assert "vinyl" in ids and "ember" in ids
    assert all("definition" in t and "reminder" in t for t in tags)


def test_registry_endpoint():
    r = client.get("/api/registry")
    data = r.json()
    assert len(data["tags"]) >= 6
    assert len(data["keywords"]) >= 12
    for e in data["tags"] + data["keywords"]:
        assert e["status"] in ("proposed", "approved", "rejected")


def test_registry_propose_and_approve(tmp_path, monkeypatch):
    import sunder.registry as registry
    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "registry.json")
    monkeypatch.setattr(registry, "REGISTRY_DIR", tmp_path)
    registry._CACHE = None
    tc = TestClient(create_app(ai_think=0, ai_delay=0))
    try:
        r = tc.post("/api/registry", json={
            "kind": "tag", "id": "neon", "definition": "glow", "reminder": "bright"})
        assert r.status_code == 201
        assert r.json()["entry"]["status"] == "proposed"
        r = tc.post("/api/registry/tag/neon/approve")
        assert r.status_code == 200
        assert r.json()["entry"]["status"] == "approved"
        assert "neon" in {t["id"] for t in tc.get("/api/tags").json()["tags"]}
        r = tc.post("/api/registry", json={"kind": "tag", "id": "Bad ID"})
        assert r.status_code == 400
        r = tc.post("/api/registry/tag/nope/approve")
        assert r.status_code == 404
    finally:
        registry._CACHE = None


def test_registry_propose_with_mechanic(tmp_path, monkeypatch):
    import sunder.registry as registry
    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "registry.json")
    monkeypatch.setattr(registry, "REGISTRY_DIR", tmp_path)
    registry._CACHE = None
    tc = TestClient(create_app(ai_think=0, ai_delay=0))
    try:
        mech = {"trigger": "ON_PLAY", "effect": "DRAW_CARD", "target": "SELF",
                "scaling": "FLAT", "value": 1}
        r = tc.post("/api/registry", json={
            "kind": "tag", "id": "probe", "definition": "a scan",
            "reminder": "derived", "mechanic": mech})
        assert r.status_code == 201
        assert r.json()["entry"]["mechanic"] == mech
        got = tc.get("/api/registry").json()
        entry = next(t for t in got["tags"] if t["id"] == "probe")
        assert entry["mechanic"] == mech
    finally:
        registry._CACHE = None


def test_generate_endpoint(monkeypatch):
    import sunder.gen as gen_mod

    def fake_pack(theme, count, seed):
        return {"cards": [], "theme": theme, "seed": seed, "mode": "deterministic"}

    monkeypatch.setattr(gen_mod, "generate_pack", fake_pack)
    tc = TestClient(create_app(ai_think=0, ai_delay=0))
    r = tc.post("/api/generate", json={"theme": "test theme", "count": 3, "seed": 7})
    assert r.status_code == 200
    d = r.json()
    assert d["theme"] == "test theme" and d["seed"] == 7 and d["mode"] == "deterministic"
    assert tc.post("/api/generate", json={"theme": "", "count": 5}).status_code == 400
    assert tc.post("/api/generate", json={"theme": "x", "count": "bogus"}).status_code == 400
    assert tc.post("/api/generate", json={"theme": "x", "seed": "nope"}).status_code == 400


def test_generate_endpoint_serializes_codex_shape(monkeypatch, tmp_path):
    """Generated packs must come back in CodexCard shape (flat stats + rules)."""
    import sunder.gen as gen_mod
    from sunder.gen import profile as prof

    monkeypatch.setattr(prof, "CACHE_DIR", tmp_path / "cache")
    orig = gen_mod.generate_pack
    monkeypatch.setattr(
        gen_mod, "generate_pack",
        lambda theme, count, seed: orig(theme, count=count, seed=seed,
                                        use_llm=False))
    tc = TestClient(create_app(ai_think=0, ai_delay=0))
    r = tc.post("/api/generate", json={"theme": "serialize", "count": 3, "seed": 7})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "deterministic"
    assert len(d["cards"]) == 3
    for c in d["cards"]:
        assert "stats" not in c
        assert "atk" in c and "def" in c
        assert "rules" in c and c["rules"]
        assert "keywords" in c and "flavor" in c
        assert len(c["tags"]) <= 2


def test_start_returns_snapshot():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        msg = ws.receive_json()
        assert msg["type"] == "state"
        assert msg["snapshot"]["turn"] == 1
        assert len(msg["snapshot"]["hand"]) == 5
        assert msg["snapshot"]["can_act"] is True


def test_bad_play_rejected():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        ws.receive_json()
        ws.send_json({"type": "play", "hand": 99})
        msg = ws.receive_json()
        assert msg["type"] == "error"


def _next_stable(ws):
    """Drain staged AI snapshots until it's the human's turn or game over."""
    while True:
        s = ws.receive_json()["snapshot"]
        if s["winner"] is not None or s["can_act"]:
            return s


def test_end_turn_runs_ai():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s1 = ws.receive_json()["snapshot"]
        assert s1["current"] == 0
        ws.send_json({"type": "end_turn", "turn": s1["turn"]})
        s2 = _next_stable(ws)
        assert s2["current"] == 0
        assert s2["turn"] == 3
        assert s2["winner"] is None


def test_end_turn_acks_immediately():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s1 = ws.receive_json()["snapshot"]
        ws.send_json({"type": "end_turn", "turn": s1["turn"]})
        s2 = ws.receive_json()["snapshot"]
        assert s2["current"] == 1
        assert s2["can_act"] is False
        s3 = _next_stable(ws)
        assert s3["current"] == 0
        assert s3["turn"] == 3


def test_end_turn_rejects_stale_turn():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s1 = ws.receive_json()["snapshot"]
        assert s1["turn"] == 1
        ws.send_json({"type": "end_turn", "turn": 99})
        s2 = ws.receive_json()["snapshot"]
        assert s2["turn"] == 1
        assert s2["current"] == 0
        assert s2["winner"] is None


def test_rapid_end_turn_skips_one_turn_only():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s1 = ws.receive_json()["snapshot"]
        assert s1["turn"] == 1
        for _ in range(3):
            ws.send_json({"type": "end_turn", "turn": 1})
        s2 = _next_stable(ws)
        assert s2["current"] == 0
        assert s2["turn"] == 3
        assert s2["winner"] is None


def test_scripted_match_terminates():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        final = None
        for _ in range(300):
            s = _next_stable(ws)
            if s["winner"] is not None:
                final = s
                break
            assert s["can_act"] is True
            idx, target = None, None
            for i, hc in enumerate(s["hand"]):
                if hc["is_playable"]:
                    idx = i
                    if hc["needs_target"] and hc["legal_targets"]:
                        target = hc["legal_targets"][0]
                    break
            if idx is not None:
                ws.send_json({"type": "play", "hand": idx, "target": target})
                continue
            attacker = next((b for b in s["me"]["board"] if b.get("can_attack")), None)
            if attacker:
                t = attacker["attack_targets"][0]
                target = "face" if t["kind"] == "face" else t["serial"]
                ws.send_json({"type": "attack", "board": s["me"]["board"].index(attacker),
                              "target": target})
                continue
            ws.send_json({"type": "end_turn", "turn": s["turn"]})
        assert final is not None and final["winner"] in (0, 1)


def test_sleeves_endpoint():
    r = client.get("/api/sleeves")
    sleeves = r.json()["sleeves"]
    ids = {s["id"] for s in sleeves}
    assert {"ember", "static", "default"} <= ids
    assert all(s.get("label") and s.get("palette") for s in sleeves)


def test_sleeves_manifest_file_matches_fallback_ids(monkeypatch):
    import json as _json

    from sunder import sleeves as sleeves_mod

    manifest = _json.loads(
        (sleeves_mod.SLEEVE_PATH).read_text())
    ids = [s["id"] for s in manifest["sleeves"]]
    assert len(ids) == len(set(ids))
    assert "default" in ids


def test_set_sleeve_updates_station():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s1 = ws.receive_json()["snapshot"]
        assert s1["players"]["0"]["sleeve"] == "ember"
        ws.send_json({"type": "set_sleeve", "sleeve": "driftglass"})
        s2 = ws.receive_json()["snapshot"]
        assert s2["players"]["0"]["sleeve"] == "driftglass"


def test_set_sleeve_rejects_unknown_id():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s1 = ws.receive_json()["snapshot"]
        assert s1["players"]["0"]["sleeve"] == "ember"
        ws.send_json({"type": "set_sleeve", "sleeve": "nope"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "sleeve" in err["message"]
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_avatars_endpoint():
    r = client.get("/api/avatars")
    avatars = r.json()["avatars"]
    ids = {a["id"] for a in avatars}
    assert {"frequency", "neon", "cinder", "callsign"} <= ids
    assert all(a.get("label") and a.get("glyph") for a in avatars)


def test_set_avatar_updates_station():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        s1 = ws.receive_json()["snapshot"]
        assert s1["players"]["0"]["avatar"] == "frequency"
        assert s1["players"]["0"]["avatar_glyph"] == "◉"
        ws.send_json({"type": "set_avatar", "avatar": "cinder"})
        s2 = ws.receive_json()["snapshot"]
        assert s2["players"]["0"]["avatar"] == "cinder"
        assert s2["players"]["0"]["avatar_glyph"] == "⌁"
        ws.send_json({"type": "set_sleeve", "sleeve": "driftglass"})
        s3 = ws.receive_json()["snapshot"]
        assert s3["players"]["0"]["sleeve_ink"] == "cyan"


def test_set_avatar_rejects_unknown_id():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "seed": 1})
        ws.receive_json()
        ws.send_json({"type": "set_avatar", "avatar": "nope"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "avatar" in err["message"]


def test_sleeves_manifest_schema():
    """Structure guard for sleeves.json: palette *channels* resolve
    client-side against web/src/sleeves.ts CHANNELS (tested there), and
    per-sleeve art files are cross-checked there too (sleeve id →
    web/src/art/sleeves/<id>.svg)."""
    import json as _json

    from sunder import sleeves as sleeves_mod

    manifest = _json.loads((sleeves_mod.SLEEVE_PATH).read_text())
    assert isinstance(manifest.get("schema_version"), int)
    sleeves = manifest["sleeves"]
    assert sleeves, "manifest must define at least one sleeve"
    for s in sleeves:
        assert _json.dumps(s)  # dict-shaped entry
        assert re.fullmatch(r"[a-z][a-z0-9_]*", s["id"]), s["id"]
        assert s.get("label"), f"{s['id']}: missing label"
        palette = s.get("palette") or {}
        assert {"ink", "glow", "paper"} <= set(palette), s["id"]
        assert all(isinstance(v, str) and v for v in palette.values()), s["id"]
    ids = [s["id"] for s in sleeves]
    assert len(ids) == len(set(ids)), "duplicate sleeve ids"
