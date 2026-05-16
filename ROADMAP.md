# gitwise — Roadmap de Features

Documento vivo con las funcionalidades propuestas para transformar gitwise de herramienta
diagnóstica/setup en el hub central de git para humanos y agentes AI.

## Estado Actual (v0.6.0)

gitwise cubre 25 comandos: `doctor`, `setup-agents`, `setup`, `audit`, `summarize`, `snapshot`,
`clean`, `optimize`, `worktree`, `diff`, `log`, `show`, `commit`, `branches`, `sync`, `pr`,
`undo`, `context`, `health`, `stash`, `tag`, `merge`, `conflicts`, `suggest`, `pick`, `update`.

**Phases 1-4 completadas.** 222 tests, 301 i18n keys (es/en), 5,312 LOC.

---

## Phase 1 — Core Daily Ops (MERGED)

`log`, `show`, `commit`, `branches` — PR #7

## Phase 2 — Sync + GitHub Integration (MERGED)

`sync`, `pr`, `undo`, `diff --full` — PR #8

## Phase 3 — AI Enhancements (MERGED)

`context`, `health`, `stash`, audit mejorado — PR #9

## Phase 4 — Advanced Workflows (MERGED)

`tag`, `merge`, `conflicts`, `suggest`, `pick` — PR #10

---

## Phase 5 — Polish & UX (Post-Audit)

Resultado de auditoria con 10 perfiles profesionales + 4 iteraciones autoresearch.

### 5.1 `gitwise status` — El comando faltante

- Wrapper de `git status` con formato mejorado + `--json`
- El comando #1 que cualquier usuario intenta primero
- Muestra: branch, ahead/behind, staged/unstaged/untracked counts, archivos modificados

**Status**: Pendiente
**Severidad**: CRITICAL (consenso UX + PM + Junior + Git Power User)

### 5.2 Unificar schema JSON

- Todos los comandos output `v: 2`, siempre incluyen `ok`
- `update` necesita `--json`
- Consistencia para agentes AI y pipelines CI/CD

**Status**: Pendiente
**Severidad**: HIGH

### 5.3 `context --json` incluir health score

- Agentes necesitan contexto + salud en una sola call
- `context --json` agrega campo `health: {score, grade}` reutilizando `compute_health()`

**Status**: Pendiente
**Severidad**: MEDIUM

### 5.4 `diff` default a diffstat

- Default actual (`name-status`) es MENOS útil que `git diff`
- Nuevo default: diffstat (insertions/deletions por archivo)
- `--name-only` para lista simple, `--full` para patch completo

**Status**: Pendiente
**Severidad**: HIGH

### 5.5 `log --json` agregar file stats por commit

- JSON output no incluye files changed, insertions, deletions por commit
- Agentes necesitan esto para summarization

**Status**: Pendiente
**Severidad**: MEDIUM

### 5.6 Tests de integracion para Phase 4

- `merge`: test de merge/rebase real (no solo dry-run)
- `pick`: test de cherry-pick/revert real
- `conflicts`: test de --ours/--theirs con conflictos reales
- `sync --push`: test de push real
- `tag --bump`: test de bump major/minor/patch

**Status**: Pendiente
**Severidad**: CRITICAL

### 5.7 Mejoras menores de UX

- `branches`: agregar last-commit-date/age
- `log`: agregar `--graph`
- `stash show`: agregar `--patch`
- `sync`: agregar `--remote` flag para scope
- Help text: agregar ejemplos a top 5 comandos
- `diff --full` help: mencionar "patch view"

**Status**: Pendiente
**Severidad**: MEDIUM

### 5.8 Documentacion actualizada

- README.md: listar los 25 comandos con descripciones
- CHANGELOG: formato user-friendly (no solo commit messages)
- CONTRIBUTING.md: actualizar con nuevo flujo

**Status**: Pendiente
**Severidad**: HIGH

---

## Nombres a revisar

| Comando actual | Problema | Alternativa propuesta | Severidad |
|---|---|---|---|
| `clean` | Colisiona con `git clean` (elimina archivos untracked) | `branch-clean` o alias `prune-branches` | HIGH |
| `stash clean` | Inconsistente con `git stash clear` | `stash clear` | MEDIUM |
| `pick` | Ambiguo — podria ser cherry-pick, revert, interactive rebase | `cherry-pick` (con `--revert` flag) | MEDIUM |
| `diff --full` | "full" no es terminologia git | Considerar `--patch` como alias | LOW |
| `suggest` | No queda claro que sugiere | `commit-suggest` | LOW |

---

## Mejoras a comandos existentes

| Comando | Mejora | Fase | Status |
|---|---|---|---|
| `diff --full` | Delta integration | Phase 2 | Done |
| `audit` | Remote health check + health score | Phase 3 | Done |
| `summarize` | Ahead/behind vs remote | Phase 3 | Done |
| `diff` | Default a diffstat | Phase 5 | Pendiente |
| `log` | `--graph` flag | Phase 5 | Pendiente |
| `branches` | last-commit-date | Phase 5 | Pendiente |
| `log --json` | file stats por commit | Phase 5 | Pendiente |
| `context --json` | incluir health score | Phase 5 | Pendiente |
| `update` | `--json` support | Phase 5 | Pendiente |

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
