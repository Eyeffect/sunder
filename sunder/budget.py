"""SUNDER — cost budget: suggested cost from clauses + fairness validator.

The tolerance (deviation) is the "fairness knob": it widens with rarity and
loosens over a run (P5). Common stays tight; Sundered may drift wildly.
"""

from __future__ import annotations

from .primitives import CardType, Effect, Rarity, Scaling, Target, Trigger
from .schema import Card

_KEYWORD_COST = {
    "LOUD": 1, "RUSH": 1, "ECHO": 0, "AMP": 0, "CARRIER": 1, "BEACON": 1,
    "DISTORT": 1, "FILTER": 1, "DRAIN": 1, "FEEDBACK": 1, "MASKED": 1,
    "FUSE": 0, "B_SIDE": 1,
}

_REPEATABLE = {
    Trigger.ON_TURN_START, Trigger.ON_TURN_END, Trigger.ON_ANY_BROADCAST_PLAYED,
    Trigger.ON_CAST_TRACK, Trigger.STATIC,
}

_TOLERANCE = {
    Rarity.COMMON: 2, Rarity.UNCOMMON: 2, Rarity.RARE: 3, Rarity.SUNDERED: 4,
}

_GROUP_TARGETS = {
    Target.ALL_ENEMY_BROADCASTS, Target.ALL_YOUR_BROADCASTS, Target.ALL_BROADCASTS,
}


def _ability_value(card: Card, ab) -> int:
    n = ab.value
    if ab.scaling is not Scaling.FLAT:
        n = 1  # unknown live metric — cheap by design, chaos is the point
    repeat = 3 if ab.trigger in _REPEATABLE else 1
    group = 2 if ab.target in _GROUP_TARGETS else 1

    if ab.effect is Effect.DEAL_DAMAGE:
        v = n * repeat * group
    elif ab.effect is Effect.DESTROY:
        v = 2 * group
    elif ab.effect is Effect.GAIN_LIFE:
        v = max(1, n // 2) * repeat
    elif ab.effect is Effect.DRAW_CARD:
        v = 2 * n
    elif ab.effect is Effect.BUFF_STAT:
        v = (n + ab.value_def) * repeat * (2 if ab.trigger is Trigger.STATIC else 1)
    elif ab.effect is Effect.SUMMON_TOKEN:
        v = 2 * n * repeat
    elif ab.effect is Effect.RETURN_FROM_DISCARD:
        v = n
    elif ab.effect is Effect.COPY_LAST_TRACK:
        v = 3 * n
    elif ab.effect is Effect.COUNTER_TRACK:
        v = 2 * repeat
    elif ab.effect is Effect.GRANT_KEYWORD:
        v = 1
    elif ab.effect is Effect.DOUBLE_NEXT_TRIGGER:
        v = 1
    elif ab.effect is Effect.GAIN_BANDWIDTH:
        v = 2 * n
    elif ab.effect is Effect.UNCAP_BANDWIDTH:
        v = 6
    else:
        v = n
    return v


def budget_score(card: Card) -> int:
    score = 0
    if card.type is CardType.BROADCAST:
        score += card.atk + card.def_
    for ab in card.abilities:
        score += _ability_value(card, ab)
    for kw in card.keywords:
        score += _KEYWORD_COST.get(kw, 0)
    if card.fuse:
        score = max(0, int(score * 0.5))  # delayed payoff is cheaper
    return score


def suggested_cost(card: Card) -> int:
    return max(0, round(budget_score(card) / 2))


def check_budget(card: Card) -> dict:
    score = budget_score(card)
    suggested = suggested_cost(card)
    tol = _TOLERANCE[card.rarity]
    ok = abs(suggested - card.cost) <= tol
    return {
        "score": score,
        "suggested": suggested,
        "cost": card.cost,
        "tolerance": tol,
        "ok": ok,
    }
