# gitwise - Product Roadmap

[English](ROADMAP.md) | [Español](ROADMAP.es.md)

Living roadmap for turning gitwise into a practical Git hub for humans and coding agents.

## Current state

gitwise currently ships 30 commands (with aliases): `doctor`, `setup-agents`, `setup`,
`audit`, `summarize`, `snapshot`, `clean` (`branch-clean`), `optimize`, `worktree`,
`diff`, `log`, `show`, `commit`, `branches`, `sync`, `pr`, `undo`, `context`,
`health`, `stash`, `tag`, `merge`, `conflicts`, `suggest` (`commit-suggest`),
`pick` (`cherry-pick`), `status`, `update`, `commands`, `schema`, `completions`.

Completed through Phase 12. Current baseline: 30 commands, 745 tests collected,
550 i18n keys (es/en), 3 runtime dependencies (rich, rich-argparse, shtab).

---

## Phase 1 -- Core Daily Ops (MERGED, PR #7)

`log`, `show`, `commit`, `branches`

## Phase 2 -- Sync + GitHub Integration (MERGED, PR #8)

`sync`, `pr`, `undo`, `diff --full`

## Phase 3 -- AI Enhancements (MERGED, PR #9)

`context`, `health`, `stash`, improved audit

## Phase 4 -- Advanced Workflows (MERGED, PR #10)

`tag`, `merge`, `conflicts`, `suggest`, `pick`

## Phase 5 -- Polish & UX (MERGED, PR #11)

- `gitwise status` -- enhanced git status with staged/unstaged/untracked counts, ahead/behind
- Unified JSON schema: all commands output `v:2` with `ok` field
- `context --json` includes `health.score` + `health.grade`
- `diff` default changed to diffstat; added `--name-only`
- `log --json` enriched with per-commit file stats
- `update --json` support
- Phase 4 integration tests (10 new)
- README updated with the complete command set at that release

## Phase 6 -- Naming Cleanup & UX (MERGED, PR #12)

- `stash clean` -> `stash clear` (backward-compatible alias)
- `pick` -> `cherry-pick` alias (argparse aliases)
- `diff --full` -> `--patch` alias
- `branches` -- last-commit age (`committerdate:relative`)
- `log --graph` flag for branch topology
- `stash show --patch` for full diff output

## Phase 7 -- Final Aliases & Changelog (MERGED, PR #13)

- `clean` -> `branch-clean` alias
- `suggest` -> `commit-suggest` alias
- ROADMAP.md updated (all items marked Done)
- CHANGELOG.md generated

## Phase 8 -- Command Enhancements (MERGED, PR #14)

- `pr` -- create GitHub PRs via `gh` CLI
- `undo` -- reflog-based undo with soft/hard modes
- `merge` -- merge/rebase with preflight checks
- `conflicts` -- conflict detection and resolution (`--ours`/`--theirs`)
- `tag` -- semver-aware tag management with `--bump`
- `suggest` -- heuristic commit message suggestion from staged diff
- `pick` -- cherry-pick/revert with conflict handling
- `update` -- self-update via `git pull` in install directory

## Phase 9 -- Cross-Verification Fixes (MERGED, PR #15)

- Multi-review audit fixes across command modules
- Edge case hardening in `audit`, `clean`, `optimize`
- GPG detection improvements in `setup`

## Phase 10 -- Architecture Cleanup (MERGED, PR #16, #17)

- `setup_agents` refactored from monolithic `_sa_*.py` files to `setup_agents/` package
- `_runtime_config.py` -- immutable runtime settings (theme, color, TTY, bat/delta detection)
- `_cli_setup_agents.py` -- CLI adapter separated from business logic
- Guidelines documentation (`docs/guidelines/`): architecture, python, testing, anti-patterns
- `require_root()` DRY refactoring across command modules
- 85+ new edge case tests

## Phase 11 -- Rich Migration (MERGED, PR #19)

- Full color system with WCAG AA themes (dark/light)
- `design.py` -- ThemeTokens (hex colors), `hex_to_ansi_fg()`, `GitwiseHelpFormatter`
- `_runtime_config.py` -- immutable RuntimeConfig with OSC 11 theme detection
- `output.py` -- Rich Console with custom Theme, color gate, force_terminal
- Environment variable precedence: NO_COLOR/GITWISE_NO_COLOR -> CLICOLOR_FORCE/FORCE_COLOR -> COLORTERM -> TERM -> auto
- `--theme` CLI flag

## Phase 12 -- Multi-Agent Adapters & Coverage (v0.12.0)

- `setup_agents/adapters/` -- adapter registry for 6 coding agents
- `--providers` and `--list-providers` CLI flags (`--adapters`/`--list-adapters` kept as compatibility aliases)
- Adapters: Cursor, Continue, opencode, Codex, Aider, Pi
- `share/<adapter>/` template files for each agent
- `[tool.coverage.run]` with subprocess patching for accurate coverage
- `tests/test_adapters.py` -- adapter planning, execution, idempotency tests
- 440+ tests across all modules

---

## Naming decisions (resolved)

| Comando | Alias | Status |
|---|---|---|
| `clean` | `branch-clean` | Done (Phase 7) |
| `stash clean` | `stash clear` | Done (Phase 6) |
| `pick` | `cherry-pick` | Done (Phase 6) |
| `diff --full` | `--patch` | Done (Phase 6) |
| `suggest` | `commit-suggest` | Done (Phase 7) |

---

## Existing command enhancements

| Comando | Mejora | Fase | Status |
|---|---|---|---|
| `diff --full` | Delta integration | Phase 2 | Done |
| `audit` | Remote health check + health score | Phase 3 | Done |
| `summarize` | Ahead/behind vs remote | Phase 3 | Done |
| `diff` | Default a diffstat | Phase 5 | Done |
| `log` | `--graph` flag | Phase 6 | Done |
| `branches` | last-commit-date | Phase 6 | Done |
| `log --json` | file stats per commit | Phase 5 | Done |
| `context --json` | include health score | Phase 5 | Done |
| `update` | `--json` support | Phase 5 | Done |

---

## Design principles

1. **Minimal deps**: `rich`, `rich-argparse`, `shtab` + stdlib + git subprocess. Optional tools via `shutil.which()`.
2. **`--json` everywhere**: machine-friendly output for coding agents using the v3 envelope.
3. **`--dry-run` for destructive paths**: commit, sync, clean, stash drop, merge, tag delete.
4. **Automatic delta rendering**: when `HAS_DELTA` and `IS_TTY`.
5. **i18n model**: strings resolved through `t()` with keys in `_i18n_data.json`.
6. **Subcommand pattern**: `run_<command>(*, as_json=False) -> int`.
7. **Execution flow**: validate -> plan -> dry-run -> confirm -> execute.
8. **Naming clarity**: avoid collisions with core git commands, keep consistent vocabulary.

---

## Deprioritized

| Idea | Reason |
|---|---|
| `gitwise init` | mostly covered by `setup` |
| `gitwise remote` | low-frequency workflow, `git remote` already sufficient |
| `gitwise ignore` | low-frequency workflow, manual editing is usually enough |
| Manpage | `--help` is enough for now |
| fzf interactive mode | high complexity and optional dependency overhead |
