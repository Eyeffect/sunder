"""Sampler: determinism, budget, tags, rarity caps, novelty ledger."""

import random

from sunder.budget import budget_score, check_budget, suggested_cost
from sunder.gen import sampler as sampler_mod
from sunder.gen.ledger import Ledger, signature_from_skeleton
from sunder.gen.profile import default_profile
from sunder.gen.sampler import (
    _SCORE_CAP,
    CardSkeleton,
    build_card_raw,
    sample_pack,
    skeleton_to_card,
)
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


def test_all_cards_within_rarity_score_cap():
    for sk in pack("caps", count=10):
        assert budget_score(skeleton_to_card(sk)) <= _SCORE_CAP[sk.rarity]


def test_tags_stay_within_registry():
    for sk in pack("tags", count=10):
        if sk.load_bearing_tag:
            assert sk.load_bearing_tag in APPROVED_TAGS
        if sk.subject_tag:
            assert sk.subject_tag in APPROVED_TAGS
        for t in sk.flavor_tag_menu:
            assert t in APPROVED_TAGS


def test_load_bearing_tag_matches_condition():
    for sk in pack("load", count=10):
        if sk.load_bearing_tag:
            assert any(ab.get("condition", {}).get("has_tag") == sk.load_bearing_tag
                       for ab in sk.abilities)


def test_n_flavor_within_menu():
    for sk in pack("flavor", count=10):
        assert 0 <= sk.n_flavor <= 1
        assert sk.n_flavor <= len(sk.flavor_tag_menu)


def test_subject_tag_every_card():
    for sk in pack("subject", count=10):
        assert sk.subject_tag is not None  # seeded registry has tags
        if sk.load_bearing_tag:
            assert sk.subject_tag == sk.load_bearing_tag
        assert sk.subject_tag not in sk.flavor_tag_menu  # never re-offered


def test_total_tags_at_most_two():
    for sk in pack("twotags", count=10):
        raw = build_card_raw(sk, "Name", "Flavor.",
                             list(sk.flavor_tag_menu[: sk.n_flavor]))
        assert len(raw["tags"]) <= 2


def test_subject_reproducible_and_varied():
    a = pack("variety", count=40, seed=11)
    b = pack("variety", count=40, seed=11)
    assert [s.subject_tag for s in a] == [s.subject_tag for s in b]
    distinct = {s.subject_tag for s in a}
    assert len(distinct) >= 2  # skews toward theme tags, does not collapse


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


# ---------------------------------------------------------------- budget gate

def _hot_skeleton(rarity="RARE"):
    """A broadcast that would score ~54 — far over every cap."""
    return CardSkeleton(
        id="hot_001", set="hot", plane="hot", type="BROADCAST", rarity=rarity,
        cost=0, keywords=["LOUD"], stats={"atk": 5, "def": 6},
        abilities=[
            {"trigger": "ON_TURN_START", "effect": "DEAL_DAMAGE",
             "target": "ALL_ENEMY_BROADCASTS", "scaling": "FLAT", "value": 4,
             "value_def": 0},
            {"trigger": "ON_TURN_END", "effect": "GAIN_BANDWIDTH",
             "target": "SELF", "scaling": "FLAT", "value": 3, "value_def": 0},
        ],
    )


def test_budget_gate_clamps_over_cap(monkeypatch):
    monkeypatch.setattr(sampler_mod, "_build_skeleton", lambda *a, **k: _hot_skeleton())
    sk = pack("hot", count=1, seed=5)[0]
    assert budget_score(skeleton_to_card(sk)) <= _SCORE_CAP[sk.rarity]
    assert len(sk.abilities) == 1  # second ability dropped first
    assert sk.cost == suggested_cost(skeleton_to_card(sk))
    parse_card(build_card_raw(sk, "N", "F.", list(sk.flavor_tag_menu[: sk.n_flavor])))


def test_budget_clamp_logs_cuts(monkeypatch, caplog):
    import logging
    monkeypatch.setattr(sampler_mod, "_build_skeleton", lambda *a, **k: _hot_skeleton())
    with caplog.at_level(logging.WARNING, logger="sunder.gen"):
        pack("hot", count=1, seed=5)
    assert any("budget clamp" in r.message for r in caplog.records)
    assert any("2nd-ability" in r.message for r in caplog.records)


def test_budget_accept_over_is_true_floor(monkeypatch, caplog):
    import logging
    # shaving disabled -> the ladder runs out and must accept + log detail
    monkeypatch.setattr(sampler_mod, "_build_skeleton", lambda *a, **k: _hot_skeleton())
    monkeypatch.setattr(sampler_mod, "_shave_ability_value", lambda sk: False)
    with caplog.at_level(logging.WARNING, logger="sunder.gen"):
        sk = pack("hot", count=1, seed=5)[0]
    assert budget_score(skeleton_to_card(sk)) > _SCORE_CAP[sk.rarity]  # accepted over
    assert sk.cost == suggested_cost(skeleton_to_card(sk))
    parse_card(build_card_raw(sk, "N", "F.", list(sk.flavor_tag_menu[: sk.n_flavor])))
    hits = [r for r in caplog.records if "budget accept-over" in r.message]
    assert hits
    assert "effect=DEAL_DAMAGE" in hits[0].message
    assert "score=" in hits[0].message and "cap=" in hits[0].message


# ---------------------------------------------------------------- tag mechanics

MECH = {"trigger": "ON_PLAY", "effect": "DRAW_CARD", "target": "SELF",
        "scaling": "FLAT", "value": 1}


def _mech_sk(type="BROADCAST", **kw):
    sk = CardSkeleton(
        id="m_001", set="m", plane="m", type=type, rarity="COMMON", cost=0,
        keywords=[], stats={"atk": 1, "def": 1},
        abilities=[{"trigger": "ON_PLAY", "effect": "GAIN_LIFE", "target": "SELF",
                    "scaling": "FLAT", "value": 2}],
        subject_tag="vinyl", flavor_tag_menu=["chrome"],
    )
    for k, v in kw.items():
        setattr(sk, k, v)
    return sk


def test_mechanical_subject_injected_as_first_ability(monkeypatch):
    monkeypatch.setattr(sampler_mod, "tag_mechanic",
                        lambda t: MECH if t == "vinyl" else None)
    sk = _mech_sk()
    sampler_mod._inject_subject_mechanic(sk)
    assert sk.abilities[0] == MECH
    assert len(sk.abilities) == 2


def test_illegal_mechanic_not_injected(monkeypatch, caplog):
    import logging
    illegal = {**MECH, "trigger": "ON_TURN_START"}  # illegal on TRACK
    monkeypatch.setattr(sampler_mod, "tag_mechanic", lambda t: illegal)
    sk = _mech_sk(type="TRACK")
    with caplog.at_level(logging.WARNING, logger="sunder.gen"):
        sampler_mod._inject_subject_mechanic(sk)
    assert len(sk.abilities) == 1  # untouched
    assert any("tag mechanic skipped" in r.message for r in caplog.records)


def test_subject_skips_illegal_mechanical_tags(monkeypatch):
    illegal = {**MECH, "trigger": "ON_TURN_START"}  # illegal on TRACK
    monkeypatch.setattr(sampler_mod, "tag_mechanic",
                        lambda t: illegal if t == "vinyl" else None)
    pick = sampler_mod._pick_subject(random.Random(1), ["vinyl", "chrome"],
                                     "TRACK", {})
    assert pick == "chrome"


def test_subject_menu_unfiltered_without_type(monkeypatch):
    monkeypatch.setattr(sampler_mod, "tag_mechanic",
                        lambda t: MECH if t == "vinyl" else None)
    # without a ctype we don't filter (flavor menu keeps every tag)
    menu = list(sampler_mod._flavor_menu(random.Random(1),
                                         approved_ids("tags"), {}, None))
    assert menu  # full seeded menu survives


def test_pick_subject_is_affinity_weighted():
    # own tag at 1.0 vs a foreign tag at floor: own should dominate but the
    # foreign tag stays possible — never guaranteed, never excluded.
    menu = ["own", "foreign"]
    affinity = {"own": 1.0, "foreign": 0.15}
    foreign = sum(
        sampler_mod._pick_subject(random.Random(seed), menu, None, affinity)
        == "foreign"
        for seed in range(400)
    )
    # expected ~13% (0.15/1.15); assert well under uniform 50%
    assert foreign < 100


def test_budget_ladder_preserves_mechanical_subject(monkeypatch):
    monkeypatch.setattr(sampler_mod, "tag_mechanic",
                        lambda t: MECH if t == "vinyl" else None)

    def build(*a, **k):
        sk = _hot_skeleton()
        sk.subject_tag = "vinyl"
        sk.abilities = [dict(MECH), sk.abilities[1]]
        return sk

    monkeypatch.setattr(sampler_mod, "_build_skeleton", build)
    sk = pack("hot", count=1, seed=5)[0]
    assert sk.abilities[0] == MECH  # the identity ability survives the ladder
    assert sk.subject_tag == "vinyl"
    parse_card(build_card_raw(sk, "N", "F.", list(sk.flavor_tag_menu[: sk.n_flavor])))
