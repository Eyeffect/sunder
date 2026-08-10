"""Sampler: determinism, budget, tags, rarity caps, novelty ledger."""

import random

from sunder.budget import check_budget
from sunder.gen.ledger import Ledger, signature_from_skeleton
from sunder.gen.profile import default_profile
from sunder.gen.sampler import build_card_raw, sample_pack, skeleton_to_card
from sunder.registry import approved_ids
from sunder.schema import parse_card

APPROVED_TAGS = approved_ids("tags")


def pack(theme="theme", count=5, seed=1, ledger=None):
    rng = random.Random(seed)
    return sample_pack(theme, default_profile(theme), rng,
                       ledger or Ledger.seeded(), count)


def test_sampler_is_reproducible():
    a = [signature_from_skeleton(s) for s in pack("repro", seed=99)]
    b = [signature_from_skeleton(s) for s in pack("repro", seed=99)]
    assert a == b


def test_sampler_differs_with_seed():
    a = [signature_from_skeleton(s) for s in pack("seed", seed=1)]
    b = [signature_from_skeleton(s) for s in pack("seed", seed=2)]
    assert a != b


def test_all_cards_parse_and_pass_budget():
    for sk in pack("budget", count=10):
        raw = build_card_raw(sk, "Name", "Flavor.", list(sk.flavor_tag_menu[: sk.n_flavor]))
        c = parse_card(raw)
        b = check_budget(c)
        assert b["ok"], f"{c.id}: score {b['score']} cost {b['cost']}"
        assert c.cost >= 0


def test_tags_stay_within_registry():
    for sk in pack("tags", count=10):
        if sk.load_bearing_tag:
            assert sk.load_bearing_tag in APPROVED_TAGS
        for t in sk.flavor_tag_menu:
            assert t in APPROVED_TAGS


def test_load_bearing_tag_matches_condition():
    for sk in pack("load", count=10):
        if sk.load_bearing_tag:
            assert any(ab.get("condition", {}).get("has_tag") == sk.load_bearing_tag
                       for ab in sk.abilities)


def test_n_flavor_within_menu():
    for sk in pack("flavor", count=10):
        assert 1 <= sk.n_flavor <= 3
        assert sk.n_flavor <= len(sk.flavor_tag_menu)


def test_rarity_caps():
    rarities = [sk.rarity for sk in pack("caps", count=10)]
    assert rarities.count("SUNDERED") <= 1
    assert rarities.count("RARE") <= 2


def test_all_types_legal():
    for sk in pack("types", count=10):
        assert sk.type in ("BROADCAST", "TRACK", "LOOP")
        for ab in sk.abilities:
            assert "trigger" in ab and "effect" in ab and "target" in ab
            assert "value" in ab


def test_ledger_avoids_known_signatures():
    known = {signature_from_skeleton(pack("known", count=1, seed=1)[0])}
    sk = pack("known", count=1, seed=1, ledger=Ledger(known))[0]
    assert signature_from_skeleton(sk) not in known


def test_ledger_narrow_theme_does_not_hang():
    # a ledger that collides with everything: full + relaxed
    sk0 = pack("narrow", count=1, seed=3)[0]
    sig = signature_from_skeleton(sk0)
    ledger = Ledger({sig, sig[:3]})
    sk = pack("narrow", count=1, seed=3, ledger=ledger)[0]
    assert sk is not None  # accepted rather than looping forever
