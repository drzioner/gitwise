# gitwise — Roadmap de Features

Documento vivo con las funcionalidades propuestas para transformar gitwise de herramienta
diagnóstica/setup en el hub central de git para humanos y agentes AI.

## Estado Actual

gitwise cubre: `doctor`, `setup-agents`, `setup`, `audit`, `summarize`, `snapshot`,
`clean`, `optimize`, `worktree`, `diff`, `update`.

**Gap principal**: No hay operaciones de escritura diaria (commit, branch, push/pull).

---

## Phase 1 — Core Daily Ops

Transforma gitwise en herramienta de uso diario.

### 1.1 `gitwise log` — Pretty log con delta + JSON

- `git log` con defaults sensatos (graph, decorate, -n 20)
- Filtros: `--author`, `--grep`, `--since`, `--until`, `--file`
- Delta automático cuando `HAS_DELTA` + `IS_TTY`
- `--json` con commits estructurados (hash, author, date, subject, files, +/-)
- `--oneline` para vista compacta

**Status**: Pendiente
**Complejidad**: small (~80 líneas)

### 1.2 `gitwise show` — Inspector de commits

- `git show [ref]` con delta automático
- `--json` con full commit data (message, author, date, diff stats, changed files)
- `--stat` para vista de estadísticas sin diff completo

**Status**: Pendiente
**Complejidad**: small (~60 líneas)

### 1.3 `gitwise commit` — Conventional commit + GPG enforcer

- Validación de formato conventional: `^(feat|fix|refactor|docs|chore|test|perf|ci|build|style)(\(.+\))?: .{1,72}`
- Firma GPG obligatoria (-S), rechaza `--no-gpg-sign`
- Preview de archivos staged antes de commit
- `--amend` con seguridad (rechaza si commit ya fue pusheado)
- `--dry-run` para validación sin commit
- `--type` y `--scope` como flags alternativos a mensaje completo
- `--breaking` para agregar `!` al tipo

**Status**: Pendiente
**Complejidad**: medium (~120 líneas)

### 1.4 `gitwise branches` — Dashboard de branches

- Lista branches con: ahead/behind, last commit age, merged status, worktree association
- `--sort date|name` (default: date, usa branch.sort config)
- `--stale` para mostrar solo branches con upstream gone
- `--remote` para incluir remote branches
- `--json` con metadata completa por branch

**Status**: Pendiente
**Complejidad**: medium (~100 líneas)

---

## Phase 2 — Sync + GitHub Integration

### 2.1 `gitwise sync` — Remote sync + safe pull/push

- `git fetch --all --prune` + ahead/behind por branch
- Safe pull (`--ff-only`) con detección de divergencia
- Push con protección (rechaza force a main/master)
- `--dry-run` + `--json`
- Muestra commits unpushed

### 2.2 `gitwise pr` — GitHub PR via gh

- Wrapper de `gh pr create/list/merge/checks`
- Solo funciona si `gh` instalado (shutil.which)
- `--json` con PR data estructurada
- CI status integration

### 2.3 `gitwise undo` — Reflog-based undo

- Lista últimas N operaciones del reflog
- Permite revertir a cualquier punto con `--soft`
- `--dry-run` + `--json`

### 2.4 `gitwise diff --full` — Delta integration en diff existente

- Nueva flag `--full` en diff.py que muestra diff completo con delta
- Reutiliza patrón de summarize.py (HAS_DELTA + subprocess.Popen)

---

## Phase 3 — AI Enhancements

### 3.1 `gitwise context` — Snapshot enriquecido para LLMs

- Extiende snapshot.py: directory tree (depth-limited)
- Top-10 contributors
- Branch topology graph
- File-type breakdown
- TODO/FIXME counts

### 3.2 `gitwise health` — Score numérico de salud

- Score 0-100 calculado de findings de audit
- JSON: `{"score": 85, "grade": "B", "breakdown": {...}}`
- Cada finding tiene peso configurable

### 3.3 `gitwise stash` — Gestión de stashes

- Extiende `_find_old_stashes()` de audit.py
- list/show/clean/pop/drop por index o edad
- `--older-than Nd` para cleanup

### 3.4 Audit mejorado

- Remote health check como finding adicional
- Health score incluido en output JSON

---

## Phase 4 — Advanced Workflows

### 4.1 `gitwise tag` — Semver-aware tag management
### 4.2 `gitwise merge` — Merge/rebase con pre-flight checks
### 4.3 `gitwise conflicts` — Conflict detection + resolution helper
### 4.4 `gitwise suggest` — Heuristic commit message from staged diff
### 4.5 `gitwise pick` — Cherry-pick/revert helper
### 4.6 fzf interactive mode (-i flag en branches/stash/log)

---

## Principios de Diseño

1. **Zero-dep**: Solo stdlib + git subprocess. `shutil.which()` para detectar herramientas opcionales
2. **`--json` en todo**: Para agentes AI
3. **`--dry-run` en destructivos**: commit, sync, clean, stash drop
4. **Delta automático**: Si `HAS_DELTA` + `IS_TTY`
5. **i18n**: Strings via `t()` con keys en `_i18n_data.json`
6. **Patrón**: `run_<command>(*, as_json=False) -> int`
7. **Arquitectura**: validate → plan → dry-run → confirm → execute

## Mejoras a comandos existentes

| Comando | Mejora | Fase |
|---|---|---|
| `diff --full` | Delta integration | Phase 2 |
| `audit` | Remote health check + health score | Phase 3 |
| `summarize` | Ahead/behind vs remote | Phase 3 |
| `setup` | Lefthook detection + delegation | Phase 4 |
