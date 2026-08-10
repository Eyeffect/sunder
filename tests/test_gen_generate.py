"""End-to-end pack generation: modes, reproducibility, caps, isolation."""

import re

import pytest

import sunder.registry as registry
from sunder.budget import check_budget
from sunder.gen import MAX_COUNT, generate_pack
from sunder.gen import profile as prof
from sunder.gen.client import LLMError
from sunder.gen.fake import FakeLLM
from sunder.schema import parse_card

PROFILE_RESP = {
    "flavor_brief": "Smoky rooms, brass, late-night swing.",
    "name_pool": ["Brass Haze", "Smoke Solo", "Velvet Tempo"],
    "type_affinity": {}, "rarity_affinity": {}, "trigger_affinity": {},
    "effect_affinity": {}, "target_affinity": {}, "keyword_affinity": {},
    "tag_affinity": {}, "proposed_tags": [],
}


@pytest.fixture
def gen_env(tmp_path, monkeypatch):
    monkeypatch.setattr(prof, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "registry.json")
    monkeypatch.setattr(registry, "REGISTRY_DIR", tmp_path)
    registry._CACHE = None
    yield
    registry._CACHE = None


def _llm_fake():
    def on_call(messages):
        txt = messages[-1]["content"]
        if "Write the profile" in txt:
            return PROFILE_RESP
        blocks = re.split(r"CARD \d+", txt)[1:]
        out = []
        for b in blocks:
            menu = re.findall(r"\n    ([a-z0-9_]+) — ", b)
            m = re.search(r"pick exactly (\d+)", b)
            n = int(m.group(1)) if m else 1
            out.append({"name": f"Card {len(out) + 1}", "flavor": "Swing.",
                        "flavor_tags": menu[: n]})
        return out

    return FakeLLM(on_call=on_call)


def test_deterministic_mode(gen_env):
    res = generate_pack("jazz club", count=5, seed=42, use_llm=False)
    assert res["mode"] == "deterministic"
    assert len(res["cards"]) == 5
    for c in res["cards"]:
        parsed = parse_card(c)
        assert check_budget(parsed)["ok"]
        assert c["plane"] == "jazz club"


def test_llm_mode(gen_env):
    res = generate_pack("jazz club", count=5, seed=7, client=_llm_fake())
    assert res["mode"] == "llm"
    assert len(res["cards"]) == 5
    names = {c["name"] for c in res["cards"]}
    assert len(names) == 5  # humanizer names landed, distinct


def test_transport_failure_falls_back_to_deterministic(gen_env):
    box = {"n": 0}

    def on_call(messages):
        box["n"] += 1
        if box["n"] == 1:
            return PROFILE_RESP  # profile succeeds
        raise LLMError("gateway down")

    res = generate_pack("jazz club", count=5, seed=7, client=FakeLLM(on_call=on_call))
    assert res["mode"] == "deterministic"
    assert len(res["cards"]) == 5


def test_profile_failure_falls_back(gen_env):
    res = generate_pack("jazz club", count=5, seed=7,
                        client=FakeLLM(on_call=lambda m: {"not": "a profile"}))
    assert res["mode"] == "deterministic"


def test_seed_reproducible(gen_env):
    a = generate_pack("repro", count=5, seed=123, use_llm=False)
    b = generate_pack("repro", count=5, seed=123, use_llm=False)
    assert a["cards"] == b["cards"]


def test_different_seed_differs(gen_env):
    a = generate_pack("repro2", count=5, seed=1, use_llm=False)
    b = generate_pack("repro2", count=5, seed=2, use_llm=False)
    assert a["cards"] != b["cards"]


def test_count_capped_at_max(gen_env):
    res = generate_pack("many", count=50, use_llm=False)
    assert len(res["cards"]) == MAX_COUNT


def test_empty_theme_rejected(gen_env):
    with pytest.raises(ValueError):
        generate_pack("   ", use_llm=False)
