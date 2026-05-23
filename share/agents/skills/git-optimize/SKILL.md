---
name: git-optimize
description: Muestra qué optimizaciones aplicaría gitwise (commit-graph, repack -A -d, prune) en modo dry-run. Usa cuando el usuario pida optimizar git, acelerar log/status, o cuando audit reporte commit-graph ausente.
argument-hint: "(sin argumentos)"
allowed-tools: Bash(gitwise optimize --dry-run --json)
disable-model-invocation: true
---

# git-optimize

## Contexto

Plan de optimización (dry-run):

!`gitwise optimize --dry-run --json`

## Tarea

1. Lista los `steps` que se ejecutarían (`name`, `desc`).
2. Estima impacto: commit-graph acelera `git log` 2-10x; repack reduce tamaño y crea bitmap-index; prune libera objetos no referenciados.
3. Recomienda al usuario ejecutar `gitwise optimize --yes` para aplicarlas. NO ejecutes la versión `--yes` tú mismo: `disable-model-invocation: true` + `allowed-tools` restrictivo lo previenen por diseño.
