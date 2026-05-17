# Changelog

All notable changes to gitwise are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.7.0] — 2025-05-16

### Added
- `branch-clean` alias for `clean` command (avoids collision with `git clean`)
- `commit-suggest` alias for `suggest` command
- `cherry-pick` alias for `pick` command (argparse aliases)
- `--patch` alias for `diff --full`
- `--graph` flag for `gitwise log` (branch topology)
- `--patch` flag for `gitwise stash show` (full diff output)
- Last-commit age column in `gitwise branches` output (`committerdate:relative`)
- 6 new tests (241 total)

### Changed
- ROADMAP.md fully updated — all completed phases and items marked Done
- `stash clean` now accepts `stash clear` as well (backward-compatible)
- `branches` dashboard uses fixed-width columns for readability

## [0.6.0] — 2025-05-16 (Phase 5)

### Added
- `gitwise status` — enhanced git status with staged/unstaged/untracked counts, ahead/behind, `--json`
- Unified JSON schema: all 27 commands output `v:2` with `ok` field
- `context --json` includes `health.score` and `health.grade`
- `log --json` enriched with per-commit file stats via `diff-tree`
- `update --json` support
- `--name-only` flag for `gitwise diff`
- 13 new tests (235 total)

### Changed
- `diff` default changed from `--name-status` to `--stat` (diffstat)
- README updated with documentation for all 27 commands
- 304 i18n keys synchronized (es/en)

## [0.5.0] — 2025-05-16 (Phase 4)

### Added
- `gitwise tag` — semver-aware tag management with `--bump major/minor/patch`
- `gitwise merge` — merge/rebase with pre-flight checks, `--no-ff`, `--dry-run`
- `gitwise conflicts` — conflict detection with `--ours`/`--theirs` auto-resolve
- `gitwise suggest` — heuristic commit message from staged diff
- `gitwise pick` — cherry-pick/revert with `--continue`/`--abort`/`--dry-run`
- 18 new tests (222 total)

## [0.4.0] — 2025-05-16 (Phase 3)

### Added
- `gitwise context` — directory tree, contributors, file types, TODO/FIXME, branch topology
- `gitwise health` — score 0-100 with grade A-F and penalty breakdown
- `gitwise stash` — list/show/pop/drop/clean with `--dry-run`, `--yes`, `--json`
- `gitwise audit` — remote health check, health score integration
- `compute_health()` extracted as reusable function
- `has_remote()`, `has_upstream()`, `has_commit_graph()` shared git helpers
- 11 new tests (204 total)

## [0.3.0] — 2025-05-16 (Phase 2)

### Added
- `gitwise sync` — pull --rebase + push in one step
- `gitwise pr` — create GitHub PR with smart defaults
- `gitwise undo` — soft reset last commit
- `diff --full` — full patch with delta integration
- 13 new tests (193 total)

## [0.2.0] — 2025-05-16 (Phase 1)

### Added
- `gitwise log` — pretty git log with filters, `--oneline`, `--json`
- `gitwise show` — commit inspector with `--stat`, `--json`
- `gitwise commit` — smart conventional commit with validation
- `gitwise branches` — branch intelligence dashboard with ahead/behind, worktree info
- 30 new tests (180 total)

## [0.1.0] — 2025-05-15

### Added
- `gitwise doctor` — environment checks
- `gitwise setup` — modern git defaults
- `gitwise setup-agents` — Claude Code configuration injection
- `gitwise audit` — repository diagnostics
- `gitwise summarize` — compact status + log
- `gitwise snapshot` — `.claude/git-snapshot.md` generation
- `gitwise clean` — stale branch cleanup
- `gitwise optimize` — gc, pack-refs, commit-graph
- `gitwise worktree` — worktree helpers for Claude agents
- `gitwise diff` — changed file list
- i18n system with es/en string catalog
- Adaptive terminal colors with dark/light theme detection
- GPG protection via hooks and deny rules
- CI/CD pipeline with multi-platform, multi-Python testing
