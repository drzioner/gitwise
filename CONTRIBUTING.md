# Contributing to gitwise

Thanks for your interest! This guide covers everything you need to contribute.

## Quick start

```bash
git clone https://github.com/drzioner/gitwise.git
cd gitwise
uv sync                            # create .venv with dev dependencies
brew install lefthook               # install git hooks manager
lefthook install                    # install git hooks
uv run pytest                      # run all tests
uv run pytest -k test_worktree     # run specific tests
```

No install step needed during development — run directly from repo root:

```bash
python -m gitwise <command>
```

## Development workflow

1. Create a branch: `gitwise worktree new feature/my-thing` (or `git checkout -b`)
2. Make changes
3. Hooks run automatically via lefthook:
   - **pre-commit**: ruff check + ruff format + shellcheck
   - **commit-msg**: conventional commit validation via commitizen
   - **pre-push**: full test suite

   To run manually:

```bash
lefthook run pre-commit
lefthook run commit-msg --commit-msg-file .git/COMMIT_EDITMSG
lefthook run pre-push
```

4. Commit with [conventional format](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
5. Open a pull request

## Architecture

Each subcommand follows the same pattern:

```python
def run_<command>(...) -> int:   # returns exit code
    # 1. Validate (is_repo, repo_root)
    # 2. Plan (_plan_actions → list[dict], warnings, errors)
    # 3. Dry-run: print plan, return 0
    # 4. Confirm (unless --yes)
    # 5. Execute (_execute_actions)
    # 6. Return exit code (0=ok, 1=error, 2=strict warnings)
```

One module per subcommand in `gitwise/`. Tests in `tests/` mirror the module
structure. Tests invoke gitwise as a subprocess via `run_gitwise()` in
`conftest.py` — no mocks, all git operations run on synthetic temp repos.

## Code style

- Type hints on all function signatures
- `pathlib.Path` over `os.path` (use `os.path.realpath` for symlink resolution)
- No comments describing what code does — only WHY (non-obvious invariants)
- Minimal dependencies — `rich` is the only allowed external dependency
- `ruff` handles linting and formatting; config is in `pyproject.toml`
- `lefthook` manages git hooks; config is in `lefthook.yml`
- `commitizen` validates commit messages; config is in `pyproject.toml`

## Key files

```
gitwise/             # Python package — one module per subcommand
  __main__.py        # argparse router → dispatches to run_<cmd>()
  setup_agents.py    # AGENTS.md/CLAUDE.md coexistence (5-bucket model)
  git.py             # git subprocess helpers
  output.py          # output functions + confirm()
  snapshot.py        # generates .claude/git-snapshot.md
  doctor.py          # environment checks
  audit.py           # repo diagnostics
  setup.py           # modern git defaults
  clean.py           # stale branch/ref cleanup
  optimize.py        # gc, pack-refs, commit-graph
  summarize.py       # compact status + log
  diff.py            # focused changed-file list
  worktree.py        # worktree helpers for Claude agents
share/claude/        # Templates copied/merged into target repos
share/hooks/         # Git hooks (pre-commit, commit-msg)
tests/               # pytest — mirrors gitwise/ modules
bin/gitwise          # Shell shebang wrapper → python -m gitwise
install.sh           # Installs to ~/.local/bin
```

## Pull request process

- PRs require CI to pass (ruff, pytest, basedpyright, shellcheck)
- PRs require at least one review (for external contributors)
- Squash merge is preferred for clean history
- Keep PRs focused — one feature or fix per PR

## Reporting issues

- Use [GitHub Issues](https://github.com/drzioner/gitwise/issues)
- Include: OS, Python version, git version, steps to reproduce
- Run `gitwise doctor` and include the output
