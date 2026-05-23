# Referencia de comandos

Source: docs/reference/commands.md
Last sync: 2026-05-22

[English](../../reference/commands.md) | [Español](commands.md)

Referencia completa de comandos para `gitwise`.

## Setup y diagnostico

### `gitwise doctor`

Verifica entorno runtime: Python, git, plataforma y herramientas opcionales.

```bash
gitwise doctor
gitwise doctor --json
```

### `gitwise setup`

Aplica defaults modernos de Git (`fetch.prune`, diff histogram, maintenance, estrategia segura de hooks).

```bash
gitwise setup --dry-run
gitwise setup --yes
gitwise setup --hooks-mode preserve
gitwise setup --hooks-mode native
gitwise setup --hooks-mode legacy
gitwise setup --hooks-mode skip
```

Comportamiento de `--hooks-mode`:

- `preserve` (default): mantiene managers/config existentes (`lefthook`, `husky`, `core.hooksPath` custom) y evita conflictos.
- `native`: usa hooks por config de Git (`hook.<name>.event` + `hook.<name>.command`) cuando el Git instalado lo soporta.
- `legacy`: fuerza hooks de Gitwise via `core.hooksPath`.
- `skip`: no gestiona hooks en `setup`.

### `gitwise setup-agents`

Instala archivos canonicos de agentes en global (default) o en el repo actual (`--local`).

- Layout canonico primero: `AGENTS.md` + `.agents/skills/`
- Integraciones de provider (Claude, Cursor, Continue, opencode, Codex, Aider, Pi) opcionales via `--adapters`
- Alias de compatibilidad deprecado: `--adapters claude-only` se interpreta como `claude`
- La salida `--json` de este comando usa schema `v=3` con `canonical_layout` y `v_compat: [1, 2, 3]`

```bash
gitwise setup-agents --local --dry-run
gitwise setup-agents --local --yes
gitwise setup-agents --list-adapters
gitwise setup-agents --local --yes --adapters cursor aider
```

## Contexto diario y revision

### `gitwise summarize`

Salida compacta de status + log para contexto de humanos y agentes.

```bash
gitwise summarize
gitwise summarize --json
gitwise summarize --diff
gitwise summarize --max-commits 5
```

### `gitwise diff`

Vista enfocada de archivos cambiados, con diffstat por defecto.

```bash
gitwise diff
gitwise diff --staged
gitwise diff --name-only
gitwise diff --patch
gitwise diff --json
```

### `gitwise status`

Status enriquecido con staged/unstaged/untracked y ahead/behind.

```bash
gitwise status
gitwise status --json
```

### `gitwise log`

Log legible con filtros y salida JSON.

```bash
gitwise log
gitwise log --oneline
gitwise log --author "user"
gitwise log --grep "fix"
gitwise log --since "2026-01-01"
gitwise log --file gitwise/diff.py
gitwise log --json
```

### `gitwise show`

Inspeccion de detalles de commit.

```bash
gitwise show
gitwise show abc123
gitwise show --json
```

### `gitwise context`

Snapshot enriquecido de repo para flujos LLM.

```bash
gitwise context
gitwise context --json
```

### `gitwise health`

Score y grado de salud del repositorio.

```bash
gitwise health
gitwise health --json
```

## Mantenimiento de repositorio

### `gitwise audit`

Diagnostico read-only de ramas stale, commit-graph, fsmonitor, stashes y blobs.

```bash
gitwise audit
gitwise audit --quick
gitwise audit --json
```

### `gitwise clean`

Limpia ramas/refs stale.

```bash
gitwise clean --branches --dry-run
gitwise clean --branches --yes
gitwise clean --branches --json
```

### `gitwise optimize`

Optimiza object database y commit graph.

```bash
gitwise optimize --dry-run
gitwise optimize --yes
```

### `gitwise snapshot`

Genera `.claude/git-snapshot.md` para contexto de sesion.

```bash
gitwise snapshot
```

### `gitwise worktree`

Crea y limpia worktrees hermanos.

```bash
gitwise worktree new feature/my-branch
gitwise worktree clean
gitwise worktree clean --dry-run
```

## Colaboracion y releases

### `gitwise commit`

Helper para conventional commits.

```bash
gitwise commit -m "feat: add command"
gitwise commit --dry-run -m "fix: handle edge case"
gitwise commit --json -m "docs: update guide"
```

### `gitwise branches`

Dashboard de ramas con metadata de antiguedad de commit.

```bash
gitwise branches
gitwise branches --stale
gitwise branches --remote
gitwise branches --json
```

### `gitwise sync`

Fetch con pull/push opcional.

```bash
gitwise sync
gitwise sync --pull
gitwise sync --push
gitwise sync --dry-run
gitwise sync --json
```

### `gitwise pr`

Wrapper de PRs con GitHub CLI (`gh` requerido).

```bash
gitwise pr list
gitwise pr checks 123
gitwise pr view 123
gitwise pr comments 123
gitwise pr view 123 --json
```

### `gitwise undo`

Revierte commits recientes con seguridad basada en reflog.

```bash
gitwise undo
gitwise undo --soft
gitwise undo --json
```

### `gitwise stash`

List/show/pop/drop/clear de stashes.

```bash
gitwise stash list
gitwise stash show --patch
gitwise stash pop
gitwise stash drop
gitwise stash clear --dry-run
gitwise stash list --json
```

### `gitwise tag`

Tags semver con soporte `--bump`.

```bash
gitwise tag list
gitwise tag create v1.0.0
gitwise tag create --bump minor
gitwise tag create --bump major -m "Release 2.0"
gitwise tag list --json
```

### `gitwise merge`

Helper de merge/rebase con checks de preflight.

```bash
gitwise merge feature-branch
gitwise merge feature-branch --rebase
gitwise merge feature-branch --no-ff
gitwise merge feature-branch --dry-run
gitwise merge feature-branch --json
```

### `gitwise conflicts`

Deteccion de conflictos con auto-resolucion opcional.

```bash
gitwise conflicts
gitwise conflicts --ours
gitwise conflicts --theirs
gitwise conflicts --json
```

### `gitwise suggest`

Sugerencia heuristica de commit message desde diff staged.

```bash
gitwise suggest
gitwise suggest --json
```

### `gitwise pick`

Cherry-pick o revert con soporte de continue/abort.

```bash
gitwise pick abc123
gitwise pick abc123 def456
gitwise pick --revert abc123
gitwise pick --continue
gitwise pick --abort
gitwise pick --dry-run
```

### `gitwise update`

Actualiza gitwise desde su directorio de instalacion.

```bash
gitwise update
gitwise update --json
```
