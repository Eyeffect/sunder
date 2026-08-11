"""Humanizer: batched naming, menu-tag validation, retries, per-card fallback."""

import random

import pytest

from sunder.gen import humanizer as humanizer_mod
from sunder.gen.fake import FakeLLM
from sunder.gen.humanizer import MAX_ATTEMPTS, deterministic_fill, humanize_pack
from sunder.gen.ledger import Ledger
from sunder.gen.profile import default_profile
from sunder.gen.sampler import sample_pack


def skeletons(n=3):
    rng = random.Random(1)
    return sample_pack("humanizer", default_profile("humanizer"), rng,
                       Ledger.seeded(), n)


def valid_pack(sks):
    return [{"name": f"Card {i + 1}", "flavor": "Swing is a frequency.",
             "flavor_tags": list(sk.flavor_tag_menu[: sk.n_flavor])}
            for i, sk in enumerate(sks)]


def test_batched_valid_pack():
    sks = skeletons()
    fake = FakeLLM(responses=[valid_pack(sks)])
    out = humanize_pack("humanizer", default_profile("humanizer"), sks, fake)
    assert len(fake.calls) == 1
    assert len(out) == len(sks)
    for i, entry in enumerate(out):
        assert entry["name"] == f"Card {i + 1}"
        assert set(entry["flavor_tags"]) == set(sks[i].flavor_tag_menu[: sks[i].n_flavor])


def test_invented_tags_rejected_then_retried():
    sks = skeletons()
    fake = FakeLLM(on_call=_sequence([
        [{"name": f"Card {i + 1}", "flavor": "x",
          "flavor_tags": ["bogus"]} for i in range(len(sks))],
        valid_pack(sks),
    ]))
    out = humanize_pack("humanizer", default_profile("humanizer"), sks, fake)
    assert len(fake.calls) == 2
    assert all(e["name"].startswith("Card") for e in out)
    retry_note = fake.calls[1][-1]["content"]
    assert "invented tags" in retry_note or "rejected" in retry_note


def test_per_card_fallback_after_max_attempts():
    sks = skeletons()
    always_bad = lambda msgs: [{  # noqa: E731
        "name": f"Card {i + 1}", "flavor": "x",
        "flavor_tags": ["nope"]} for i in range(len(sks))]
    fake = FakeLLM(on_call=always_bad)
    out = humanize_pack("humanizer", default_profile("humanizer"), sks, fake)
    assert len(fake.calls) == MAX_ATTEMPTS
    assert len(out) == len(sks)
    for sk, entry in zip(sks, out):
        assert entry["name"].startswith("Untitled")  # deterministic fill
        assert entry["flavor_tags"] == sk.flavor_tag_menu[: sk.n_flavor]


def test_wrong_card_count_retries():
    sks = skeletons()
    short = valid_pack(sks)[:1]
    fake = FakeLLM(on_call=_sequence([short, valid_pack(sks)]))
    out = humanize_pack("humanizer", default_profile("humanizer"), sks, fake)
    assert len(fake.calls) == 2
    assert len(out) == len(sks)


def test_deterministic_fill_uses_pool_and_menu():
    from sunder.gen.humanizer import deterministic_fill
    sks = skeletons(4)
    profile = default_profile("humanizer")
    out = deterministic_fill(sks, profile)
    assert len(out) == len(sks)
    for sk, entry in zip(sks, out):
        assert entry["flavor_tags"] == sk.flavor_tag_menu[: sk.n_flavor]
        assert "humanizer" in entry["flavor"]
    names = [e["name"] for e in out]
    assert all(n in profile.name_pool for n in names)


def test_prompt_surfaces_subject_first():
    sks = skeletons()
    messages = humanizer_mod._build_prompt("humanizer",
                                           default_profile("humanizer"), sks)
    first = messages[-1]["content"].split("CARD 1")[1]
    assert first.startswith(" — ")
    assert "Subject tag: #" in first
    assert first.index("Subject tag") < first.index("Ability")
    assert "additional" in first


def test_zero_flavor_picks_validate():
    sks = [s for s in skeletons(60) if s.n_flavor == 0]
    assert sks, "expected some zero-pick skeletons"
    out = humanize_pack("humanizer", default_profile("humanizer"), sks,
                        FakeLLM(responses=[valid_pack(sks)]))
    assert all(e["flavor_tags"] == [] for e in out)


def _sequence(responses):
    """on_call that pops scripted responses in order."""
    box = {"i": 0}

    def on_call(messages):
        i = box["i"]
        box["i"] += 1
        return responses[i] if i < len(responses) else responses[-1]

    return on_call
