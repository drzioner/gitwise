# gitwise

Source: README.md
Last sync: 2026-07-21

[English](README.md) | [Español](README.es.md)

CLI de Python para optimizar flujos de Git e integración con agentes de código.

[![CI](https://github.com/drzioner/gitwise/actions/workflows/ci.yml/badge.svg)](https://github.com/drzioner/gitwise/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/drzioner/gitwise/graph/badge.svg)](https://codecov.io/gh/drzioner/gitwise)
[![Version](https://img.shields.io/github/v/release/drzioner/gitwise?display_name=tag)](https://github.com/drzioner/gitwise/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docs: EN/ES](https://img.shields.io/badge/docs-EN%20%7C%20ES-0A7EA4)](docs/es/README.md)

gitwise ofrece a los agentes de codigo contexto acotado del repositorio, trabajo
aislado por rama y commits seguros sin ocultar las operaciones Git subyacentes.
Todos los comandos soportan JSON para maquinas y las operaciones destructivas
exponen dry-run o confirmacion.

## Requisitos

- Python >= 3.10
- git >= 2.29
- macOS, Linux o Windows

## Instalación

Elige el canal que ya usas y confias:

**Homebrew** (macOS/Linux, recomendado si ya usas [Homebrew](https://brew.sh)):

```bash
brew install drzioner/tap/gitwise
```

Actualiza después con `brew upgrade gitwise`. Desinstala con `brew uninstall gitwise`.

**Script instalador** (auto-instala `uv` si hace falta):

```bash
curl -fsSL https://raw.githubusercontent.com/drzioner/gitwise/main/install.sh | bash
```

**uv** (si ya usas [uv](https://docs.astral.sh/uv/)):

```bash
uv tool install gitwise-cli
```

**Windows PowerShell** (PowerShell 5.1+):

```powershell
irm https://raw.githubusercontent.com/drzioner/gitwise/main/install.ps1 | iex
```

**Desde source** (solo contribuidores):

```bash
git clone https://github.com/drzioner/gitwise.git
cd gitwise
uv sync
uv run python -m gitwise doctor
```

Actualiza con el mismo canal usado para instalar:

```bash
brew upgrade gitwise                   # si se instaló via Homebrew (macOS/Linux)
uv tool upgrade gitwise-cli            # si se instaló via uv (cualquier OS)
# o vuelve a ejecutar el script instalador
```

Desinstalar:

```bash
brew uninstall gitwise                 # si se instaló via Homebrew
uv tool uninstall gitwise-cli          # si se instaló via uv (cualquier OS)
```

## Inicio rápido

```bash
gitwise doctor
gitwise setup --dry-run
gitwise setup-agents --local --dry-run
gitwise summarize
```

Los tres primeros comandos inspeccionan o planifican cambios. Agrega `--yes` solo
despues de revisar el plan.

## Cinco flujos

### 1. Preparar un repositorio

Verifica el entorno, previsualiza defaults modernos de Git e instala el layout
canonico para agentes:

```bash
gitwise doctor --json
gitwise setup --dry-run
gitwise setup --yes
gitwise setup-agents --local --dry-run
gitwise setup-agents --local --yes
```

`setup` y `setup-agents` no cambian `commit.gpgsign` ni `user.signingkey`.

### 2. Dar contexto acotado a un agente

Usa resumenes estructurados en vez de enviar un diff crudo sin limites:

```bash
gitwise context --json
gitwise context --max-entries 50 --json
gitwise summarize --json
gitwise diff --stat --json
```

`context --json` usa 100 entradas del arbol por defecto y reporta `tree_total`
y `tree_truncated` cuando omite entradas.

### 3. Aislar el trabajo del agente

Crea un worktree hermano para una rama y usa el path que imprime el comando:

```bash
gitwise worktree new feature/agent-task
gitwise worktree list --json
```

Ejecuta `gitwise worktree remove feature/agent-task --dry-run` antes de eliminarlo.

### 4. Revisar y crear un commit seguro

Revisa el stage, busca posibles secretos y crea un commit convencional firmado
por la configuracion Git del repositorio:

```bash
gitwise diff --staged --scan-secrets
gitwise commit -m "fix: handle empty configuration"
```

gitwise bloquea bypasses conocidos de firma y hooks en las reglas generadas para
agentes. No crea ni reemplaza claves de firma.

### 5. Mantener el repo y comprobar un PR

Haz explicito el mantenimiento e inspecciona GitHub sin cambios implicitos:

```bash
gitwise audit --quick
gitwise clean --branches --dry-run
gitwise optimize --dry-run
gitwise pr checks
gitwise pr create --fill
```

`pr` delega operaciones de GitHub a `gh`; autentica `gh` antes de usarlo.

## Comandos centrales

| Comando | Propósito |
|---|---|
| `setup-agents` | Instala el layout multi-agente canonico y templates de providers |
| `worktree` | Aisla trabajo por rama en directorios hermanos |
| `summarize` | Produce contexto compacto de status, log y diff opcional |
| `context` | Produce contexto acotado con metadata de truncacion |
| `diff` | Inspecciona salida enfocada, staged, estadistica o patch |
| `commit` | Protege y crea commits convencionales |
| `audit` | Diagnostica ramas stale, estructura y mantenimiento pendiente |

Comandos de soporte como `doctor`, `setup`, `status`, `clean`, `optimize`, `pr`,
`commands` y `schema` sirven a esos flujos. Para los 30 comandos, aliases, flags
y ejemplos:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Español)](docs/es/reference/commands.md)

## Contrato JSON para agentes

Los flags globales de maquina funcionan antes o despues del subcomando:

```bash
gitwise --json status
gitwise status --json
gitwise commands --json
gitwise schema diff --json
```

La mayoria de comandos JSON usa el envelope v3 estandar:

```json
{"v":3,"ok":true,"command":"status","data":{},"hints":[],"errors":[]}
```

Usa `command` y los valores estables de `code` para decisiones. `data` contiene
el payload especifico del comando. `setup-agents` conserva campos versionados de
compatibilidad; consulta su contrato con `gitwise schema setup-agents --json`.

## Modelo de seguridad

- Los subprocess Git limpian variables de inyeccion y usan timeouts explicitos.
- Los comandos destructivos por lote requieren confirmacion; JSON devuelve un gate explicito.
- `diff --scan-secrets` y `commit` detectan patrones de credenciales de alta confianza.
- setup-agents limita los symlinks al repositorio objetivo.
- CI ejecuta ruff, basedpyright, pytest con floor de cobertura 75%, pip-audit y shellcheck.

Consulta la [politica de seguridad](SECURITY.es.md) para reportar vulnerabilidades.

## Documentación

- [Documentation index (English)](docs/README.md)
- [Índice de documentación (Español)](docs/es/README.md)
- [Contributing guide](CONTRIBUTING.md)
- [Guía de contribución](CONTRIBUTING.es.md)
- [Security policy](SECURITY.md)
- [Política de seguridad](SECURITY.es.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Código de conducta](CODE_OF_CONDUCT.es.md)
- [Git conventions](CONVENTIONS.md)
- [Convenciones Git](CONVENTIONS.es.md)

## Variables de entorno

| Variable | Descripción |
|---|---|
| `GITWISE_DEBUG=1` | Muestra cada comando `git` ejecutado por subprocess en stderr |
| `GITWISE_LOG_JSON=1` | Emite logs estructurados en stderr como líneas JSON |
| `GITWISE_JSON_PRETTY=1` | Formatea JSON en modo pretty por defecto |
| `GITWISE_LANG=es` / `GITWISE_LANG=en` | Fuerza el locale de salida |
| `GITWISE_THEME=dark` / `GITWISE_THEME=light` / `GITWISE_THEME=auto` | Fuerza selección de tema de color |
| `GITWISE_NO_COLOR=1` | Desactiva salida ANSI con color |
| `GITWISE_OUTPUT=agent` | Fuerza modo de salida orientado a máquina |
| `GITWISE_AGENT=1` | Alias para habilitar modo agent |
| `GITWISE_GIT_TIMEOUT=<segundos>` | Override del timeout de subprocess git |
| `GITWISE_WIDTH=<columnas>` | Override del ancho de salida |

## Completions de shell

Genera script de completions por shell:

```bash
gitwise completions bash > ~/.local/share/bash-completion/completions/gitwise
gitwise completions zsh > ~/.zsh/completions/_gitwise
gitwise completions fish > ~/.config/fish/completions/gitwise.fish
```

**PowerShell** (Windows o PowerShell Core):

```powershell
gitwise completions powershell > gitwise.ps1
. .\gitwise.ps1
Add-Content $PROFILE ('. ' + ((Resolve-Path 'gitwise.ps1').Path))
```

## Demo

Ejecuta el demo actual no destructivo desde un repositorio Git:

```bash
bash demo/script.sh
```

## Licencia

[MIT](LICENSE) - Deiner
