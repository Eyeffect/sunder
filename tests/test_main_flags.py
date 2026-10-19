"""Entry-point flags: --version and --help must not start the web server."""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "sunder", *args],
                          capture_output=True, text=True, timeout=30)


def test_version_flag():
    p = _run("--version")
    assert p.returncode == 0
    assert p.stdout.strip() == version("sunder")


def test_short_version_flag():
    p = _run("-V")
    assert p.returncode == 0
    assert version("sunder") in p.stdout


def test_help_flag():
    p = _run("--help")
    assert p.returncode == 0
    assert "codex" in p.stdout and "gen" in p.stdout
