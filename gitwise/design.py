"""Design system tokens and utilities for gitwise CLI output.

Defines the visual identity: dual themes (Light/Dark), Gitwise Orange accent,
WCAG AA compliant colors, and text layout utilities.

Rich library handles all rendering. This module provides color definitions,
text utilities, and the argparse help formatter only.
"""

import argparse
import os
import re
import shutil
import unicodedata
from collections.abc import Callable
from typing import Literal

from .i18n import t

ColorDepth = Literal["truecolor", "256color", "16color"]

DARK_FG = "#CDD6F4"
DARK_BG = "#1E1E2E"
DARK_SECONDARY = "#9399B2"
DARK_MUTED = "#8B8FA8"
DARK_DIM = "#A6ADC8"
DARK_ACCENT = "#E69138"
DARK_SUCCESS = "#A6E3A1"
DARK_ERROR = "#F38BA8"
DARK_WARNING = "#F9E2AF"
DARK_BRAND = "#89B4FA"

LIGHT_FG = "#1A1A1A"
LIGHT_BG = "#F8F6F1"
LIGHT_SECONDARY = "#585B70"
LIGHT_MUTED = "#6C7086"
LIGHT_DIM = "#64646E"
LIGHT_ACCENT = "#C45200"
LIGHT_SUCCESS = "#2E7D32"
LIGHT_ERROR = "#C62828"
LIGHT_WARNING = "#BF360C"
LIGHT_BRAND = "#1565C0"

ACCENT_HEX = "#E69138"

MIN_WIDTH = 80
DEFAULT_WIDTH = 100
MAX_WIDTH = 120
BRACKET_LEFT = "["
BRACKET_RIGHT = "]"
SEPARATOR = "  "

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"


def hex_to_ansi_fg(hex_color: str) -> str:
    """Convert a hex color string to a 24-bit ANSI foreground escape code."""
    h = hex_color.lstrip("#")
    if len(h) < 6:
        return ""
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"


class ThemeTokens:
    """Named collection of hex color tokens for a single theme."""

    __slots__ = (
        "accent",
        "bg",
        "brand",
        "dim",
        "error",
        "fg",
        "secondary",
        "success",
        "warning",
    )

    def __init__(
        self,
        fg: str,
        bg: str,
        secondary: str,
        accent: str,
        success: str,
        error: str,
        warning: str = "",
        brand: str = "",
        dim: str = "",
    ) -> None:
        """Initialize all theme token slots."""
        self.fg = fg
        self.bg = bg
        self.secondary = secondary
        self.accent = accent
        self.success = success
        self.error = error
        self.warning = warning
        self.brand = brand
        self.dim = dim


_DARK_THEME = ThemeTokens(
    fg=DARK_FG,
    bg=DARK_BG,
    secondary=DARK_SECONDARY,
    accent=DARK_ACCENT,
    success=DARK_SUCCESS,
    error=DARK_ERROR,
    warning=DARK_WARNING,
    brand=DARK_BRAND,
    dim=DARK_DIM,
)

_LIGHT_THEME = ThemeTokens(
    fg=LIGHT_FG,
    bg=LIGHT_BG,
    secondary=LIGHT_SECONDARY,
    accent=LIGHT_ACCENT,
    success=LIGHT_SUCCESS,
    error=LIGHT_ERROR,
    warning=LIGHT_WARNING,
    brand=LIGHT_BRAND,
    dim=LIGHT_DIM,
)

_THEMES: dict[str, ThemeTokens] = {"dark": _DARK_THEME, "light": _LIGHT_THEME}


def detect_color_depth() -> ColorDepth:
    """Detect terminal color depth from COLORTERM, TERM, and NO_COLOR env vars."""
    if os.environ.get("NO_COLOR", "") != "" or os.environ.get("GITWISE_NO_COLOR", "").lower() in (
        "1",
        "true",
    ):
        return "16color"
    if (
        os.environ.get("CLICOLOR_FORCE", "").lower() in ("1", "true")
        or os.environ.get("FORCE_COLOR", "") != ""
    ):
        colorterm = os.environ.get("COLORTERM", "").lower()
        if colorterm.startswith(("truecolor", "24bit")):
            return "truecolor"
        return "256color"
    colorterm = os.environ.get("COLORTERM", "").lower()
    if colorterm.startswith(("truecolor", "24bit")):
        return "truecolor"
    term = os.environ.get("TERM", "").lower()
    if "256color" in term or "xterm-256color" in term:
        return "256color"
    return "16color"


def detect_terminal_width() -> int:
    """Return the terminal width clamped between MIN_WIDTH and MAX_WIDTH."""
    width = shutil.get_terminal_size(fallback=(DEFAULT_WIDTH, 24)).columns
    return max(MIN_WIDTH, min(width, MAX_WIDTH))


def build_theme(theme: str) -> ThemeTokens:
    """Return ThemeTokens for the given theme name, defaulting to dark."""
    return _THEMES.get(theme, _DARK_THEME)


def truncate(text: str, width: int, ellipsis: str = "...") -> str:
    """Truncate text to fit within width using visible-length-aware counting."""
    vl = visible_length(text)
    if vl <= width:
        return text
    available = width - visible_length(ellipsis)
    if available <= 0:
        return ellipsis[:width]
    stripped = strip_ansi(text)
    res: list[str] = []
    curr_w = 0
    for c in stripped:
        w = 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
        if curr_w + w > available:
            break
        res.append(c)
        curr_w += w
    return "".join(res) + ellipsis


def pad_right(text: str, width: int) -> str:
    """Right-pad text with spaces up to the given visible width."""
    vl = visible_length(text)
    if vl >= width:
        return text
    return text + " " * (width - vl)


def pad_left(text: str, width: int) -> str:
    """Left-pad text with spaces up to the given visible width."""
    vl = visible_length(text)
    if vl >= width:
        return text
    return " " * (width - vl) + text


_CSI_FINAL_BYTES = frozenset(chr(c) for c in range(0x40, 0x7F))


def strip_ansi(text: str) -> str:
    """Remove CSI escape sequences from text."""
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\033" and i + 1 < len(text) and text[i + 1] == "[":
            j = i + 2
            while j < len(text) and text[j] not in _CSI_FINAL_BYTES:
                j += 1
            i = j + 1
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def visible_length(text: str) -> int:
    """Return the display width of text, accounting for ANSI escapes and wide chars."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in strip_ansi(text))


class GitwiseHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Argparse help formatter with raw ANSI color injection."""

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
    ) -> None:
        """Initialize with gitwise default indent and help-position settings."""
        super().__init__(
            prog,
            indent_increment=indent_increment,
            max_help_position=max_help_position,
            width=width,
        )

    def _format_action(self, action: argparse.Action) -> str:
        """Format a single action with colorized option flags."""
        parts = super()._format_action(action)
        tokens = _get_tokens_for_help()
        if tokens is None:
            return parts
        return _colorize_help_line(parts, tokens)

    def start_section(self, heading: str | None) -> None:
        """Begin a help section with an optional bold colored heading."""
        if heading:
            tokens = _get_tokens_for_help()
            if tokens:
                heading = f"{ANSI_BOLD}{hex_to_ansi_fg(tokens.accent)}{heading}{ANSI_RESET}"
        super().start_section(heading)


def _get_tokens_for_help() -> ThemeTokens | None:
    """Return theme tokens if color is allowed for help output, else None."""
    try:
        if os.environ.get("NO_COLOR", "") != "":
            return None
        if os.environ.get("GITWISE_NO_COLOR", "").lower() in ("1", "true"):
            return None
        import sys

        if not sys.stdout.isatty():
            return None
        theme = os.environ.get("GITWISE_THEME", "auto")
        if theme == "auto":
            theme = "dark"
        return build_theme(theme)
    except (OSError, KeyError, ValueError):
        return None


_OPT_RE = re.compile(r"^(\s*)(-{1,2}[\w.\-]+(?:,\s*-{1,2}[\w.\-]+)*)")


def _colorize_help_line(line: str, tokens: ThemeTokens) -> str:
    """Colorize option flags in a help line using the accent color."""
    m = _OPT_RE.match(line)
    if not m:
        return line
    indent, opts = m.group(1), m.group(2)
    rest = line[m.end() :]
    return f"{indent}{hex_to_ansi_fg(tokens.accent)}{opts}{ANSI_RESET}{rest}"


class GitwiseRichHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Rich-argparse bridge that preserves gitwise theme and no-color behavior."""

    _FORMATTER: type[argparse.RawDescriptionHelpFormatter] | None = None
    _DEFAULT_GROUP_NAME_FORMATTER: Callable[[str], object] | None = None
    _NO_COLOR_ENV_KEY: tuple[str, str] | None = None
    _NO_COLOR_ENABLED = False
    _THEME_ENV_VALUE: str | None = None
    _THEME_NAME = "dark"

    def __new__(
        cls,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
    ) -> argparse.RawDescriptionHelpFormatter:
        """Factory that returns a plain or Rich formatter depending on color support."""
        if cls._no_color_enabled():
            return GitwiseHelpFormatter(
                prog,
                indent_increment=indent_increment,
                max_help_position=max_help_position,
                width=width,
            )

        formatter_cls = cls._formatter_cls()
        help_formatter = formatter_cls(
            prog,
            indent_increment=indent_increment,
            max_help_position=max_help_position,
            width=width,
        )
        cls._apply_theme(help_formatter)
        return help_formatter

    @classmethod
    def _formatter_cls(cls) -> type[argparse.RawDescriptionHelpFormatter]:
        """Lazily resolve the rich_argparse formatter class."""
        formatter = cls._FORMATTER
        if formatter is not None:
            return formatter

        import importlib

        try:
            rich_argparse = importlib.import_module("rich_argparse")
        except ModuleNotFoundError:
            return GitwiseHelpFormatter
        formatter = rich_argparse.RawDescriptionRichHelpFormatter
        cls._FORMATTER = formatter
        return formatter

    @classmethod
    def _no_color_enabled(cls) -> bool:
        """Check if NO_COLOR or GITWISE_NO_COLOR is set, with caching."""
        env_key = (os.environ.get("NO_COLOR", ""), os.environ.get("GITWISE_NO_COLOR", "").lower())
        if env_key != cls._NO_COLOR_ENV_KEY:
            cls._NO_COLOR_ENV_KEY = env_key
            cls._NO_COLOR_ENABLED = env_key[0] != "" or env_key[1] in ("1", "true")
        return cls._NO_COLOR_ENABLED

    @classmethod
    def _theme_name(cls) -> str:
        """Return the resolved theme name from GITWISE_THEME, defaulting to dark."""
        env_theme = os.environ.get("GITWISE_THEME", "").lower()
        if env_theme != cls._THEME_ENV_VALUE:
            cls._THEME_ENV_VALUE = env_theme
            cls._THEME_NAME = env_theme if env_theme in {"dark", "light"} else "dark"
        return cls._THEME_NAME

    @classmethod
    def _install_group_name_localization(
        cls, formatter_cls: type[argparse.RawDescriptionHelpFormatter]
    ) -> None:
        """Patch the formatter's group_name_formatter to use i18n for standard groups."""
        if cls._DEFAULT_GROUP_NAME_FORMATTER is not None:
            return

        formatter_obj = getattr(formatter_cls, "group_name_formatter", str.title)
        if not callable(formatter_obj):
            return

        default_group_formatter: Callable[[str], object] = formatter_obj
        cls._DEFAULT_GROUP_NAME_FORMATTER = default_group_formatter

        def localized_group_formatter(name: object) -> str:
            """Return a localized group name for known standard groups."""
            normalized = str(name).lower().replace(" ", "_")
            if normalized in {"options", "positional_arguments"}:
                return t(f"help_group_{normalized}")
            return str(default_group_formatter(str(name)))

        setattr(formatter_cls, "group_name_formatter", localized_group_formatter)  # noqa: B010

    @classmethod
    def _apply_theme(cls, help_formatter: argparse.RawDescriptionHelpFormatter) -> None:
        """Apply gitwise theme styles and group-name localization to a formatter."""
        theme_tokens = build_theme(cls._theme_name())

        styles = getattr(help_formatter, "styles", None)
        if isinstance(styles, dict):
            styles.update(
                {
                    "argparse.args": theme_tokens.accent,
                    "argparse.groups": theme_tokens.brand,
                    "argparse.metavar": theme_tokens.secondary,
                    "argparse.prog": theme_tokens.dim,
                    "argparse.help": theme_tokens.fg,
                    "argparse.text": theme_tokens.fg,
                    "argparse.syntax": f"bold {theme_tokens.accent}",
                    "argparse.default": f"italic {theme_tokens.secondary}",
                }
            )

        cls._install_group_name_localization(type(help_formatter))
