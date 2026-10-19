# Rules

How a match of SUNDER plays. The vocabulary (Broadcast, Track, Signal, …)
is reskinned classic TCG terms — see the table in the [README](../README.md).

## Match setup

* Both stations open with **30 Signal** and identical-size playlists (starter sets: `neon_frequency` vs `cinderworks`), shuffled with the match seed.
* Each station draws **4 opening cards**.
* **Station 2 goes second and draws one extra Track: the Signal Spike** — a free Track that grants **+1 Bandwidth this turn**. This is the compensation for Station 1's first-move tempo advantage (the "coin" slot in other games).
* Turn 1 belongs to Station 1.

## Turn loop

1. **Refill** — `max_bandwidth = turns_taken` (+ any bonus, capped at **10** unless a card's UNCAP_BANDWIDTH removed the cap). Current Bandwidth refills to the max.
2. **Draw 1** from your playlist. Empty playlist → no draw (no fatigue mechanic).
3. **FUSE ticks** — broadcasts with a fuse counter tick; detonation fires their `ON_FUSE_EXPIRED` ability when the counter reaches the fuse number.
4. `ON_TURN_START` abilities fire.
5. **Main phase** — play cards, attack (any order).
6. `ON_TURN_END` abilities fire, then the turn passes.

Playing a card: pay its cost in Bandwidth, Broadcasts/Loops go to the airwaves (board, **cap 6** — the last card drifts to Static on overflow), Tracks resolve immediately and collapse into your Static pile.

## Combat

A Broadcast can attack when it is live (def > 0), hasn't attacked, and — unless it has **LOUD** — wasn't **aired this turn**. Logic:

* **FEEDBACK** broadcasts attack twice.
* **RUSH** lets an aired-one attack Broadcasts immediately — but not the rival station's Signal, unless it also has LOUD.
* **BEACON** taunt — while any enemy Broadcast has BEACON, all attacks must go to a BEACON.
* **MASKED** — can't be targeted (by attacks or chosen effects) until it has attacked; once it attacks, the mask is permanently broken.
* **Trade resolution** — simultaneous: defender takes the attacker's Noise; the attacker takes the defender's. Damage accumulates (`damage_taken`) and death is checked against remaining def, so an attacker always deals its Noise even if it dies in the trade.
* **DRAIN** — Noise that a DRAIN broadcast deals to Broadcasts *or* the rival station also heals its own Signal.
* **DISTORT** — any Noise this broadcast deals to Broadcasts is lethal.
* **FILTER** — negates the *first* Noise incoming damage once (per-card spent flag).

## Keywords (13)

| Key | Kind | Effect |
|---|---|---|
| `LOUD` | flag | Can attack the turn it's aired. |
| `RUSH` | flag | Can attack Broadcasts immediately, but not the rival station. |
| `ECHO` | trigger macro | When this goes silent, do the listed (death) effect. |
| `AMP` | trigger macro | +1/+1 to itself **each time any Broadcast is aired** (either station, itself included). |
| `CARRIER` | aura | Always-on ability (legacy alias: `STATIC` → `CARRIER`). |
| `BEACON` | flag | Enemy attacks must target this one (taunt). |
| `DISTORT` | modifier | Noise this deals to Broadcasts is lethal. |
| `FILTER` | one-shot modifier | Negates the first Noise dealt to it. |
| `DRAIN` | modifier | Noise dealt also boosts your own Signal. |
| `FEEDBACK` | flag | Attacks twice. |
| `MASKED` | targeting rule | Can't be targeted until it attacks. |
| `FUSE` | counter | Detonates when the fuse expires. |
| `B_SIDE` | hidden | Played face-down; reveals when a listed trigger condition fires. |

Notes:

* **ECHO is declarative** — the card's `ON_DEATH` ability is what fires; the card is served by its schema validation. Any card with ECHO *must* carry an `ON_DEATH` ability.
* **AMP is engine-implemented** (no separate ability needed): every aired Broadcast — including itself — counts.
* B-SIDE reveal, confusion, and hidden-death rules live in [Architecture](architecture.md).

## Death

A broadcast dies when `base_def + buff_def + aura − damage_taken ≤ 0` or a lethal hit was recorded (DISTORT). Death moves it to Static and fires `ON_DEATH` (ECHO) triggers, which can chain into further deaths until the board settles.

## Winning

Signal at 0 or below ends the match — one shared check (`GameState.check_win`) fires from anywhere (`engine._wincheck` delegates to it) so no code path can skip the referee.
