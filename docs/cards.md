# Card format

Sets live as JSON files in `sunder/cards/*.json` — flat arrays of card dicts.
Enum values are the exact uppercase strings from `primitives.py`
(no case normalization happens at parse).

```json
{
  "id": "neonfreq_001", "name": "Vinyl Golem", "set": "neon_frequency",
  "plane": "neon_frequency",
  "rarity": "COMMON", "cost": 4,
  "type": "BROADCAST", "stats": {"atk": 3, "def": 5},
  "keywords": ["ECHO"],
  "tags": ["vinyl", "static"],
  "abilities": [
    {"trigger": "ON_DEATH", "effect": "GAIN_LIFE",
     "target": "SELF", "scaling": "FLAT", "value": 3}
  ],
  "flavor": "It remembers every beat pressed into it."
}
```

## Fields

| Field | Notes |
|---|---|
| `id` | unique within the set; convention `<set-slug>_###` |
| `name` / `set` / `plane` | display strings; `plane` is the theme |
| `rarity` | `COMMON` / `UNCOMMON` / `RARE` / `SUNDERED` (mythic tier) |
| `cost` | Bandwidth 0–10 |
| `type` | `BROADCAST` / `TRACK` / `LOOP` |
| `stats` | `{atk, def}` — **Broadcast only** (set 0 for Tracks/Loops) |
| `keywords` | 0–… from the [13-keyword table](rules.md); unknown keys rejected |
| `tags` | 0–4, unique, must be **approved** in `cards/registry.json` |
| `abilities` | 0–3 × [ability shape](#ability-shape) |
| `flavor` | optional flavor-line string |

## Ability shape

```json
{"trigger": "…", "effect": "…", "target": "…",
 "scaling": "FLAT", "value": 1, "value_def": 0,
 "condition": {}, "count_type": "BROADCAST", "tag": "ember",
 "keyword": "…"}
```

* **trigger** (9): `ON_PLAY`, `ON_ATTACK`, `ON_DEATH`, `ON_TURN_START`,
  `ON_TURN_END`, `ON_CAST_TRACK`, `ON_ANY_BROADCAST_PLAYED`,
  `ON_FUSE_EXPIRED`, `STATIC` (always-on aura, not event driven).
* **effect** (13): `DEAL_DAMAGE`, `GAIN_LIFE`, `DRAW_CARD`, `BUFF_STAT`,
  `SUMMON_TOKEN`, `RETURN_FROM_DISCARD`, `COPY_LAST_TRACK`,
  `COUNTER_TRACK`, `DESTROY`, `GRANT_KEYWORD`, `DOUBLE_NEXT_TRIGGER`,
  `GAIN_BANDWIDTH`, `UNCAP_BANDWIDTH`.
* **target** (8): `SELF`, `ENEMY_FACE`, `ENEMY_BROADCAST`, `ALL_ENEMY_BROADCASTS`,
  `ALL_YOUR_BROADCASTS`, `ALL_BROADCASTS`, `RANDOM`, `CHOSEN`.
* **scaling** (6): `FLAT`, `X_TURN_NUMBER`, `X_CARDS_PLAYED_THIS_TURN`,
  `X_COUNT_OF_TYPE_ON_BOARD` (with `count_type`),
  `X_COUNT_OF_TAG_ON_BOARD` (with `tag`),
  `X_TIMES_THIS_TRIGGERED_THIS_GAME`.
* **condition**: optional `{"min_turn": n}` / `{"not_self": true}` /
  `{"has_tag": "…"}` (guard on the firing event), combined.
* `keyword` / `tag` are payloads for `GRANT_KEYWORD` and
  `X_COUNT_OF_TAG_ON_BOARD` respectively.

## Validation invariants (`parse_card`)

* 0–3 abilities, 0–4 tags, no duplicated tag.
* Every trigger/effect/target/scaling is a known enum value.
* Unknown keywords rejected (legacy `STATIC` auto-maps to `CARRIER`).
* `BROADCAST` counts on stats; other types must not carry stats.
* Every tag on the card must be **approved** in the registry.
* **ECHO requires an `ON_DEATH` ability** — the keyword promises an effect on
  death; the validator enforces that the card actually has one.
* FUSE broadcasts carry a `fuse` counter that ticks at their owner's turn start.

## Budget model

Cost isn't hand-tuned. `budget.budget_score()` sums clause weights —
stats (atk+def), per-effect values (×3 for repeating triggers, ×2 for group
targets, ×0.5 for delayed FUSE payoff), keyword costs — and
`suggested_cost = max(0, round(score / 2))`. `check_budget()` accepts a card
when its suggested cost sits within rarity tolerance (COMMON±2, UNCOMMON±2,
RARE±3, SUNDERED±4). Starter sets are all checked in-budget by tests.

## Registry + governance

`cards/registry.json` (schema_version 1):

* `tags` — 6 approved starters (`vinyl, chrome, ghost, static, ember, tide`)
  plus whatever passed the review queue; entries may carry a structured
  `mechanic` (validated trigger/effect/target tuple) that generation loads
  onto carrier cards — "a card that carries the tag actually does what the
  tag promises".
* `keywords` — auto-synced from the engine's `KEYWORD_REGISTRY`.

Lifecycle: `proposed → approved` (sampler may draw it) or `rejected` (stays
gated until someone re-opens it). LLM `proposed_tags` land in the review
queue, never straight into packs — see [generation.md](generation.md).
Browse everything human-friendly with `python -m sunder codex`.
