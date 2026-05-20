"""Output: Rich-powered human-readable + plain JSON. Detects bat/delta."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

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
from .design import ColorDepth, pad_right, visible_length
from .i18n import confirm_responses, t

_COLOR_SYSTEM_MAP: dict[ColorDepth, str] = {
    "truecolor": "truecolor",
    "256color": "256",
    "16color": "16",
}

_LOG_JSON = os.environ.get("GITWISE_LOG_JSON", "").lower() in ("1", "true")


def _structured_log(level: str, msg: str, **kwargs: Any) -> None:
    entry: dict[str, Any] = {
        "ts": time.time(),
        "level": level,
        "msg": msg,
    }
    if kwargs:
        entry.update(kwargs)
    sys.stderr.write(json.dumps(entry, default=str) + "\n")


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


def _build_rich_theme() -> dict[str, str]:
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
    return os.environ.get("NO_COLOR", "") != "" or os.environ.get(
        "GITWISE_NO_COLOR", ""
    ).lower() in ("1", "true")


def _color_forced() -> bool:
    return (
        os.environ.get("CLICOLOR_FORCE", "").lower()
        in (
            "1",
            "true",
        )
        or os.environ.get("FORCE_COLOR", "") != ""
    )


def _use_rich() -> bool:
    if not _HAS_RICH:
        return False
    if _color_disabled():
        return False
    if _color_forced():
        return True
    return get_runtime_config().is_tty


_use_rich_cached: bool | None = None


def _should_use_rich() -> bool:
    global _use_rich_cached
    if _use_rich_cached is None:
        _use_rich_cached = _use_rich()
    return _use_rich_cached


def _make_console(*, file: Any = sys.stdout, force: bool = False) -> Console:
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
        import sys as _sys

        _sys.stderr.write(
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
    global _console
    if _console is None:
        _console = _make_console(force=True)
    return _console


def _get_stderr_console() -> Console:
    global _stderr_console
    if _stderr_console is None:
        _stderr_console = _make_console(file=sys.stderr, force=True)
    return _stderr_console


def info(msg: str) -> None:
    if _should_use_rich():
        _get_console().print(Text(msg, style="dim"))
    else:
        print(msg)


def warn(msg: str) -> None:
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


def error(msg: str) -> None:
    if _LOG_JSON:
        _structured_log("error", msg)
        return
    prefix = t("error")
    if _should_use_rich():
        text = Text()
        text.append(f"{prefix}: ", style="error")
        text.append(msg)
        _get_stderr_console().print(text)
    else:
        print(f"{prefix}: {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    prefix = t("ok_prefix")
    if _should_use_rich():
        text = Text()
        text.append(f"{prefix} ", style="success")
        text.append(msg)
        _get_console().print(text)
    else:
        print(f"{prefix} {msg}")


def debug(msg: str) -> None:
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
        except OSError:
            pass
    print(text, end="")


def print_header(text: str) -> None:
    if _should_use_rich():
        _get_console().print(text, style="bold")
    else:
        print(text)


def print_section(title: str) -> None:
    if _should_use_rich():
        _get_console().print()
        _get_console().rule(f" {title} ", style="accent")
    else:
        print()
        print(f"  {title}")


def print_bracket(label: str, value: str = "") -> None:
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
    if _should_use_rich():
        _get_console().print(text, style="accent")
    else:
        print(text)


def print_dim(text: str) -> None:
    if _should_use_rich():
        _get_console().print(text, style="dim")
    else:
        print(text)


def print_success(text: str) -> None:
    if _should_use_rich():
        _get_console().print(text, style="success")
    else:
        print(text)


def print_error_styled(text: str) -> None:
    if _should_use_rich():
        _get_console().print(text, style="error")
    else:
        print(text)


def print_kv(key: str, value: str) -> None:
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
        print(f"  {icon} {label} {status}")


def print_table(
    title: str,
    columns: list[tuple[str, str]],
    rows: list[list[str]],
    *,
    column_styles: list[str] | None = None,
    highlight_rows: set[int] | None = None,
) -> None:
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
    )

    for col_name, _col_key in columns:
        table.add_column(col_name, no_wrap=True)

    styles = column_styles or []
    highlights = highlight_rows or set()

    for idx, row_data in enumerate(rows):
        if idx in highlights:
            table.add_row(*row_data, style="accent")
        else:
            row_style = styles[idx % len(styles)] if styles else ""
            table.add_row(*row_data, style=row_style)

    console.print(table)
