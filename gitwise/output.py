"""Dual output: human-readable (colored, localized) + JSON (structured). Detects bat/delta/rg."""

import json
import os
import shutil
import sys
from typing import Any

from .i18n import confirm_responses, t

HAS_BAT = bool(shutil.which("bat"))
HAS_DELTA = bool(shutil.which("delta"))


def _should_color() -> bool:
    if os.environ.get("CLICOLOR_FORCE", "").lower() in ("1", "true"):
        return True
    if os.environ.get("NO_COLOR", "") != "":
        return False
    if os.environ.get("GITWISE_NO_COLOR", "").lower() in ("1", "true"):
        return False
    if os.environ.get("CLICOLOR", "1") not in ("1", "true"):
        return False
    return sys.stdout.isatty()


def _detect_theme() -> str:
    colorfgbg = os.environ.get("COLORFGBG", "")
    if colorfgbg:
        parts = colorfgbg.split(";")
        if len(parts) == 2:
            bg = parts[1]
            if bg in ("0", "8", "16"):
                return "dark"
            return "light"
    return "dark"


_THEME = _detect_theme()
_USE_COLOR = _should_color()
IS_TTY = sys.stdout.isatty()
DEBUG = os.environ.get("GITWISE_DEBUG", "").lower() in ("1", "true")

_COLORS_DARK = {
    "success": "\033[0;32m",
    "warning": "\033[0;33m",
    "error": "\033[0;31m",
    "info": "\033[0;36m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

_COLORS_LIGHT = {
    "success": "\033[0;32m",
    "warning": "\033[0;35m",
    "error": "\033[0;31m",
    "info": "\033[0;34m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

_C = _COLORS_DARK if _THEME == "dark" else _COLORS_LIGHT


def _color(name: str) -> str:
    if _USE_COLOR:
        return _C.get(name, "")
    return ""


def info(msg: str) -> None:
    print(msg)


def warn(msg: str) -> None:
    prefix = t("advertencia")
    colored_prefix = f"{_color('warning')}{prefix}:{_color('reset')}"
    print(f"{colored_prefix} {msg}", file=sys.stderr)


def error(msg: str) -> None:
    prefix = t("error")
    colored_prefix = f"{_color('error')}{prefix}:{_color('reset')}"
    print(f"{colored_prefix} {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    prefix = t("ok_prefix")
    colored_prefix = f"{_color('success')}{prefix}{_color('reset')}"
    print(f"{colored_prefix} {msg}")


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
    return resp in confirm_responses()


def bat_pipe(text: str, language: str = "plain") -> None:
    if not text:
        return
    if not text.endswith("\n"):
        text += "\n"
    if HAS_BAT and IS_TTY:
        import subprocess

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
