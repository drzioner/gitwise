# gitwise — Agent Guide

gitwise is a Python CLI for optimizing git workflows and Claude Code integration. It uses `rich` for terminal rendering and applies modern git defaults, generates context files (CLAUDE.md, settings.json, skills), and manages AGENTS.md ↔ CLAUDE.md coexistence (5-bucket model).

## Dev Environment

For development, use `uv` to sync dependencies and run the package in place:

```bash
uv sync                            # create .venv and install rich + deps
uv run python -m gitwise <command> # run from repo root using the venv
```

For end-user installation (installs `gitwise` as a global CLI tool, isolated from your other Python environments):

```bash
bash install.sh                    # local: installs gitwise-cli via `uv tool install`
# or remote one-liner (macOS/Linux):
curl -fsSL https://raw.githubusercontent.com/drzioner/gitwise/main/install.sh | bash
```

Windows users use `install.ps1`:

```powershell
irm https://raw.githubusercontent.com/drzioner/gitwise/main/install.ps1 | iex
```

The installer auto-installs `uv` if missing, then runs `uv tool install --upgrade gitwise-cli`. The `gitwise` binary lands in `~/.local/bin` (macOS/Linux) or `%USERPROFILE%\.local\bin` (Windows). See `bash install.sh --help` / `Get-Help .\install.ps1` for options (`--dry-run` / `-DryRun`, `--version=X.Y.Z` / `-Version`).

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

## Test Commands

```bash
uv run pytest                      # all tests (from repo root)
uv run pytest tests/test_setup_agents.py -v   # single module
uv run pytest -k test_bucket2      # filter by name
uv run pytest --cov=gitwise        # with coverage
```

## Lint, Format & Type Check

```bash
ruff check gitwise/ tests/         # lint
ruff format gitwise/ tests/        # format
uv run basedpyright                # type check (Python 3.10+, All platforms)
shellcheck install.sh bin/gitwise  # shell lint
lefthook run pre-commit            # run all pre-commit hooks
```

## Project Structure

See `.agents/rules/project-structure.md` for full tree.

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

See `.agents/rules/setup-agents.md` for `setup_agents/` package internals and JSON schema.

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

## Git conventions for this project

- Diff: `git diff --stat` or `gitwise summarize`. Never raw `git diff`.
- Log: `git --no-pager log --oneline -n 20`. Never without a limit.
- Commits: conventional format `feat/fix/refactor/docs/chore: description`.
- Commits: always GPG-signed. Never `--no-gpg-sign`.
- Commits: breaking changes MUST include the `BREAKING CHANGE` footer
  (the marker word in caps followed by a colon and a description), or `!`
  after the type (e.g. `feat!: ...`). Without one of these markers,
  `commitizen` will pick a patch bump even when the body mentions breaks,
  and the CHANGELOG entry generated by the auto-release workflow will not
  surface the break in `### Breaking Changes`. With `major_version_zero = true`,
  a real breaking change should rotate the minor (e.g. `0.22.x → 0.23.0`).
- Commits: never write the exact `BREAKING CHANGE` + colon sequence in prose
  inside a commit body unless that commit really introduces a breaking change.
  `commitizen` scans the full message for the marker and fires a minor bump
  on any commit that contains it — including `docs:` commits that merely
  document the convention. Backticks do NOT escape — commitizen reads raw
  text. When you need to refer to the marker descriptively, omit the colon
  (write `BREAKING CHANGE` alone) or use a placeholder like
  `BREAKING CHANGE [colon]`. Avoid invisible Unicode tricks (no-break
  spaces, zero-width joiners) — editors silently auto-format them back to
  regular characters. See the `v0.23.0` CHANGELOG entry for an example of
  what happens when this rule is violated.
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
- Use `gh pr merge --admin` to bypass branch protection — if a check fails, rerun the failed job (`gh run rerun --job <id>`) and wait for all checks to pass before merging
- Merge a PR that has any failing checks — all checks must be green, no exceptions
- **Iterate superficially** when a CI step fails. Stop, read the actual traceback / failure log, identify the root cause, and apply ONE fix that addresses it. Each "ci(diag): ..." style commit that just adds another workaround is a smell — by the third iteration, pause and re-analyze the whole problem from the logs. The verify-before-implement skill documents the Consult → Analyze → Verify → Decide → Implement loop; skipping Analyze produces the loop of reactive commits.

## Scoped Rules

Detailed rules for specific subsystems are in `.agents/rules/`:

| File | Loads when editing |
|------|-------------------|
| `project-structure.md` | Always |
| `testing.md` | `tests/**` |
| `setup-agents.md` | `gitwise/setup_agents/**` |
| `color-system.md` | `gitwise/output.py`, `design.py`, `_runtime_config.py` |
| `shell-scripts.md` | `bin/*`, `install.sh` |
| `github-actions.md` | `.github/workflows/*`, `scripts/audit-template-injection.py` |
| `python-cli.md` | `gitwise/__main__.py`, `gitwise/output.py`, any CLI entry point or exception handler |
