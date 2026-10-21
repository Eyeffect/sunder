"""SUNDER — FastAPI + WebSocket server for the web UI.

Serves the built SPA from `web/dist` (when present) and a single `/ws` channel.
Each client message triggers an engine action and the server replies with a
full state snapshot plus the newly appended log lines.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..avatars import load_avatars
from ..game import GameState
from ..lore import rules_text
from ..schema import load_card_file
from ..sleeves import load_manifest
from .match import BotSeat, HumanSeat, MatchRoom

SERVER_DIR = Path(__file__).parent
CARDS_DIR = SERVER_DIR.parent / "cards"
DIST_DIR = SERVER_DIR.parent.parent / "web" / "dist"


def default_decks() -> tuple[list, list]:
    return (load_card_file(CARDS_DIR / "neon_frequency.json"),
            load_card_file(CARDS_DIR / "cinderworks.json"))


def _registry_json(e) -> dict:
    return {"id": e.id, "definition": e.definition, "reminder": e.reminder,
            "status": e.status, "mechanic": e.mechanic}


def _card_json(c) -> dict:
    return {
        "id": c.id, "name": c.name, "set": c.set, "plane": c.plane,
        "rarity": c.rarity.value, "cost": c.cost, "type": c.type.value,
        "atk": c.atk, "def": c.def_, "keywords": list(c.keywords),
        "tags": list(c.tags), "rules": rules_text(c), "flavor": c.flavor,
    }


def create_app(decks=None, ai_think: float = 1.4, ai_delay: float = 1.4) -> FastAPI:
    """Build the app. `ai_think`/`ai_delay` are the base seconds for the
    rival's thinking pause and per-action delay (randomized around them);
    pass 0 to make AI turns instant (tests)."""
    decks = tuple(decks) if decks else default_decks()
    sleeves = load_manifest()
    avatars = load_avatars()
    app = FastAPI(title="SUNDER", docs_url="/api/docs")

    @app.get("/api/cards")
    def api_cards():
        return {"cards": [_card_json(c) for deck in decks for c in deck]}

    @app.get("/api/keywords")
    def api_keywords():
        from ..keywords import KEYWORD_REGISTRY, resolve_key
        return {"keywords": [
            {
                "key": resolve_key(key),
                "display": kw.display,
                "meaning": kw.reminder,
                "kind": kw.kind,
            }
            for key, kw in sorted(KEYWORD_REGISTRY.items())
        ]}

    @app.get("/api/sleeves")
    def api_sleeves():
        return {"sleeves": list(sleeves.values())}

    @app.get("/api/avatars")
    def api_avatars():
        return {"avatars": list(avatars.values())}

    @app.get("/api/tags")
    def api_tags():
        from ..registry import all_entries
        return {"tags": [
            {
                "id": e.id,
                "definition": e.definition,
                "reminder": e.reminder,
            }
            for e in all_entries("tags") if e.status == "approved"
        ]}

    @app.get("/api/registry")
    def api_registry():
        from ..registry import all_entries
        return {
            "tags": [_registry_json(e) for e in all_entries("tags")],
            "keywords": [_registry_json(e) for e in all_entries("keywords")],
        }

    @app.post("/api/registry")
    def api_registry_propose(payload: dict):
        from ..registry import propose
        try:
            entry = propose(
                str(payload.get("kind", "tag")),
                str(payload.get("id", "")),
                str(payload.get("definition", "")),
                str(payload.get("reminder", "")),
                mechanic=payload.get("mechanic") if isinstance(
                    payload.get("mechanic"), dict) else None,
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"entry": _registry_json(entry)}, status_code=201)

    @app.post("/api/registry/{kind}/{entry_id}/approve")
    def api_registry_approve(kind: str, entry_id: str):
        from ..registry import approve
        entry = approve(kind, entry_id)
        if entry is None:
            return JSONResponse({"error": f"no such {kind} entry"}, status_code=404)
        return {"entry": _registry_json(entry)}

    @app.post("/api/generate")
    async def api_generate(payload: dict):
        import asyncio

        from ..gen import generate_pack
        from ..schema import parse_card
        theme = str(payload.get("theme", "")).strip()
        if not theme:
            return JSONResponse({"error": "theme is required"}, status_code=400)
        try:
            count = int(payload.get("count", 5))
        except (TypeError, ValueError):
            return JSONResponse({"error": "count must be a number"}, status_code=400)
        seed = payload.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError):
                return JSONResponse({"error": "seed must be a number"}, status_code=400)
        result = await asyncio.to_thread(generate_pack, theme, count, seed)
        result["cards"] = [_card_json(parse_card(c)) for c in result["cards"]]
        return result

    @app.get("/api/health")
    def api_health():
        return {"ok": True}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        # Single-human server for now: this socket is seat 0 vs a bot seat.
        # A PvP lobby will build the same MatchRoom with two HumanSeats.
        seat = HumanSeat(0, ws)
        room: MatchRoom | None = None

        async def send_error(message: str) -> None:
            await seat.send({"type": "error", "message": message})

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await send_error("malformed message")
                    continue
                if not isinstance(msg, dict):
                    await send_error("malformed message")
                    continue
                mtype = msg.get("type")

                if mtype == "start" or mtype == "restart":
                    if room is not None:
                        await room.close()
                    gs = GameState(*decks, seed=msg.get("seed"),
                                   sleeves=sleeves, avatars=avatars)
                    gs.start_game()
                    room = MatchRoom(gs, [seat, BotSeat(1, think=ai_think, delay=ai_delay)])
                    await room.send_state(seat)
                    room.kick()

                elif room is None:
                    await send_error("send {type:start} first")

                elif mtype == "ping":
                    await seat.send({"type": "pong"})

                else:
                    err = await room.handle(seat, msg, sleeves=sleeves, avatars=avatars)
                    if err:
                        await send_error(err)
        except WebSocketDisconnect:
            return
        finally:
            seat.connected = False
            if room is not None:
                await room.close()

    if DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")

    return app


app = create_app()
