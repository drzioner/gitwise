---
alwaysApply: false
paths: gitwise/output.py, gitwise/design.py, gitwise/_runtime_config.py
---

# Color System Architecture

`rich>=13.0` is a hard dependency (`pyproject.toml`). `output.py` uses `try/except ImportError` to degrade gracefully if missing.

## Rendering pipeline

- `design.py` — ThemeTokens (hex colors), `hex_to_ansi_fg()` (for argparse help only), text utilities
- `_runtime_config.py` — immutable RuntimeConfig: theme (dark/light via OSC 11 query), color depth, terminal width, TTY detection
- `output.py` — Rich Console with custom Theme, all output functions (`ok`, `warn`, `error`, `info`, `print_header`, `print_section`, `print_status_line`, `print_table`, etc.)
- `GitwiseHelpFormatter` (in `design.py`) — raw ANSI via `hex_to_ansi_fg()` because argparse cannot use Rich

## Console creation (`_make_console`)

- `force_terminal=True` — bypasses Rich's `isatty()` check, always emits ANSI codes
- `color_system` — from `detect_color_depth()`: truecolor/256/16 based on `COLORTERM`/`TERM`
- `no_color=None` — delegates to Rich's native `NO_COLOR` detection
- `markup=False` — prevents Rich from parsing `[brackets]` in git output as markup

## Color gate (`_use_rich`)

- Returns `False` → plain `print()`, no ANSI codes (non-TTY: pipes, pytest capsys, AI agents)
- Returns `True` → Rich Console with themed colors

## Environment variable precedence (highest to lowest)

1. `NO_COLOR` / `GITWISE_NO_COLOR` → disable all colors
2. `CLICOLOR_FORCE` / `FORCE_COLOR` → force colors even in non-TTY
3. `COLORTERM=truecolor` → 24-bit color (detected by `detect_color_depth()`)
4. `TERM=xterm-256color` → 256-color fallback
5. Auto-detect via `sys.stdout.isatty()` → TTY check

## Theme detection (`_detect_theme`)

1. `GITWISE_THEME` env var (dark/light)
2. `CLITHEME` env var
3. OSC 11 background query (`\x1b]11;?\x1b\\`) to terminal
4. `COLORFGBG` / `FG_BG` env vars
5. Default: `dark`

## Diagnostics

`GITWISE_DEBUG=1 python -m gitwise doctor` prints console config (force_terminal, color_system, is_terminal, no_color, theme, depth, is_tty) to stderr.

## Debugging color issues checklist

1. **Python version:** Run `python -m gitwise doctor`. If `python` line shows system Python (3.14+), Rich is not installed → use `uv run python -m gitwise` or `bin/gitwise` instead.
2. **Rich installed:** Run `python -c "import rich"`. If `ModuleNotFoundError`, the active Python lacks Rich → wrong interpreter.
3. **Console config:** Run `GITWISE_DEBUG=1 python -m gitwise doctor 2>&1 | grep console:`. Verify `force_terminal=True`, `is_terminal=True`, `no_color=False`.
4. **Env vars:** Check `NO_COLOR`, `GITWISE_NO_COLOR`, `CLICOLOR_FORCE`, `FORCE_COLOR` — these override auto-detection.
5. **OSC 11 query:** If theme detection fails (always defaults to dark), the terminal may not support OSC 11. Set `GITWISE_THEME=dark` or `GITWISE_THEME=light` explicitly.
6. **Piped output:** Colors are intentionally disabled in non-TTY (pipes, `| cat`, pytest capsys). Use `CLICOLOR_FORCE=1` to force colors for debugging.
