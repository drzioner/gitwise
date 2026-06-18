# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.25.0 (2026-06-18)

### Feat

- **install**: rewrite install.sh for remote curl|bash via uv tool install (#57)

## v0.24.5 (2026-06-18)

### Fix

- **packaging**: add project URLs and SPDX license metadata (#55)
- **ci**: abort auto-release when commits cancel out via revert (#56)

## v0.24.4 (2026-06-17)

### Fix

- **packaging**: add project URLs and SPDX license metadata

## v0.24.3 (2026-06-17)

### Fix

- **doctor**: handle missing git executable gracefully

## v0.24.2 (2026-06-16)

### Fix

- **packaging**: rename distribution to gitwise-cli to avoid PyPI name conflict

## v0.24.1 (2026-06-16)

### Fix

- **ci**: replace invalid action SHAs in publish-pypi workflow

## v0.24.0 (2026-06-16)

### Feat

- enable pip and brew distribution with packaging, security, and refactor fixes (#54)

## v0.23.0 (2026-06-16)

### Notes

- Semver realignment for the breaking changes shipped in `v0.22.1`. The
  underlying changes are documented in the `v0.22.1` entry below; this
  release contains no additional functional changes. The minor bump was
  triggered when a subsequent `docs:` commit included the literal string
  `BREAKING CHANGE:` in its body (explaining the convention rule itself),
  which commitizen detected as a breaking-change marker. The CHANGELOG
  section for this version is intentionally empty of items because
  commitizen filters `docs:` commits out of the rendered output.

## v0.22.1 (2026-06-16)

> **Note on versioning:** This release contains breaking changes to the JSON
> output of `optimize`, `clean`, and `setup`. Under strict semver with
> `major_version_zero = true` it should have been `v0.23.0`. The patch
> increment was the result of a `fix:` commit lacking the `BREAKING CHANGE:`
> footer that commitizen needs to detect breaking changes. The next minor
> bump will resync; meanwhile this entry documents the breaks explicitly so
> consumers can react.

### Fix

- **optimize/clean/setup**: `--json` now executes the same write paths as the
  TTY mode (closes #45). Previously the JSON branch printed a plan and
  returned `ok:true` without running any side effects, silently breaking
  agents/CI that drove gitwise in JSON mode. (#50)
- **sync**: `sync --pull` on diverged branches now returns an actionable hint
  in EN/ES plus a structured `suggested_commands` array in the JSON envelope
  (closes #43). (#50)

### Breaking Changes

- **optimize/clean/setup**: `--json` on a write command now requires `--yes`
  to execute side effects. Without `--yes` the command returns `rc=2` and
  emits an `error_envelope` with `code:"yes_required"`. Use `--dry-run` for
  plan-only inspection. (#50)
- **clean (JSON only)**: domain-specific error array renamed from `errors`
  to `delete_errors` to avoid collision with the envelope-level `errors[]`
  field used by `error_envelope`. (#50)
- **optimize/clean/setup (JSON only)**: all three commands now emit through
  the unified `ok_envelope`/`error_envelope` helpers. Shape:
  `{v, ok, applied, dry_run, ...payload}` on success and
  `{v, ok:false, error, errors:[{code, message, hint}], ...payload}` on
  failure. (#50)

## v0.22.0 (2026-05-23)

### Feat

- **schema**: add versioned schema catalog and CI validation (#41)

## v0.21.0 (2026-05-23)

### Feat

- **cli**: add P2 commands/schema introspection with resilient dependency fallbacks (#40)

## v0.20.0 (2026-05-23)

### Feat

- implement P1 completions, rich help, and env docs (#38)

## v0.19.0 (2026-05-23)

### Feat

- close P0 agent safety and JSON error consistency (#37)

## v0.18.0 (2026-05-23)

### Feat

- **release**: auto-sync CHANGELOG.es on bump

### Fix

- **ci**: eliminate workflow_call auth failure and cache collisions on main (#36)
- **setup-agents**: restore rollback correctness and isolate claude core

### Refactor

- **setup-agents**: canonical local default and transactional rollback

## v0.17.0 (2026-05-23)

### Feat

- **setup-agents**: add providers flag and legacy migration flow

### Fix

- **setup-agents**: address PR review feedback and strict JSON behavior

## v0.16.0 (2026-05-23)

### Feat

- **setup-agents**: canonical-first layout and json v3

### Fix

- **setup-agents**: address PR review feedback

## v0.15.3 (2026-05-23)

### Refactor

- **setup-agents**: providers foundation and claude wrapper extraction (#32)

## v0.15.2 (2026-05-22)

### Fix

- version version badget

## v0.15.1 (2026-05-22)

### Fix

- **release**: align roadmap and lockfile with v0.15.0 (#30)

## v0.15.0 (2026-05-22)

### Feat

- **setup**: add safe hooks strategy with native Git support (#29)

## v0.14.2 (2026-05-22)

### Refactor

- unify command dispatch, shared utils, and JSON envelopes (#27)

## v0.14.1 (2026-05-22)

### Fix

- **audit**: resolve post-merge review follow-ups and docs mismatches (#26)

## v0.14.0 (2026-05-22)

### Feat

- **pr**: improve view comments and checks readability (#25)

## v0.13.0 (2026-05-21)

### Feat

- unify human output styling and global JSON modes (#24)

## v0.12.2 (2026-05-20)

### Fix

- **ci**: unblock auto-release — workflow_call, dev deps, scoped permissions
- full audit — 35 items across security, quality, performance and CI

## v0.12.1 (2026-05-19)

### Refactor

- split AGENTS.md into scoped rules for opencode and Claude Code (#21)

## v0.12.0 (2026-05-19)

### Feat

- demo, subprocess coverage, agent adapters (#20)

## v0.11.0 (2026-05-19)

### Feat

- Rich migration — full color system with WCAG AA themes (#19)

## v0.10.3 (2026-05-18)

### Refactor

- 6-phase architecture cleanup + guidelines expansion (#17)

## v0.10.2 (2026-05-17)

### Refactor

- Phase 10 — require_root() DRY + edge case tests (#16)

## v0.10.1 (2026-05-17)

### Fix

- Phase 9 — Cross-verification fixes from multi-review audit (#15)

## v0.10.0 (2026-05-17)

### Feat

- Phase 8 — command enhancements (#14)

## v0.9.0 (2026-05-17)

### Feat

- Phase 7 — final aliases, ROADMAP & CHANGELOG (#13)

## v0.8.0 (2026-05-16)

### Feat

- Phase 7 — final aliases, ROADMAP & CHANGELOG (#13)
- Phase 6 — naming cleanup & UX enhancements (#12)

## v0.7.0 (2026-05-16)

### Feat

- Phase 5 — polish & UX improvements (#11)

## v0.6.0 (2026-05-16)

### Feat

- Phase 4 — advanced workflows (tag, merge, conflicts, suggest, pick)

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
