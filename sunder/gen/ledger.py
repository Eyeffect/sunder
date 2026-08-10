"""SUNDER — novelty ledger.

A signature summarises a card's mechanical identity:

    (type, sorted keywords, ability tuples, load-bearing tag)

Ability tuples carry trigger/effect/target/scaling and a normalised
condition (incl. any `has_tag` target). The ledger is pre-seeded from the
starter codex so generated packs don't re-ship existing designs; the sampler
re-rolls on collision and only relaxes the load-bearing-tag slot after a few
attempts so narrow themes can't hang.
"""

from __future__ import annotations

from ..schema import Ability, Card


def _ability_key(ab: Ability) -> tuple:
    cond = tuple(sorted((str(k), str(v)) for k, v in (ab.condition or {}).items()))
    return (ab.trigger.value, ab.effect.value, ab.target.value,
            ab.scaling.value, cond)


def signature_from_card(card: Card) -> tuple:
    return (card.type.value,
            tuple(sorted(card.keywords)),
            tuple(_ability_key(ab) for ab in card.abilities),
            None)


def signature_from_skeleton(sk) -> tuple:
    """Same shape as `signature_from_card`, from a CardSkeleton."""
    ability_keys = []
    for ab in sk.abilities:
        cond = tuple(sorted((str(k), str(v)) for k, v in
                            (ab.get("condition") or {}).items()))
        ability_keys.append((ab["trigger"], ab["effect"], ab["target"],
                             ab.get("scaling", "FLAT"), cond))
    return (sk.type,
            tuple(sorted(sk.keywords)),
            tuple(ability_keys),
            sk.load_bearing_tag)


class Ledger:
    def __init__(self, known: set | None = None):
        self.known: set[tuple] = set(known or ())

    @classmethod
    def seeded(cls) -> "Ledger":
        from ..codex import all_cards
        return cls(signature_from_card(c) for c in all_cards())

    def collides(self, sig: tuple) -> bool:
        return sig in self.known

    def relaxed_collides(self, sig: tuple) -> bool:
        """Collision check with the load-bearing tag slot dropped."""
        return sig[:3] in self.known

    def add(self, sig: tuple) -> None:
        self.known.add(sig)
