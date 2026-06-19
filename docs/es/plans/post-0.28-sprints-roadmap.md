# Roadmap: sprints post-0.28 — seguridad, capacidades, contratos, pulido

Source: docs/plans/post-0.28-sprints-roadmap.md
Last sync: 2026-06-19

[English](../../plans/post-0.28-sprints-roadmap.md) | [Espanol](post-0.28-sprints-roadmap.md)

Estado: vivo · Última actualización: 2026-06-19 · Origen: sesión de revisión del merge `feat/loading-feedback-integration`

Este documento es el plan hacia adelante que emergió de una multi-review a
profundidad máxima del merge `feat/loading-feedback-integration` (la rama que
se convirtió en v0.28.0). El plan hermano
[`agent-output-status-diff-roadmap.md`](./agent-output-status-diff-roadmap.md)
captura lo que ese PR entregó y lo que diferió explícitamente. Este documento
captura los cuatro sprints que retoman esos pendientes más los gaps que la
revisión encontró fuera del alcance original.

Propósito rector de gitwise (sin cambios): **simplificar comandos, mejorar el
DX, mejorar la seguridad y mejorar el flujo con agentes IA.** Cada sprint se
justifica contra esos pilares.

---

## Cómo está organizado este plan

Cada sprint es una unidad del tamaño de un PR con: objetivo, archivos tocados
(con anclas `file:line` actuales), pilares, estado de cambios rompedores,
criterios de salida y dependencias con sprints previos. Los sprints se
secuencian poniendo seguridad primero (anti-corrupción), luego gaps de
capacidad, luego rediseño de contratos, luego pulido.

Todas las referencias a archivos son baselines pre-0.28 verificadas con
`verify-before-implement` contra el árbol mergeado el 2026-06-19.

---

## Sprint 1 — Seguridad en operaciones en curso y endurecimiento i18n

**Objetivo:** evitar que un agente commitee a mitad de un merge/rebase/
cherry-pick, y hacer que la paridad i18n sea exigible por locale.

**Por qué primero:** un commit a mitad de rebase corrompe el estado del
repositorio silenciosamente. Es el único sprint cuya ausencia es un riesgo
activo de pérdida de datos, no solo un gap de capacidad.

### Ítems de trabajo

| ID | Ítem | Anclas | Pilar | Esfuerzo |
|----|------|--------|-------|----------|
| S1 | Detectar operaciones en curso y exponerlas | nuevo `gitwise/utils/in_progress.py` (helper); integrar en `gitwise/status.py` (nuevo campo JSON `in_progress`) | Seguridad + Workflow | pequeño |
| G2 | Proteger `suggest` y `commit` contra estado en curso | `gitwise/suggest.py:112` (`run_suggest`), `gitwise/commit.py:97` (`run_commit`) | Seguridad | trivial (reusa helper de S1) |
| G1 | Subcomandos `merge --abort` y `merge --continue` | `gitwise/merge.py:146` (`run_merge`); añadir flags `abort`/`continue` | Simplificar | pequeño |
| G6 | Test de paridad i18n (ya entregado en 0.28.0) | `tests/test_i18n.py::test_all_keys_have_es_and_en_translations` | Calidad | hecho |

### Contrato de detección S1

`detect_in_progress(root: Path) -> InProgressState` donde `InProgressState` es
un TypedDict `{"state": Literal["none","merge","rebase","cherry-pick","revert","bisect"], "ref": str | None}`.

La detección lee artefactos de `.git/` (sin costo de porcelain):
- `MERGE_HEAD` → `merge`
- `.git/rebase-merge/` o `.git/rebase-apply/` → `rebase`
- `CHERRY_PICK_HEAD` → `cherry-pick`
- `REVERT_HEAD` → `revert`
- `.git/BISECT_LOG` → `bisect`

`status --json` gana `in_progress: InProgressState` (aditivo, sin bump de
`v`). `suggest` y `commit` se rehúsan con un error claro + pista accionable
cuando `state != "none"`.

### Criterios de salida

- Tests nuevos: `test_in_progress_*` por estado; `test_suggest_refuses_during_merge`;
  `test_commit_refuses_during_rebase`; `test_merge_abort` / `test_merge_continue`.
- Los cuatro `scripts/docs/check_*` pasan (baseline ajustado en ROADMAP).
- Sin marcador BREAKING CHANGE nuevo en ningún footer de commit (todo aditivo
  o protegido por detección).

### Dependencias

Ninguna. Este sprint puede aterrizar inmediatamente después de 0.28.0.

### Impacto en release

Commits tipo `fix:` → bump de patch `0.28.x → 0.28.(x+1)` salvo que un commit
`feat:` (p.ej. `--abort`/`--continue` como flags nuevos) rote minor.

---

## Sprint 2 — Paridad de capacidades de diff y escaneo de secretos

**Objetivo:** cerrar los dos gaps de capacidad más grandes vs git nativo
(`diff <ref>`, `diff -- path`) y entregar un feature de seguridad
diferenciador (escaneo de secretos antes del commit).

### Ítems de trabajo

| ID | Ítem | Anclas | Pilar | Esfuerzo |
|----|------|--------|-------|----------|
| D1 | `gitwise diff <ref>`, `diff a..b`, `diff a...b` | `gitwise/diff.py:146` (`_diff_cmd` solo soporta `staged/name_only/full` hoy) | Simplificar + DX | mediano |
| D2 | `gitwise diff -- <path>` (scope por path) | `gitwise/diff.py:146` | DX | pequeño |
| D3 | Escaneo de secretos en diff y como pre-check de commit | nuevo `gitwise/utils/secret_scan.py`; integrar en `diff.py`, `suggest.py:112`, `commit.py:97` | **Seguridad** (diferenciador) | mediano-grande |
| D4 | Aviso de archivo grande/binario (candidatos LFS) | `gitwise/diff.py:127` (ya detecta binarios; extender a tamaño) | Workflow | pequeño |
| D5 | `gitwise diff --summary` (resumen compacto para IA, ± por hunk, sin patch completo) | `gitwise/diff.py` (nueva ruta de render) | IA (tokens) | pequeño |

### Contrato de escaneo de secretos D3

Nuevo `secret_scan(diff_text: str) -> list[Finding]` donde `Finding` es
`{"rule": str, "path": str, "line": int, "preview": str, "severity": "high"|"medium"}`.

Ruleset inicial (patrones verificados, sin falsos positivos en fixtures):
- AWS access key: `AKIA[0-9A-Z]{16}` (Verificado: AWS docs §IAM identifiers)
- AWS secret: base64 de 40 chars tras `aws_secret_access_key`
- GitHub PAT clásico: `gh[pousr]_[A-Za-z0-9]{36}` (Verificado: GitHub blog
  2021-04-12 cambio de formato de token clásico). Los PATs fine-grained usan
  un formato distinto `github_pat_[A-Za-z0-9_]{82}` y necesitan una regla
  separada.
- GitLab PAT: `glpat-[A-Za-z0-9_-]{20}` (Verificado: GitLab docs §Personal
  access tokens)
- Bloque de private key: `-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----`
- Asignación `.env`: `^[A-Z_]+=(https?://|\S+@)` tras header de archivo `.env`

Salida: `gitwise diff --scan-secrets --json` devuelve findings; exit no-cero
en `severity=high`. `gitwise commit` corre el escaneo por defecto y se rehúsa
ante hallazgos high a menos que se pase `--allow-secret` (con confirmación).

### Criterios de salida

- `test_diff_ref_*`, `test_diff_path_scope`, `test_secret_scan_*` (por regla
  + por fixture limpio).
- Tasa de falsos positivos documentada objetivo: 0 sobre el corpus de tests
  del proyecto.
- Baseline del ROADMAP ajustado; scripts de check en verde.

### Dependencias

Ninguna dura. D3 se integra naturalmente con los guards del G2 del Sprint 1
(se rehúsa a commitear en operación en curso + se rehúsa ante leak de
secreto — misma capa de guard).

### Impacto en release

Commits tipo `feat:` → bump minor `0.28.x → 0.29.0`.

---

## Sprint 3 — Envelope v3 (rediseño de contrato)

**Objetivo:** unificar el envelope `--json` para que los consumidores puedan
parsear cada comando con un único schema, y publicar schemas de salida para
que los agentes los autodescubran.

**Por qué tercero, no primero:** este es el sprint más grande (~1500 líneas,
todos los comandos tocados) y entrega un cambio rompedor real. Hacerlo antes
de S1/S2 forzaría retrabajo (S1 añade `in_progress` al JSON de status; hacer
eso en v2 y luego migrar a v3 es churn desperdiciado).

### Ítems de trabajo

| ID | Ítem | Anclas | Pilar | Esfuerzo |
|----|------|--------|-------|----------|
| J2 | Envelope canónico `{"v":3,"ok","command","data","hints","errors"}` | `gitwise/utils/json_envelope.py` (reescribir); los 27 comandos | Workflow IA | grande |
| J3 | Único `FileEntry` compartido por status/diff/summarize | `gitwise/status.py:58`, `gitwise/diff.py`, `gitwise/summarize.py` | Workflow IA | mediano |
| J7 | Colecciones como arrays: `log.parents`, `log.stats` | `gitwise/log.py:101` (`parents: lines[6]` string), `:133` (`stats: ""` string) | Workflow IA | pequeño |
| J9 | Metadatos `truncated`, `total`, `next_actions` | todos los envelopes | DX agentes | mediano |
| S2 | `conflicted` como categoría de status de primera clase | `gitwise/status.py:30-32` (mezcla UU/AA/DD en staged/unstaged) | Seguridad + IA | pequeño |
| S3 | JSON por archivo con code/stage/binary en status | `gitwise/status.py:58` (`files: [paths]` con pérdida) | Workflow IA | pequeño |
| M1 + G5 | Catálogo de schemas de salida `share/schemas/v1/output/` + `gitwise schema <cmd> --output` | `share/schemas/v1/output/` (no existe); `gitwise/_cli_dispatch.py:422` | Workflow IA | mediano |

### Contrato del envelope v3

```json
{
  "v": 3,
  "ok": true,
  "command": "status",
  "data": { "..." },
  "hints": ["gitwise commit"],
  "errors": []
}
```

- `errors` siempre presente (vacío si ok); shape `[{code, message, hint}]`.
  Ya existe como `error_envelope` en `utils/json_envelope.py`; se vuelve
  universal across comandos.
- `FileEntry`: `{"path","old_path"?,"code","status","staged":bool,
  "insertions"?,"deletions"?,"binary":bool}` — mismo shape en status/diff/
  summarize.
- Fechas ISO-8601 strict en todos lados (ya entregado para log/tag en 0.28.0).

### Cambio rompedor

Real, intencional, documentado. El footer del commit del PR lleva el marcador
BREAKING CHANGE listando cada renombre/cambio de shape por comando. Con
`major_version_zero=true` esto rota el minor `0.29.x → 0.30.0`. La sección del
CHANGELOG `### Breaking Changes` lista el delta de cada comando.

### Criterios de salida

- `share/schemas/v1/output/<command>.json` por cada comando (~27 archivos).
- `gitwise schema <cmd> --output` imprime el schema de salida.
- Cada test `--json` de cada comando actualizado al nuevo envelope; nuevos
  tests afirman invariantes de shape del envelope en un solo lugar
  (`tests/test_envelope_contract.py`).
- Nota de migración en CHANGELOG con ejemplos JSON antes/después.

### Dependencias

Dura: debe venir después del Sprint 1 (el campo in-progress se estabiliza
primero en v2). Suave: mejor después del Sprint 2 (D1 añade nuevos args de
diff que v3 absorbe limpiamente).

### Impacto en release

`feat!:` con footer BREAKING → bump minor `0.29.x → 0.30.0`.

---

## Sprint 4 — Pulido DX

**Objetivo:** llenar los gaps UX restantes e ítems de paridad Windows. Prioridad
más baja; entregar después de que los contratos se estabilicen para que el
pulido no se retrabaje.

### Ítems de trabajo

| ID | Ítem | Anclas | Pilar | Esfuerzo |
|----|------|--------|-------|----------|
| G3 | Subcomando `gitwise worktree list` | `gitwise/worktree.py:21` (`_list_worktrees` es helper interno únicamente) | DX | pequeño |
| G4 | `conflicts --union` y detección de conflictos semánticos | `gitwise/conflicts.py:31` (`_resolve_all_conflicts` solo ours/theirs) | Simplificar | mediano-grande |
| G7 | Completion para PowerShell | `gitwise/_cli_completions.py:1` (bash/zsh/fish hoy; el installer Windows se entregó en 0.27.0) | Paridad Windows | mediano |
| P10 (D4+D5 plegado) | Aviso binario + `diff --summary` | se arrastra del Sprint 2 si no se recoge | DX + IA | pequeño |
| NDJSON | `log --json-lines` y `diff --full --json-lines` para procesamiento incremental | `gitwise/log.py`, `gitwise/diff.py` | IA (tokens) | mediano |

### Criterios de salida

- `test_worktree_list`; `test_conflicts_union`; `test_completion_powershell`
  (smoke test de generación de script); `test_log_ndjson`.
- Completion de PowerShell documentado en README + sección de install Windows.

### Dependencias

Ninguna dura. G3/G4 independientes. G7 independiente. NDJSON absorbe el
envelope v3 del Sprint 3.

### Impacto en release

Mixto `feat:` / `chore:` → minor o patch según el tipo de commit dominante
en el sprint.

---

## Transversal: verificación y orden

### Orden recomendado

1. **Sprint 1** — anti-corrupción primero (único sprint con riesgo de pérdida
   de datos).
2. **Sprint 2** — paridad de capacidad + diferenciador de seguridad.
3. **Sprint 3** — rediseño de contrato (absorbe adiciones de S1/S2 limpiamente).
4. **Sprint 4** — pulido (cabalga sobre el contrato v3 estable).

### Riesgos de orden fuera de secuencia

- **Sprint 3 antes del Sprint 1:** el campo `in_progress` de S1 se añadiría a
  v2, para migrarse inmediatamente a v3 — churn desperdiciado y un cambio
  rompedor redundante.
- **Sprint 2 antes del Sprint 1:** la integración del escaneo de secretos D3
  colisiona con la del guard G2 en `commit.py`; hacer G2 primero da una única
  capa de guard a extender.

### Tren de releases (objetivo)

| PR | Rama | Base | Genera release |
|----|------|------|----------------|
| #1 | `feat/loading-feedback-integration` | main | 0.28.0 (BREAKING branches + log + tag) |
| #2 | `feat/in-progress-safety` | main (post 0.28.0) | 0.28.x o 0.29.0 |
| #3 | `feat/diff-refs-secret-scan` | main | 0.29.0 |
| #4 | `feat/envelope-v3` | main | 0.30.0 (BREAKING envelope) |
| #5 | `chore/dx-polish` | main | 0.30.x |

### Disciplina de verificación (aplica a cada sprint)

Cada PR de sprint debe:
1. Correr los cuatro scripts `scripts/docs/check_*` localmente antes del push
   (son la puerta del pre-push vía `lefthook.yml`).
2. Adjustar el baseline del ROADMAP (conteo de tests + conteo de keys i18n)
   en el mismo PR.
3. Citar una referencia `Verified:` en el cuerpo del PR por cualquier claim
   que dependa de comportamiento externo (disponibilidad de flag git,
   versión de librería, estado de CVE).
4. Llevar un footer BREAKING CHANGE únicamente si el sprint introduce una
   ruptura real de contrato — y listar cada ruptura, no una representativa
   (la lección v0.23.0 en `CHANGELOG.md:82-92`).
5. Abrirse como PR separado por sprint; sin merges monolito.

### Ítems explícitamente fuera de alcance

- Migrar de argparse a Typer/Click (sin dolor concreto; argparse + shtab
  funciona).
- Reescribir la capa de loading feedback en async (limitado por subprocess;
  async no da ganancia).
- Añadir un modo TUI de `gitwise` (rich ya cubre el render human-mode).
