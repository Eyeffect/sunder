"""Profile cache: genuine hits are trusted; fallback entries re-probe."""

import pytest

import sunder.registry as registry
from sunder.gen import profile as prof
from sunder.gen.client import LLMError
from sunder.gen.fake import FakeLLM

PROFILE_RESP = {
    "flavor_brief": "Smoky rooms, brass, late-night swing.",
    "name_pool": ["Brass Haze", "Smoke Solo", "Velvet Tempo"],
    "type_affinity": {}, "rarity_affinity": {}, "trigger_affinity": {},
    "effect_affinity": {}, "target_affinity": {}, "keyword_affinity": {},
    "tag_affinity": {}, "proposed_tags": [],
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(prof, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "registry.json")
    monkeypatch.setattr(registry, "REGISTRY_DIR", tmp_path)
    registry._CACHE = None
    yield
    registry._CACHE = None


def _plant_fallback(theme):
    prof._save_cached(theme, prof.default_profile(theme))


def _plant_genuine(theme):
    fake = FakeLLM(responses=[PROFILE_RESP])
    prof._save_cached(theme, prof._fetch_profile(theme, fake))


def test_genuine_cache_hit_never_probes(env):
    _plant_genuine("jazz club")
    fake = FakeLLM(responses=[PROFILE_RESP])
    p = prof.profile_for("jazz club", fake)
    assert p.fallback is False
    assert fake.calls == []


def test_fallback_hit_probe_success_overwrites(env):
    _plant_fallback("jazz club")
    fake = FakeLLM(responses=[PROFILE_RESP])
    p = prof.profile_for("jazz club", fake)
    assert p.fallback is False
    assert len(fake.calls) == 1
    # cache was overwritten: next call is a genuine hit, no probe
    fake2 = FakeLLM(responses=[PROFILE_RESP])
    p2 = prof.profile_for("jazz club", fake2)
    assert p2.fallback is False
    assert fake2.calls == []


def test_fallback_hit_probe_failure_keeps_stale_and_retries(env):
    _plant_fallback("jazz club")
    calls = {"n": 0}

    def down(messages):
        calls["n"] += 1
        raise LLMError("gateway down")

    p = prof.profile_for("jazz club", FakeLLM(on_call=down))
    assert p.fallback is True
    assert calls["n"] == 1
    # second request re-probes rather than trusting the stale entry
    p2 = prof.profile_for("jazz club", FakeLLM(on_call=down))
    assert p2.fallback is True
    assert calls["n"] == 2


class _SpyLLM:
    """FakeLLM that also records chat_json kwargs (FakeLLM keeps only msgs)."""

    def __init__(self, response):
        self.response = response
        self.kwargs = []

    def chat_json(self, messages, **kwargs):
        self.kwargs.append(kwargs)
        return self.response


def test_fresh_fetch_uses_client_full_timeout(env):
    spy = _SpyLLM(dict(PROFILE_RESP))
    prof.profile_for("jazz club", spy)
    assert spy.kwargs and spy.kwargs[0].get("timeout") is None


def test_fallback_reprobe_uses_probe_timeout(env):
    _plant_fallback("jazz club")
    spy = _SpyLLM(dict(PROFILE_RESP))
    prof.profile_for("jazz club", spy)
    assert spy.kwargs and spy.kwargs[0].get("timeout") == prof.PROBE_TIMEOUT


def test_no_llm_writes_fallback_then_llm_mode_reprobes(env):
    p = prof.profile_for("jazz club", FakeLLM(responses=[PROFILE_RESP]),
                         use_llm=False)
    assert p.fallback is True
    fake = FakeLLM(responses=[PROFILE_RESP])
    p2 = prof.profile_for("jazz club", fake)
    assert p2.fallback is False
    assert len(fake.calls) == 1


def test_cold_llm_probe_success_cached(env):
    fake = FakeLLM(responses=[PROFILE_RESP])
    p = prof.profile_for("jazz club", fake)
    assert p.fallback is False
    assert len(fake.calls) == 1
    fake2 = FakeLLM(responses=[PROFILE_RESP])
    assert prof.profile_for("jazz club", fake2).fallback is False
    assert fake2.calls == []


# ---------------------------------------------------------------- mechanics

def test_prompt_lists_scalings_and_mechanic_rules(env):
    fake = FakeLLM(responses=[PROFILE_RESP])
    prof._fetch_profile("jazz club", fake)
    content = fake.calls[0][-1]["content"]
    assert "X_COUNT_OF_TYPE_ON_BOARD" in content
    assert "X_TIMES_THIS_TRIGGERED_THIS_GAME" in content
    assert "legal targets per effect" in content
    assert "value ranges per effect" in content
    assert "triggers per card type" in content
    assert "effects per card type" in content
    assert "mechanic" in fake.calls[0][0]["content"]


def test_valid_mechanic_proposal_stored_with_derived_reminder(env):
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [{
        "id": "probe", "definition": "a scan",
        "mechanic": {"trigger": "ON_PLAY", "effect": "DRAW_CARD",
                     "target": "SELF", "scaling": "FLAT", "value": 1},
    }]
    prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    from sunder.registry import all_entries
    entry = next(e for e in all_entries("tags") if e.id == "probe")
    assert entry.status == "approved"
    assert entry.mechanic["effect"] == "DRAW_CARD"
    assert entry.reminder == "When this enters play: cue 1."


def test_damage_mechanic_reminder_states_target(env):
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [{
        "id": "probe", "definition": "a scan",
        "mechanic": {"trigger": "ON_TURN_END", "effect": "DEAL_DAMAGE",
                     "target": "ENEMY_FACE", "scaling": "FLAT", "value": 1},
    }]
    prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    from sunder.registry import all_entries
    entry = next(e for e in all_entries("tags") if e.id == "probe")
    assert entry.reminder == \
        "At the end of your turn: deal 1 Noise to the rival station."


def test_tag_scaling_may_reference_itself(env):
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [{
        "id": "probe", "definition": "a scan",
        "mechanic": {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE",
                     "target": "RANDOM", "scaling": "X_COUNT_OF_TAG_ON_BOARD",
                     "tag": "probe"},
    }]
    prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    from sunder.registry import tag_mechanic
    assert tag_mechanic("probe")["scaling"] == "X_COUNT_OF_TAG_ON_BOARD"


def test_invalid_mechanic_degrades_to_flavor_tag(env, caplog):
    import logging
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [{
        "id": "probe", "definition": "a scan",
        "reminder": "scans things",
        "mechanic": {"trigger": "BOGUS", "effect": "DRAW_CARD",
                     "target": "SELF", "scaling": "FLAT", "value": 1},
    }]
    with caplog.at_level(logging.WARNING, logger="sunder.gen"):
        prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    from sunder.registry import all_entries, tag_mechanic
    entry = next(e for e in all_entries("tags") if e.id == "probe")
    assert tag_mechanic("probe") is None
    assert entry.reminder == "scans things"
    assert any("rejecting mechanic" in r.message for r in caplog.records)


def test_unapproved_ref_mechanic_degraded(env, caplog):
    import logging
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [{
        "id": "probe", "definition": "a scan",
        "mechanic": {"trigger": "ON_PLAY", "effect": "GRANT_KEYWORD",
                     "target": "SELF", "scaling": "FLAT", "value": 1,
                     "keyword": "NOT_A_KEYWORD"},
    }]
    with caplog.at_level(logging.WARNING, logger="sunder.gen"):
        prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    from sunder.registry import tag_mechanic
    assert tag_mechanic("probe") is None
    assert any("rejecting mechanic" in r.message for r in caplog.records)


# ------------------------------------------------ auto-approve + tag emphasis

def test_proposals_auto_approved(env):
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [{"id": "probe", "definition": "a scan"}]
    prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    from sunder.registry import all_entries
    entry = next(e for e in all_entries("tags") if e.id == "probe")
    assert entry.status == "approved"


def test_rejected_tag_not_auto_approved(env):
    import sunder.registry as reg
    from sunder.registry import all_entries
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [{"id": "probe", "definition": "a scan"}]
    prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    reg.reject("tag", "probe")
    # re-proposed by a later fetch: re-opened to proposed, but NOT approved
    prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    entry = next(e for e in all_entries("tags") if e.id == "probe")
    assert entry.status == "proposed"


def test_own_tags_boosted_in_profile(env):
    resp = dict(PROFILE_RESP)
    resp["proposed_tags"] = [
        {"id": "probe", "definition": "a scan"},
        {"id": "sonar", "definition": "echo locating"},
    ]
    p = prof._fetch_profile("jazz club", FakeLLM(responses=[resp]))
    assert p.tag_affinity["probe"] == 1.0
    assert p.tag_affinity["sonar"] == 1.0


def test_cached_profile_floors_unranked_tags(env):
    resp = dict(PROFILE_RESP)
    resp["tag_affinity"] = {"static": 0.9}
    prof._save_cached("jazz club", prof._fetch_profile("jazz club",
                                                       FakeLLM(responses=[resp])))
    from sunder.registry import propose as reg_propose, approve as reg_approve
    reg_propose("tag", "foreign", "some other theme's tag")
    reg_approve("tag", "foreign")
    p = prof.profile_for("jazz club", FakeLLM(responses=[resp]))
    assert p.tag_affinity["static"] == 0.9   # LLM-ranked weight preserved
    assert p.tag_affinity["foreign"] == prof._TAG_FLOOR  # unranked at floor


def test_clamp_default_param(env):
    assert prof._clamp({"ghost": 0.9}, ["ghost", "foreign"],
                       default=prof._TAG_FLOOR) == \
        {"ghost": 0.9, "foreign": prof._TAG_FLOOR}
    assert prof._clamp(None, ["a"], default=prof._TAG_FLOOR) == {}
