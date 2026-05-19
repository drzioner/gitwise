---
alwaysApply: false
paths: tests/**
---

# Testing Conventions

- No mocks — all git operations run on synthetic temp repos via fixtures
- One behavior per test; test name follows `test_<unit>_<scenario>_<expected>` pattern
- Test error paths and edge cases, not just happy paths
- Fixtures in `conftest.py`; no shared mutable state between tests
- `run_gitwise()` helper for subprocess invocation; assert exit codes and output
- `pytest -k` filters preferred over commenting out tests
- Coverage: aim for meaningful coverage of critical paths (setup_agents, symlink safety)

## Coverage note

`--cov` reports ~22% because tests run gitwise as a subprocess (`subprocess.run()`). `pytest --cov` only instruments the parent process, so 24 command modules show 0% despite being fully tested via subprocess invocations. With `[tool.coverage.run] patch = ["subprocess"]` in `pyproject.toml`, subprocess coverage is collected when running with `--cov`. The real coverage is significantly higher. Only modules directly imported in test files (`setup_agents/`, `clean`, `optimize`, `git`, `i18n`, `output`) show accurate coverage numbers. 440+ tests across all modules.
