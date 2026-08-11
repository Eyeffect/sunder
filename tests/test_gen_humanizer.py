"""Humanizer: batched naming, menu-tag validation, retries, per-card fallback."""

import random

import pytest

from sunder.gen.fake import FakeLLM
from sunder.gen.humanizer import MAX_ATTEMPTS, deterministic_fill, humanize_pack
from sunder.gen.ledger import Ledger
from sunder.gen.profile import default_profile
from sunder.gen.sampler import sample_pack


def skeletons(n=3):
    """
    Create a deterministic collection of humanizer card skeletons.
    
    Parameters:
    	n (int): Number of card skeletons to create.
    
    Returns:
    	list: The generated card skeletons.
    """
    rng = random.Random(1)
    return sample_pack("humanizer", default_profile("humanizer"), rng,
                       Ledger.seeded(), n)


def valid_pack(sks):
    """Build valid humanized card data for the provided card skeletons.
    
    Parameters:
    	sks (iterable): Card skeletons whose allowed flavor tags and tag counts determine each card's flavor tags.
    
    Returns:
    	list: Card data with sequential names, fixed flavor text, and tags selected from each skeleton's allowed menu.
    """
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


def _sequence(responses):
    """
    Create a callback that returns scripted responses in sequence and repeats the final response after the sequence is exhausted.
    
    Parameters:
        responses (list): Responses to return in order.
    
    Returns:
        on_call (callable): A callback that accepts messages and returns the next scripted response.
    """
    box = {"i": 0}

    def on_call(messages):
        """
        Return scripted responses in sequence, reusing the final response after the sequence is exhausted.
        
        Parameters:
            messages: Messages provided to the language model callback.
        
        Returns:
            The next scripted response.
        """
        i = box["i"]
        box["i"] += 1
        return responses[i] if i < len(responses) else responses[-1]

    return on_call
