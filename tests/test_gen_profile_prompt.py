"""Guard the generation prompt's vocabulary against drift.

`profile._build_prompt` teaches the LLM which enum values are legal by
listing them straight from `primitives(.SCALINGS in legality)`. If a new
trigger/effect/target/scaling/type/rarity/keyword is added but never lands
in the prompt list, the model can never propose it and generation silently
narrows. This test fails the moment those part ways.
"""

from __future__ import annotations

import sunder.gen.profile as prof
import sunder.registry as registry
from sunder.keywords import KEYWORD_REGISTRY
from sunder.primitives import CardType, Effect, Rarity, Target, Trigger


def _prompt_text(monkeypatch, tmp_path) -> str:
    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "registry.json")
    monkeypatch.setattr(registry, "REGISTRY_DIR", tmp_path)
    registry._CACHE = None
    try:
        prompt = prof._build_prompt("drift-check")
    finally:
        registry._CACHE = None
    return "\n".join(part["content"] for part in prompt)


def test_prompt_lists_every_primitive_enum_value(monkeypatch, tmp_path):
    text = _prompt_text(monkeypatch, tmp_path)
    for enum in (CardType, Rarity, Trigger, Effect, Target):
        for member in enum:
            assert member.value in text, f"{enum.__name__}.{member.value} missing from gen prompt"


def test_prompt_lists_every_scaling(monkeypatch, tmp_path):
    from sunder.gen.legality import SCALINGS
    from sunder.primitives import Scaling

    text = _prompt_text(monkeypatch, tmp_path)
    for member in Scaling:
        assert member.value in text
    assert set(SCALINGS) == {m.value for m in Scaling}


def test_prompt_lists_all_engine_keywords(monkeypatch, tmp_path):
    text = _prompt_text(monkeypatch, tmp_path)
    for key in KEYWORD_REGISTRY:
        assert key in text, f"keyword {key} missing from gen prompt"
