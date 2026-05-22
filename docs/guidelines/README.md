# Guidelines — gitwise

> Stack: `python@3.10+` · `argparse` · `stdlib` · `pytest` · `ruff` · `basedpyright`
> Minimal dependencies. `rich` for terminal rendering + stdlib + git subprocess.
> Last reviewed: 2026-05-22

Index of development standards for the project.

---

## Which guideline to read for X?

| I want to know about... | Read |
|-------------------------|------|
| Types, type hints, Literal, Protocol, pathlib, error handling, resources | [python-guidelines.md](python-guidelines.md) |
| Plan/execute/rollback, subcommand pattern, managed blocks, batch failures | [architecture.md](architecture.md) |
| pytest, subprocess testing, conftest, no mocks, error paths | [testing-guidelines.md](testing-guidelines.md) |
| What NOT to do — prohibited anti-patterns | [anti-patterns.md](anti-patterns.md) |
| Visual identity, color palette, typography, component patterns | [../../DESIGN.md](../../DESIGN.md) |

---

## Quick reference stack

```
gitwise/                # Python package — one module per subcommand
  __main__.py           # argparse router → dispatches to run_<cmd>()
  setup_agents/         # AGENTS.md/CLAUDE.md coexistence (5-bucket model)
  _cli_setup_agents.py  # CLI adapter for setup-agents
  _runtime_config.py    # immutable runtime settings (theme, color, TTY)
  git.py                # git subprocess helpers (run, config, is_repo, etc.)
  output.py             # ok/warn/error/info/debug/print_json
  _i18n_data.json       # es/en string catalog (434 keys)
  i18n.py               # translation helper + locale detection
  snapshot.py           # .claude/git-snapshot.md generator
  doctor.py             # Environment checks
  audit.py              # Repo diagnostics (7 finding types)
  setup.py              # Modern git defaults
  clean.py              # Stale branch cleanup
  optimize.py           # gc, pack-refs, commit-graph
  summarize.py          # Compact status + log
  diff.py               # Changed file list
  worktree.py           # Worktree helpers
tests/                  # pytest — mirrors gitwise/ modules
  conftest.py           # run_gitwise() subprocess helper + fixtures
share/claude/           # Templates copied/merged into target repos
```

- **Runtime**: Python 3.10+ with git 2.29+
- **Dependencies**: 1 runtime (`rich>=13.0` for terminal rendering). Stdlib + `git` subprocess for everything else.
- **CLI**: `argparse` (no Click, no Typer)
- **Tests**: `pytest` as dev dependency, no mocks, real subprocess
- **Lint**: `ruff check` + `ruff format`
- **Type check**: `basedpyright` (Python 3.10+, Darwin)
- **Hooks**: `lefthook` (pre-commit: ruff, commit-msg: commitizen, pre-push: pytest)
- **Exit codes**: 0 = ok, 1 = error, 2 = strict warnings
