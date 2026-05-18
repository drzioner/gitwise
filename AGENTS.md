---
description: Guidance for AI coding agents working on gitwise, a zero-dependency Python CLI for optimizing git workflows and Claude Code integration.
tags: [python, cli, git, pytest, claude-code, agents-md]
---

# gitwise — Agent Guide

gitwise is a zero-dependency Python CLI for optimizing git workflows and Claude Code integration. It applies modern git defaults, generates context files (CLAUDE.md, settings.json, skills), and manages AGENTS.md ↔ CLAUDE.md coexistence (5-bucket model). Only stdlib and git subprocesses.

## Dev Environment

No install step needed. Run directly:

```bash
python -m gitwise <command>       # from repo root
gitwise <command>                 # if installed via install.sh
```

Install (one-time):

```bash
bash install.sh                   # symlinks bin/gitwise → ~/.local/bin/gitwise
```

**Shell compatibility notes for AI agents:**
- Claude Code's non-interactive shell does NOT source `~/.zshrc`. Use `python -m gitwise` (always works from repo root) or the full `gitwise` path if `~/.local/bin` is on PATH.
- `gw` is a terminal-only alias (`alias gw='gitwise'` in `~/.zshrc`). It is NOT available in Claude Code's bash environment. Never use `gw` in tool calls — use `gitwise` or `python -m gitwise`.
- `settings.json` allow list includes both `Bash(gitwise *)` and `Bash(python -m gitwise *)` for this reason.

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
  output.py          # ok/warn/error/info/debug/print_json/bat_pipe
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
bin/gitwise          # Shell shebang wrapper → python -m gitwise
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

**Ask first:**
- Adding a new subcommand (touches `__main__.py` router and needs its own test module)
- Changing the 5-bucket model logic in `setup_agents.plan._resolve_canonical_doc`
- Modifying `share/claude/` templates (affects all repos that run setup-agents)

**Never:**
- Create AGENTS.md in a target repo from scratch — that's the user's content decision
- Add external dependencies to `gitwise/` (zero-dep is a hard constraint)
- Use `Path.resolve()` for symlink sandbox checks — use `os.path.realpath()` instead
- Commit without GPG (`--no-gpg-sign` is only allowed in test fixtures, never in real commits)
- Add `--global` to `npm config set` or similar package manager globals
