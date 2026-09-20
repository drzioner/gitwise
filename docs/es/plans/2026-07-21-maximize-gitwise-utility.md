# Plan: maximizar la utilidad de gitwise

Source: docs/plans/2026-07-21-maximize-gitwise-utility.md  
Last sync: 2026-07-21  

[English](../../plans/2026-07-21-maximize-gitwise-utility.md) | Español

## Objetivo

Entregar primero los cambios que hacen a gitwise más útil y confiable en flujos reales, sin ampliar el número de comandos ni perseguir paridad con Git o GitHub CLI.

## Principio de priorización

Un cambio entra en este plan solo si:

- evita una clase reproducible de error;
- reduce bytes o contexto en un flujo de agente;
- elimina una promesa pública falsa;
- refuerza uno de los siete comandos centrales;
- reduce mantenimiento sin romper consumidores conocidos.

## Núcleo de inversión

```text
setup-agents  worktree  summarize  context  diff  commit  audit
```

## Tren de PRs

| Orden | PR | Resultado | Valor | Esfuerzo |
|---:|---|---|---|---|
| 1 | Contrato JSON fiable | Global flags en cualquier posición y errores siempre parseables | Máximo | Medio-alto |
| 2 | Invariantes de subprocess | Entorno Git saneado y timeout para git-sizer | Alto | Bajo |
| 3 | Contexto acotado | `context` limita árbol y declara truncación | Máximo | Medio |
| 4 | Snapshot multi-agente | `.agents/` se convierte en canon real con fallback legacy | Alto | Bajo-medio |
| 5 | Contrato público | Se retira `clean --refs` y se depreca `update` | Alto | Bajo-medio |
| 6 | Verdad documental | README, roadmap, seguridad y demo reflejan el producto | Alto | Medio |

## PR 1: contrato JSON

- Preparsear `--json`, `--json-pretty`, `--lang` y `--theme` con argparse para que funcionen antes o después del subcomando.
- Corregir errores JSON de `worktree new`, `stash pop`, `stash drop` y `stash clear`.
- Usar exit 2 para operaciones destructivas JSON que requieren `--yes`.
- Añadir matriz contractual de rutas negativas sin duplicar el inventario completo de comandos.

**Salida:** 100% de las rutas tocadas producen envelope v3 parseable.

## PR 2: seguridad y robustez

- Aplicar `_GIT_ENV` a `_git_bytes`.
- Añadir timeout configurable a `git-sizer`.
- Añadir gate CI de coverage en 75% después de confirmar estabilidad con `-n 2`.

**Salida:** ningún subprocess nuevo o existente en estas rutas evade las invariantes centrales.

## PR 3: contexto acotado

- Añadir `context --max-entries`; candidato default 100, elegido tras medir 50/100/200 contra un presupuesto de 8 KB.
- Emitir `tree_total` y `tree_truncated`.
- Actualizar dispatch, schemas, tests y referencia EN/ES.
- Medir bytes antes/después; no introducir tokenizer ni nueva dependencia.

**Salida:** payload predecible para monorepos y metadata explícita de truncación.

## PR 4: snapshot multi-agente

- Escribir `.agents/git-snapshot.md` cuando existe layout canónico.
- Mantener `.claude/git-snapshot.md` como fallback legacy.
- No escribir ambos archivos y no añadir flags de provider/output.
- Actualizar templates solo después de aprobación explícita, porque `share/claude/` afecta a todos los repos que ejecutan setup-agents.

**Salida:** el comando snapshot y setup-agents toman la misma decisión de layout.

## PR 5: contrato público

- Eliminar `clean --refs` en una release marcada como breaking; no implementar una operación destructiva sin demanda.
- Deprecar `update` y devolver instrucciones para Homebrew, uv o clone, sin ejecutar gestores de paquetes.

**Salida:** help, schemas y referencia dejan de prometer comportamiento inexistente.

## PR 6: verdad documental y foco

- Hacer que CI valide versión, comandos, dependencias, tests e i18n del roadmap.
- Reescribir README y demo alrededor de cinco flujos: onboarding, agente en worktree, commit seguro, mantenimiento y PR/CI.
- Corregir ROADMAP, SECURITY, CONTRIBUTING, `pr create`, PowerShell ES y flags legacy del demo.

**Salida:** cero flags públicos `not_implemented` y cero contradicciones verificables en documentos principales.

## No se prioriza

- Nuevos comandos, adapters, formatos o modos de diff.
- TUI, fzf, plugins, manpages o wrapper de `git add`.
- Retirar `health`, `suggest`, `snapshot` o wrappers con consumidores desconocidos.
- Cambiar pesos de `health`; queda congelado hasta decidir si se integra en `audit` con evidencia de usuarios.
- Archivar historia antes de corregir README y contratos actuales.
- Cambiar bots de release o soporte Windows dentro de este tren.

## Gate

Cada PR debe pasar tests focales, suite completa, coverage >=75%, ruff, formato, basedpyright, pip-audit y checks documentales. El tren termina con `/multi-review` sobre CLI/DX, seguridad, contratos JSON, compatibilidad y documentación.

El plan de ejecución detallado, con tests rojos, archivos y comandos exactos, está en `.agentskills/tasks/2026-07-22-maximize-gitwise-utility/plan.md`.
