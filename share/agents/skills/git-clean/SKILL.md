---
name: git-clean
description: Lista en dry-run las ramas locales cuyo upstream fue eliminado ([gone]) y reporta cuáles son seguras de borrar. Usa cuando el usuario pida limpiar ramas stale, huérfanas o merged.
argument-hint: "(sin argumentos)"
allowed-tools: Bash(gitwise clean --branches --dry-run --json)
disable-model-invocation: true
---

# git-clean

## Contexto

Resultado de `gitwise clean --branches --dry-run --json`:

!`gitwise clean --branches --dry-run --json`

## Tarea

1. Reporta el conteo y nombres de ramas en `deletable` y `skipped` (con su `reason`).
2. Si `deletable` está vacío, responde "No hay ramas stale eliminables" y termina.
3. Si hay ramas eliminables, sugiere al usuario el comando para borrarlas tras revisión: `gitwise clean --branches --yes`.
4. NUNCA ejecutes el borrado tú mismo. La versión `--yes` NO está en `allowed-tools` por diseño — requiere confirmación humana explícita.
