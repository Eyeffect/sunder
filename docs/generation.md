# Card generation

`python -m sunder gen <theme>` (or `POST /api/generate`) turns a free-word
theme into a pack of up to 10 playable cards. Design principle, all the way
down: **the LLM never invents mechanics** — it weights a closed vocabulary
and strings words together; a seeded sampler produces all mechanical
content. Every generated card is schema-valid, in-budget, and executable
without any new engine code.

## Pipeline (one run = one pack)

```
theme ──profile──▶ ThemeProfile ──sampler──▶ skeleton(s) ──ledger──▶ novelty check
                       │                          │
                       │                       budget ladder (cost clamp)
                       │                          │
                       └──humanizer◀────names/flavor picks──▶ pack
```

**1. Theme profile** (`gen/profile.py`) — one LLM call. The model returns
affinity weights (0–1, clamped) for every type/rarity/trigger/effect/target/
keyword/tag, a name pool, and a flavor brief. It may **propose up to 2 new
tags**, each optionally carrying a structured `mechanic`; proposals are
validated (`gen/legality.py`) and, if sound, registered with a machine-
derived reminder text — as `proposed`, into the review queue. Only a human
approve turns them draw-able (see below). Profiles are cached on disk in
`sunder/gen/cache/` keyed by theme slug + profile schema version; a
*fallback-grade* cache gets one bounded re-probe.

**2. Sampler** (`gen/sampler.py`) — deterministic `random.Random(seed)`:
rarity (SUNDERED ≤1, RARE ≤2 per pack), type, keywords, ability tuples
(value mix: FLAT 72% / X_TURN_NUMBER 12% / X-tag 16%), stats, tags. When the
card's load-bearing tag has a mechanic and its type can host it, the
mechanic becomes the card's primary ability — thematic identity is
mechanical, not just flavor. Cards with ECHO are forced to pair a death
trigger, then re-paired on the budget ladder below (so the keyword's
promise survives downgrades).

**3. Novelty ledger** (`gen/ledger.py`) — signature =
(type, keywords, ability tuple, load-bearing tag); pre-seeded from the whole
starter codex so packs don't re-ship existing designs. 5 re-roll attempts,
then the tag slot relaxes, then the duplicate is *accepted* and logged as
"near-duplicate" (the pool is finite; honesty over silence).

**4. Budget ladder** (`budget.py` + sampler) — cost is set **equal** to
`suggested_cost()`, so cards are in-budget by construction, then a per-
rarity ceiling keeps packs draftable: COMMON 6 / UNCOMMON 8 / RARE 11 /
SUNDERED 14 score-caps. Over-budget skeletons go through a downgrade
ladder — drop 2nd ability → drop costliest keyword → reduce def / atk →
shave the remaining ability's values — never re-rolled stats; a line is
logged if the true floor is reached.

**5. Humanizer** (`gen/humanizer.py`) — the *only* other LLM touch, one
batched call per pack: `[{name, flavor, flavor_tags}]` per skeleton. Strict
validation: names ≤ 40 chars / newline-free / unique within the pack, tags
picked verbatim from the offered menu (invented tags rejected), flavors
plain strings. Up to 3 attempts (errors fed back as retry notes);
skeletons that never make it stay deterministic.

**6. Assembly** (`gen.generate`) — merged skeleton + names → `parse_card()`
on every card (guaranteeing schema validity). The result carries
`{cards, theme, seed, mode}` where `mode` is `"llm"` only when the humanizer
succeeded against a real (non-fallback) profile, else `"deterministic"`.

## Review gate

Proposed tags from the LLM lifecycle are **not** auto-approved:

1. `gen/profile.py::_register_proposals` calls `registry.propose` — landing
   them as `proposed` in `cards/registry.json`.
2. Previously **rejected** tags are re-opened to `proposed` but never
   approved again without a human action.
3. The web REGISTRY panel (or `POST /api/registry/{kind}/{id}/approve`) is
   the approval switch. Until approved, the tag is invisible to the sampler
   and cannot appear on cards.

## LLM endpoint + env

Hand-rolled OpenAI-compatible chat-completions client over `httpx`
(`gen/client.py`). It tolerates gateways that stream-even-when-asked-not-to,
strips ` ```json ` fences, parses either SSE frames or plain JSON bodies,
and retries twice with a 120 s timeout. On any LLM failure the pack degrades
to deterministic mode — no crash, smaller pack.

| Env var | Default |
|---|---|
| `SUNDER_LLM_BASE_URL` | `http://127.0.0.1:20128/v1` |
| `SUNDER_LLM_MODEL` | `oc/big-pickle` |
| `SUNDER_LLM_API_KEY` | *(optional)* |
| `SUNDER_LLM_TIMEOUT` | `120` |

## CLI

```bash
python -m sunder gen "radio ghosts"            # 5-card pack (model + sampler)
python -m sunder gen "radio ghosts" --count 8 --seed 42 --json
python -m sunder gen "radio ghosts" --no-llm   # skip profile + humanizer
```

Same theme + same seed + same approved-registry = the same pack, always.
