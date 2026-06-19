# Roadmap: salida para agentes AI + mejoras de `status` y `diff`

Source: docs/plans/agent-output-status-diff-roadmap.md
Last sync: 2026-05-29

[English](../../plans/agent-output-status-diff-roadmap.md) | [Espanol](agent-output-status-diff-roadmap.md)

Estado: vivo · Última actualización: 2026-05-28 · Rama de arranque: `feat/unified-loading-feedback`

Este documento captura el análisis completo de tres revisiones relacionadas para que
no se pierda la información:

1. Sistema de loading/feedback unificado (implementado).
2. Mejoras de capacidad de `gitwise status` y `gitwise diff` vs git nativo.
3. Mejores formatos de salida `--json` para que los agentes AI las entiendan mejor.

Propósito rector de gitwise: **simplificar comandos, mejorar la DX, mejorar la seguridad
y mejorar el workflow con agentes de AI.** Toda mejora aquí se justifica contra esos pilares.

---

## 1. Loading/feedback unificado — IMPLEMENTADO

Patrón: context manager `status(message)` en `gitwise/output.py`.

- Gate global de modo JSON: `set_json_mode(bool)` en `output.py`, cableado en
  `__main__.py:main()` tras resolver `args.json`. `status()` es no-op cuando JSON está
  activo. **Regla:** el loading se muestra siempre en modo humano y se suprime SOLO con
  `--json` / `--json-pretty` (no por mera detección de TTY).
- Spinner añadido a: `status`, `summarize`, `diff`, `log`, `show`, `branches`, `suggest`,
  `context`, `health`, `snapshot`, `worktree`, `conflicts`, `pr` (helper `_gh`), `stash`
  (list/show), `tag` (list), `doctor`, `clean` (scan). Ya lo tenían: `sync`, `optimize`,
  `audit`.
- Claves i18n nuevas: `status_reading_status`, `status_summarizing`, `status_reading_diff`,
  `status_reading_log`, `status_loading_commit`, `status_analyzing_branches`,
  `status_analyzing_staged`, `status_detecting_conflicts`, `status_reading_stashes`,
  `status_reading_tags`, `status_querying_github`, `status_checking_env`,
  `status_scanning_stale`, `status_worktree_add`, `status_health_scan`,
  `status_context_scan`, `status_snapshot_gen`, `status_updating`.

Comandos mutantes (`commit`, `merge`, `undo`, `pick`, `setup`, `setup-agents`) NO llevan
spinner envolvente: ya imprimen su plan/confirmación/resultado en vivo y un spinner
chocaría con los prompts.

---

## 2. `gitwise status` vs `git status` — gaps y propuestas

### Gaps de paridad (incluso vs git nativo)

| # | Gap | Pilar | Estado |
|---|-----|-------|--------|
| S1 | **Operación en curso** (merge/rebase/cherry-pick/revert/bisect) no se detecta. Un agente puede commitear en medio de un rebase. Detectar `MERGE_HEAD`, `rebase-merge/`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `BISECT_LOG` → exponer `in_progress: "rebase"`. | Seguridad+Workflow+AI | pendiente |
| S2 | **Conflictos/unmerged** no son categoría propia. `status.py` clasifica con `ln[0]/ln[1]` y mezcla `UU/AA/DD` dentro de staged/unstaged. Necesita categoría explícita `conflicted`. | Seguridad+AI | pendiente |
| S3 | **JSON lossy:** `files: [rutas]` sin código de estado. El agente recibe `unstaged: 21` y una lista plana, no sabe cuál es staged/untracked/conflictivo. Debe ser `files: [{path, code, status, staged}]`. | AI workflow | pendiente (parte de 4 FileEntry) |

### Mejoras de DX/orientación (menor prioridad)

- Nombre del upstream (no solo ahead/behind, sino `origin/main`).
- Último commit (hash + subject) para orientar al agente.
- Conteo de stashes.
- Hints accionables en humano: "tienes cambios staged → `gitwise commit`".
- Renames estructurados (`old → new`) en vez de la línea porcelain cruda.

---

## 3. `gitwise diff` vs `git diff` — gaps y propuestas

| # | Mejora | Pilar | Estado |
|---|--------|-------|--------|
| D1 | **Comparar refs/ramas/rangos arbitrarios.** Hoy `diff.py:_diff_cmd` siempre compara vs `HEAD` o `--staged`. No hay `gitwise diff <ref>`, `diff main..HEAD`, `diff <a> <b>`. Obliga a caer a git nativo. | Simplificar+DX | pendiente |
| D2 | **Acotar a paths:** `gitwise diff -- <path>`. | DX | pendiente |
| D3 | **Escaneo de secretos en el diff** (API keys, tokens, `.env`, claves privadas) antes de commit. No existe en git; encaja con seguridad + evitar que un agente filtre credenciales. Feature diferenciador. | **Seguridad** | pendiente |
| D4 | **Aviso de archivos grandes/binarios** (candidatos a LFS). Ya detecta binarios (`diff.py:127`); extender a tamaño. | Seguridad/Workflow | pendiente |
| D5 | **Resumen compacto para AI** (`--summary`): archivos + ± por hunk, sin volcar el patch entero → ahorra tokens. | AI (tokens) | pendiente |

---

## 4. Formato `--json` para agentes AI

**Decisión de formato:** mantener JSON como formato canónico (los LLMs lo parsean más
fiable que YAML/TOML/tablas). NO cambiar de formato. Única adición que vale la pena:
**NDJSON (JSON Lines)** opcional para listas grandes (`log`, `diff --full`) → procesamiento
incremental y truncado por tokens.

### Problemas detectados (con evidencia real, pre-fix)

| # | Problema | Ejemplo real | Severidad | Estado |
|---|----------|--------------|-----------|--------|
| J1 | **Tipos como strings** | `branches`: `"current":"false"` (truthy!), `"ahead":""` | crítico | **HECHO** |
| J2 | **Envelope inconsistente** | `status` mete `v/ok` al inicio; `diff`/`health` al final; `summarize` usa `v:3` | alto | pendiente |
| J3 | **3 formas para "archivos cambiados"** | status `["ruta"]`, diff `[{...}]`, summarize `{"ruta":"M"}` | alto | pendiente (FileEntry único) |
| J4 | **Empty string en vez de null** | `branches`: `"upstream":""` | medio | **HECHO** (ahora `null`) |
| J5 | **Códigos crudos sin normalizar** | `M`, `??`, `UU` sin etiqueta legible | medio | **HECHO en diff** (`status_label`); pendiente en status/summarize |
| J6 | **Fechas en formato local inconsistente** | `tag`: `-0500` y `+0000` mezclados | medio | **HECHO** (ISO-8601 strict) |
| J7 | **Colecciones como string** | `log`: `"parents":"hash1 hash2"` (debe ser array), `"stats":""` | medio | pendiente |
| J8 | **Redundancia que gasta tokens** | `diff` repite `changes`, `graph`(ASCII), `lines_changed`, `insertions`, `deletions` | bajo | pendiente |
| J9 | **Falta metadata de truncamiento + next-actions** | sin `truncated`/`total`; sin `next_actions` machine-readable | DX agentes | pendiente |

### Esquema canónico propuesto (objetivo, requiere `v3`)

```json
{
  "v": 3,
  "ok": true,
  "command": "status",
  "data": { "...payload específico..." },
  "hints": ["gitwise commit"],
  "errors": []
}
```

- `errors` siempre presente (vacío si ok), forma `[{code, message, hint}]` — ya existe en
  `error_envelope` (`utils/json_envelope.py`), hay que universalizarlo.
- Tipos correctos, `null` explícito, fechas ISO-8601.
- **`FileEntry` único** reutilizado por status/diff/summarize:
  `{"path", "old_path"?, "code", "status", "staged": bool, "insertions"?, "deletions"?, "binary": bool}`.

**Nota de compatibilidad:** J2/J3 rompen la forma del envelope actual → subir a `v3`,
actualizar el catálogo `gitwise schema` y los tests. Por eso quedan para un PR mayor versionado.

---

## 5. Lo implementado en esta tanda (bloque de bajo riesgo, backward-compatible)

- **J1 — tipos correctos** en `branches.py`: nuevo `TypedDict BranchEntry`.
  `current`/`in_worktree` → `bool`; `ahead`/`behind` → `int | None`;
  `upstream`/`tracking` → `str | None`. Helper `_parse_track_count`.
- **J4 — null explícito** en `branches` (`upstream`/`tracking`/`ahead`/`behind`).
- **J5 — etiqueta normalizada** `status_label(code)` en `utils/git_output.py`
  (M→modified, ??→untracked, UU→conflicted, ...). Aplicado a `diff --json`
  (`status_label` junto al `status` crudo).
- **J6 — fechas ISO-8601 strict**: `log` (`--date=iso-strict`) y `tag`
  (`creatordate:iso-strict`). Resultado: `2026-05-15T09:59:35-05:00`.

**Cambio incompatible (explícito):** el cambio de tipos en `branches` (string `"false"`/`""`
→ `bool`/`int`/`null`) NO es backward-compatible para un consumidor que fijó `v:2` y comparaba
strings (p.ej. `entry["current"] == "false"`, antes truthy, ahora un bool falsy). El campo `v`
sigue siendo `2`. Como el proyecto es pre-1.0 y aún no hay contrato de output-schema por
comando, esta tanda lo marca aquí y en el PR/CHANGELOG en vez de subir solo `branches` (lo que
empeoraría la divergencia de `v` entre comandos, J2). El versionado completo del envelope
(`v3` en todos los comandos) es el PR futuro documentado.

`status.ahead_commits`/`behind_commits` se emiten como objetos estructurados
`[{hash, short_hash, subject}]` (consistente con `log --json`), no strings "hash subject".

Enum estable `status_label`: `modified | added | deleted | renamed | copied | type_changed |
conflicted | untracked | ignored | unknown` (`utils/git_output.py`). Aún sin catálogo de
output-schema descubrible — ver item pendiente abajo.

Además en esta tanda (no es cambio de JSON): `update` ahora detecta la falta de upstream con
un error accionable (`code: no_upstream` + hint) en vez del error crudo de git, y usa el
spinner de loading.

### Hardening pendiente detectado por el review

- **Catálogo de output-schema (M1):** `share/schemas/v1/` es solo INPUT; no hay catálogo
  `output/`, así que los agentes no pueden descubrir enums como `status_label`. Añadir
  `share/schemas/v1/output/` + flag `gitwise schema <cmd> --output` (entra en el PR `v3`).
- **Higiene de escapes de terminal (global):** nombres de rama / refs se imprimen verbatim en
  salida humana en varios comandos (`status`, `branches`, `update`); un nombre de rama con
  caracteres de control ANSI es un vector (bajo) de inyección de terminal (CWE-150). Arreglar
  centralizado en la capa de output, no por comando.
- **`log.parents`/`log.stats` como strings (J7):** siguen siendo string; entra en `v3`.

---

## 6b. Veredicto del multi-review (panel 33+ perfiles, respaldado por docs oficiales)

Una revisión multi-perspectiva a máxima profundidad (seguridad, arquitectura/Python,
QA/test-arch, DX/consumidor-AI/docs) validó esta tanda. Hallazgos reales, fixes aplicados:

- **HIGH — bug de timeout en `git.run` (corregido):** `_get_timeout` usaba `args[0]`; con un
  `--no-pager` inicial caía al default de 120s en vez del timeout por-comando. Corregido en
  `gitwise/git.py` para tomar el primer arg sin guion — repara los nuevos sitios de status.py
  Y los pre-existentes con `--no-pager` (diff/summarize/snapshot).
- **HIGH — commits ahead/behind estructurados (corregido):** ahora `[{hash, short_hash, subject}]`.
- **MEDIUM — doble spinner en suggest.py (corregido):** consolidado en un solo spinner.
- **CRITICAL — cambio incompatible de tipos en `branches`:** reconocido y documentado (ver 5);
  los tipos son correctos, el break se marca para el PR/CHANGELOG, `v3` completo diferido.
- **LOW — flicker del spinner** en comandos sub-100ms y **higiene de escapes de terminal**:
  documentados como pendientes.

**Propuesta pytest-xdist — veredicto: SEGURO-CON-CONDICIONES.** Los docs oficiales de
`pytest-cov` confirman que xdist `--dist load` combina la cobertura por worker y "cada worker
mide sus subprocesos", así que `--cov` + `patch=["subprocess"]` funciona bajo `-n`. El
aislamiento de tests se sostiene (`tmp_path` por test, `GIT_CONFIG_GLOBAL/SYSTEM=/dev/null`,
sin estado compartido). Condiciones antes de adoptar:
1. Pre-push: `-n auto --maxprocesses=4` (o `-n 4`) para no saturar el laptop; CI: `-n 2`.
2. Añadir `parallel=true` a `[tool.coverage.run]`.
3. Arreglar dos tests de tiempo que se vuelven flaky en paralelo: `test_audit_quick_under_5s`
   y el test de mtime de `test_snapshot`.
4. Palanca complementaria de mayor ROI: convertir tests de lógica pura a llamadas in-process
   (el costo dominante son ~440 spawns de subprocess × import completo de Python+rich).

## 6. Orden de ataque sugerido para lo pendiente

1. **status S1 + S2 + S3** (un solo módulo, altísimo valor agentes): operación en curso,
   conflictos, JSON con FileEntry por archivo.
2. **diff D1 + D2** (refs/rangos + paths): cierra el gap de capacidad core.
3. **diff D3** (escaneo de secretos): feature de seguridad diferenciador.
4. **Envelope v3** (J2 + J3 + J7 + J9): rediseño versionado con FileEntry único,
   `next_actions`, metadata de truncamiento, colecciones como arrays. Actualizar
   `gitwise schema` + tests.
5. **NDJSON** opcional para `log` / `diff --full`.
