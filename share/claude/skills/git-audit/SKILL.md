---
name: git-audit
description: Diagnostica el repositorio git (ramas stale, commit-graph, fsmonitor, blobs grandes, stashes viejos) y reporta hallazgos priorizados con fixes recomendados. Usa cuando el usuario pida auditar, revisar salud o diagnosticar el repo.
argument-hint: "[--quick]"
allowed-tools: Bash(gitwise audit*)
disable-model-invocation: true
---

# git-audit

## Contexto

Resultado de `gitwise audit --json`:

!`gitwise audit --json`

## Tarea

Eres un asistente experto en git. Analiza el JSON anterior y produce un reporte breve y accionable:

1. **Resumen ejecutivo** (1 línea): estado general del repo.
2. **Hallazgos priorizados**: lista cada `finding` ordenado por `severity` (critical > high > medium > low > info). Para cada uno indica: `message`, `fix` sugerido, `cost_of_ignore`.
3. **Acción recomendada**: el comando exacto a ejecutar primero (típicamente el `fix` del finding más severo). NO lo ejecutes — solo recomiéndalo.

Si `findings` está vacío, responde "Repo en buen estado" y termina. No inventes hallazgos no presentes en el JSON.
