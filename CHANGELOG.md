# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
