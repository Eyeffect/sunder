# SUNDER documentation

A procedural duel card game — two pirate-radio broadcast stations fight for
the airwaves, and an LLM generates new card packs that never break the rules.

| Doc | What's in it |
|---|---|
| [Rules](rules.md) | How a match plays: turn loop, combat, all 13 keywords, win condition |
| [Architecture](architecture.md) | Module map, the closed vocabulary, why the engine never special-cases cards |
| [Card format](cards.md) | JSON schema for sets, the cost budget, tag + keyword governance |
| [Card generation](generation.md) | The LLM pipeline end-to-end: profile → sampler → ledger → budget → humanizer |
| [Server API](api.md) | REST endpoints, the WebSocket match protocol, snapshot shape |
| [Developing](developing.md) | Setup, tests, lint, CI, and deploying the web server (Docker, efx-lab) |

For a quick start (play, CLI, generating packs) see the repo [README](../README.md).
