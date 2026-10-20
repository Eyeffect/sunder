"""SUNDER — game-state snapshot serializer (engine → JSON for the web UI).

A snapshot is built from the human's perspective (`viewer=0`): the rival's
hand is masked to a count and hidden B-SIDE cards are rendered as mystery
faces. Everything else (playability, legal targets, attack options) is
computed server-side from the existing game helpers so the client stays dumb.
"""

from __future__ import annotations

from .game import MAX_SIGNAL, GameState
from .lore import rules_text
from .primitives import CardType, Target


def _revealed_view(gs: GameState, inst, viewer: int) -> dict:
    card = inst.card
    view = {
        "serial": inst.serial,
        "hidden": False,
        "type": card.type.value,
        "name": card.name,
        "cost": card.cost,
        "plane": card.plane,
        "rarity": card.rarity.value,
        "keywords": list(card.keywords),
        "tags": list(card.tags),
        "is_token": inst.is_token,
        "fuse": card.fuse,
        "fuse_ticks": inst.fuse_ticks,
        "damage": inst.damage_taken,
        "rules": rules_text(card),
        "flavor": card.flavor,
    }
    if card.type is CardType.BROADCAST:
        view["atk"] = gs.effective_atk(inst)
        view["def"] = gs.def_remaining(inst)
    if viewer == inst.controller:
        view["can_attack"] = gs.can_attack(inst)
        view["attack_targets"] = [
            {"kind": "face"} if kind == "FACE" else {"kind": "broadcast", "serial": obj.serial}
            for kind, obj in gs.legal_attack_targets(inst)
        ]
    return view


def _inst_view(gs: GameState, inst, viewer: int) -> dict:
    if inst.hidden:
        view = {
            "serial": inst.serial,
            "hidden": True,
            "type": None,
            "name": "???",
            "keywords": ["B_SIDE"],
            "is_token": inst.is_token,
        }
        if viewer == inst.controller:
            view.update(_revealed_view(gs, inst, viewer))
            view["hidden"] = True
        return view
    return _revealed_view(gs, inst, viewer)


def player_view(gs: GameState, p, viewer: int) -> dict:
    sleeve = gs.sleeves.get(p.sleeve, {})
    avatar = gs.avatars.get(p.avatar, {})
    return {
        "index": p.index,
        "sleeve": p.sleeve,
        "sleeve_ink": (sleeve.get("palette") or {}).get("ink", "amber"),
        "avatar": p.avatar,
        "avatar_glyph": avatar.get("glyph", "◉"),
        "signal": p.signal,
        "max_signal": MAX_SIGNAL,
        "bandwidth": p.bandwidth,
        "max_bandwidth": p.current_max_bandwidth(),
        "hand_count": len(p.hand),
        "static_count": len(p.static),
        "playlist_count": len(p.playlist),
        "board": [_inst_view(gs, i, viewer) for i in p.board],
    }


def hand_view(gs: GameState, p) -> list[dict]:
    hand = []
    for inst in p.hand:
        card = inst.card
        needs = any(ab.target in (Target.CHOSEN, Target.ENEMY_BROADCAST)
                    for ab in card.abilities)
        legal = gs.legal_track_targets(inst) if needs else []
        hand.append({
            "serial": inst.serial,
            "id": card.id,
            "name": card.name,
            "cost": card.cost,
            "plane": card.plane,
            "rarity": card.rarity.value,
            "type": card.type.value,
            "keywords": list(card.keywords),
            "tags": list(card.tags),
            "atk": card.atk,
            "def": card.def_,
            "rules": rules_text(card),
            "flavor": card.flavor,
            "is_playable": gs.is_playable(inst),
            "needs_target": needs,
            "legal_targets": [t.serial for t in legal],
        })
    return hand


def snapshot(gs: GameState, viewer: int = 0) -> dict:
    me, foe = gs.players[viewer], gs.players[1 - viewer]
    return {
        "turn": gs.turn,
        "current": gs.current,
        "phase": gs.phase,
        "winner": gs.winner,
        "status": gs.status(),
        "viewer": viewer,
        "can_act": gs.winner is None and gs.current == viewer,
        "players": {p.index: player_view(gs, p, viewer) for p in gs.players},
        "me": player_view(gs, me, viewer),
        "foe": player_view(gs, foe, viewer),
        "hand": hand_view(gs, me),
        "log": list(gs.log),
        "log_offset": len(gs.log),
        "history": list(gs.history),
    }
