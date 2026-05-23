# Plan de refactor `gitwise setup-agents`: de Claude-centric a AI agents-first

Source: docs/plans/setup-agents-ai-agents-first.md
Last sync: 2026-05-22

[English](../../plans/setup-agents-ai-agents-first.md) | [Espanol](setup-agents-ai-agents-first.md)

## Estado del documento

- Fecha: 2026-05-22
- Estado: Aprobado para implementacion
- Alcance: diseno + rollout + riesgos + pruebas + criterios de aceptacion
- Regla de ejecucion: no empezar implementacion fuera de este plan

---

## Objetivo

Convertir `gitwise setup-agents` en un comando claramente orientado a agentes AI con este modelo:

1. Canonico por defecto: `AGENTS.md` + `.agents/skills/`
2. Proveedores (Claude/Cursor/etc.) como capa opcional y explicita
3. Compatibilidad controlada con usuarios existentes

---

## Problema actual (baseline verificado)

Hoy `setup-agents` sigue acoplado al layout Claude:

- Narrativa publica centrada en Claude (`README.md`, `README.es.md`, `pyproject.toml`)
- Help de CLI centrado en `~/.claude/` como default (`gitwise/__main__.py`)
- Planner local/global agrega artefactos `.claude/*` de forma estructural (`gitwise/setup_agents/plan.py`)
- Skills provenientes de `share/claude/skills/*` (`gitwise/setup_agents/plan_skills.py`)
- Adapters implementados como extras post-plan (`gitwise/_cli_setup_agents.py`)

Tambien existe deuda tecnica:

- Rollback parcial ante fallos: no revierte todos los tipos de accion (`gitwise/setup_agents/exec.py`)
- Inconsistencias semanticas de flags y UX (`--replace-claude-with-symlink`, multiples `--no-*`)

---

## Decisiones finales

### D1) Arquitectura objetivo

- Base canonica: `AGENTS.md` + `.agents/skills/*`
- Claude pasa a ser provider explicito
- Otros providers siguen opcionales (`cursor`, `continue`, `opencode`, `codex`, `aider`, `pi`)

### D2) Compatibilidad y rollout

- Rollout incremental en 3 PRs
- Sin cambio directo de default en un solo PR
- Sin desactivar suite legacy completa durante transicion

### D3) Flags

- Mantener `--adapters`
- Agregar `claude` como provider explicito
- Deprecar `claude-only` por 2 minors y alias a `claude` (NO a `none`)

### D4) Contrato JSON

- Pasar a `v=3` en cambio de comportamiento
- Mantener `v_compat` para consumidores existentes
- Mantener `bucket` durante ventana de compatibilidad con semantica documentada

### D5) Auto-deteccion

- Fuera de alcance en este refactor
- Providers siguen siendo opt-in explicito

---

## No objetivos

- No agregar auto-deteccion de providers
- No romper uso existente de `--adapters`
- No eliminar rutas legacy sin migracion
- No enviar un mega-PR sin checkpoints

---

## Diseno tecnico aprobado

## 1) Modelo canonico + providers

### Capa canonica

- `AGENTS.md` como documento principal de convenciones
- `.agents/skills/<skill>/SKILL.md` como ubicacion canonica de skills

### Capa provider

- Claude y otros providers crean sus artefactos solo si estan habilitados
- Cuando aplique, providers linkean o referencian artefactos canonicos

---

## 2) Reglas de compatibilidad de aliases

- `--adapters none`: modo canonico puro (sin providers)
- `--adapters claude`: habilita provider Claude
- `--adapters claude-only`: deprecado, tratado como `claude`
- `--adapters cursor,aider`: habilita solo los providers listados

---

## 3) Seguridad y rollback (obligatorio antes del cambio de default)

### Riesgo critico actual

`_undo_partial()` no revierte completamente managed-block, append, merge y acciones relacionadas.

### Accion requerida

Antes de cambiar default a canonico:

1. Guardar estado previo de todos los archivos mutados
2. Asegurar rollback completo por tipo de accion
3. Cubrir con pruebas de fallo intermedio

Sin esto, el PR de cambio de comportamiento queda bloqueado.

---

## Plan de implementacion (3 PRs)

## PR #1 - Foundations + bugfixes (sin cambio de comportamiento)

### Objetivo

Preparar arquitectura de providers sin cambiar comportamiento esperado para usuarios actuales.

### Cambios

1. Corregir claves i18n inconsistentes en `plan.py`:
   - usar `claude_md_symlink_other` y `claude_md_replaced`
2. Refactor minimo del sistema de adapters para soportar estrategia por provider
3. Renombrar namespace interno de `setup_agents/adapters` a `setup_agents/providers` con shims backward-compatible en `adapters/`
4. Introducir `providers/claude.py` como wrapper inicial (sin mover toda la logica todavia)
5. Agregar pruebas de regresion para bug i18n
6. Registrar `claude` en el registry de providers (sin cambio de comportamiento)

### Criterios de aceptacion

- Salida funcional equivalente en escenarios actuales
- Tests existentes + nuevos tests de regresion en verde

---

## PR #2 - Canonical switch + schema v3 (cambio controlado)

### Objetivo

Habilitar canonical-first con compatibilidad explicita por providers.

### Cambios

1. Reorganizar templates:
   - mover skills canonicas a `share/agents/skills/*`
   - mantener templates provider-specific donde aplique
2. Refactor de planning:
   - planner canonico primero
   - planner por providers despues
3. Refactor de skills:
   - canonico siempre en `.agents/skills/`
   - links/copias provider-specific gestionados por adapter
4. Permitir adapters tambien en modo global
5. Actualizar `format.py` a `v=3` con campos discriminadores (`canonical_layout`)
6. Agregar warnings legacy claros y no destructivos
7. Actualizar docs y narrativa publica

### Criterios de aceptacion

- En repo limpio, `setup-agents --local --yes` crea layout canonico sin depender de Claude
- `--adapters claude` mantiene experiencia Claude equivalente
- Contrato JSON documentado y testeado

---

## PR #3 - Migracion legacy + cleanup

### Objetivo

Cerrar la transicion para usuarios con layout antiguo Claude-only.

### Cambios

1. Agregar flujo de migracion legacy (`--migrate-legacy-claude`)
2. Reusar accion existente `skill-migrate-to-agents` con idempotencia
3. Publicar guia `docs/MIGRATION-0.17.md`
4. Mantener deprecacion de `claude-only` por 2 minors

### Criterios de aceptacion

- Migracion legacy funciona en dry-run y ejecucion real
- Re-ejecucion idempotente

---

## Estrategia de testing

## Regla clave

No se permite skip masivo de suite legacy en PR #2.

Se usa cobertura dual temporal:

- mantener cobertura legacy relevante
- agregar suite v3 con matriz canonical + providers

## Matriz minima obligatoria

1. Local empty repo, sin adapters
2. Local empty repo, con `claude`
3. Local empty repo, multi-adapter
4. Local con artefactos legacy Claude
5. Modo global, sin adapters
6. Modo global, con `claude`
7. Falla intermedia de ejecucion para validar rollback completo

---

## Archivos objetivo (implementacion)

- `gitwise/setup_agents/plan.py`
- `gitwise/setup_agents/plan_skills.py`
- `gitwise/setup_agents/state.py`
- `gitwise/setup_agents/exec.py`
- `gitwise/setup_agents/plan_gitfiles.py`
- `gitwise/setup_agents/types.py`
- `gitwise/setup_agents/format.py`
- `gitwise/setup_agents/providers/base.py`
- `gitwise/setup_agents/providers/__init__.py`
- `gitwise/setup_agents/providers/claude.py` (nuevo)
- `gitwise/setup_agents/adapters/*` (shims de compatibilidad)
- `gitwise/_cli_setup_agents.py`
- `gitwise/__main__.py`
- `gitwise/_i18n_data.json`
- `share/agents/skills/*` (nueva ubicacion canonica)
- `README.md`, `README.es.md`
- `docs/reference/commands.md`, `docs/es/reference/commands.md`
- `docs/MIGRATION-0.17.md` (nuevo)
- tests relacionados

---

## Criterios de release

## Gate tecnico

- `uv run pytest`
- `ruff check gitwise/ tests/`
- `ruff format --check gitwise/ tests/`
- `uv run basedpyright`

## Gate funcional

- Smokes local/global segun matriz minima
- Comportamiento de deprecacion validado (`claude-only`)
- Salida JSON v3 validada

## Gate documental

- README EN/ES actualizado
- Command reference EN/ES actualizado
- Migration guide publicada
- CHANGELOG/CHANGELOG.es con notas de transicion

---

## Riesgos abiertos y mitigaciones

1. Rollback incompleto -> bloquear PR #2 hasta cerrar rollback transaccional
2. Rotura de consumidores JSON -> schema v3 + compat + tests de contrato
3. Friccion UX por flags -> mantener `--adapters`, deprecacion gradual y mensajes claros
4. Drift de providers -> fuente canonica unica + links gestionados por adapter

---

## Checklist de inicio de implementacion

- [x] Objetivo y alcance cerrados
- [x] Decisiones tecnicas cerradas
- [x] Plan por PR definido
- [x] Estrategia de compatibilidad definida
- [x] Riesgos criticos identificados
- [x] Criterios de aceptacion y release definidos
- [x] Implementacion PR #1 iniciada
