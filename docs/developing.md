# Developing

## Setup

```bash
pip install -e .            # Python ≥ 3.11; deps: fastapi, uvicorn[standard], httpx
pip install pytest          # test runner (kept out of project deps)
```

## Running

```bash
python -m sunder            # web server on 127.0.0.1:8000 (default)
python -m sunder --port <port> --host 0.0.0.0    # adjust to taste
python -m sunder cli        # headless print battle
python -m sunder codex      # card browser
```

The SPA ships in two modes:

* **dev** — `npm run dev` in `web/` (Vite proxies `/api` and `/ws` to the
  Python server; hot reload).
* **prod** — `npm run build` in `web/` produces `web/dist`; the server picks
  it up automatically on next start. Local `npm` may be unavailable; a yarn
  install (`yarn install && yarn build`) is equivalent for local builds
  (never commit a `yarn.lock` — CI uses `npm ci` against
  `package-lock.json`).

## Tests

```bash
pytest tests -q             # engine, combat, keywords, AI-vs-AI determinism,
                            # every gen module (FakeLLM doubles), server API/WS
cd web && npm run test      # vitest: components + socket layer
```

Style notes: AI-vs-AI matches are asserted to finish *and* replay
deterministically across seeds — if your change perturbs RNG order, that's
where you'll see it. Tests clean the registry cache via fixtures/monkeypatch;
never touch the real `cards/registry.json` by writing through
`registry.propose` outside that fixture — copy the pattern from
`tests/test_gen_generate.py`.

## Lint

Ruff is the only linter (config in `pyproject.toml`: rules `E4/E7/E9/F/I`,
100-col):

```bash
ruff check .                # CI runs exactly this
ruff check --fix .          # autofix import order + unused imports
```

## CI (`.github/workflows/ci.yml`)

* **lint** — `ruff check .`
* **python-test** — `pip install -e . pytest` + `pytest`, matrix 3.11/3.13
* **web-test** — node 22, `npm ci`, `npm run build` (includes `tsc --noEmit`),
  `npm run test`

## Deploying the web server

Two supported modes.

### Docker build (any host)

```bash
docker compose up -d --build      # image built in two stages:
                                  #   node:22-alpine → builds web/dist
                                  #   python:3.11-slim → runs uvicorn + SPA
```

Ports live in `docker-compose.yml` (defaults `8929:8000`). Runtime deps are
installed in the image layer above the source layer, so code-only changes
rebuild fast. `.dockerignore` keeps node_modules, local dist, caches, and
development docs out of the build context.

### Homelab (efx-lab) flow

The lab host consumes a tar-over-ssh stream (no rsync, no clone needed — the
repo is private):

```bash
tar -czf - --exclude='.git' --exclude='web/node_modules' \
    -C ~/Projects/sunder . \
  | rssh 'mkdir -p ~/apps/sunder && tar -xzf - -C ~/apps/sunder'
rssh 'docker compose -f ~/apps/sunder/docker-compose.yml up -d --build'
```

The tar ships `web/` without `node_modules`; the node build stage regenerates
`web/dist` inside the image. Verify with
`rssh 'curl -s localhost:8929/api/health'` → `{"ok": true}`.
Note: the LLM gateway is a localhost service on the
design machine, so generation inside the lab container falls back to
deterministic mode unless you expose the gateway and point
`SUNDER_LLM_BASE_URL` at it (compose `environment:`).

## Versioning + changelog

Version bumps are **three-file** (visible to users, CI, and packaging):

1. `web/src/changelog.ts` — add the `VersionEntry` (top of `VERSIONS`, set
   `current: true`, player-voiced changes; strip `current` from the
   previous entry)
2. `pyproject.toml` `version` — packaging/readme source of truth
3. `web/package.json` `version` — header readout (`App.tsx` imports it)

Rules text, prompts, and engine semantics need care, because generation
prompts quote engine vocabulary. Changing triggers/effects/scalings/targets
means regenerating the legality coverage in `gen/legality.py` and matching
it to `_SCORE_CAP`/budget weights — [cards.md](cards.md) documents exactly
where each table lives.

## Adding a card-back sleeve

Sleeves are defined in **one JSON file**: `sunder/cards/sleeves.json`.
`sunder/sleeves.py` loads the manifest at server start and serves it at
`GET /api/sleeves`, validates WS `set_sleeve` ids against it, and stores
the chosen sleeve per station (`players[*].sleeve` in snapshots) — restart
the Python server to pick up edits to the file. The client fetches the
same manifest for the SLEEVES gallery in the codex and falls back to a
hard-coded 3-sleeve list offline.

1. Add an entry: `{"id": "mineral", "label": "Mineral", "pattern":
   "staticNoise", "palette": {"ink": "cyan", "glow": "green", "paper":
   "voidDeep"}, "emblem": "◆"}`.
2. `pattern` keys into the SVG pattern library in `web/src/
   backPatterns.tsx` (`wavelength`, `starburst`, `staticNoise`, `circuit`,
   `vinyl`, `spool`, `mixtape`, `vhs`, `topo`, `barcode`) — add a new
   component there only if you want a genuinely new *art style*. The
   manifest's top-level `patterns` catalog must list every shipped
   pattern; the TS test suite asserts it matches the library exactly, and
   the Python test suite validates manifest structure against it.
3. `palette` channels reference theme.css colors by name (`amber`, `cyan`,
   `magenta`, `green`, `cinder`, `danger`, `text`, `voidDeep`, `panel`)
   resolved client-side in `web/src/sleeves.ts` (`CHANNELS`) — palettes
   never hardcode hex, so sleeves stay themable. The TS drift test
   validates every manifest channel against `CHANNELS`.
4. Optional `"plane": "<plane-id>"` — that deck (any playlist whose cards
   carry the plane) then wears this sleeve as its **default** back
   (`sunder/sleeves.py:seat_sleeve` resolves deck-plane → sleeve, falling
   back to the legacy ember/static seat colors for unknown planes). Your
   own `set_sleeve` pick still overrides your station; the opponent's deck
   keeps its plane's back.
5. Done. Tests guard the wiring both sides: `web/src/backPatterns.test.tsx`
   (every manifest pattern must have a rendered component; renders them
   all), `web/src/sleeves.test.ts` (channel resolution, fallback↔manifest
   parity), `tests/test_sleeves.py` (deck-bound defaults), and
   `tests/test_web.py` (endpoint + `set_sleeve` acceptance + manifest
   schema).

## Registry safety

`registry.py` holds a module-level cache guarded by an RLock: web generation
runs in `asyncio.to_thread` while WS handlers mutate the same file. Never
bypass `propose`/`approve`/`set_status` to edit `cards/registry.json` — they
handle atomic writes (`tempfile` + `os.replace`) and the lock.
