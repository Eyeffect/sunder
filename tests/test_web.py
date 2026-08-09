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
