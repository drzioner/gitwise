"""Dual output: human-readable + JSON. Detects bat/delta/rg availability."""

import json
import os
import shutil
import sys
from typing import Any

HAS_BAT = bool(shutil.which("bat"))
HAS_DELTA = bool(shutil.which("delta"))

_NO_COLOR = os.environ.get("GITWISE_NO_COLOR", "").lower() in ("1", "true")
IS_TTY = sys.stdout.isatty() and not _NO_COLOR
DEBUG = os.environ.get("GITWISE_DEBUG", "").lower() in ("1", "true")


def info(msg: str) -> None:
    print(msg)


def warn(msg: str) -> None:
    print(f"advertencia: {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"✓ {msg}")


def debug(msg: str) -> None:
    if DEBUG:
        print(f"[gitwise debug] {msg}", file=sys.stderr)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def confirm(prompt: str) -> bool:
    try:
        resp = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return resp in ("s", "si", "sí", "y", "yes")


def bat_pipe(text: str, language: str = "plain") -> None:
    """Print text via bat (highlighted) when available and stdout is a TTY."""
    if not text:
        return
    if not text.endswith("\n"):
        text += "\n"
    if HAS_BAT and IS_TTY:
        import subprocess

        # Only pass --language for named syntaxes; omit for plain text (auto-detect)
        cmd = ["bat", "--style=plain", "--pager=never", "--color=always"]
        if language and language != "plain":
            cmd += ["--language", language]
        try:
            r = subprocess.run(cmd, input=text, text=True, check=False, stderr=subprocess.DEVNULL)
            if r.returncode == 0:
                return
        except OSError:
            pass
    print(text, end="")
