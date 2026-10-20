# SUNDER — the Sundered spectrum

Sunder is a procedural duel card game inspired by Hearthstone, with LLM-assisted pack generation. Two pirate-radio broadcast stations fight for the airwaves — you play tracks, air broadcasts, and fight for signal in a fully deterministic rules engine. The twist: new card packs are generated with an LLM, but **the LLM never invents mechanics** — it only shapes flavor, while a seeded sampler produces cards that are schema-valid, budgeted, and executable by the same engine that runs the game.

## The reskin

Everything classic is renamed via `sunder/lore.py`:

| Classic     | Sunder     |
|-------------|------------|
| Hero / life | Station / Signal (30) |
| Mana        | Bandwidth (cap 10, +1/turn) |
| Deck        | Playlist   |
| Discard pile| Static     |
| Minion      | Broadcast  |
| Spell       | Track      |
| Enchantment | Loop       |
| Token       | Echo       |
| Damage      | Noise      |

## Quick start

```bash
# game + web UI server (needs Python >= 3.11)
pip install -e .
python -m sunder                      # web: http://localhost:8000

# terminal battle (Station 1 = you, Station 2 = AI)
python -m sunder cli

# production SPA build (served automatically at / if web/dist exists)
npm install && npm run build --prefix web
npm run test     --prefix web         # frontend tests
```

Right now matches pit the two starter decks (`neon_frequency` vs `cinderworks`) against each other; the AI is a greedy heuristic opponent — no search, no LLM. Going second gets a **Signal Spike** (a free Track that grants +1 Bandwidth this turn) as second-player compensation — the coin analog.

## CLI

```bash
python -m sunder codex [query]        # browse the card set, show budget verdicts
python -m sunder codex -j             # same, raw JSON
python -m sunder gen "radio ghost"    # generate a 5-card LLM pack for a theme
python -m sunder gen "radio ghost" --count 8 --seed 42 --json
python -m sunder gen "radio ghost" --no-llm   # deterministic-only pack
```

## LLM card generation

```bash
python -m sunder gen <theme>
```

Pipeline (one call = one pack of up to 10 cards):

1. **Theme profile** (`gen/profile.py`) — one LLM call: affinity weights over the closed vocabulary (types/rarities/triggers/effects/targets/keywords/tags), a name pool and a flavor brief. May propose ≤ 2 **new tags** with optional structured `mechanic`, validated and registered.
2. **Sampler** (`gen/sampler.py`) — deterministic `random.Random(seed)`: rarity, type, keywords, ability tuples, stats, tags. Tag mechanics load onto the carrying card so "a card that carries the tag actually does what the tag promises".
3. **Novelty ledger** (`gen/ledger.py`) — tests each candidate design against the whole starter codex so packs don't re-ship existing designs.
4. **Budget** (`budget.py`) — cost is set so every card is in-budget by construction; over-budget cards go through a downgrade ladder (drop ability → drop keyword → shave stats) instead of a reroll.
5. **Humanizer** (`gen/humanizer.py`) — the only other LLM touch, one tight batched call: card *names*, *flavor text*, *tag picks* — strictly validated (≤ 40 chars, unique names, tags chosen verbatim from the offered menu). Up to 3 retries, then deterministic fallback.

Output mode is `"llm"` only if the humanizer succeeded with a non-fallback profile, else `"deterministic"`. Profiles are cached in `sunder/gen/cache/` keyed by theme + schema version. Graceful degradation throughout — bad JSON, timeout or missing gateway just means smaller/deterministic output, never a crash.

### LLM endpoint

The client (`gen/client.py`) is a small hand-rolled OpenAI-compatible chat-completions client over `httpx`, all defaults configurable:

| Env var               | Default                     |
|-----------------------|-----------------------------|
| `SUNDER_LLM_BASE_URL` | `http://127.0.0.1:20128/v1` |
| `SUNDER_LLM_MODEL`    | `oc/big-pickle`             |
| `SUNDER_LLM_API_KEY`  | *(optional)*                |
| `SUNDER_LLM_TIMEOUT`  | `120`                       |

## Server API

FastAPI app (`sunder/server/app.py`), docs at `/api/docs`:

- `GET  /api/cards` `/api/keywords` `/api/tags` `/api/registry` `/api/health`
- `POST /api/registry`                                    — propose a tag
- `POST /api/registry/{kind}/{id}/approve`                — approve a proposal
- `POST /api/generate`                                    — run `generate_pack` (async thread)
- `WS   /ws` — the match protocol: `start` / `restart` / `play {hand, target?}` / `attack {board, target}` / `end_turn`, all answers as full `state` snapshots

Snapshots (`state.py`) are viewer-aware: opponent hand is a count, hidden B-SIDEs are masked AND precomputed server-side (`is_playable`, `attack_targets`, `legal_targets`) — the client stays dumb.

## Game engine

- **`primitives.py`** — the closed vocabulary: 3 card types, 4 rarities (incl. mythic `SUNDERED`), 9 triggers, 13 effects, 8 targets, 6 scalings.
- **`schema.py`** — `Card` dataclass + `parse_card()` validation: 0–3 abilities, 0–4 known keywords, stats only for Broadcasts, tags must be registered/approved.
- **`engine.py`** — the data-driven ability resolver: runs *any* schema-conforming card deterministically, with trigger firing, death processing, stacking, `X` scaling.
- **`game.py`** — zone/turn loop, combat, board cap 6, stacks, `check_win` at 0 Signal (single implementation — the engine delegates to it).
- **`ai.py`** — greedy heuristic opponent: lethal damage → removal → most expensive playable → value trades → face damage, paced with jittered delays for realism.

Costs don't need hand-balancing: `budget.py` derives cost from clause scores (`suggested_cost = score / 2`), so any mechanical shape resolves to a fair price tier by construction, with rarity-tiered tolerance (COMMON 2 … SUNDERED 4).

## Keywords (13)

| Key       | Display | Rules |
|-----------|---------|-------|
| `LOUD`    | LOUD | Can attack the turn it's aired. |
| `RUSH`    | RUSH | Can attack Broadcasts immediately, but not the rival station. |
| `ECHO`    | ECHO | When this goes silent, do the listed effect. |
| `AMP`     | AMP  | +1/+1 each time a Broadcast is aired. |
| `CARRIER` | CARRIER | Always-on ability (aura). |
| `BEACON`  | BEACON | Enemy Broadcasts must target this one (taunt). |
| `DISTORT` | DISTORT | Noise this deals to Broadcasts is lethal. |
| `FILTER`  | FILTER | Negates the first Noise dealt to this. |
| `DRAIN`   | DRAIN | Noise this deals also boosts your Signal. |
| `FEEDBACK`| FEEDBACK | Attacks twice. |
| `MASKED`  | MASKED | Can't be targeted until it attacks. |
| `FUSE`    | FUSE | Detonates when the fuse expires. |
| `B_SIDE`  | B-SIDE | Hidden until its listed condition triggers. |

## Card data

Sets live in `sunder/cards/*.json` — lists of cards:

```json
{
  "id": "neonfreq_001", "name": "Vinyl Golem", "set": "neon_frequency", "plane": "neon_frequency",
  "rarity": "COMMON", "cost": 4, "type": "BROADCAST", "stats": {"atk": 3, "def": 5},
  "keywords": ["ECHO"],
  "tags": ["vinyl", "static"],
  "abilities": [{"trigger": "ON_DEATH", "effect": "GAIN_LIFE", "target": "SELF", "scaling": "FLAT", "value": 3}],
  "flavor": "…"
}
```

Tag + keyword governance lives in `sunder/cards/registry.json` (`proposed → approved` lifecycle, mechanic attachments, keyword reminders). See `python -m sunder codex` for the human view.

## Docs

Full documentation lives in [docs/](docs/index.md):

- [Rules](docs/rules.md) — turn loop, combat, all 13 keywords
- [Architecture](docs/architecture.md) — module map, closed vocabulary, engine design
- [Card format](docs/cards.md) — JSON schema, budget model, registry governance
- [Card generation](docs/generation.md) — the LLM pipeline + review gate
- [Server API](docs/api.md) — REST + WebSocket protocol, snapshot shape
- [Developing](docs/developing.md) — setup, tests, lint, CI, Docker/homelab deploy

## Testing

```bash
pytest tests -x
```

- **Engine** — combat, interactions, all 13 keywords, B-side, bandwidth, state snapshots
- **Match** — AI vs AI across seeds: every match terminates, every seed is deterministic
- **Generation** — every module in isolation (client/SSE, profile, sampler, ledger, humanizer, legality, end-to-end with a `FakeLLM` double), including graceful-degradation paths
- **Web** — API routes, tag registry, WS loop

## Status / notes

- v0.3.6.1 — changelog inside the game UI (Changelog tab) with a short roadmap.
- Card backs are hand-editable SVG art (`web/src/art/sleeves/*.svg`), one file per sleeve, themed via palette channels from `sunder/cards/sleeves.json`. Browse + pick in the codex (SLEEVES tab), carried server-side per station so opponents see your back too. Adding a sleeve = one JSON entry + one SVG.
- Second station starts with a Signal Spike — the coin analog for the first-turn tempo advantage.
- AMP is a "trigger macro" keyword: implemented engine-side, it buffs the aired card +1/+1 for every Broadcast aired (counting itself, either station, and DOUBLE_NEXT_TRIGGER doubles). ECHO is declarative — the card's ON_DEATH ability carries the behavior, and schema validation guarantees every ECHO card actually has one.
