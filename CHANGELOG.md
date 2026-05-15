# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-14

### Added

- `doctor` — environment checks (git, Python, optional tools)
- `setup-agents` — Claude Code config injection (AGENTS.md/CLAUDE.md coexistence, 5-bucket model)
- `setup` — modern git defaults (fetch.prune, diff.algorithm, hooks, fsmonitor)
- `audit` — read-only repo diagnostics (gone branches, commit-graph, stashes, large blobs)
- `summarize` — compact status + log with optional diff
- `snapshot` — generates .claude/git-snapshot.md for Claude Code session context
- `clean --branches` — removes local branches with deleted upstream
- `optimize` — commit-graph, repack, prune
- `worktree new/clean` — worktree management for Claude agent workflow
- `diff` — focused changed-file list
- `update` — self-update via git pull
- Visual integration: `bat` for log highlighting, `delta` for diff rendering
- GPG protection: pre-commit hook + Claude Code deny rules
- Conventional commit enforcement via commit-msg hook
- Zero external dependencies — stdlib only
- `install.sh` for one-command setup
- CI with ruff, pytest, basedpyright, shellcheck, pip-audit

[0.1.0]: https://github.com/drzioner/gitwise/releases/tag/v0.1.0
