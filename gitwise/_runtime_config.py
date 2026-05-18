"""Runtime configuration: immutable settings detected from environment at import time."""

import os
import shutil
import sys


class RuntimeConfig:
    __slots__ = (
        "debug",
        "has_bat",
        "has_delta",
        "is_tty",
        "theme",
        "use_color",
    )

    def __init__(self) -> None:
        self.has_bat = bool(shutil.which("bat"))
        self.has_delta = bool(shutil.which("delta"))
        self.theme = self._detect_theme()
        self.use_color = self._should_color()
        self.is_tty = sys.stdout.isatty()
        self.debug = os.environ.get("GITWISE_DEBUG", "").lower() in ("1", "true")

    @staticmethod
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

    @staticmethod
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


_runtime_config: RuntimeConfig | None = None


def get_runtime_config() -> RuntimeConfig:
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = RuntimeConfig()
    return _runtime_config


def reset_runtime_config() -> None:
    global _runtime_config
    _runtime_config = None
