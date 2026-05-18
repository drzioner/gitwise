# gitwise — Roadmap de Features

Documento vivo con las funcionalidades propuestas para transformar gitwise de herramienta
diagnóstica/setup en el hub central de git para humanos y agentes AI.

## Estado Actual (v0.10.3)

gitwise cubre 27+ comandos (con aliases): `doctor`, `setup-agents`, `setup`, `audit`,
`summarize`, `snapshot`, `clean` (`branch-clean`), `optimize`, `worktree`, `diff`, `log`,
`show`, `commit`, `branches`, `sync`, `pr`, `undo`, `context`, `health`, `stash`, `tag`,
`merge`, `conflicts`, `suggest` (`commit-suggest`), `pick` (`cherry-pick`), `status`, `update`.

**Phases 1-10 completadas.** 326 tests, 624 i18n keys (es/en), zero deps.

---

## Phase 1 — Core Daily Ops (MERGED, PR #7)

`log`, `show`, `commit`, `branches`

## Phase 2 — Sync + GitHub Integration (MERGED, PR #8)

`sync`, `pr`, `undo`, `diff --full`

## Phase 3 — AI Enhancements (MERGED, PR #9)

`context`, `health`, `stash`, audit mejorado

## Phase 4 — Advanced Workflows (MERGED, PR #10)

`tag`, `merge`, `conflicts`, `suggest`, `pick`

## Phase 5 — Polish & UX (MERGED, PR #11)

- `gitwise status` — enhanced git status with staged/unstaged/untracked counts, ahead/behind
- Unified JSON schema: all commands output `v:2` with `ok` field
- `context --json` includes `health.score` + `health.grade`
- `diff` default changed to diffstat; added `--name-only`
- `log --json` enriched with per-commit file stats
- `update --json` support
- Phase 4 integration tests (10 new)
- README updated with all 27 commands

## Phase 6 — Naming Cleanup & UX (MERGED, PR #12)

- `stash clean` → `stash clear` (backward-compatible alias)
- `pick` → `cherry-pick` alias (argparse aliases)
- `diff --full` → `--patch` alias
- `branches` — last-commit age (`committerdate:relative`)
- `log --graph` flag for branch topology
- `stash show --patch` for full diff output

## Phase 7 — Final Aliases & Changelog (MERGED, PR #13)

- `clean` → `branch-clean` alias
- `suggest` → `commit-suggest` alias
- ROADMAP.md updated (all items marked Done)
- CHANGELOG.md generated

## Phase 8 — Command Enhancements (MERGED, PR #14)

- `pr` — create GitHub PRs via `gh` CLI
- `undo` — reflog-based undo with soft/hard modes
- `merge` — merge/rebase with preflight checks
- `conflicts` — conflict detection and resolution (`--ours`/`--theirs`)
- `tag` — semver-aware tag management with `--bump`
- `suggest` — heuristic commit message suggestion from staged diff
- `pick` — cherry-pick/revert with conflict handling
- `update` — self-update via `git pull` in install directory

## Phase 9 — Cross-Verification Fixes (MERGED, PR #15)

- Multi-review audit fixes across command modules
- Edge case hardening in `audit`, `clean`, `optimize`
- GPG detection improvements in `setup`

## Phase 10 — Architecture Cleanup (MERGED, PR #16, #17)

- `setup_agents` refactored from monolithic `_sa_*.py` files to `setup_agents/` package
- `_runtime_config.py` — immutable runtime settings (theme, color, TTY, bat/delta detection)
- `_cli_setup_agents.py` — CLI adapter separated from business logic
- Guidelines documentation (`docs/guidelines/`): architecture, python, testing, anti-patterns
- `require_root()` DRY refactoring across command modules
- 85+ new edge case tests

---

## Nombres resueltos

| Comando | Alias | Status |
|---|---|---|
| `clean` | `branch-clean` | Done (Phase 7) |
| `stash clean` | `stash clear` | Done (Phase 6) |
| `pick` | `cherry-pick` | Done (Phase 6) |
| `diff --full` | `--patch` | Done (Phase 6) |
| `suggest` | `commit-suggest` | Done (Phase 7) |

---

## Mejoras a comandos existentes

| Comando | Mejora | Fase | Status |
|---|---|---|---|
| `diff --full` | Delta integration | Phase 2 | Done |
| `audit` | Remote health check + health score | Phase 3 | Done |
| `summarize` | Ahead/behind vs remote | Phase 3 | Done |
| `diff` | Default a diffstat | Phase 5 | Done |
| `log` | `--graph` flag | Phase 6 | Done |
| `branches` | last-commit-date | Phase 6 | Done |
| `log --json` | file stats por commit | Phase 5 | Done |
| `context --json` | incluir health score | Phase 5 | Done |
| `update` | `--json` support | Phase 5 | Done |

---

## Principios de Diseño

1. **Zero-dep**: Solo stdlib + git subprocess. `shutil.which()` para detectar herramientas opcionales
2. **`--json` en todo**: Para agentes AI (schema unificado v:2)
3. **`--dry-run` en destructivos**: commit, sync, clean, stash drop, merge, tag delete
4. **Delta automático**: Si `HAS_DELTA` + `IS_TTY`
5. **i18n**: Strings via `t()` con keys en `_i18n_data.json`
6. **Patrón**: `run_<command>(*, as_json=False) -> int`
7. **Arquitectura**: validate → plan → dry-run → confirm → execute
8. **Nombres claros**: Evitar colisiones con git builtins, usar terminologia consistente

---

## Deprioritized

| Idea | Razón |
|---|---|
| `gitwise init` | `setup` ya cubre la mayoria |
| `gitwise remote` | Baja frecuencia, `git remote` es suficiente |
| `gitwise ignore` | Baja frecuencia, edicion manual es suficiente |
| Streaming JSON | Complejidad alta, beneficio bajo |
| Manpage | `--help` es suficiente por ahora |
| fzf interactive mode | Complejidad alta, requiere dependencia opcional |
