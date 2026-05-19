---
description: Guidance for AI coding agents working on gitwise, a Python CLI for optimizing git workflows and Claude Code integration.
tags: [python, cli, git, pytest, claude-code, agents-md]
---

# gitwise — Agent Guide

gitwise is a Python CLI for optimizing git workflows and Claude Code integration. It uses `rich` for terminal rendering and applies modern git defaults, generates context files (CLAUDE.md, settings.json, skills), and manages AGENTS.md ↔ CLAUDE.md coexistence (5-bucket model).

## Dev Environment

No install step needed. Run directly:

```bash
python -m gitwise <command>       # from repo root (uses venv via uv)
gitwise <command>                 # if installed via install.sh
```

Install (one-time):

```bash
bash install.sh                   # symlinks bin/gitwise → ~/.local/bin/gitwise
```

### Python resolution — CRITICAL

`bin/gitwise` resolves the Python interpreter in this order:
1. `.venv/bin/python` in the project root (managed by `uv`, has `rich` installed)
2. System `python3` (fallback — may NOT have `rich`)

**Common pitfall:** Running `python -m gitwise` from the terminal may invoke the SYSTEM Python (e.g., 3.14) which does NOT have `rich` installed. The `try/except ImportError` in `output.py` silently falls back to plain `print()` with zero colors. Always verify with `python -m gitwise doctor` — if it reports the system Python version and shows no colors, the wrong interpreter is being used.

**Correct invocation from repo root:**
- `uv run python -m gitwise <cmd>` — guaranteed to use venv Python with rich
- `bin/gitwise <cmd>` — auto-detects `.venv/bin/python`, falls back to `python3`
- `gitwise <cmd>` (if installed) — same as `bin/gitwise` via symlink

**Shell compatibility notes for AI agents:**
- Claude Code's non-interactive shell does NOT source `~/.zshrc`. Use `python -m gitwise` (always works from repo root) or the full `gitwise` path if `~/.local/bin` is on PATH.
- `gw` is a terminal-only alias (`alias gw='gitwise'` in `~/.zshrc`). It is NOT available in Claude Code's bash environment. Never use `gw` in tool calls — use `gitwise` or `python -m gitwise`.
- `settings.json` allow list includes both `Bash(gitwise *)` and `Bash(python -m gitwise *)` for this reason.

### Color system architecture

`rich>=13.0` is a hard dependency (`pyproject.toml`). `output.py` uses `try/except ImportError` to degrade gracefully if missing.

**Rendering pipeline:**
- `design.py` — ThemeTokens (hex colors), `hex_to_ansi_fg()` (for argparse help only), text utilities
- `_runtime_config.py` — immutable RuntimeConfig: theme (dark/light via OSC 11 query), color depth, terminal width, TTY detection
- `output.py` — Rich Console with custom Theme, all output functions (`ok`, `warn`, `error`, `info`, `print_header`, `print_section`, `print_status_line`, `print_table`, etc.)
- `GitwiseHelpFormatter` (in `design.py`) — raw ANSI via `hex_to_ansi_fg()` because argparse cannot use Rich

**Console creation (`_make_console`):**
- `force_terminal=True` — bypasses Rich's `isatty()` check, always emits ANSI codes
- `color_system` — from `detect_color_depth()`: truecolor/256/16 based on `COLORTERM`/`TERM`
- `no_color=None` — delegates to Rich's native `NO_COLOR` detection
- `markup=False` — prevents Rich from parsing `[brackets]` in git output as markup

**Color gate (`_use_rich`):**
- Returns `False` → plain `print()`, no ANSI codes (non-TTY: pipes, pytest capsys, AI agents)
- Returns `True` → Rich Console with themed colors

**Environment variable precedence** (highest to lowest):
1. `NO_COLOR` / `GITWISE_NO_COLOR` → disable all colors
2. `CLICOLOR_FORCE` / `FORCE_COLOR` → force colors even in non-TTY
3. `COLORTERM=truecolor` → 24-bit color (detected by `detect_color_depth()`)
4. `TERM=xterm-256color` → 256-color fallback
5. Auto-detect via `sys.stdout.isatty()` → TTY check

**Theme detection (`_detect_theme`):**
1. `GITWISE_THEME` env var (dark/light)
2. `CLITHEME` env var
3. OSC 11 background query (`\x1b]11;?\x1b\\`) to terminal
4. `COLORFGBG` / `FG_BG` env vars
5. Default: `dark`

**Diagnostics:** `GITWISE_DEBUG=1 python -m gitwise doctor` prints console config (force_terminal, color_system, is_terminal, no_color, theme, depth, is_tty) to stderr. Use this to diagnose color issues.

## Test Commands

```bash
uv run pytest                      # all tests (from repo root)
uv run pytest tests/test_setup_agents.py -v   # single module
uv run pytest -k test_bucket2      # filter by name
uv run pytest --cov=gitwise        # with coverage (see note below)
```

Tests invoke gitwise as a subprocess via `run_gitwise()` in `conftest.py`. No mocks — all git operations run on synthetic temp repos created by fixtures.

**Coverage note:** `--cov` reports ~22% because tests run gitwise as a subprocess (`subprocess.run()`). `pytest --cov` only instruments the parent process, so 24 command modules show 0% despite being fully tested via subprocess invocations. The real coverage is significantly higher. Only modules directly imported in test files (`setup_agents/`, `clean`, `optimize`, `git`, `i18n`, `output`) show accurate coverage numbers.

## Lint, Format & Type Check

```bash
ruff check gitwise/ tests/         # lint
ruff format gitwise/ tests/        # format
uvx basedpyright                   # type check (Python 3.10+, Darwin)
/opt/homebrew/bin/shellcheck install.sh bin/gitwise   # shell lint (macOS)
lefthook run pre-commit            # run all pre-commit hooks
```

## Project Structure

```
gitwise/             # Python package — one module per subcommand
  __main__.py        # argparse router → dispatches to run_<cmd>()
  setup_agents/      # setup-agents sub-package (plan, state, exec, types, format)
  _cli_setup_agents.py  # CLI adapter for setup-agents
  _runtime_config.py  # immutable runtime settings (theme, color, TTY, bat/delta)
  i18n.py            # t(), confirm_responses(), reset_cache() — loads from _i18n_data.json
  _i18n_data.json    # i18n string catalog (es/en, 624 keys)
  git.py             # git subprocess helpers (is_repo, repo_root, config, run, _get_timeout)
  output.py          # Rich Console engine: ok/warn/error/info/debug/print_json/bat_pipe
  design.py          # ThemeTokens (hex), GitwiseHelpFormatter (raw ANSI), text utilities
  snapshot.py        # generates .claude/git-snapshot.md
  doctor.py          # environment checks
  audit.py           # repo diagnostics
  setup.py           # modern git defaults
  clean.py           # stale branch/ref cleanup
  optimize.py        # gc, pack-refs, commit-graph
  summarize.py       # compact status + log
  diff.py            # focused changed-file list (gitwise diff)
  worktree.py        # worktree helpers for Claude agents
share/claude/        # Templates copied/merged into target repos
  CLAUDE.md.template
  settings.json.template
  rules/gitwise.md
  skills/git-audit/SKILL.md
  skills/git-clean/SKILL.md
  skills/git-optimize/SKILL.md
tests/               # pytest — mirrors gitwise/ modules
  conftest.py        # shared fixtures + run_gitwise() helper
bin/gitwise          # Shell wrapper → .venv/bin/python (or python3 fallback)
install.sh           # Installs to ~/.local/bin
```

## Architecture Conventions

Each subcommand follows this pattern:

```python
def run_<command>(...) -> int:   # returns exit code
    # 1. Validate (is_repo, repo_root)
    # 2. Plan (_plan_actions → list[dict], warnings, errors)
    # 3. Dry-run: print plan, return 0
    # 4. Confirm (unless --yes)
    # 5. Execute (_execute_actions)
    # 6. Return exit code (0=ok, 1=error, 2=strict warnings)
```

`setup_agents/` package — key modules:
- `setup_agents/state.py`: `_detect_state(root)` → state dict, `_classify_path()`, `_detect_rules()`, `reset_caches()`
- `setup_agents/plan.py`: `_resolve_canonical_doc()` → bucket 1-5, `_plan_actions()` → actions list
- `setup_agents/exec.py`: `_execute_actions()` — writes files, rolls back via `_undo_partial`; `_safe_create_symlink()` — sandbox + TOCTOU-safe
- `setup_agents/plan_skills.py`: `plan_skills()`, `plan_global_skills()` — skill installation planning
- `setup_agents/plan_gitfiles.py`: `plan_managed_block()` — .gitignore/.gitattributes managed blocks
- `setup_agents/types.py`: `ActionDict`, `StateDict`, `PathState`, `ActionSummary` — shared type definitions
- `setup_agents/format.py`: `format_json_output_local()`, `format_json_output_global()` — JSON output formatting

JSON output schema: `v=2`, `v_compat=[1,2]`. Keys: `bucket`, `agents_md_detected`, `agents_dir_detected`, `supports_symlinks`, `actions`, `warnings`, `rules_warnings`, `errors`, `summary`, `ok`.

## Code Style

- Type hints on all function signatures (enforced by basedpyright)
- `pathlib.Path` over `os.path` (use `os.path.realpath` for symlink resolution — `Path.resolve()` can fail on broken symlinks)
- `Literal["absent","regular","symlink_valid","symlink_broken"]` for path states
- Never silence exceptions; `try/except OSError` only at I/O boundaries
- No comments describing what the code does — only WHY (non-obvious invariants)
- No abstractions before 3+ concrete use cases (Rule of Three)
- `T | None` over `Optional[T]` (Python 3.10+ syntax)
- Return types always explicit; never rely on inference for public APIs
- Named tuples or dataclasses over plain tuples for multi-value returns
- Constants as `SCREAMING_SNAKE_CASE` at module level
- Absolute imports only; no relative imports
- Functions: one purpose, max ~50 lines; extract when complexity grows
- Composition over inheritance; prefer protocols for interface definitions
- No `Any` type without explicit justification comment

## Error Handling

- Validate inputs early at function boundaries (fail-fast)
- `try/except` only at I/O boundaries; never bare `except Exception: pass`
- Chain exceptions with `raise ... from e` to preserve debug trail
- Specific exception types (`ValueError`, `TypeError`, `FileNotFoundError`) over generic `Exception`
- Batch operations: track successes and failures separately; never abort entire batch on single item error
- Error messages: explain what failed, why, and how to fix

## Resource Management

- Context managers (`with`) for all file handles and external resources
- No unclosed resources; `__exit__` / `finally` must run unconditionally
- `subprocess.run()` with explicit `timeout` and `capture_output=True` for git calls
- Clean up temp files/dirs in `finally` blocks or fixture teardown

## Testing

- No mocks — all git operations run on synthetic temp repos via fixtures
- One behavior per test; test name follows `test_<unit>_<scenario>_<expected>` pattern
- Test error paths and edge cases, not just happy paths
- Fixtures in `conftest.py`; no shared mutable state between tests
- `run_gitwise()` helper for subprocess invocation; assert exit codes and output
- `pytest -k` filters preferred over commenting out tests
- Coverage: aim for meaningful coverage of critical paths (setup_agents, symlink safety)

## Shell Scripts

- ShellCheck clean: `shellcheck install.sh bin/gitwise` passes with zero warnings
- `set -Eeuo pipefail` at top of all shell scripts
- Quote all variable expansions; never leave `$var` unquoted
- Check exit codes directly with `if command; then` — never `if [ $? -eq 0 ]`

## Git conventions for this project

- Diff: `git diff --stat` or `gitwise summarize`. Never raw `git diff`.
- Log: `git --no-pager log --oneline -n 20`. Never without a limit.
- Commits: conventional format `feat/fix/refactor/docs/chore: description`.
- Commits: always GPG-signed. Never `--no-gpg-sign`.
- Branch switch: `gitwise worktree new <branch>`. Never `git stash + checkout`.
- Changed files: `gitwise diff` (= `git diff --name-status HEAD`). Never raw `git diff`.
- Before large commits: `gitwise audit --quick`.

## Boundaries

**Always:**
- Run `uv run pytest` after any change to `setup_agents/` or its tests
- Run `ruff check` and `ruff format --check` before committing
- Use `_safe_create_symlink` for any new symlink creation (sandbox enforced)
- Keep `_plan_actions` read-only (no write I/O) — state detection reads are acceptable; planning and execution are separate phases
- Preserve JSON schema backward compat: v1 mandatory keys must remain
- Verify `doctor` reports the venv Python version (3.12.x) when testing colors — if it shows the system Python (3.14.x), colors will NOT work

**Ask first:**
- Adding a new subcommand (touches `__main__.py` router and needs its own test module)
- Changing the 5-bucket model logic in `setup_agents.plan._resolve_canonical_doc`
- Modifying `share/claude/` templates (affects all repos that run setup-agents)

**Never:**
- Create AGENTS.md in a target repo from scratch — that's the user's content decision
- Add external dependencies beyond `rich` to `gitwise/` (rich is the only allowed external dep)
- Use `Path.resolve()` for symlink sandbox checks — use `os.path.realpath()` instead
- Commit without GPG (`--no-gpg-sign` is only allowed in test fixtures, never in real commits)
- Add `--global` to `npm config set` or similar package manager globals
- Run `python -m gitwise` without verifying it uses the venv Python (colors silently break if system Python is used)

### Debugging color issues — troubleshooting checklist

If colors don't appear in terminal output, check in this order:

1. **Python version:** Run `python -m gitwise doctor`. If `python` line shows system Python (3.14+), Rich is not installed → use `uv run python -m gitwise` or `bin/gitwise` instead.
2. **Rich installed:** Run `python -c "import rich"`. If `ModuleNotFoundError`, the active Python lacks Rich → wrong interpreter.
3. **Console config:** Run `GITWISE_DEBUG=1 python -m gitwise doctor 2>&1 | grep console:`. Verify `force_terminal=True`, `is_terminal=True`, `no_color=False`.
4. **Env vars:** Check `NO_COLOR`, `GITWISE_NO_COLOR`, `CLICOLOR_FORCE`, `FORCE_COLOR` — these override auto-detection.
5. **OSC 11 query:** If theme detection fails (always defaults to dark), the terminal may not support OSC 11. Set `GITWISE_THEME=dark` or `GITWISE_THEME=light` explicitly.
6. **Piped output:** Colors are intentionally disabled in non-TTY (pipes, `| cat`, pytest capsys). Use `CLICOLOR_FORCE=1` to force colors for debugging.
