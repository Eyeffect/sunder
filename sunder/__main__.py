"""SUNDER — entry points.

  python -m sunder            launch the web server (browse to localhost:8000)
  python -m sunder codex …    browse the codex from the terminal
  python -m sunder cli        play the headless print battle
"""

from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "codex":
        from .codex import main as codex_main
        sys.exit(codex_main(args[1:]))
    if args and args[0] == "cli":
        from .cli import main as cli_main
        cli_main()
        return
    from .server.serve import main as web_main
    web_main()


if __name__ == "__main__":
    main()
