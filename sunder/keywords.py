"""SUNDER — keyword registry.

Keywords are macros over the primitive vocabulary (or static modifiers).
Internal keys are mechanical; display names are lore. `reminder` is the
auto-templated rules text shown in the TUI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordDef:
    display: str
    reminder: str
    kind: str  # flag | trigger macro | modifier | one-shot modifier | aura | counter


KEYWORD_REGISTRY: dict[str, KeywordDef] = {
    "LOUD": KeywordDef("LOUD", "Can attack the turn it's aired.", "flag"),
    "RUSH": KeywordDef("RUSH", "Can attack Broadcasts immediately, but not the rival station.", "flag"),
    "ECHO": KeywordDef("ECHO", "When this goes silent, do the listed effect.", "trigger macro"),
    "AMP": KeywordDef("AMP", "+1/+1 each time a Broadcast is aired.", "trigger macro"),
    "CARRIER": KeywordDef("CARRIER", "Always-on ability.", "aura"),
    "BEACON": KeywordDef("BEACON", "Enemy Broadcasts must target this one.", "flag"),
    "DISTORT": KeywordDef("DISTORT", "Noise this deals to Broadcasts is lethal.", "modifier"),
    "FILTER": KeywordDef("FILTER", "Negates the first Noise dealt to this.", "one-shot modifier"),
    "DRAIN": KeywordDef("DRAIN", "Noise this deals also boosts your Signal.", "modifier"),
    "FEEDBACK": KeywordDef("FEEDBACK", "Attacks twice.", "flag"),
    "MASKED": KeywordDef("MASKED", "Can't be targeted until it attacks.", "targeting rule"),
    "FUSE": KeywordDef("FUSE", "Detonates when the fuse expires.", "counter"),
    "B_SIDE": KeywordDef("B-SIDE", "Hidden until its listed condition triggers.", "hidden loop"),
}

_LEGACY = {"STATIC": "CARRIER"}


def resolve_key(key: str) -> str:
    """Map any mechanical/legacy key to its canonical registry key."""
    if key in KEYWORD_REGISTRY:
        return key
    if key in _LEGACY:
        return _LEGACY[key]
    return key


def display(key: str) -> str:
    k = resolve_key(key)
    return KEYWORD_REGISTRY[k].display if k in KEYWORD_REGISTRY else key


def remind(key: str) -> str:
    k = resolve_key(key)
    return KEYWORD_REGISTRY[k].reminder if k in KEYWORD_REGISTRY else ""
