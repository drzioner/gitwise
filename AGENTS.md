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
uv run pytest --cov=gitwise        # with coverage
```

Tests invoke gitwise as a subprocess via `run_gitwise()` in `conftest.py`. No mocks — all git operations run on synthetic temp repos created by fixtures.

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
  setup_agents.py    # entry point: run_setup_agents → _run_setup_local/global
  _sa_state.py       # state detection (_classify_path, _detect_state, _detect_rules)
  _sa_plan.py        # planning (_resolve_canonical_doc, _plan_*, managed blocks, 5-bucket model)
  _sa_exec.py        # execution (_execute_actions, _safe_create_symlink, _undo_partial)
  i18n.py            # t(), confirm_responses() — loads strings from _i18n_data.json
  _i18n_data.json    # i18n string catalog (es/en)
  git.py             # git subprocess helpers (is_repo, repo_root, config, run)
  output.py          # ok/warn/error/info/debug/print_json
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

`setup_agents.py` — key functions:
- `_detect_state(root)` → state dict (a_state, c_state, agents_dir, skills_state, rules_warnings, supports_symlinks, errors, …)
- `_resolve_canonical_doc(root, state, ...)` → `(bucket: 1-5, actions, warnings)`
- `_plan_actions(root, ...)` → `(actions, warnings, errors, bucket, state)` — read-only I/O for state detection is acceptable
- `_execute_actions(root, actions)` — writes files; rolls back on failure via `_undo_partial`
- `_safe_create_symlink(link, target_relative, root)` — sandbox + TOCTOU-safe

JSON output schema: `v=2`, `v_compat=[1,2]`. Keys: `bucket`, `agents_md_detected`, `agents_dir_detected`, `supports_symlinks`, `actions`, `warnings`, `rules_warnings`, `errors`, `summary`, `ok`.

## Code Style

- Type hints on all function signatures
- `pathlib.Path` over `os.path` (use `os.path.realpath` for symlink resolution — `Path.resolve()` can fail on broken symlinks)
- `Literal["absent","regular","symlink_valid","symlink_broken"]` for path states
- Never silence exceptions; `try/except OSError` only at I/O boundaries
- No comments describing what the code does — only WHY (non-obvious invariants)
- No abstractions before 3+ concrete use cases

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
- Run `uv run pytest` after any change to `setup_agents.py` or its tests
- Run `ruff check` and `ruff format --check` before committing
- Use `_safe_create_symlink` for any new symlink creation (sandbox enforced)
- Keep `_plan_actions` read-only (no write I/O) — state detection reads are acceptable; planning and execution are separate phases
- Preserve JSON schema backward compat: v1 mandatory keys must remain

**Ask first:**
- Adding a new subcommand (touches `__main__.py` router and needs its own test module)
- Changing the 5-bucket model logic in `_resolve_canonical_doc`
- Modifying `share/claude/` templates (affects all repos that run setup-agents)

**Never:**
- Create AGENTS.md in a target repo from scratch — that's the user's content decision
- Add external dependencies to `gitwise/` (zero-dep is a hard constraint)
- Use `Path.resolve()` for symlink sandbox checks — use `os.path.realpath()` instead
- Commit without GPG (`--no-gpg-sign` is only allowed in test fixtures, never in real commits)
- Add `--global` to `npm config set` or similar package manager globals
