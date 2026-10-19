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

## Registry safety

`registry.py` holds a module-level cache guarded by an RLock: web generation
runs in `asyncio.to_thread` while WS handlers mutate the same file. Never
bypass `propose`/`approve`/`set_status` to edit `cards/registry.json` — they
handle atomic writes (`tempfile` + `os.replace`) and the lock.
