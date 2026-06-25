# gitwise - Hoja de ruta de producto

Source: ROADMAP.md
Last sync: 2026-05-22

[English](ROADMAP.md) | [Español](ROADMAP.es.md)

Roadmap vivo para consolidar gitwise como hub practico de Git para humanos y agentes de codigo.

## Estado actual (v0.15.0)

gitwise actualmente incluye 27 comandos (con aliases): `doctor`, `setup-agents`, `setup`,
`audit`, `summarize`, `snapshot`, `clean` (`branch-clean`), `optimize`, `worktree`,
`diff`, `log`, `show`, `commit`, `branches`, `sync`, `pr`, `undo`, `context`,
`health`, `stash`, `tag`, `merge`, `conflicts`, `suggest` (`commit-suggest`),
`pick` (`cherry-pick`), `status`, `update`.

Completado hasta la Phase 12. Baseline actual: 718 tests recolectados, 548 keys i18n (es/en),
una dependencia runtime (`rich>=13.0`).

---

## Historial de fases

## Phase 1 - Core Daily Ops (MERGED, PR #7)

`log`, `show`, `commit`, `branches`

## Phase 2 - Sync + GitHub Integration (MERGED, PR #8)

`sync`, `pr`, `undo`, `diff --full`

## Phase 3 - AI Enhancements (MERGED, PR #9)

`context`, `health`, `stash`, audit mejorado

## Phase 4 - Advanced Workflows (MERGED, PR #10)

`tag`, `merge`, `conflicts`, `suggest`, `pick`

## Phase 5 - Polish & UX (MERGED, PR #11)

- `gitwise status` - status enriquecido con staged/unstaged/untracked y ahead/behind
- Schema JSON unificado con `v:2` y `ok`
- `context --json` incluye `health.score` + `health.grade`
- `diff` por defecto en diffstat y `--name-only`
- `log --json` con stats por commit
- `update --json`
- Tests de integracion de Phase 4
- README actualizado con comandos

## Phase 6 - Naming Cleanup & UX (MERGED, PR #12)

- `stash clean` -> `stash clear` (alias backward-compatible)
- `pick` -> `cherry-pick` alias
- `diff --full` -> `--patch` alias
- `branches` con edad de ultimo commit
- `log --graph`
- `stash show --patch`

## Phase 7 - Final Aliases & Changelog (MERGED, PR #13)

- `clean` -> `branch-clean` alias
- `suggest` -> `commit-suggest` alias
- ROADMAP y CHANGELOG actualizados

## Phase 8 - Command Enhancements (MERGED, PR #14)

- `pr` para crear PRs via `gh`
- `undo` con reflog en modos soft/hard
- `merge`/`rebase` con preflight checks
- `conflicts` con `--ours`/`--theirs`
- `tag` semver con `--bump`
- `suggest` heuristico desde diff staged
- `pick` con manejo de conflictos
- `update` por `git pull`

## Phase 9 - Cross-Verification Fixes (MERGED, PR #15)

- Ajustes de auditoria multi-review
- Hardening de edge cases en `audit`, `clean`, `optimize`
- Mejora de deteccion GPG en `setup`

## Phase 10 - Architecture Cleanup (MERGED, PR #16, #17)

- `setup_agents` migrado de `_sa_*.py` a paquete `setup_agents/`
- `_runtime_config.py` para settings inmutables
- `_cli_setup_agents.py` separado de logica de negocio
- `docs/guidelines/` ampliado
- Refactor DRY de `require_root()`
- 85+ tests nuevos de edge cases

## Phase 11 - Rich Migration (MERGED, PR #19)

- Sistema completo de color con temas WCAG AA
- `design.py` con tokens, helpers ANSI y formatter
- `_runtime_config.py` con deteccion de tema via OSC 11
- `output.py` con Rich Console y gates de color
- Precedencia de variables de entorno para color
- Flag `--theme`

## Phase 12 - Multi-Agent Adapters & Coverage (v0.12.0)

- `setup_agents/adapters/` con registry para 6 agentes
- Flags `--providers` y `--list-providers` (`--adapters`/`--list-adapters` quedan como aliases de compatibilidad)
- Adapters: Cursor, Continue, opencode, Codex, Aider, Pi
- Templates en `share/<adapter>/`
- Cobertura con patch de subprocess
- `tests/test_adapters.py` para planning, execution, idempotency

---

## Decisiones de naming (resueltas)

| Comando | Alias | Status |
|---|---|---|
| `clean` | `branch-clean` | Done (Phase 7) |
| `stash clean` | `stash clear` | Done (Phase 6) |
| `pick` | `cherry-pick` | Done (Phase 6) |
| `diff --full` | `--patch` | Done (Phase 6) |
| `suggest` | `commit-suggest` | Done (Phase 7) |

---

## Mejoras en comandos existentes

| Comando | Mejora | Fase | Status |
|---|---|---|---|
| `diff --full` | Integracion con delta | Phase 2 | Done |
| `audit` | Remote health check + health score | Phase 3 | Done |
| `summarize` | Ahead/behind vs remote | Phase 3 | Done |
| `diff` | Default a diffstat | Phase 5 | Done |
| `log` | Flag `--graph` | Phase 6 | Done |
| `branches` | Edad de ultimo commit | Phase 6 | Done |
| `log --json` | Stats por commit | Phase 5 | Done |
| `context --json` | Incluir health score | Phase 5 | Done |
| `update` | Soporte `--json` | Phase 5 | Done |

---

## Principios de diseno

1. **Dependencias minimas**: `rich>=13.0` + stdlib + subprocess de git.
2. **`--json` en todos los comandos**: salida util para agentes (envelope v2; `setup-agents` ahora v3).
3. **`--dry-run` para operaciones destructivas**.
4. **Delta automatico** cuando hay TTY.
5. **i18n centralizado** con `t()` y `_i18n_data.json`.
6. **Patron por comando** `run_<command>(*, as_json=False) -> int`.
7. **Flujo estable**: validate -> plan -> dry-run -> confirm -> execute.
8. **Nombres claros** y consistentes con Git.

---

## Depriorizado

| Idea | Razon |
|---|---|
| `gitwise init` | mayormente cubierto por `setup` |
| `gitwise remote` | baja frecuencia, `git remote` suficiente |
| `gitwise ignore` | baja frecuencia, edicion manual suficiente |
| Streaming JSON | complejidad alta, beneficio bajo |
| Manpage | `--help` suficiente por ahora |
| Modo interactivo con fzf | complejidad alta y dependencia opcional |
