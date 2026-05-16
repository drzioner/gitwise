# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.5.0 (2026-05-16)

### Feat

- Phase 3 — AI enhancements (context, health, stash, audit)

## v0.4.0 (2026-05-16)

### Feat

- Phase 2 — sync + GitHub integration (sync, pr, undo, diff --full)

## v0.3.0 (2026-05-16)

### Feat

- Phase 1 — core daily operations (log, show, commit, branches)

## v0.2.4 (2026-05-16)

### Fix

- resolve CI auto-release cancellation and deprecation warnings (#6)

## v0.2.3 (2026-05-16)

### Fix

- resolve all AGENTS.md guideline violations (i18n, code style, boundaries) (#5)

## v0.2.2 (2026-05-15)

### Fix

- remove persist-credentials: false from release checkout
- harden CI/CD pipeline — security, reliability, efficiency

## v0.2.1 (2026-05-15)

### Fix

- match commitizen changelog format in release notes extraction

## v0.2.0 (2026-05-15)

### Feat

- add automated release via commitizen bump on merge to main
- apply i18n to all modules — replace 200+ hardcoded Spanish strings
- add adaptive terminal colors with dark/light theme detection
- add i18n system with es/en string catalog
- add lefthook hooks, commitizen versioning, fix CI

### Fix

- auto-release bump bug, harden CI workflows, eliminate double CI
- address PR review — template format bug, redundant logic, missed string
- eliminate cache race condition in CI
- resolve CI failures, add dependabot, harden release workflow

## v0.1.0 (2026-05-14)

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
