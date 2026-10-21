"""SUNDER — heuristic AI opponent.

No learning, no search tree: greedy value decisions. Honours BEACON via the
game's legality checks; Tracks try to remove threats before going face.
"""

from __future__ import annotations

from .primitives import CardType, Effect, Scaling, Target, Trigger


def play_turn(gs) -> None:
    """Run the heuristic AI turn synchronously (drain iter_turn)."""
    for _ in iter_turn(gs):
        pass


def iter_turn(gs):
    """Run the heuristic AI turn, yielding after each discrete action so the
    server can pace/stage the moves (one snapshot per action)."""
    yield from _main_phase(gs)
    if gs.game_over:
        return
    yield from _combat(gs)
    if gs.game_over:
        return
    gs.end_turn()


# ------------------------------------------------------------------ main

def _main_phase(gs):
    while not gs.game_over:
        play = _choose_play(gs)
        if play is None:
            return
        inst, chosen = play
        try:
            gs.play_card(gs.cur.hand.index(inst), chosen)
        except ValueError:
            return
        yield


def _choose_play(gs):
    p = gs.cur
    affordable = [i for i in p.hand if i.card.cost <= p.bandwidth]
    if not affordable:
        return None

    # 1) Tracks that kill an enemy Broadcast outright.
    for inst in affordable:
        if inst.card.type is not CardType.TRACK:
            continue
        for ab in inst.card.abilities:
            if (ab.effect is Effect.DEAL_DAMAGE and ab.scaling is Scaling.FLAT
                    and ab.target in (Target.CHOSEN, Target.ENEMY_BROADCAST)):
                for t in p.opponent.board:
                    if gs.def_remaining(t) <= ab.value:
                        return (inst, t)

    # 2) Broadcasts/Loops — play the most expensive affordable.
    broadcastish = [i for i in affordable if i.card.type is not CardType.TRACK]
    if broadcastish:
        best = max(broadcastish, key=lambda i: i.card.cost)
        return (best, None)

    # 3) Any Track, aimed sensibly.
    best = max(affordable, key=lambda i: i.card.cost)
    return (best, _track_target(gs, best))


def _track_target(gs, inst):
    p = gs.cur
    for ab in inst.card.abilities:
        if ab.target not in (Target.CHOSEN, Target.ENEMY_BROADCAST, Target.RANDOM):
            continue
        if ab.effect is Effect.DEAL_DAMAGE:
            foe = sorted(
                (i for i in p.opponent.board if i.card.type is CardType.BROADCAST),
                key=lambda i: gs.def_remaining(i), reverse=True,
            )
            return foe[0] if foe else None
        if ab.effect in (Effect.BUFF_STAT, Effect.GRANT_KEYWORD):
            mine = sorted(
                (i for i in p.board if i.card.type is CardType.BROADCAST),
                key=lambda i: gs.effective_atk(i), reverse=True,
            )
            return mine[0] if mine else None
        if ab.effect is Effect.DOUBLE_NEXT_TRIGGER:
            mine = [i for i in p.board if any(a.trigger is not Trigger.STATIC for a in i.card.abilities)]
            return mine[0] if mine else None
    return None


# ------------------------------------------------------------------ combat

def _combat(gs):
    p = gs.cur
    for attacker in list(p.board):
        if gs.game_over:
            return
        if not gs.can_attack(attacker):
            continue
        targets = gs.legal_attack_targets(attacker)
        if not targets:
            continue
        target = _combat_target(gs, attacker, targets)
        if target is not None:
            gs.attack(attacker, target)
            yield


def _combat_target(gs, attacker, targets):
    # Prefer trades that kill; otherwise go face; otherwise soften a blocker.
    for kind, inst in targets:
        if kind == "BROADCAST" and gs.effective_atk(attacker) >= gs.def_remaining(inst):
            return (kind, inst)
    for kind, inst in targets:
        if kind == "FACE":
            return (kind, inst)
    blocker = min((i for k, i in targets if k == "BROADCAST"),
                  key=lambda i: gs.def_remaining(i), default=None)
    if blocker is not None:
        return ("BROADCAST", blocker)
    return None
