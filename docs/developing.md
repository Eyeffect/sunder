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
3. `web/package.json` `version` — header readout (`App.tsx` imports it);
   keep the two root `version` fields in `web/package-lock.json` in sync

Rules text, prompts, and engine semantics need care, because generation
prompts quote engine vocabulary. Changing triggers/effects/scalings/targets
means regenerating the legality coverage in `gen/legality.py` and matching
it to `_SCORE_CAP`/budget weights — [cards.md](cards.md) documents exactly
where each table lives.

## Adding a card-back sleeve

Sleeves are defined in **one JSON file**: `sunder/cards/sleeves.json`
(`schema_version` 2, per-sleeve art). `sunder/sleeves.py` loads the
manifest at server start and serves it at `GET /api/sleeves`, validates
WS `set_sleeve` ids against it, and stores the chosen sleeve per station
(`players[*].sleeve` in snapshots) — restart the Python server to pick up
edits to the file. The client fetches the same manifest for the SLEEVES
gallery in the codex and falls back to a hard-coded 3-sleeve list offline.

1. Add an entry: `{"id": "mineral", "label": "Mineral", "palette": {"ink":
   "cyan", "glow": "green", "paper": "voidDeep"}}`.
2. Create the art file `web/src/art/sleeves/mineral.svg` — a 90×120 SVG
   with a single root element (see *Editing card-back art* below). Every
   manifest sleeve needs exactly one art file; the TS test suite asserts
   the id sets match on both sides.
3. `palette` channels reference theme.css colors by name (`amber`, `cyan`,
   `magenta`, `green`, `cinder`, `danger`, `text`, `voidDeep`, `panel`)
   resolved client-side in `web/src/sleeves.ts` (`CHANNELS`) — palettes
   never hardcode hex, so sleeves stay themable.
4. Optional `"plane": "<plane-id>"` — that deck (any playlist whose cards
   carry the plane) then wears this sleeve as its **default** back
   (`sunder/sleeves.py:seat_sleeve` resolves deck-plane → sleeve, falling
   back to the legacy ember/static seat colors for unknown planes). Your
   own `set_sleeve` pick still overrides your station; the opponent's deck
   keeps its plane's back.
5. Done. Tests guard the wiring both sides: `web/src/backPatterns.test.tsx`
   (art registry ↔ manifest parity, sentinel-color / forbidden-markup
   / unique-defs-id guards, renders every back), `web/src/sleeves.test.ts`
   (channel resolution, fallback↔manifest parity), `tests/test_sleeves.py`
   (deck-bound defaults), and `tests/test_web.py` (endpoint + `set_sleeve`
   acceptance + manifest schema).

## Profile icons (station avatars)

The avatar in each station panel is a **separate pick from the card back**.
Glyphs live in `sunder/cards/avatars.json` (`{id, label, glyph}`), loaded by
`sunder/avatars.py`, served at `GET /api/avatars`, and validated on WS
`set_avatar`. The server resolves the chosen id into `avatar` +
`avatar_glyph` on every player view; the client tints the glyph with
`sleeve_ink` (a palette channel name), so changing sleeves recolours the
icon without changing the glyph. The picker opens from your own station
avatar and the choice persists in `localStorage` under `sunder-avatar`.

Adding an icon is one JSON entry — no artwork: `{"id": "mineral", "label":
"Mineral", "glyph": "◆"}`. Keep `web/src/avatars.ts` (`FALLBACK_AVATARS`)
in sync for offline boot; `web/src/avatars.test.ts` asserts parity with the
server manifest. `tests/test_avatars.py` guards the manifest shape and
`tests/test_web.py` covers the endpoint, `set_avatar`, and rejection.

## Card faces

Every face uses the 2.5×3.5 playing-card ratio (5:7) at `--card-w` width;
hand, board, and codex share one layout:

`cost bars + edition/rarity badge → name → type → keyword chips/tags →
rules → flavor (codex only) → power/health`, with stats pinned to the
bottom.

- Rules clamp to 5 lines in hand/board and 4 in the codex. Firefox ignores
  `-webkit-line-clamp`, so the cap is an explicit `max-height`; when the
  text overflows, `ClampedText` sets `data-clipped` and the bottom fades.
- `CardBadge` prints the two-letter station code (`NF`/`CW`/`DG`/`SW`,
  fallback `FM`) above the rarity; codex `size-lg` cards swap in the full
  plane name. The same code is painted as the translucent
  `.card-watermark` in the bottom-right corner.
- Flavor is **not** printed on hand or board faces — hovering shows it in
  the inspector. The codex keeps its flavor line for reference.
- Playability lives on the hand cost bars, not on card opacity: the
  `playable` class paints the bars and cost in `--plane-color`, while
  `unplayable` greys them. `.hand-card` must stay fully opaque.
- Board cards render at `size="md"` (max 124px) so six slots fit; the
  single-column breakpoint is 1200px.

## Editing card-back art (Inkscape)

Card art is **hand-editable SVG source**, one file per sleeve:
`web/src/art/sleeves/<sleeve-id>.svg` (90×120 viewBox). The rim and
vignette stay in code (`web/src/backPatterns.tsx`), so files only carry
the interior art. Cards display at the standard 2.5×3.5 playing-card
ratio (5:7); the 3:4 art is center-sliced, so keep critical detail away
from the extreme left/right edges.

Open in Inkscape, edit, save as **Plain SVG** — the dev server picks the
change up instantly (`VITE_API_TARGET=http://127.0.0.1:8100 yarn dev` in
`web/`, then CODEX → SLEEVES); otherwise rebuild (`yarn build`).

Rules (enforced by `web/src/backPatterns.test.tsx`):

- Keep the `viewBox="0 0 90 120"` and a single root `<svg>`; one wrapping
  `<g>` is conventional.
- Paint **only** with the three palette sentinels, remapped to the
  sleeve's theme at runtime: `#ffb545` → `var(--sleeve-ink)`,
  `#5ff2e0` → `var(--sleeve-glow)`, `#030304` → `var(--sleeve-paper)`.
  Use opacity (or gradients over the paper) for shades.
- No scripts, event handlers, external hrefs, embedded images, `<style>`
  blocks, or `class` attributes — Firefox/Chrome render what the code
  permits.
- Text: set any font family, the loader normalizes `font-family` to the
  theme's mono face; sizes/spacings are preserved.
- Gradient/filter `id`s are namespaced per card instance automatically
  (`id="mt"` is fine; duplicate ids across backs were the old bug class).

An XML declaration and comments are stripped from the bundled copy and
Inkscape's `inkscape:`/`sodipodi:` leftovers are ignored at load time, but
prefer saving as Plain SVG so sources stay small.

## Registry safety

`registry.py` holds a module-level cache guarded by an RLock: web generation
runs in `asyncio.to_thread` while WS handlers mutate the same file. Never
bypass `propose`/`approve`/`set_status` to edit `cards/registry.json` — they
handle atomic writes (`tempfile` + `os.replace`) and the lock.
