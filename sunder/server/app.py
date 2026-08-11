"""SUNDER — FastAPI + WebSocket server for the web UI.

Serves the built SPA from `web/dist` (when present) and a single `/ws` channel.
Each client message triggers an engine action and the server replies with a
full state snapshot plus the newly appended log lines.
"""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
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
    """Load the default Neon Frequency and Cinderworks card decks.
    
    Returns:
    	tuple[list, list]: The Neon Frequency and Cinderworks decks, respectively.
    """
    return (load_card_file(CARDS_DIR / "neon_frequency.json"),
            load_card_file(CARDS_DIR / "cinderworks.json"))


def _registry_json(e) -> dict:
    """Serialize a registry entry for API responses.
    
    Parameters:
    	e: The registry entry to serialize.
    
    Returns:
    	dict: The entry's identifier, definition, reminder text, and status.
    """
    return {"id": e.id, "definition": e.definition, "reminder": e.reminder,
            "status": e.status}


def _card_json(c) -> dict:
    """
    Serialize a card into the JSON-compatible representation used by the API.
    
    Parameters:
    	c: Card whose metadata, combat values, keywords, tags, rules, and flavor are serialized.
    
    Returns:
    	dict: A JSON-compatible mapping of the card's public data.
    """
    return {
        "id": c.id, "name": c.name, "set": c.set, "plane": c.plane,
        "rarity": c.rarity.value, "cost": c.cost, "type": c.type.value,
        "atk": c.atk, "def": c.def_, "keywords": list(c.keywords),
        "tags": list(c.tags), "rules": rules_text(c), "flavor": c.flavor,
    }


def create_app(decks=None, ai_think: float = 1.4, ai_delay: float = 1.4) -> FastAPI:
    """Create and configure the SUNDER FastAPI application.
    
    Parameters:
    	decks: Card decks to use; defaults to the built-in decks when omitted.
    	ai_think (float): Base duration of the AI's thinking pause in seconds.
    	ai_delay (float): Base duration of the AI's per-action delay in seconds.
    
    Returns:
    	FastAPI: The configured application."""
    decks = tuple(decks) if decks else default_decks()
    app = FastAPI(title="SUNDER", docs_url="/api/docs")

    @app.get("/api/cards")
    def api_cards():
        return {"cards": [_card_json(c) for deck in decks for c in deck]}

    @app.get("/api/keywords")
    def api_keywords():
        """
        List registered keywords with their resolved keys, display names, meanings, and kinds.
        
        Returns:
        	dict: A mapping containing the registered keyword metadata.
        """
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

    @app.get("/api/tags")
    def api_tags():
        """Return all approved tag registry entries."""
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
        """Return all registered tags and keywords with their serialized metadata.
        
        Returns:
        	dict: A mapping containing serialized registry entries under ``"tags"`` and ``"keywords"``.
        """
        from ..registry import all_entries
        return {
            "tags": [_registry_json(e) for e in all_entries("tags")],
            "keywords": [_registry_json(e) for e in all_entries("keywords")],
        }

    @app.post("/api/registry")
    def api_registry_propose(payload: dict):
        """
        Propose a tag or keyword registry entry from the supplied payload.
        
        Parameters:
        	payload (dict): Registry entry data containing kind, ID, definition, and reminder fields.
        
        Returns:
        	JSONResponse: A 201 response containing the proposed entry, or a 400 response containing a validation error.
        """
        from ..registry import propose
        try:
            entry = propose(
                str(payload.get("kind", "tag")),
                str(payload.get("id", "")),
                str(payload.get("definition", "")),
                str(payload.get("reminder", "")),
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"entry": _registry_json(entry)}, status_code=201)

    @app.post("/api/registry/{kind}/{entry_id}/approve")
    def api_registry_approve(kind: str, entry_id: str):
        """Approve a tag or keyword registry entry.
        
        Parameters:
            kind (str): Registry entry type to approve.
            entry_id (str): Identifier of the registry entry.
        
        Returns:
            JSONResponse or dict: A 404 error response when the entry does not exist; otherwise, an object containing the approved entry.
        """
        from ..registry import approve
        entry = approve(kind, entry_id)
        if entry is None:
            return JSONResponse({"error": f"no such {kind} entry"}, status_code=404)
        return {"entry": _registry_json(entry)}

    @app.post("/api/generate")
    async def api_generate(payload: dict):
        """
        Generate a card pack for the requested theme.
        
        Parameters:
            payload (dict): Request data containing a non-empty ``theme``, an optional numeric ``count``, and an optional numeric ``seed``.
        
        Returns:
            JSONResponse: The generated card pack, or an error response with status 400 when the theme, count, or seed is invalid.
        """
        import asyncio

        from ..gen import generate_pack
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
        return await asyncio.to_thread(generate_pack, theme, count, seed)

    @app.get("/api/health")
    def api_health():
        """Return the server health status."""
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
                    if gs.winner is None and gs.current == 0 and msg.get("turn") == gs.turn:
                        gs.end_turn()
                        await send_state()
                        if gs.winner is None and gs.current == 1:
                            await asyncio.sleep(ai_think * random.uniform(0.8, 1.2))
                            for _ in ai_mod.iter_turn(gs):
                                await send_state()
                                await asyncio.sleep(ai_delay * random.uniform(0.6, 1.3))
                            await asyncio.sleep(ai_delay * random.uniform(0.4, 0.8))
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
