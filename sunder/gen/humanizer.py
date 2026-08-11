"""SUNDER — humanizer: names, flavour text, and tag picks.

One batched LLM call per pack: the model sees every skeleton at once (so it
won't reuse names or jokes) and returns a JSON array in the same order. Only
the sampler's shortlisted tags are offered; invented tags are rejected and
fed back as an error. A bad card never invalidates the rest of the pack —
after retries it gets a deterministic fill.
"""

from __future__ import annotations

import json
import logging

from ..registry import tag_definition, tag_mechanic, tag_reminder
from ..schema import SchemaError
from .client import LLMError
from .profile import ThemeProfile
from .sampler import CardSkeleton, skeleton_to_card

log = logging.getLogger("sunder.gen")

MAX_ATTEMPTS = 3

_FLAVOR_TEMPLATES = [
    "A shard of {theme}, bleeding in from across the multiverse.",
    "Every {theme} card carries its whole world with it.",
    "The broadcast catches {theme} at its strangest.",
    "No two universes see {theme} the same way.",
    "Somewhere in the multiverse, {theme} is all there is.",
]


def humanize_pack(theme: str, profile: ThemeProfile, skeletons: list[CardSkeleton],
                  client) -> list[dict]:
    """Return one {name, flavor, flavor_tags} per skeleton, in order.

    Raises `LLMError` if the transport itself fails; validation failures are
    retried and then patched with deterministic fills.
    """
    messages = _build_prompt(theme, profile, skeletons)
    raw = None
    for attempt in range(MAX_ATTEMPTS):
        raw = client.chat_json(messages, temperature=0.9, max_tokens=24000)
        human = _validate_all(raw, skeletons)
        if human is not None:
            return human
        errors = _error_summary(raw, skeletons)
        log.info("humanizer retry %d/%d: %s", attempt + 1, MAX_ATTEMPTS, errors)
        messages = messages + [
            {"role": "assistant", "content": json.dumps(raw)},
            {"role": "user", "content": _retry_note(errors)},
        ]
    return _validate_or_fill(raw, skeletons)


def deterministic_fill(skeletons: list[CardSkeleton], profile: ThemeProfile) -> list[dict]:
    """Offline fallback: pool names + templated flavour + first menu tags."""
    pool = profile.name_pool or ["Untitled"]
    out = []
    for i, sk in enumerate(skeletons):
        name = pool[i % len(pool)]
        if len(pool) > 1 and i >= len(pool) and any(
                name == p for p in pool[:i]):
            name = f"{name} {i // len(pool)}"
        out.append({
            "name": name,
            "flavor": _FLAVOR_TEMPLATES[i % len(_FLAVOR_TEMPLATES)].format(
                theme=profile.theme),
            "flavor_tags": list(sk.flavor_tag_menu[: sk.n_flavor]),
        })
    return out


# ---------------------------------------------------------------- prompt

def _tag_note(tag_id: str) -> str:
    """Menu/subject annotation: the engine-true reminder for mechanical
    tags, the subject-matter definition otherwise."""
    if tag_mechanic(tag_id):
        return tag_reminder(tag_id)
    return tag_definition(tag_id)


def _build_prompt(theme: str, profile: ThemeProfile,
                  skeletons: list[CardSkeleton]) -> list[dict]:
    blocks = []
    for i, sk in enumerate(skeletons):
        card = skeleton_to_card(sk)
        menu = "".join(f"\n    {t} — {_tag_note(t)}"
                       for t in sk.flavor_tag_menu)
        subject = (f"  Subject tag: #{sk.subject_tag} — "
                   f"{_tag_note(sk.subject_tag)}\n"
                   if sk.subject_tag else "")
        stats = (f"Stats: {sk.stats['atk']}/{sk.stats['def']}"
                 if sk.type == "BROADCAST" else "Stats: —")
        kw = ", ".join(sk.keywords) if sk.keywords else "none"
        blocks.append(
            f"CARD {i + 1} — {sk.type} ({sk.rarity}, cost {sk.cost})\n"
            f"{subject}"
            f"  {stats}   Keywords: {kw}\n"
            f"  Ability: {card.rules_text()}\n"
            f"  Offered flavor tags (pick exactly {sk.n_flavor} "
            f"additional):{menu}"
        )
    return [
        {"role": "system",
         "content": (
             "You write cards for SUNDER, a multiverse card game: you play "
             "a broadcast station battling another across a shared "
             "spectrum, and every card is a transmission from some world — "
             "any world. Keep each card true to its theme; the radio frame "
             "is just the shell. Reply with ONLY a JSON array — one object "
             "per card, in the exact same order as the input. Each object is:\n"
             '{"flavor_tags": ["tag ids from the offered menu, verbatim"], '
             '"name": "punchy card name", "flavor": "one evocative sentence '
             'of flavour text"}\n'
             "Rules:\n"
             "- Every card has a subject tag. The name and flavor text must "
             "name or clearly evoke the subject tag.\n"
             "- flavor_tags holds only the additional picks — exactly the "
             "required count, chosen ONLY from the offered menu (ids "
             "verbatim, no invented tags). Never put the subject tag in "
             "flavor_tags.\n"
             "- Names must be fresh and must not repeat within the pack.\n"
             "- Do not add quotes around the flavor text."
         )},
        {"role": "user",
         "content": (
             f"THEME: {theme}\n"
             f"THEME BRIEF: {profile.flavor_brief}\n"
             f"NAME POOL (inspiration only — invent better): "
             f"{', '.join(profile.name_pool)}\n\n"
             + "\n\n".join(blocks)
         )},
    ]


# ---------------------------------------------------------------- validation

def _validate_all(raw, skeletons: list[CardSkeleton]) -> list[dict] | None:
    if not isinstance(raw, list) or len(raw) != len(skeletons):
        return None
    result: list[dict] = []
    for i, sk in enumerate(skeletons):
        entry, _err = _validate_entry(raw[i], sk)
        if entry is None:
            return None
        result.append(entry)
    if not _unique_names(result):
        return None
    return result


def _validate_entry(human, sk: CardSkeleton) -> tuple[dict | None, str]:
    if not isinstance(human, dict):
        return None, "not an object"
    name = human.get("name")
    if not isinstance(name, str) or not name.strip() or "\n" in name or len(name) > 40:
        return None, f"bad name {name!r}"
    flavor = human.get("flavor")
    if not isinstance(flavor, str):
        return None, "flavor is not a string"
    picks = human.get("flavor_tags")
    if not isinstance(picks, list) or not all(isinstance(t, str) for t in picks):
        return None, "flavor_tags must be a list of tag ids"
    if len(picks) != sk.n_flavor:
        return None, f"flavor_tags has {len(picks)} entries, need {sk.n_flavor}"
    if len(set(picks)) != len(picks):
        return None, "flavor_tags are not distinct"
    menu = set(sk.flavor_tag_menu)
    invented = [t for t in picks if t not in menu]
    if invented:
        return None, f"invented tags {invented} (not on the menu)"
    try:
        skeleton_to_card(sk, name=name, flavor=flavor, flavor_tags=picks)
    except (SchemaError, ValueError, TypeError) as exc:
        return None, f"schema error: {exc}"
    return {"name": name, "flavor": flavor, "flavor_tags": list(picks)}, ""


def _unique_names(entries: list[dict]) -> bool:
    seen: set[str] = set()
    for e in entries:
        key = e["name"].strip().lower()
        if key in seen:
            return False
        seen.add(key)
    return True


def _error_summary(raw, skeletons: list[CardSkeleton]) -> str:
    if not isinstance(raw, list) or len(raw) != len(skeletons):
        return "wrong card count"
    lines = []
    for i, sk in enumerate(skeletons):
        _entry, err = _validate_entry(raw[i], sk)
        if err:
            lines.append(f"  card {i + 1}: {err}")
    return "\n".join(lines) if lines else "unknown validation failure"


def _retry_note(errors: str) -> str:
    return ("The following cards were rejected. Return the FULL JSON array "
            "again (same order, all cards), fixing only these entries:\n"
            f"{errors}")


def _validate_or_fill(raw, skeletons: list[CardSkeleton]) -> list[dict]:
    out: list[dict] = []
    for i, sk in enumerate(skeletons):
        entry, _err = _validate_entry(raw[i], sk) if isinstance(raw, list) \
            and i < len(raw) else (None, "")
        if entry is not None:
            out.append(entry)
        else:
            out.append(_fill(sk, i))
    return out


def _fill(sk: CardSkeleton, index: int) -> dict:
    name = f"Untitled {index + 1}"
    return {"name": name, "flavor": "", "flavor_tags": list(sk.flavor_tag_menu[: sk.n_flavor])}
