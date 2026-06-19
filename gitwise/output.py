"""Output: Rich-powered human-readable + plain JSON. Detects bat/delta."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

from ._runtime_config import get_runtime_config
from .design import ColorDepth, pad_right, truncate, visible_length
from .i18n import confirm_responses, t

_COLOR_SYSTEM_MAP: dict[ColorDepth, str] = {
    "truecolor": "truecolor",
    "256color": "256",
    "16color": "16",
}

_LOG_JSON = os.environ.get("GITWISE_LOG_JSON", "").lower() in ("1", "true")
_JSON_PRETTY = os.environ.get("GITWISE_JSON_PRETTY", "").lower() in ("1", "true")
_JSON_MODE = False


def _structured_log(level: str, msg: str, **kwargs: Any) -> None:
    """Write a JSON log entry to stderr."""
    entry: dict[str, Any] = {
        "ts": time.time(),
        "level": level,
        "msg": msg,
    }
    if kwargs:
        entry.update(kwargs)
    sys.stderr.write(json.dumps(entry, default=str) + "\n")


def set_json_pretty(pretty: bool) -> None:
    """Toggle pretty-printed JSON output."""
    global _JSON_PRETTY
    _JSON_PRETTY = pretty


def set_json_mode(enabled: bool) -> None:
    """Toggle JSON-only output mode (suppresses Rich rendering)."""
    global _JSON_MODE
    _JSON_MODE = enabled


class _ModuleAttr:
    """Lazy boolean accessor for a RuntimeConfig attribute."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        """Store the attribute name to look up at access time."""
        self._name = name

    def __bool__(self) -> bool:
        """Resolve the RuntimeConfig attribute and return its truth value."""
        return bool(getattr(get_runtime_config(), self._name))

    def __repr__(self) -> str:
        """Return ``repr(True)`` or ``repr(False)`` for the attribute."""
        return repr(bool(self))


HAS_BAT = _ModuleAttr("has_bat")
HAS_DELTA = _ModuleAttr("has_delta")
IS_TTY = _ModuleAttr("is_tty")


def _build_rich_theme() -> dict[str, str]:
    """Map ThemeTokens to a Rich theme dict (style-name -> color)."""
    tokens = get_runtime_config().theme_tokens
    return {
        "fg": tokens.fg,
        "secondary": tokens.secondary,
        "dim": tokens.dim or tokens.secondary,
        "accent": tokens.accent,
        "success": tokens.success,
        "error": tokens.error,
        "warning": tokens.warning or tokens.accent,
        "brand": tokens.brand or tokens.accent,
        "bold": f"bold {tokens.fg}",
        "header": f"bold {tokens.fg}",
        "rule": tokens.dim or tokens.secondary,
        "bold.accent": f"bold {tokens.accent}",
    }


def _color_disabled() -> bool:
    """Return True when NO_COLOR or GITWISE_NO_COLOR is set."""
    return os.environ.get("NO_COLOR", "") != "" or os.environ.get(
        "GITWISE_NO_COLOR", ""
    ).lower() in ("1", "true")


def _color_forced() -> bool:
    """Return True when CLICOLOR_FORCE or FORCE_COLOR is set."""
    return (
        os.environ.get("CLICOLOR_FORCE", "").lower()
        in (
            "1",
            "true",
        )
        or os.environ.get("FORCE_COLOR", "") != ""
    )


def _use_rich() -> bool:
    """Decide whether Rich rendering should be used for the current output."""
    if not _HAS_RICH:
        return False
    if _color_disabled():
        return False
    if _color_forced():
        return True
    return get_runtime_config().is_tty


_use_rich_cached: bool | None = None


def _should_use_rich() -> bool:
    """Return the cached Rich-usage decision."""
    global _use_rich_cached
    if _use_rich_cached is None:
        _use_rich_cached = _use_rich()
    return _use_rich_cached


def _make_console(*, file: Any = sys.stdout, force: bool = False) -> Console:
    """Create and return a Rich Console configured with the current theme."""
    cfg = get_runtime_config()
    depth = cfg.color_depth
    console = Console(
        theme=Theme(_build_rich_theme()),
        color_system=_COLOR_SYSTEM_MAP.get(depth, "auto"),  # pyright: ignore[reportArgumentType]
        no_color=None,
        force_terminal=force,
        width=cfg.terminal_width,
        legacy_windows=False,
        highlight=False,
        emoji=False,
        markup=False,
        file=file,
    )
    if cfg.debug:
        sys.stderr.write(
            f"[gitwise debug] console: force_terminal={force}, "
            f"color_system={console.color_system}, "
            f"is_terminal={console.is_terminal}, "
            f"no_color={console.no_color}, "
            f"theme={cfg.theme}, depth={depth}, "
            f"is_tty={cfg.is_tty}\n"
        )
    return console


_console: Console | None = None
_stderr_console: Console | None = None


def _get_console() -> Console:
    """Return the lazily-created stdout Console singleton."""
    global _console
    if _console is None:
        _console = _make_console(force=True)
    return _console


def _get_stderr_console() -> Console:
    """Return the lazily-created stderr Console singleton."""
    global _stderr_console
    if _stderr_console is None:
        _stderr_console = _make_console(file=sys.stderr, force=True)
    return _stderr_console


def info(msg: str) -> None:
    """Print a dim informational message to stdout."""
    if _should_use_rich():
        _get_console().print(Text(msg, style="dim"))
    else:
        print(msg)


def warn(msg: str) -> None:
    """Print a warning to stderr (JSON-logged when GITWISE_LOG_JSON is set)."""
    if _LOG_JSON:
        _structured_log("warn", msg)
        return
    prefix = t("warning_label")
    if _should_use_rich():
        text = Text()
        text.append(f"{prefix}: ", style="warning")
        text.append(msg)
        _get_stderr_console().print(text)
    else:
        print(f"{prefix}: {msg}", file=sys.stderr)


def error(msg: str, *, hint: str | None = None) -> None:
    """Print an error to stderr with an optional hint line."""
    if _LOG_JSON:
        if hint:
            _structured_log("error", msg, hint=hint)
        else:
            _structured_log("error", msg)
        return
    prefix = t("error")
    if _should_use_rich():
        text = Text()
        text.append(f"{prefix}: ", style="error")
        text.append(msg)
        _get_stderr_console().print(text)
        if hint:
            hint_text = Text()
            hint_text.append(f"{t('hint_prefix')}: ", style="dim")
            hint_text.append(hint, style="dim")
            _get_stderr_console().print(hint_text)
    else:
        print(f"{prefix}: {msg}", file=sys.stderr)
        if hint:
            print(f"{t('hint_prefix')}: {hint}", file=sys.stderr)


def ok(msg: str) -> None:
    """Print a success-prefixed message to stdout."""
    prefix = t("ok_prefix")
    if _should_use_rich():
        text = Text()
        text.append(f"{prefix} ", style="success")
        text.append(msg)
        _get_console().print(text)
    else:
        print(f"{prefix} {msg}")


def debug(msg: str) -> None:
    """Print a debug message to stderr when GITWISE_DEBUG is enabled."""
    if not get_runtime_config().debug:
        return
    if _should_use_rich():
        text = Text()
        text.append("[gitwise debug] ", style="dim")
        text.append(msg)
        _get_stderr_console().print(text)
    else:
        print(f"[gitwise debug] {msg}", file=sys.stderr)


def print_json(data: Any) -> None:
    """Print data as JSON, compact or pretty depending on the current setting."""
    if _JSON_PRETTY:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def print_blank() -> None:
    """Print an empty line to stdout."""
    if _should_use_rich():
        _get_console().print()
    else:
        print()


def confirm(prompt: str) -> bool:
    """Ask the user a yes/no prompt; returns False when stdin is not a TTY."""
    if not sys.stdin.isatty():
        return False

    if _should_use_rich():
        try:
            import importlib

            prompt_mod = importlib.import_module("rich.prompt")
            resp = prompt_mod.Prompt.ask(
                prompt,
                default="",
                show_default=False,
                show_choices=False,
                console=_get_console(),
            )
            return resp.strip().lower() in confirm_responses()
        except (EOFError, KeyboardInterrupt):
            return False

    try:
        resp = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return resp in confirm_responses()


@contextmanager
def status(message: str) -> Iterator[None]:
    """Show a Rich spinner (or plain text in debug/fallback mode)."""
    if _JSON_MODE:
        yield
        return

    if _should_use_rich():
        with _get_console().status(message):
            yield
        return

    if get_runtime_config().debug:
        print_dim(message)
    yield


def bat_pipe(text: str, language: str = "plain") -> None:
    """Pipe text through bat for syntax highlighting; falls back to plain print."""
    if not text:
        return
    if not text.endswith("\n"):
        text += "\n"
    if language is None or language == "plain":
        for line in text.splitlines():
            print(line)
        return
    cfg = get_runtime_config()
    if cfg.has_bat and cfg.is_tty:
        color_flag = "always" if not _color_disabled() else "never"
        cmd = [
            "bat",
            "--style=plain",
            "--pager=never",
            f"--color={color_flag}",
            "--language",
            language,
        ]
        try:
            r = subprocess.run(
                cmd, input=text, text=True, check=False, stderr=subprocess.DEVNULL, timeout=120
            )
            if r.returncode == 0:
                return
        except OSError as e:
            if get_runtime_config().debug:
                sys.stderr.write(f"[gitwise debug] bat execution failed: {e}\n")
    print(text, end="")


def print_header(text: str) -> None:
    """Print text in bold (or plain when Rich is disabled)."""
    if _should_use_rich():
        _get_console().print(text, style="bold")
    else:
        print(text)


def print_section(title: str) -> None:
    """Print a horizontal-rule section header."""
    if _should_use_rich():
        print_blank()
        _get_console().rule(f" {title} ", style="accent")
    else:
        print_blank()
        print(f"  {title}")


def print_bullet(text: str, *, icon: str = "•", accent: bool = False, indent: int = 2) -> None:
    """Print an indented bullet-point item."""
    prefix = " " * max(0, indent)
    if _should_use_rich():
        row = Text()
        row.append(prefix)
        row.append(icon, style="accent" if accent else "secondary")
        row.append(" ")
        row.append(text)
        _get_console().print(row)
    else:
        print(f"{prefix}{icon} {text}")


def _commit_type_style(message: str) -> str:
    """Return the Rich style name for a commit message based on its conventional type."""
    msg = message.strip().lower()
    match = re.match(r"^([a-z]+)(\([^)]*\))?(!)?:", msg)
    if not match:
        if msg.startswith("merge "):
            return "dim"
        return "fg"
    commit_type = match.group(1)
    if commit_type == "feat":
        return "success"
    if commit_type == "fix":
        return "warning"
    if commit_type in {"docs", "style", "test", "ci", "build"}:
        return "accent"
    if commit_type in {"refactor", "perf"}:
        return "brand"
    if commit_type in {"revert"}:
        return "error"
    return "fg"


def print_commit_line(line: str, *, indent: int = 2) -> None:
    """Print a single log line with hash and color-coded commit type."""
    prefix = " " * max(0, indent)
    parts = line.strip().split(" ", 1)
    if len(parts) != 2:
        print_bullet(line.strip(), icon="-", accent=False, indent=indent)
        return
    short_hash, subject = parts[0], parts[1]
    if not re.fullmatch(r"[0-9a-f]{7,40}", short_hash):
        print_bullet(line.strip(), icon="-", accent=False, indent=indent)
        return

    if _should_use_rich():
        text = Text()
        text.append(prefix)
        text.append(short_hash, style="secondary")
        text.append("  ", style="dim")
        text.append(subject, style=_commit_type_style(subject))
        _get_console().print(text)
        return

    print(f"{prefix}- {short_hash} {subject}")


def _status_style(code: str) -> str:
    """Return the Rich style for a git status code character."""
    normalized = code.strip().upper()
    if normalized in {"??", "A", "M", "R", "C", "T", "U", "D"}:
        if normalized in {"D", "U"}:
            return "error"
        if normalized in {"M", "R", "C", "T"}:
            return "warning"
        return "success"
    return "secondary"


def _path_style_for_status(code: str) -> str:
    """Return the Rich style for the file path next to a git status code."""
    normalized = code.strip().upper()
    if normalized in {"??", "A"}:
        return "success"
    if normalized in {"D", "U"}:
        return "error"
    if normalized in {"M", "R", "C", "T"}:
        return "warning"
    return "fg"


def print_file_status(code: str, path: str, *, indent: int = 2) -> None:
    """Print a color-coded git status code and file path."""
    status = code.strip() or "--"
    prefix = " " * max(0, indent)
    if _should_use_rich():
        text = Text()
        text.append(prefix)
        text.append(status.rjust(2), style=_status_style(status))
        text.append("  ", style="dim")
        text.append(path, style=_path_style_for_status(status))
        _get_console().print(text)
    else:
        print(f"{prefix}{status.rjust(2)}  {path}")


def _append_diffstat_changes(text: Text, changes: str) -> None:
    """Append + and - characters with color to a Rich Text object."""
    for char in changes:
        if char == "+":
            text.append(char, style="success")
        elif char == "-":
            text.append(char, style="error")
        else:
            text.append(char, style="secondary")


def print_diffstat(title: str, entries: list[dict[str, str]]) -> None:
    """Print a diffstat-style summary of changed files."""
    if not entries:
        return
    if _should_use_rich():
        print_header(title)
        width = get_runtime_config().terminal_width
        path_col = max(24, min(width // 2, max(visible_length(e["path"]) for e in entries)))
        for entry in entries:
            path = truncate(entry["path"], path_col)
            padded_path = pad_right(path, path_col)
            status = entry.get("status", "M")
            changes = entry.get("changes", "")
            row = Text()
            row.append("  ")
            row.append(padded_path, style=_path_style_for_status(status))
            row.append("  ", style="dim")
            _append_diffstat_changes(row, changes)
            _get_console().print(row)
        return

    print(title)
    for entry in entries:
        print(f"  {entry['path']}  {entry.get('changes', '')}")


def print_summary_box(title: str, lines: list[str]) -> None:
    """Print a titled summary box with indented lines."""
    if not lines:
        return
    if _should_use_rich():
        _get_console().rule(f" {title} ", style="dim")
        for line in lines:
            row = Text()
            row.append("  ", style="dim")
            row.append(line)
            _get_console().print(row)
        return
    print(title)
    for line in lines:
        print(f"  {line}")


def print_bracket(label: str, value: str = "") -> None:
    """Print a [label] bracketed item with an optional value."""
    if _should_use_rich():
        text = Text()
        text.append("  [", style="secondary")
        text.append(label, style="accent")
        text.append("]", style="secondary")
        if value:
            text.append(f" {value}")
        _get_console().print(text)
    else:
        if value:
            print(f"  [{label}] {value}")
        else:
            print(f"  [{label}]")


def print_accent(text: str) -> None:
    """Print text in the accent color."""
    if _should_use_rich():
        _get_console().print(text, style="accent")
    else:
        print(text)


def print_dim(text: str) -> None:
    """Print text in the dim color."""
    if _should_use_rich():
        _get_console().print(text, style="dim")
    else:
        print(text)


def print_success(text: str) -> None:
    """Print text in the success color."""
    if _should_use_rich():
        _get_console().print(text, style="success")
    else:
        print(text)


def print_error_styled(text: str) -> None:
    """Print text in the error color."""
    if _should_use_rich():
        _get_console().print(text, style="error")
    else:
        print(text)


def print_kv(key: str, value: str) -> None:
    """Print a key-value pair with aligned columns."""
    width = get_runtime_config().terminal_width
    key_col = min(24, width // 3)
    padded_key = pad_right(f"  {key}", key_col)
    if _should_use_rich():
        text = Text()
        text.append(padded_key, style="secondary")
        text.append(f" {value}")
        _get_console().print(text)
    else:
        print(f"{padded_key} {value}")


def print_status_line(icon: str, label: str, status: str, ok_flag: bool = True) -> None:
    """Print a status row with icon, label, dotted filler, and status value."""
    if _should_use_rich():
        console = _get_console()
        width = get_runtime_config().terminal_width
        icon_style = "success" if ok_flag else "error"
        text = Text()
        text.append(f"  {icon} ", style=icon_style)
        text.append(label, style="secondary")
        used = visible_length(f"  {icon} {label}") + visible_length(status) + 3
        dots = max(1, width - used)
        text.append(" " + "." * dots + " ", style="dim")
        text.append(status, style=icon_style)
        console.print(text)
    else:
        width = get_runtime_config().terminal_width
        base = f"  {icon} {label}"
        if not status:
            print(base)
            return
        used = visible_length(base) + visible_length(status) + 2
        dots = max(1, width - used)
        print(f"{base} {'·' * dots} {status}")


def print_table(
    title: str,
    columns: list[tuple[str, str]],
    rows: list[list[str]],
    *,
    column_styles: list[str] | None = None,
    highlight_rows: set[int] | None = None,
    no_wrap_columns: set[int] | None = None,
    min_widths: dict[int, int] | None = None,
    max_widths: dict[int, int] | None = None,
    overflow_columns: dict[int, Literal["fold", "crop", "ellipsis"]] | None = None,
    column_ratios: dict[int, int] | None = None,
) -> None:
    """Print a styled table with optional column widths, overflow, and row highlights."""
    if not _should_use_rich() or not rows:
        if title:
            print(title)
        if not rows:
            return
        num_cols = len(columns)
        col_widths = [len(c[0]) for c in columns]
        for row in rows:
            for i, cell in enumerate(row):
                if i < num_cols:
                    col_widths[i] = max(col_widths[i], visible_length(cell))
        headers = [columns[i][0] for i in range(num_cols)]
        header_row = "  ".join(pad_right(headers[i], col_widths[i]) for i in range(num_cols))
        sep_row = "  ".join("-" * col_widths[i] for i in range(num_cols))
        print(f"   {header_row}")
        print(f"   {sep_row}")
        highlights = highlight_rows or set()
        for idx, row in enumerate(rows):
            prefix = " * " if idx in highlights else "   "
            padded = "  ".join(
                pad_right(row[i], col_widths[i]) if i < num_cols else row[i]
                for i in range(len(row))
            )
            print(f"{prefix}{padded}")
        return

    console = _get_console()
    table = Table(
        title=title,
        title_style="bold",
        border_style="dim",
        show_header=True,
        header_style="bold.accent",
        pad_edge=False,
        padding=(0, 1),
        expand=True,
    )

    no_wrap = no_wrap_columns or set()
    mins = min_widths or {}
    maxs = max_widths or {}
    overflows = overflow_columns or {}
    ratios = column_ratios or {}

    for idx, (col_name, _col_key) in enumerate(columns):
        no_wrap_value = (idx in no_wrap) if no_wrap_columns is not None else True
        overflow_value: Literal["fold", "crop", "ellipsis"] = overflows.get(idx, "ellipsis")
        table.add_column(
            col_name,
            no_wrap=no_wrap_value,
            min_width=mins.get(idx),
            max_width=maxs.get(idx),
            overflow=overflow_value,
            ratio=ratios.get(idx),
        )

    styles = column_styles or []
    highlights = highlight_rows or set()

    for idx, row_data in enumerate(rows):
        if idx in highlights:
            table.add_row(*row_data, style="accent")
        else:
            row_style = styles[idx % len(styles)] if styles else ""
            table.add_row(*row_data, style=row_style)

    console.print(table)
