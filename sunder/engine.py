"""SUNDER — generic ability resolver.

Executes any schema-conforming card deterministically. Effects are a closed
set; triggers/scalings/targets grow as data. Never branches on lore.
"""

from __future__ import annotations

from .primitives import CardType, Effect, Scaling, Target, Trigger
from .schema import Ability, Card

_TOKEN_CACHE: dict[str, Card] = {}


def _token_card() -> Card:
    if "TOKEN" not in _TOKEN_CACHE:
        from .primitives import Rarity
        _TOKEN_CACHE["TOKEN"] = Card(
            id="TOKEN", name="Echo", set="", plane="",
            rarity=Rarity.COMMON, cost=0, type=CardType.BROADCAST, atk=1, def_=1,
        )
    return _TOKEN_CACHE["TOKEN"]


# ------------------------------------------------------------------ helpers

def _is_dead(gs, inst) -> bool:
    if inst.zone != "AIRWAVES":
        return False
    if inst.card.type is not CardType.BROADCAST:
        return False
    if inst.serial in gs.lethal_hits:
        return True
    return gs.def_remaining(inst) <= 0


def _condition_ok(gs, inst, ab: Ability, event) -> bool:
    c = ab.condition
    if not c:
        return True
    if "min_turn" in c and gs.turn < int(c["min_turn"]):
        return False
    if "not_self" in c and event is inst:
        return False
    if "has_tag" in c:
        tag = c["has_tag"]
        if not getattr(event, "card", None) or tag not in getattr(event.card, "tags", ()):
            return False
    return True


def _scaled(gs, source, ab: Ability) -> tuple[int, int]:
    """Returns (value, value_def) after applying the scaling metric."""
    s = ab.scaling
    if s is Scaling.FLAT:
        return ab.value, ab.value_def
    if s is Scaling.X_TURN_NUMBER:
        n = gs.turn
    elif s is Scaling.X_CARDS_PLAYED_THIS_TURN:
        n = gs.players[source.controller].cards_played_this_turn
    elif s is Scaling.X_COUNT_OF_TYPE_ON_BOARD:
        ct = ab.count_type or source.card.type
        n = sum(1 for p in gs.players for i in p.board if i.card.type is ct)
    elif s is Scaling.X_COUNT_OF_TAG_ON_BOARD:
        tag = ab.tag or ""
        n = sum(1 for p in gs.players for i in p.board if tag in i.card.tags)
    elif s is Scaling.X_TIMES_THIS_TRIGGERED_THIS_GAME:
        source.trigger_counts[ab.ref] = source.trigger_counts.get(ab.ref, 0) + 1
        n = source.trigger_counts[ab.ref]
    else:
        n = ab.value
    return n, n


def _collect_targets(gs, source, tgt: Target, chosen):
    me = gs.players[source.controller]
    foe = gs.players[1 - source.controller]
    mine = [i for i in me.board if i.card.type is CardType.BROADCAST]
    theirs = [i for i in foe.board if i.card.type is CardType.BROADCAST]
    if tgt is Target.SELF:
        return [source]
    if tgt is Target.ENEMY_FACE:
        return ["FACE"]
    if tgt is Target.ENEMY_BROADCAST:
        return [chosen] if chosen is not None and not chosen.hidden else []
    if tgt is Target.ALL_ENEMY_BROADCASTS:
        return theirs
    if tgt is Target.ALL_YOUR_BROADCASTS:
        return mine
    if tgt is Target.ALL_BROADCASTS:
        return mine + theirs
    if tgt is Target.RANDOM:
        pool = [i for i in mine + theirs if not i.hidden]
        return [gs.rng.choice(pool)] if pool else []
    if tgt is Target.CHOSEN:
        return [chosen] if chosen is not None and not chosen.hidden else []
    return []


# ------------------------------------------------------------------ damage

def drain_heal(gs, source, dmg: int) -> None:
    if source is not None and source.has("DRAIN") and dmg > 0:
        gs.players[source.controller].signal += dmg
        gs.log_line(f"{source.label()} drains {dmg} Signal.")


def apply_damage(gs, inst, amount: int, source) -> int:
    """Apply noise to a Broadcast. Returns the actual noise dealt."""
    if amount <= 0:
        return 0
    if inst.card.type is not CardType.BROADCAST:
        return 0
    if inst.has("FILTER") and not inst.filter_spent:
        inst.filter_spent = True
        gs.log_line(f"{inst.label()}'s FILTER negates the Noise.")
        return 0
    if source is not None and source.has("DISTORT"):
        gs.lethal_hits.add(inst.serial)
    inst.damage_taken += amount
    gs.log_line(
        f"{inst.label()} takes {amount} Noise.",
        kind="damage",
        card=inst,
        station=inst.controller,
    )
    drain_heal(gs, source, amount)
    return amount


# ------------------------------------------------------------------ triggers

def fire(gs, inst, trigger: Trigger, event=None, chosen=None) -> None:
    """Resolve every ability of `inst` matching `trigger` (with doubles)."""
    if inst.zone == "AIRWAVES" and _is_dead(gs, inst):
        return
    if inst.hidden:
        wants = any(ab.trigger is trigger and _condition_ok(gs, inst, ab, event)
                    for ab in inst.card.abilities)
        if wants:
            inst.hidden = False
            gs.log_line(
                f"Station {inst.controller + 1} reveals a B-SIDE: {inst.card.name}.",
                kind="reveal",
                card=inst,
                station=inst.controller,
            )
    for ab in inst.card.abilities:
        if ab.trigger is not trigger:
            continue
        if not _condition_ok(gs, inst, ab, event):
            continue
        mult = 1 + inst.pending_doubles
        inst.pending_doubles = 0
        resolve_ability(gs, inst, ab, event, chosen, mult)
    process_deaths(gs)


def fire_global(gs, trigger: Trigger, event=None, chosen=None) -> None:
    for p in (gs.cur, gs.opp):
        for inst in list(p.board):
            if inst in p.board:
                fire(gs, inst, trigger, event, chosen)


def begin_turn(gs) -> None:
    p = gs.cur
    for inst in list(p.board):
        if inst.card.fuse is not None:
            inst.fuse_ticks += 1
            if inst.fuse_ticks >= inst.card.fuse:
                gs.log_line(
                    f"{inst.label()} fuse ticks to {inst.fuse_ticks} — detonating!",
                    kind="death",
                    card=inst,
                    station=inst.controller,
                )
                fire(gs, inst, Trigger.ON_FUSE_EXPIRED)
    for inst in list(p.board):
        if inst in p.board:
            fire(gs, inst, Trigger.ON_TURN_START)
    process_deaths(gs)


def end_turn(gs) -> None:
    for inst in list(gs.cur.board):
        if inst in gs.cur.board:
            fire(gs, inst, Trigger.ON_TURN_END)
    process_deaths(gs)


def on_attack(gs, attacker) -> None:
    fire(gs, attacker, Trigger.ON_ATTACK)
    process_deaths(gs)


def on_broadcast_played(gs, inst, chosen=None) -> None:
    fire(gs, inst, Trigger.ON_PLAY, chosen=chosen)
    fire_global(gs, Trigger.ON_ANY_BROADCAST_PLAYED, event=inst)
    process_deaths(gs)


# ------------------------------------------------------------------ tracks

def _wants_cut(gs, event_track) -> bool:
    for p in gs.players:
        for inst in p.board:
            for ab in inst.card.abilities:
                if ab.trigger is Trigger.ON_CAST_TRACK and ab.effect is Effect.COUNTER_TRACK:
                    if _condition_ok(gs, inst, ab, event_track):
                        return True
    return False


def play_track(gs, inst, chosen=None) -> None:
    gs.last_track_stack.append(inst)
    if _wants_cut(gs, inst):
        inst.zone = "STATIC"
        gs.cur.static.append(inst)
        gs.log_line(f"{inst.label()} was cut before it played.")
        return
    gs.resolving.add(inst.serial)
    try:
        for ab in inst.card.abilities:
            if ab.trigger is Trigger.ON_PLAY:
                resolve_ability(gs, inst, ab, event=inst, chosen=chosen, mult=1)
    finally:
        gs.resolving.discard(inst.serial)
    inst.zone = "STATIC"
    gs.cur.static.append(inst)
    process_deaths(gs)


# ------------------------------------------------------------------ combat

def attack_trade(gs, attacker, defender) -> None:
    a_dmg = gs.effective_atk(attacker)
    d_dmg = gs.effective_atk(defender)
    apply_damage(gs, defender, a_dmg, attacker)
    apply_damage(gs, attacker, d_dmg, defender)
    gs.log_line(
        f"{attacker.label()} trades with {defender.label()} ({a_dmg}/{d_dmg}).",
        kind="attack",
        card=attacker,
        station=attacker.controller,
    )
    process_deaths(gs)


# ------------------------------------------------------------------ effects

def resolve_ability(gs, source, ab: Ability, event=None, chosen=None, mult: int = 1) -> None:
    value, value_def = _scaled(gs, source, ab)
    value *= mult
    value_def *= mult
    eff = ab.effect

    if eff is Effect.DEAL_DAMAGE:
        for t in _collect_targets(gs, source, ab.target, chosen):
            if t == "FACE":
                foe = gs.players[1 - source.controller]
                foe.signal -= value
                gs.log_line(
                    f"Station {source.controller + 1}: {value} Noise to the rival station.",
                    kind="damage",
                    card=source,
                    station=source.controller,
                )
                drain_heal(gs, source, value)
            else:
                apply_damage(gs, t, value, source)

    elif eff is Effect.GAIN_LIFE:
        gs.players[source.controller].signal += value
        gs.log_line(f"Station {source.controller + 1} boosts its Signal by {value}.")

    elif eff is Effect.DRAW_CARD:
        gs.draw(gs.players[source.controller], value)

    elif eff is Effect.BUFF_STAT:
        for t in _collect_targets(gs, source, ab.target, chosen):
            if t != "FACE":
                t.buff_atk += value
                t.buff_def += value_def
                gs.log_line(f"{t.label()} gets +{value}/+{value_def}.")

    elif eff is Effect.SUMMON_TOKEN:
        _summon(gs, gs.players[source.controller], max(0, value))

    elif eff is Effect.RETURN_FROM_DISCARD:
        _return_from_discard(gs, gs.players[source.controller], max(0, value))

    elif eff is Effect.COPY_LAST_TRACK:
        _copy_last_track(gs, source, max(0, value), chosen)

    elif eff is Effect.COUNTER_TRACK:
        pass  # handled by the cast pre-scan

    elif eff is Effect.DESTROY:
        for t in _collect_targets(gs, source, ab.target, chosen):
            if t != "FACE":
                _jam(gs, t)

    elif eff is Effect.GRANT_KEYWORD:
        for t in _collect_targets(gs, source, ab.target, chosen):
            if t != "FACE" and ab.keyword:
                t.granted_keywords.add(ab.keyword)
                gs.log_line(f"{t.label()} gains {ab.keyword}.")

    elif eff is Effect.DOUBLE_NEXT_TRIGGER:
        for t in _collect_targets(gs, source, ab.target, chosen):
            if t != "FACE":
                t.pending_doubles += 1

    elif eff is Effect.GAIN_BANDWIDTH:
        p = gs.players[source.controller]
        p.bandwidth += value
        gs.log_line(f"Station {source.controller + 1} generates {value} Bandwidth.")

    elif eff is Effect.UNCAP_BANDWIDTH:
        p = gs.players[source.controller]
        p.uncapped = True
        p.max_bandwidth = p.current_max_bandwidth()
        gs.log_line(f"Station {source.controller + 1} removes its Bandwidth cap.")

    process_deaths(gs)
    _wincheck(gs)


def _summon(gs, player, n: int) -> None:
    for _ in range(n):
        token = gs.make_instance(_token_card(), player.index)
        token.is_token = True
        token.zone = "AIRWAVES"
        player.board.append(token)
        gs.log_line(
            f"Station {player.index + 1}: a 1/1 Echo joins the airwaves.",
            kind="summon",
            card=token,
            station=player.index,
        )
    _prune_board(gs, player)


def _return_from_discard(gs, player, n: int) -> None:
    taken = 0
    while player.static and taken < n:
        inst = player.static.pop()
        inst.zone = "HAND"
        player.hand.append(inst)
        taken += 1
    if taken:
        gs.log_line(f"Station {player.index + 1} rewinds {taken} from Static.")


def _copy_last_track(gs, source, replays: int, chosen) -> None:
    target = None
    for inst in reversed(gs.last_track_stack):
        if inst.serial not in gs.resolving and inst.zone == "STATIC":
            target = inst
            break
    if target is None:
        gs.log_line("No Track to replay.")
        return
    gs.resolving.add(target.serial)
    try:
        for _ in range(replays):
            for ab in target.card.abilities:
                if ab.trigger is Trigger.ON_PLAY:
                    resolve_ability(gs, target, ab, event=target, chosen=chosen, mult=1)
    finally:
        gs.resolving.discard(target.serial)
    process_deaths(gs)


def _prune_board(gs, player) -> None:
    while len(player.board) > 6:
        victim = player.board.pop()
        victim.zone = "STATIC"
        player.static.append(victim)


# ------------------------------------------------------------------ death

def _jam(gs, inst) -> None:
    p = gs.players[inst.controller]
    if inst in p.board:
        p.board.remove(inst)
    inst.zone = "STATIC"
    gs.lethal_hits.discard(inst.serial)
    p.static.append(inst)
    gs.log_line(
        f"{inst.label()} goes silent.",
        kind="death",
        card=inst,
        station=inst.controller,
    )
    fire(gs, inst, Trigger.ON_DEATH)


def process_deaths(gs) -> None:
    while True:
        found = None
        for p in gs.players:
            for inst in list(p.board):
                if _is_dead(gs, inst):
                    found = inst
                    break
            if found:
                break
        if found is None:
            return
        _jam(gs, found)


def _wincheck(gs) -> None:
    if gs.winner is not None:
        return
    if gs.players[1].signal <= 0:
        gs.winner = 0
    elif gs.players[0].signal <= 0:
        gs.winner = 1
    if gs.winner is not None:
        gs.log_line(f"Station {gs.winner + 1} cuts the rival off the air.")
