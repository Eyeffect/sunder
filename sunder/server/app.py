"""SUNDER — FastAPI + WebSocket server for the web UI.

Serves the built SPA from `web/dist` (when present) and a single `/ws` channel.
Each client message triggers an engine action and the server replies with a
full state snapshot plus the newly appended log lines.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from .. import ai as ai_mod
from ..game import GameState
from ..lore import rules_text
from ..schema import load_card_file
from ..state import snapshot

SERVER_DIR = Path(__file__).parent
CARDS_DIR = SERVER_DIR.parent / "cards"
DIST_DIR = SERVER_DIR.parent.parent / "web" / "dist"


def default_decks() -> tuple[list, list]:
    return (load_card_file(CARDS_DIR / "neon_frequency.json"),
            load_card_file(CARDS_DIR / "cinderworks.json"))


def _card_json(c) -> dict:
    return {
        "id": c.id, "name": c.name, "set": c.set, "plane": c.plane,
        "rarity": c.rarity.value, "cost": c.cost, "type": c.type.value,
        "atk": c.atk, "def": c.def_, "keywords": list(c.keywords),
        "rules": rules_text(c), "flavor": c.flavor,
    }


def create_app(decks=None) -> FastAPI:
    decks = tuple(decks) if decks else default_decks()
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

    @app.get("/api/health")
    def api_health():
        return {"ok": True}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        gs: GameState | None = None

        def human_turn() -> bool:
            return gs is not None and gs.winner is None and gs.current == 0

        async def send_state() -> None:
            await ws.send_text(json.dumps({"type": "state", "snapshot": snapshot(gs)}))

        async def send_error(message: str) -> None:
            await ws.send_text(json.dumps({"type": "error", "message": message}))

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await send_error("malformed message")
                    continue
                mtype = msg.get("type")

                if mtype == "start" or mtype == "restart":
                    gs = GameState(*decks, seed=msg.get("seed"))
                    gs.start_game()
                    await send_state()

                elif gs is None:
                    await send_error("send {type:start} first")

                elif mtype == "play":
                    if not human_turn():
                        await send_error("not your turn")
                        continue
                    try:
                        idx = int(msg["hand"])
                        chosen = None
                        target = msg.get("target")
                        if target is not None:
                            chosen = next((i for i in gs.opp.board if i.serial == target), None)
                        gs.play_card(idx, chosen)
                        await send_state()
                    except (IndexError, ValueError) as exc:
                        await send_error(str(exc))

                elif mtype == "attack":
                    if not human_turn():
                        await send_error("not your turn")
                        continue
                    try:
                        attacker = gs.cur.board[int(msg["board"])]
                        target = msg.get("target")
                        if target == "face":
                            t: tuple = ("FACE", None)
                        else:
                            inst = next((i for i in gs.opp.board if i.serial == target), None)
                            if inst is None:
                                await send_error("bad target")
                                continue
                            t = ("BROADCAST", inst)
                        gs.attack(attacker, t)
                        await send_state()
                    except (IndexError, ValueError) as exc:
                        await send_error(str(exc))

                elif mtype == "end_turn":
                    if gs.winner is None and gs.current == 0:
                        gs.end_turn()
                    if gs.winner is None and gs.current == 1:
                        ai_mod.play_turn(gs)
                    await send_state()

                elif mtype == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))

                else:
                    await send_error(f"unknown type {mtype!r}")
        except WebSocketDisconnect:
            return

    if DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="spa")

    return app


app = create_app()
