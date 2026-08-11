"""SUNDER — lore layer. Player-facing words only; the engine never sees these."""

from .primitives import Effect, Scaling, Target, Trigger

WORDS = {
    "life": "Signal",
    "mana": "Bandwidth",
    "draw": "Cue",
    "deck": "Playlist",
    "board": "Airwaves",
    "discard": "Static",
    "creature": "Broadcast",
    "instant_sorcery": "Track",
    "enchantment": "Loop",
    "token": "Echo",
    "damage": "Noise",
    "counter": "Cut",
    "destroy": "Jam",
    "pack": "Transmission",
    "currency": "Watts",
    "mythic": "Sundered",
    "win": "off the air",
    "summon_sick": "warming up",
}


def w(key: str) -> str:
    return WORDS.get(key, key)


def remind(keyword: str) -> str:
    from .keywords import remind as _remind
    return _remind(keyword)


_TRIGGER_WORDS = {
    Trigger.ON_PLAY: "When this enters play",
    Trigger.ON_ATTACK: "When this attacks",
    Trigger.ON_DEATH: "When this goes silent",
    Trigger.ON_TURN_START: "At the start of your turn",
    Trigger.ON_TURN_END: "At the end of your turn",
    Trigger.ON_CAST_TRACK: "When a Track is played",
    Trigger.ON_ANY_BROADCAST_PLAYED: "Whenever a Broadcast is aired",
    Trigger.ON_FUSE_EXPIRED: "When the fuse expires",
    Trigger.STATIC: "Always on",
}

_TARGET_WORDS = {
    Target.SELF: "self",
    Target.ENEMY_FACE: "the rival station",
    Target.ENEMY_BROADCAST: "an enemy Broadcast",
    Target.ALL_ENEMY_BROADCASTS: "all enemy Broadcasts",
    Target.ALL_YOUR_BROADCASTS: "your Broadcasts",
    Target.ALL_BROADCASTS: "all Broadcasts",
    Target.RANDOM: "a random Broadcast",
    Target.CHOSEN: "a chosen Broadcast",
}

_EFFECT_WORDS = {
    Effect.DEAL_DAMAGE: "deal {n} Noise",
    Effect.GAIN_LIFE: "boost your Signal by {n}",
    Effect.DRAW_CARD: "cue {n}",
    Effect.BUFF_STAT: "+{n}/+{nd}",
    Effect.SUMMON_TOKEN: "summon {n} 1/1 Echo",
    Effect.RETURN_FROM_DISCARD: "return {n} from Static",
    Effect.COPY_LAST_TRACK: "replay the last Track {n} time(s)",
    Effect.COUNTER_TRACK: "cut the Track",
    Effect.DESTROY: "jam {t}",
    Effect.GRANT_KEYWORD: "grant {kw} to {t}",
    Effect.DOUBLE_NEXT_TRIGGER: "double {t}'s next trigger",
    Effect.GAIN_BANDWIDTH: "generate {n} Bandwidth this turn",
    Effect.UNCAP_BANDWIDTH: "remove your Bandwidth cap",
}


def rules_text(card, live_values: dict | None = None) -> str:
    """Deterministic rules text from the card's ability tuples.

    `live_values` optionally overrides numbers (engine resolves live ones;
    display falls back to the raw value).
    """
    from .keywords import display as kw_display

    parts = []
    has_static = any(ab.trigger is Trigger.STATIC for ab in card.abilities)
    for key in card.keywords:
        if key == "FUSE" and card.fuse is not None:
            parts.append(f"FUSE {card.fuse} — detonates {card.fuse} of your turns after airing.")
        elif key == "CARRIER" and has_static:
            continue  # the STATIC ability already reads "Always on"
        elif key == "B_SIDE":
            continue  # explained by the B-SIDE keyword entry + hidden "???" render
        else:
            parts.append(kw_display(key))
    for ab in card.abilities:
        live = (live_values or {}).get(ab.ref, {})
        n = live.get("value", ab.value)
        nd = live.get("value_def", ab.value_def)
        kw = live.get("keyword", ab.keyword or "")
        t = _TARGET_WORDS.get(ab.target, ab.target.value)
        template = _EFFECT_WORDS.get(ab.effect, ab.effect.value)
        if ab.target is not Target.SELF and "{t}" not in template:
            template += " to {t}"
        e = template.format(n=n, nd=nd, kw=kw, t=t)
        clause = _TRIGGER_WORDS.get(ab.trigger, ab.trigger.value)
        if ab.condition and ab.condition.get("has_tag"):
            tag = ab.condition["has_tag"]
            if ab.trigger is Trigger.ON_ANY_BROADCAST_PLAYED:
                clause = f"Whenever a Broadcast with the {tag} tag is aired"
            else:
                clause = f"{clause}, if the triggering card has the {tag} tag"
        if ab.scaling is Scaling.X_COUNT_OF_TAG_ON_BOARD:
            note = f" (X = number of {ab.tag} cards on the airwaves)"
        elif ab.scaling is Scaling.X_COUNT_OF_TYPE_ON_BOARD:
            ct = ab.count_type or card.type
            note = f" (X = number of {ct.value} cards on the airwaves)"
        else:
            note = ""
        parts.append(f"{clause}: {e}.{note}")
    return " ".join(parts) if parts else "(no text)"
