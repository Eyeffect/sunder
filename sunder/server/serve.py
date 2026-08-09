"""Launch the SUNDER web server (FastAPI + uvicorn).

`python -m sunder` starts this; `python -m sunder web --port 8000` also works.
Serves the built SPA from `web/dist` when present (dev: run `npm run dev` in
`web/` and Vite proxies /ws and /api to this server).
"""

from __future__ import annotations

import argparse

import uvicorn

from .app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="SUNDER web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
