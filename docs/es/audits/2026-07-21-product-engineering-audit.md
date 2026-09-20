# Auditoría integral de gitwise v0.34.0

Source: docs/audits/2026-07-21-product-engineering-audit.md  
Last sync: 2026-07-21  

[English](../../audits/2026-07-21-product-engineering-audit.md) | Español

**Fecha:** 2026-07-21  
**Alcance:** producto, arquitectura, seguridad, calidad, documentación, distribución y uso real  
**Estado analizado:** `main` en `30733e3`, con un cambio previo del usuario en `uv.lock`  
**Método:** inspección de código, ejecución local, metadatos públicos de GitHub, cinco análisis especializados, seis revisiones adversariales y refutación de afirmaciones contradictorias

## Veredicto ejecutivo

gitwise es técnicamente más sólido de lo que su adopción y su narrativa pública sugieren. Tiene contratos JSON consistentes en la mayoría de rutas, schemas descubribles, validación de entradas, protección GPG, escaneo de secretos, rollback transaccional en `setup-agents`, 718 pruebas, 79.82% de coverage medido y una cadena de release con buenas prácticas de supply chain.

El problema principal ya no es falta de capacidad. Es falta de foco.

El proyecto creció hasta 30 comandos, 14,476 líneas Python, 57 releases y 67 documentos Markdown antes de esta auditoría en poco más de un mes, pero su propuesta de valor sigue descrita como tres problemas estrechos y la señal pública de uso es mínima. No hay evidencia pública de que más wrappers de Git o GitHub produzcan retorno. El siguiente ciclo debe reducir ambigüedad, corregir contratos y demostrar que los flujos centrales ahorran tiempo, tokens o riesgo.

**Tesis recomendada:** gitwise debe ser una capa de control segura y legible por máquinas para flujos Git ejecutados por humanos y agentes. No debe intentar reemplazar Git ni perseguir paridad con `git` o `gh`.

**Decisión general:**

- Invertir en 7 comandos o áreas que forman flujos diferenciados: `setup-agents`, `worktree`, `summarize`, `context`, `diff`, `commit` y `audit`.
- Mantener 13 comandos estables sin ampliar su superficie.
- Consolidar 3 comandos que duplican información o etapas del mismo flujo.
- Despriorizar 6 wrappers de bajo retorno y mantenerlos en modo fix-only.
- Retirar o rediseñar 1 comando que no funciona en los canales normales de instalación.
- No añadir nuevos subcomandos hasta resolver los contratos P0 y validar uso real.

## Línea base verificada

| Métrica | Estado actual | Evidencia |
|---|---:|---|
| Versión | 0.34.0 | `pyproject.toml:1-8` |
| Comandos canónicos | 30 | `gitwise commands --json` |
| Dependencias runtime | 3 | `pyproject.toml:30-34` |
| Líneas Python | 14,476 | `rg --files gitwise -g '*.py' \| xargs wc -l` |
| Líneas de tests | 8,121 | `rg --files tests -g '*.py' \| xargs wc -l` |
| Pruebas | 718 | `uv run pytest --collect-only -q` |
| Coverage real | 79.82% | `uv run pytest --cov=gitwise --cov-fail-under=75 -n auto` |
| Schemas de entrada | 30 | `share/schemas/v1/input/` |
| Schemas de salida | 27 | `share/schemas/v1/output/` |
| Releases | 57 | `gitwise tag list --json` y GitHub Releases |
| Documentos Markdown antes de estos artefactos | 67 | `rg --files -g '*.md'` antes de crear el informe |
| Documentos bajo `docs/` antes de estos artefactos | 36 | `rg --files docs -g '*.md'` antes de crear el informe |
| Última release | v0.34.0, 2026-06-25 | GitHub CLI |
| Señal pública | 1 estrella, 0 forks, 0 issues abiertos | GitHub CLI, 2026-07-21 |
| CI reciente | verde | 20 ejecuciones consultadas con `gh run list` |
| Vulnerabilidades conocidas | 0 | `uv run pip-audit` |

Las estrellas y forks no demuestran falta de valor. Sí muestran que todavía no hay evidencia pública suficiente para justificar expansión por demanda.

## Evaluación por dimensión

| Dimensión | Evaluación | Lectura |
|---|---|---|
| Ingeniería y mantenibilidad | Fuerte | Arquitectura modular, typing limpio, tests amplios y dependencias limitadas |
| Seguridad operacional | Fuerte con gaps | Buenas defensas; quedan dos inconsistencias de subprocess y varias rutas JSON |
| Contrato para agentes | Fuerte | Envelope v3, registry, schemas y NDJSON en `diff/log` son diferenciadores reales |
| DX humano | Media | Buen render y completions, pero demasiados comandos y documentación desalineada |
| Foco de producto | Débil | El núcleo existe, pero está mezclado con wrappers de bajo valor |
| Validación de mercado | Insuficiente | No hay evidencia de uso recurrente ni métricas de ahorro o reducción de errores |

## Fortalezas reales

### 1. Contrato orientado a agentes

El envelope `{"v":3,"ok","command","data","hints","errors"}` centraliza éxito y error en `gitwise/utils/json_envelope.py:1-76`. `commands --json` permite descubrimiento, y `schema <command> --output --json` expone el contrato de salida. Hay 30 schemas de entrada y 27 de salida.

Esto es más valioso que tener wrappers bonitos. Un agente puede descubrir capacidades, validar argumentos y parsear respuestas sin depender del texto localizado.

### 2. Seguridad más allá de Git nativo

- `gitwise/git.py:18-44` limpia variables `GIT_CONFIG*`, `GIT_SSH`, `GIT_SSH_COMMAND` y `GIT_ASKPASS` antes de ejecutar Git.
- `gitwise/git.py:274-360` valida passthrough, refs y patrones regex.
- `gitwise/commit.py:134-210` bloquea secretos de alta severidad y requiere una señal fuera de banda para permitirlos en modo JSON.
- `gitwise/commit.py:63-85` limita amend en ramas protegidas o ya publicadas.
- `gitwise/utils/in_progress.py` evita commits durante merge, rebase, cherry-pick, revert o bisect.
- No se encontró `shell=True` ni `os.system` en el paquete.

Estas defensas justifican `commit`, `diff`, `worktree` y parte de `sync/merge`. Son una propuesta de valor que `git` por sí solo no entrega.

### 3. `setup-agents` resuelve un problema difícil

El paquete separa planificación y ejecución, clasifica estados, soporta siete providers y usa rollback transaccional. `_safe_create_symlink` valida el sandbox con `os.path.realpath` en `gitwise/setup_agents/exec.py:23-53`; `_execute_actions` restaura snapshots ante fallos en `gitwise/setup_agents/exec.py:445-477`.

Es el subsistema más complejo y uno de los más diferenciados. Merece inversión, pero no una expansión ilimitada de adapters.

### 4. Calidad y release por encima de la media para un CLI pequeño

- 718 pruebas pasan en macOS con 79.82% de coverage.
- CI prueba Python 3.10 a 3.14 en Ubuntu y macOS: `.github/workflows/ci.yml:89-116`.
- Windows tiene workflow propio, aunque excluye el núcleo POSIX de `setup-agents`: `.github/workflows/test-windows-installer.yml:122-147`.
- Actions están fijadas por SHA.
- PyPI usa trusted publishing, provenance y SBOM: `.github/workflows/publish-pypi.yml:13-48,57-73`.
- La automatización de release tiene guards de revert y CHANGELOG, pero conserva excepciones de firma y protección de rama que se analizan en P1.7.
- `ruff` y `basedpyright` pasan sin hallazgos.
- `pip-audit` no encontró vulnerabilidades conocidas.

### 5. Distribución y portabilidad

Hay Homebrew, PyPI/uv, instalador shell y PowerShell. Las dependencias runtime se limitan a Rich, rich-argparse y shtab. Esto mantiene bajo el coste de instalación y reduce superficie de supply chain.

### 6. Diseño bilingüe y documentación verificable

Existe paridad i18n en 548 claves, checks de links, schemas, baseline y pares EN/ES. La intención es buena y el contenido técnico tiene profundidad. El problema es selección y vigencia, no ausencia de documentación.

## Lo que está mal o debe mejorar

### P0: contratos y comportamiento observable

#### P0.1 `--json` global se pierde antes del subcomando

Reproducción:

```bash
uv run python -m gitwise --json status
```

El resultado es texto humano. En cambio, `gitwise status --json` retorna JSON.

La causa es que el parser padre registra `--json` y cada subparser vuelve a heredar el mismo padre en `gitwise/_cli_parser.py:17-50`. El default del subparser sobreescribe el valor global. `__main__.py:71-87` solo preprocesa el caso de help y `--json-pretty`.

**Impacto:** rompe scripts y agentes que usan la convención normal `tool --global-flag subcommand`.

**Decisión:** corregir antes de añadir cualquier nueva opción global.

#### P0.2 Hay rutas de error que rompen el contrato JSON

- `gitwise worktree new --json` sin branch imprime texto humano: `gitwise/worktree.py:253-256`.
- `stash drop --json` sin `--yes` imprime `warning: aborted.` sin envelope: `gitwise/stash.py:132-146`.
- `stash clear --json` tiene el mismo problema: `gitwise/stash.py:149-172`.
- `stash pop --json` imprime el stderr de Git sin envelope cuando Git falla: `gitwise/stash.py:118-129`.

**Impacto:** un consumidor debe implementar excepciones precisamente en las rutas donde más necesita estructura.

**Decisión:** añadir tests contractuales negativos para todos los comandos, no solo happy paths.

#### P0.3 `clean --refs` está publicado pero no existe

`gitwise/clean.py:73-76` devuelve `not_implemented`. El flag aparece en `--help` y tiene schema.

**Decisión:** no priorizar su implementación sin evidencia de uso. Retirar el flag en el siguiente cambio compatible o marcarlo como experimental fuera del help. Una opción pública que siempre falla reduce confianza más que una capacidad ausente.

#### P0.4 `update` no funciona para usuarios instalados normalmente

`gitwise/update.py:12-26` exige que el paquete esté dentro de un clone Git y hace `git pull`. Los canales recomendados son Homebrew y `uv tool install`, donde el wheel no contiene `.git`.

**Decisión:** deprecar `update`. En una release posterior, retirarlo o convertirlo en un detector de canal que solo imprima el comando correcto. No debe ejecutar un gestor de paquetes automáticamente.

### P1: robustez y escalabilidad

#### P1.1 Dos subprocess escapan a las reglas centrales

- `gitwise/conflicts.py:24-32` ejecuta Git binario sin el entorno saneado de `gitwise.git.run`.
- `gitwise/audit.py:111-121` ejecuta `git-sizer` sin timeout.

No son vulnerabilidades explotables demostradas en el flujo actual, pero rompen invariantes de defensa y pueden bloquear `audit` indefinidamente en repos grandes.

#### P1.2 `context --json` no limita anchura

`_directory_tree` limita profundidad a 3, pero no número de entradas: `gitwise/context.py:20-53`. El modo humano corta a 50 líneas, mientras que JSON entrega el árbol completo: `gitwise/context.py:134-156`.

**Impacto:** el comando que promete contexto útil puede generar miles de entradas y desperdiciar tokens en monorepos anchos.

**Decisión:** añadir `max_entries`, `truncated` y `total`; no añadir más fuentes de contexto antes de resolver este límite.

#### P1.3 `snapshot` sigue siendo Claude-first dentro de una narrativa multi-agente

`run_snapshot` siempre escribe `.claude/git-snapshot.md`: `gitwise/snapshot.py:67-74,101-114`. `setup-agents` sí elige `.agents/git-snapshot.md` cuando existe layout canónico: `gitwise/setup_agents/plan.py:26-30`. Sin embargo, templates de Cursor, Continue, Codex, opencode y Pi todavía indican que `gitwise snapshot` regenera `.claude/git-snapshot.md`.

**Decisión:** consolidar `snapshot` dentro de `setup-agents` o hacerlo consciente del layout canónico. No invertir en nuevas opciones de snapshot hasta corregir la identidad del destino.

#### P1.4 `health` comunica precisión no calibrada y duplica `audit`

`health` aplica pesos internos a remote, upstream, GPG, ramas, commit-graph, stashes y untracked: `gitwise/health.py:97-110,121-207`. Dos stashes de 39 y 65 días no afectan el score porque la penalización empieza en más de tres stashes, mientras `audit` sí los reporta como findings. Por eso el mismo repo puede tener `health=100/A` y findings pendientes.

**Decisión:** congelar pesos, documentar que es un indicador heurístico y evaluar integrarlo como resumen de `audit`. No usarlo como KPI ni ajustar pesos sin datos.

#### P1.5 La cobertura es buena pero no está protegida

La suite obtiene 79.82%, pero CI no usa `--cov-fail-under` y Codecov tiene `fail_ci_if_error: false`: `.github/workflows/ci.yml:110-116`. Los módulos más débiles son `update.py` 28%, `output.py` 48%, `status.py` 54% y `stash.py` 62%.

**Decisión:** gate inicial en 75%, no 90%. Invertir en rutas de contrato y rendering, no en aumentar el número bruto de tests.

#### P1.6 El soporte Windows es parcial

`pyproject.toml:18-26` declara Windows y Python 3.10-3.14. El workflow Windows excluye `test_setup_agents.py` y `test_sa_unit.py`, precisamente el subsistema más complejo: `.github/workflows/test-windows-installer.yml:129-141`.

**Decisión:** elegir una de dos promesas. O completar soporte de `setup-agents` en Windows, o declarar explícitamente que el CLI general funciona en Windows pero el layout con symlinks tiene limitaciones. Mantener una promesa ambigua no es aceptable.

#### P1.7 La automatización de release contradice políticas declaradas

El release bot desactiva firma GPG en `.github/workflows/auto-release.yml:51-55`, y el bot del tap hace lo mismo en `.github/workflows/update-homebrew-tap.yml:182-190`. Además, el tap usa `gh pr merge --admin` después de validar que el diff solo cambie URL y SHA: `.github/workflows/update-homebrew-tap.yml:365-410`.

Estas decisiones pueden ser operativamente necesarias, y el sanity check reduce el riesgo, pero son excepciones reales a las políticas “GPG obligatorio” y “no saltar branch protection”. Deben documentarse como modelo de confianza de bots, con permisos mínimos y revisión periódica de la GitHub App.

### P1: documentación y posicionamiento

#### P1.8 El roadmap contradice el producto actual

`ROADMAP.md` conserva:

- versión actual v0.15.0 en `ROADMAP.md:7`;
- 27 comandos en `ROADMAP.md:9-13`;
- una sola dependencia en `ROADMAP.md:15-16`;
- envelope v2 en `ROADMAP.md:138-147`;
- “Streaming JSON” como despriorizado en `ROADMAP.md:151-159`, mientras `diff` y `log` ya ofrecen NDJSON con `--json-lines`; el roadmap debe aclarar si se refería a streaming incremental distinto de NDJSON.

`SECURITY.md:42` afirma incorrectamente que solo existe Rich como dependencia runtime; debe listar también rich-argparse y shtab.

El checker de baseline valida tests e i18n, pero no versión, comandos, dependencias ni contrato.

#### P1.9 La documentación es extensa, pero no guía al flujo principal

El README presenta 12 comandos como “más usados” sin evidencia de uso y describe tres problemas, mientras el producto publica 30 comandos. `docs/reference/commands.md:222-232` omite `pr create`, aunque está implementado. `demo/script.sh:4-19` sigue en v0.12.0 y enseña aliases legacy funcionales, pero ocultos del help: `--adapters` y `--list-adapters`.

Hay planes y reportes históricos en el nivel principal de `docs/`. Son evidencia útil de decisiones, pero compiten con la documentación vigente.

**Decisión:** archivar historia, reescribir el README alrededor de flujos y regenerar o retirar el demo actual.

#### P1.10 La política bilingüe permite drift

`README.es.md` no incluye la sección PowerShell presente en inglés. `CONTRIBUTING.md:104` pide actualizar espejo español, pero no distingue qué documentos son traducciones completas y cuáles son stubs que apuntan al canon inglés.

**Decisión:** mantener traducción completa solo para contenido estable y de entrada. Usar stubs para documentos técnicos o volátiles. No crear nuevos documentos duplicados.

## Portafolio de comandos

### Criterios

- **Invertir:** diferenciación alta y parte de un flujo central.
- **Mantener:** aporta valor o infraestructura, pero debe estabilizarse sin crecer.
- **Consolidar:** el comportamiento debe sobrevivir, pero no necesariamente como comando independiente.
- **Despriorizar:** fix-only; no añadir features ni promover en el happy path.
- **Retirar/rediseñar:** el contrato actual no sirve al canal principal.

| Comando | Decisión | Razón |
|---|---|---|
| `audit` | Invertir | Diagnóstico accionable y diferenciador; debe ser el centro de mantenimiento |
| `branches` | Mantener | Dashboard útil, pero no necesita más paridad con `git branch` |
| `clean` | Mantener | Limpieza segura de ramas; retirar `--refs` hasta que exista demanda |
| `commands` | Mantener | Registry de capacidades para agentes; infraestructura estable |
| `commit` | Invertir | GPG, conventional commits, secret scan y protección de amend |
| `completions` | Mantener | Calidad básica de CLI; congelar superficie y añadir smoke tests |
| `conflicts` | Mantener | Resolución segura aporta valor; corregir entorno de subprocess |
| `context` | Invertir tras limitar salida | Contexto para LLM sin equivalente directo; hoy puede crecer demasiado |
| `diff` | Invertir | Summary, secret scan, FileEntry y NDJSON opt-in concentran valor para agentes |
| `doctor` | Mantener | Onboarding y diagnóstico de entorno; one-shot pero necesario |
| `health` | Consolidar | Score heurístico duplica parte de `audit` y aparenta más precisión de la real |
| `log` | Mantener | JSON/NDJSON útil; no añadir más opciones de `git log` |
| `merge` | Mantener | Preflight y estados en curso reducen riesgo |
| `optimize` | Mantener | Cierra el ciclo de `audit`; mantener pequeño y explícito |
| `pick` | Despriorizar | Wrapper de cherry-pick/revert de uso bajo; fix-only |
| `pr` | Mantener | JSON sobre `gh` y checks son útiles; no perseguir paridad total con `gh` |
| `schema` | Mantener | Contrato de agentes; infraestructura, no feature a expandir |
| `setup` | Despriorizar | Configuración one-shot de 581 líneas; mantener estable, sin más defaults |
| `setup-agents` | Invertir | Diferenciador principal, con rollback y soporte multi-provider |
| `show` | Despriorizar | `git show` con delta ya cubre el caso humano; JSON tiene valor marginal |
| `snapshot` | Consolidar | Debe alinearse con layout canónico o ser parte de `setup-agents/context` |
| `stash` | Despriorizar | Git ya lo resuelve; quedan inconsistencias JSON y riesgo inherente de conflictos |
| `status` | Mantener | Orientación rápida e `in_progress`; no duplicar más datos de `context` |
| `suggest` | Consolidar | Debe ser una etapa de commit, no una línea de producto separada |
| `summarize` | Invertir | Resumen compacto y medible para sesiones humanas/agente |
| `sync` | Mantener | Pull/push seguro y hints de divergencia; no ampliar a remote management |
| `tag` | Despriorizar | Semver aporta algo, pero es baja frecuencia y ya tiene superficie amplia |
| `undo` | Despriorizar | Útil como seguridad, pero no necesita más modos ni abstracciones |
| `update` | Retirar o rediseñar | Falla en Homebrew y `uv tool install`; solo funciona desde clone |
| `worktree` | Invertir | Aislamiento para agentes paralelos y limpieza de worktrees huérfanos |

### Núcleo recomendado

Los comandos que deben protagonizar documentación, demos y benchmarks son:

```text
setup-agents  worktree  summarize  context  diff  commit  audit
```

`doctor`, `status`, `branches`, `clean`, `optimize`, `sync`, `merge`, `conflicts`, `pr`, `commands` y `schema` son soporte del núcleo, no productos paralelos.

## Flujos de trabajo reales

### 1. Onboarding de un repositorio

```bash
gitwise doctor
gitwise setup --dry-run
gitwise setup-agents --local --dry-run
gitwise setup-agents --local --yes
gitwise summarize
```

**Valor:** valida entorno, muestra cambios antes de escribir y crea configuración canónica para agentes.

**Límite:** `setup` modifica configuración Git y debe seguir siendo opt-in. No debe ejecutarse automáticamente desde instalación ni desde `setup-agents`.

### 2. Agente trabajando en una tarea aislada

```bash
gitwise worktree new feat/my-change --json
gitwise status --json
gitwise summarize --json
gitwise diff --summary --json
git add <paths>
gitwise suggest --json
gitwise commit -m "feat(scope): description" --json
```

**Valor:** aislamiento, contexto compacto, diff estructurado y commit protegido.

**Decisión correcta:** gitwise no necesita un wrapper de `git add`. La selección explícita de archivos debe seguir en Git; añadirla ampliaría riesgo y superficie sin diferenciación.

### 3. Mantenimiento semanal

```bash
gitwise audit --quick --json
gitwise branches --stale --json
gitwise clean --branches --dry-run --json
gitwise optimize --dry-run --json
```

Aplicar `clean` u `optimize` solo después de revisar el plan y con `--yes` explícito.

**Valor:** convierte diagnóstico, decisión y acción en un ciclo auditable.

### 4. Sincronización y PR

```bash
gitwise sync --dry-run --json
gitwise pr create --title "..." --fill --json
gitwise pr checks <number> --json
```

**Valor:** un contrato JSON uniforme sobre Git y `gh`.

**Límite:** si una operación `gh` no necesita política o estructura adicional, debe seguir usando `gh` directamente. Paridad total no es objetivo.

### 5. CI o automatización headless

Recomendados como read-only:

```bash
gitwise doctor --json
gitwise status --json
gitwise diff --summary --json
gitwise audit --quick --json
gitwise schema status --output --json
```

No ejecutar `setup`, `clean`, `optimize`, `stash pop`, `merge`, `sync --push` o `commit` en CI genérico. Que soporten JSON no los hace seguros para ejecución desatendida.

## Qué descartar o no priorizar

### Descartar como dirección de producto

- Paridad completa con `git` o `gh`.
- Nuevos subcomandos antes de medir los siete flujos centrales.
- Más modos de `diff`; ya existen stat, name-only, summary, full y NDJSON opt-in.
- Un TUI, fzf, manpages o un framework de plugins.
- Nuevos adapters sin usuarios que los soliciten y mantengan fixtures reales.
- Más pesos o categorías en `health` sin calibración externa.
- Nuevos formatos además de JSON/NDJSON y salida humana.
- Un wrapper de `git add`.
- Auto-update que ejecute Homebrew o uv en nombre del usuario.

### Mantener en modo fix-only

- `show`, `pick`, `setup`, `stash`, `tag`, `undo`.
- Alias legacy `branch-clean`, `commit-suggest`, `cherry-pick`, `--adapters` y `--list-adapters`, con fecha explícita de deprecación si se decide retirarlos.
- Render visual adicional. La prioridad es consistencia de contrato, no más decoración.

### Archivar o eliminar de navegación principal

- `docs/action-plan.md` y `docs/action-plan-v0.12.md`.
- `docs/review-analysis-report.md`.
- Planes ya implementados bajo `docs/plans/`.
- `demo/script.sh` y el asciicast v0.12, salvo que se regeneren con el núcleo actual.
- Taxonomías y documentos comunitarios aspiracionales que no se usan, manteniendo lo requerido por GitHub en una única ubicación.

No hace falta eliminar contenido histórico. Se puede crear `docs/archive/`, mover allí esos documentos y sacarlos del recorrido principal.

## Roadmap recomendado

### P0: 1-2 semanas

1. Corregir `--json` antes del subcomando.
2. Hacer que todas las rutas de error de worktree y stash respeten envelope v3.
3. Retirar `clean --refs` del help/schema o implementarlo solo si existe un caso real validado.
4. Deprecar `update` y documentar actualización por canal.
5. Corregir las contradicciones de ROADMAP, SECURITY, CONTRIBUTING, README y referencia de `pr create`.
6. Añadir `timeout` a `git-sizer` y entorno saneado a `_git_bytes`.

**Criterio de salida:** matriz automática que recorra comandos y rutas de argumento faltante, validando que `--json` siempre produzca envelope y exit code coherente; el catálogo no contiene flags que respondan siempre `not_implemented`; `update` emite una deprecación útil por canal y los checkers documentales validan versión, comandos y dependencias.

### P1: 30 días

1. Limitar `context` y emitir `truncated/total`.
2. Alinear `snapshot` con `.agents/` o integrarlo en `setup-agents`.
3. Congelar `health` y decidir si sigue como comando independiente.
4. Añadir coverage gate de 75% y cubrir output/status/stash por comportamiento, no por conteo.
5. Archivar documentación histórica y rehacer README/demo alrededor de los cinco flujos principales.
6. Definir el nivel real de soporte Windows.
7. Documentar y revisar las excepciones de firma GPG y branch protection de los bots de release.

### P2: 60-90 días

1. Medir al menos cinco usos reales por perfil: humano, agente y CI.
2. Comparar el núcleo contra Git/gh en pasos, errores evitados, bytes/tokens y tiempo.
3. Eliminar o rediseñar `update` después de la ventana de deprecación.
4. Decidir si `health`, `snapshot` y `suggest` siguen como comandos o pasan a ser etapas de otros flujos.
5. Publicar una release de estabilización, no otra expansión de superficie.

## Métricas de éxito

### Producto

- Tiempo desde instalación hasta primer `setup-agents` exitoso.
- Porcentaje de usuarios que repite al menos uno de los flujos centrales.
- Comandos usados por sesión, recolectados mediante entrevistas, issues o telemetría estrictamente opt-in.
- Número de operaciones que vuelven a Git/gh porque gitwise no agrega valor.

### Agentes

- Bytes y tokens de `summarize/context/diff --summary` frente a comandos Git equivalentes.
- Porcentaje de respuestas parseables en rutas de éxito y error: objetivo 100%.
- Secretos o commits en operaciones en curso bloqueados antes de ejecutar.
- Tiempo para descubrir un comando y su schema sin documentación externa.

### Ingeniería

- Coverage no inferior a 75%, con foco en rutas contractuales.
- Cero flags públicos que siempre retornen `not_implemented`.
- Cero contradicciones de versión, dependencias o comandos en docs verificadas por CI.
- Menos documentos activos, sin perder historia archivada.
- Ratio de releases de estabilización frente a releases que añaden superficie.

## Riesgos estratégicos

### Bus factor y expansión

El repositorio depende principalmente de un mantenedor. Cada comando, adapter, idioma y canal de distribución multiplica revisiones, schemas, tests y documentación. La arquitectura soporta crecimiento, pero el equipo actual no justifica usar toda esa capacidad.

### Dependencia de agentes específicos

El proyecto nació alrededor de Claude Code y ahora soporta varios providers. Esa expansión reduce riesgo de plataforma, pero solo si el layout canónico `.agents/` es realmente la fuente de verdad. Referencias residuales a `.claude/` debilitan la promesa multi-agente.

### Privacidad frente a validación

La ausencia de telemetría es una fortaleza. No debe añadirse tracking por defecto para resolver el problema de adopción. Entrevistas, opt-in explícito, issues y ejemplos reproducibles son suficientes para la siguiente fase.

## Conclusión

gitwise no necesita más amplitud. Necesita demostrar que su capa de control segura y legible por máquinas mejora flujos Git reales.

La ventaja defendible es la combinación de:

1. contexto compacto para agentes;
2. contratos JSON y schemas descubribles;
3. seguridad en commit, diff y operaciones en curso;
4. worktrees y configuración canónica multi-agente;
5. diagnóstico y mantenimiento con dry-run.

Todo lo que no refuerce uno de esos cinco puntos debe mantenerse estable, consolidarse o salir del recorrido principal.

## Registro de verificación

- Verified: `pyproject.toml:1-66` (consultado 2026-07-21).
- Verified: `gitwise commands --json` con 30 comandos (ejecutado 2026-07-21).
- Verified: `gitwise schema status --output --json` con envelope v3 y JSON Schema draft 2020-12 (ejecutado 2026-07-21).
- Verified: `uv run pytest --collect-only -q`, 718 tests (ejecutado 2026-07-21).
- Verified: `uv run pytest --cov=gitwise --cov-fail-under=75 -q -n auto`, 718 passed y 79.82% (ejecutado 2026-07-21).
- Verified: `uv run ruff check gitwise/ tests/`, `uv run ruff format --check gitwise/ tests/` y `uv run basedpyright` en la fase final.
- Verified: `uv run pip-audit`, sin vulnerabilidades conocidas (ejecutado 2026-07-21).
- Verified: GitHub CLI 2.96.0 contra `drzioner/gitwise`, release v0.34.0, 1 estrella, 0 forks, 0 issues abiertos y CI reciente verde (consultado 2026-07-21).
- Verified: `gitwise doctor --json`, Python 3.12.11, Git 2.55.0 y GPG ready (ejecutado 2026-07-21).
- Verified: inspección de `gitwise/conflicts.py`, `audit.py`, `context.py`, `snapshot.py`, `health.py` y workflows de release en las líneas citadas (consultado 2026-07-21).
- Verified: `gitwise status --json`, worktree reparado sin conflictos; solo `uv.lock` modificado previamente y este informe nuevo (ejecutado 2026-07-21).

## Limitaciones

- No hay telemetría ni entrevistas de usuarios; las decisiones de producto son hipótesis informadas, no evidencia de retención.
- No se midió Windows directamente en esta máquina; se inspeccionó el workflow y sus exclusiones.
- No se reprodujo un conflicto de `stash pop` sobre el repo de trabajo porque sería destructivo. El análisis de esa ruta se limita al código.
- Durante subrevisiones se ejecutaron indebidamente `setup --yes` y pruebas de stash. Ocho archivos llegaron a quedar en conflicto y los dos stashes preexistentes fueron eliminados. Los archivos se restauraron exclusivamente desde `HEAD`, usando como línea base el status inicial. Los stashes se recuperaron de objetos dangling identificados por hash y mensaje, y se recrearon en su orden original. Ramas y worktrees quedaron intactos. `setup --yes` activó al menos `core.fsmonitor`; no se revirtió configuración Git sin una línea base segura.
