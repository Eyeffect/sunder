# SUNDER — Design Document v1.0

## 1. Identity & lore

The Sundering cracked the multiverse; every plane's signal now leaks into one shared
spectrum. You are a **broadcast station**. Every card is a transmission bleeding in
from some world. Reduce the rival station's Signal to 0 to cut it **off the air**.

## 2. Glossary (player-facing; engine enums stay mechanical)

| Mechanic | Sunder term | Mechanic | Sunder term |
|---|---|---|---|
| Life (20) | Signal | Enchantment | Loop |
| Mana (1→10) | Bandwidth | Token (1/1) | Echo |
| Draw | Cue | Damage | Noise |
| Deck (20) | Playlist | Counter | Cut |
| Board (cap 6) | Airwaves | Destroy | Jam |
| Discard | Static | Booster (5) | Transmission |
| Creature | Broadcast | Currency | Watts |
| Instant/Sorcery | Track | Mythic rarity | Sundered |
| Summoning sickness | warming up | Win | rival off the air |

## 3. Core rules

- Signal 20; lose at 0. Bandwidth starts 1, +1/turn, cap 10, refills fully each turn.
- Turn: Bandwidth → Cue 1 → Main → Combat → Main2 → End. No untap/tap.
- Zones: Playlist, Hand, Airwaves, Static. Board cap 6. No hand limit. Deck exactly 20, max 2 copies/card.
- Types: **Broadcast** (atk/def, can't attack turn aired unless LOUD/RUSH), **Track** (one-shot, resolves instantly, no stack), **Loop** (persistent, can't attack).
- Combat (Hearthstone-style): attacker picks a target — an enemy Broadcast or the enemy Signal. Broadcasts trade damage simultaneously; damage persists; def = HP; death at ≤0 → jam → Static + ON_DEATH. No blockers.
- BEACON rule: while a Beacon is on the enemy airwaves, their attackers must target it if able; Signal can't be hit while one is on air.
- Win: opponent Signal ≤ 0.

## 4. Card schema

```
{ "id", "name", "set", "plane", "rarity", "cost", "type",
  "stats": {"atk","def"} (Broadcast only), "abilities": [1–3],
  "keywords": [], "fuse": N (optional), "flavor" }

Ability = { trigger, condition?, effect, scaling, target, value }
```

## 5. Ability grammar

- **Trigger** (grows as data): ON_PLAY, ON_ATTACK, ON_DEATH, ON_TURN_START, ON_TURN_END,
  ON_CAST_TRACK, ON_ANY_BROADCAST_PLAYED, ON_FUSE_EXPIRED, STATIC (always-on)
- **Effect** (CLOSED core — determinism lives here):
  DEAL_DAMAGE, GAIN_LIFE, DRAW_CARD, BUFF_STAT, SUMMON_TOKEN, RETURN_FROM_DISCARD,
  COPY_LAST_TRACK, COUNTER_TRACK, DESTROY, GRANT_KEYWORD, DOUBLE_NEXT_TRIGGER,
  GAIN_BANDWIDTH, UNCAP_BANDWIDTH
- **Scaling**: FLAT, X_COUNT_OF_TYPE_ON_BOARD, X_CARDS_PLAYED_THIS_TURN, X_TURN_NUMBER,
  X_TIMES_THIS_TRIGGERED_THIS_GAME  (X_ overrides value with the live metric)
- **Target**: SELF, ENEMY_FACE, ENEMY_BROADCAST, ALL_ENEMY_BROADCASTS, ALL_YOUR_BROADCASTS,
  ALL_BROADCASTS, RANDOM, CHOSEN
- **Condition**: `min_turn`, `not_self` (trigger ignores its own airing).
- **Key semantics**: copies are not "played" (no ON_PLAY recursion); COPY_LAST_TRACK copies
  the last Track in Static and inherits its target (re-choose if CHOSEN, fizzle if gone);
  tokens default to a 1/1 Echo. Bandwidth refills to `min(10, turns taken + bonus)` each
  turn; `GAIN_BANDWIDTH` adds this turn only; `UNCAP_BANDWIDTH` removes the 10 cap.

## 6. Keywords (macros/modifiers; key → display → reminder)

| Key | Display | Reminder | Kind |
|---|---|---|---|
| LOUD | LOUD | Can attack the turn it's aired | flag |
| RUSH | RUSH | Can attack Broadcasts immediately, not Signal | flag |
| ECHO | ECHO | On death, do the listed effect | trigger macro |
| AMP | AMP | +1/+1 each time a Broadcast is aired | trigger macro |
| CARRIER | CARRIER | Always-on ability | modifier/aura |
| BEACON | BEACON | Enemy Broadcasts must target this one | flag |
| DISTORT | DISTORT | Noise this deals to Broadcasts is lethal | damage modifier |
| FILTER | FILTER | Negates the first Noise dealt to this | one-shot modifier |
| DRAIN | DRAIN | Noise this deals also boosts your Signal | damage modifier |
| FEEDBACK | FEEDBACK | Attacks twice | flag |
| MASKED | MASKED | Can't be targeted until it attacks | targeting rule |
| FUSE | FUSE n | Detonates n of your turns after airing | counter + trigger |
| (SECRET) | B-SIDE | Hidden until its listed condition triggers; untargetable while hidden | hidden Loop |

## 7. Rarity

Tiers as complexity/deviation budgets: Common (1 simple ability, tight),
Uncommon (1 interesting / 2 simple), Rare (engine/rule-bender), Sundered (run-defining).

Drop table (per card slot, packs + stream): Common 76%, Uncommon 20%, Rare 3%, Sundered 1%
→ ~1 Sundered per 20 packs. Floor rule: any all-common pack bumps one slot to Uncommon.
No duplicate card within a pack.

## 8. Economy & loop

Battle (win +5W, loss +2W) → buy Transmissions (8W): type a theme → 5-card pack → collection.
Persistent set per theme (seeded), revealed in rarer chunks over time. Stream menu: free/cheap
random cards (~1/min), same rarity table, the main source of Rares. Deck builder: exactly 20,
max 2 copies, from your collection.

## 9. Generation architecture (P3)

1. Theme profile (LLM, once): primitive weights + keyword affinity + name pool + flavor brief; cached.
2. Deterministic sampler: combinatorial space, seeded by theme, rarity ceilings.
3. Novelty ledger: reject near-duplicate ability signatures.
4. LLM humanizer: validate, tune numbers, write name + flavor; validator reject/retry.
5. Closed effect core; conditions/scalings/keywords grow as grammar-checked data.

## 10. Vocabulary growth (validated in design-test)

FUSE counter + ON_FUSE_EXPIRED · DRAIN as damage modifier · COPY semantics (no recursion,
inherit target) · X_ scalings override value · 1/1 Echo tokens. New triggers/conditions/
scalings/keywords are data-level additions; effects stay closed.

## 11. Open / future

P5 gauntlet + budget loosening · growing keyword registry ·
LLM provider/key for P3 · collection screen & deck-builder UI · stream cadence tuning.

## 12. Phase roadmap

- **P1 ✅** — closed engine, starter 20, budget validator, heuristic AI, print CLI, tests.
- **P2 ✅** — B-SIDE completion (reveal + untargetability) and a Textual TUI.
- **P3 ✅** — web app (React + TS + Vite over FastAPI/WebSocket): battle UI, codex page,
  theming/animations; Textual TUI removed.
- **P4** — LLM-assisted generation (see §9).
- **P5** — economy/collection, transmissions, deck builder, stream.
- **P6** — gauntlet, tuning, budget loosening.
