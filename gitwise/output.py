"""Dual output: human-readable (colored, localized) + JSON (structured). Detects bat/delta/rg."""

import json
import subprocess
import sys
from typing import Any

from ._runtime_config import get_runtime_config
from .i18n import confirm_responses, t

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


class _ModuleAttr:
    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __bool__(self) -> bool:
        return bool(getattr(get_runtime_config(), self._name))

    def __repr__(self) -> str:
        return repr(bool(self))


HAS_BAT = _ModuleAttr("has_bat")
HAS_DELTA = _ModuleAttr("has_delta")
IS_TTY = _ModuleAttr("is_tty")


def _color(name: str) -> str:
    cfg = get_runtime_config()
    if not cfg.use_color:
        return ""
    colors = _COLORS_DARK if cfg.theme == "dark" else _COLORS_LIGHT
    return colors.get(name, "")


def info(msg: str) -> None:
    print(msg)


def warn(msg: str) -> None:
    prefix = t("warning_label")
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
    if get_runtime_config().debug:
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
    cfg = get_runtime_config()
    if cfg.has_bat and cfg.is_tty:
        color_flag = "always" if cfg.use_color else "never"
        cmd = ["bat", "--style=plain", "--pager=never", f"--color={color_flag}"]
        if language and language != "plain":
            cmd += ["--language", language]
        try:
            r = subprocess.run(
                cmd, input=text, text=True, check=False, stderr=subprocess.DEVNULL, timeout=120
            )
            if r.returncode == 0:
                return
        except OSError:
            pass
    print(text, end="")
