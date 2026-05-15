# Guidelines — gitwise

> Stack: `python@3.10+` · `argparse` · `stdlib` · `pytest` · `ruff` · `basedpyright`
> Zero dependencies. Only stdlib + git subprocess.
> Last reviewed: 2026-05-15

Index of development standards for the project.

---

## Which guideline to read for X?

| I want to know about... | Read |
|-------------------------|------|
| Types, type hints, Literal, Protocol, pathlib | [python-guidelines.md](python-guidelines.md) |
| Plan/execute/rollback, subcommand pattern, managed blocks | [architecture.md](architecture.md) |
| pytest, subprocess testing, conftest, no mocks | [testing-guidelines.md](testing-guidelines.md) |
| What NOT to do — prohibited anti-patterns | [anti-patterns.md](anti-patterns.md) |

---

## Quick reference stack

```
gitwise/                # Python package — one module per subcommand
  __main__.py           # argparse router → dispatches to run_<cmd>()
  setup_agents.py       # AGENTS.md/CLAUDE.md coexistence (5-bucket model)
  git.py                # git subprocess helpers (run, config, is_repo, etc.)
  output.py             # ok/warn/error/info/debug/print_json
  i18n.py               # es/en strings (~170 keys), auto locale detection
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
- **Dependencies**: Zero. Only stdlib + `git` subprocess
- **CLI**: `argparse` (no Click, no Typer)
- **Tests**: `pytest` as dev dependency, no mocks, real subprocess
- **Lint**: `ruff check` + `ruff format`
- **Type check**: `basedpyright` (Python 3.10+, Darwin)
- **Hooks**: `lefthook` (pre-commit: ruff, commit-msg: commitizen, pre-push: pytest)
- **Exit codes**: 0 = ok, 1 = error, 2 = strict warnings
