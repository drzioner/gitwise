# gitwise

Source: README.md
Last sync: 2026-05-22

[English](README.md) | [Español](README.es.md)

CLI de Python para optimizar flujos de Git e integración con agentes de código.

[![CI](https://github.com/drzioner/gitwise/actions/workflows/ci.yml/badge.svg)](https://github.com/drzioner/gitwise/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/drzioner/gitwise/graph/badge.svg)](https://codecov.io/gh/drzioner/gitwise)
[![Version](https://img.shields.io/github/v/release/drzioner/gitwise?display_name=tag)](https://github.com/drzioner/gitwise/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docs: EN/ES](https://img.shields.io/badge/docs-EN%20%7C%20ES-0A7EA4)](docs/es/README.md)

gitwise resuelve tres problemas comunes:

1. Contexto excesivo para AI por usar `git diff` crudo
2. Repos lentos sin configuraciones modernas de mantenimiento de Git
3. Flujos de commit inseguros que evaden las reglas de GPG

## Requisitos

- Python >= 3.10
- git >= 2.29
- macOS o Linux

## Instalación

Elige una:

**Homebrew** (macOS/Linux, recomendado si ya usas [Homebrew](https://brew.sh)):

```bash
brew install drzioner/tap/gitwise
```

Actualiza después con `brew upgrade gitwise`. Desinstala con `brew uninstall gitwise`.

**curl | bash** (auto-instala `uv` si no está, no requiere gestor de paquetes):

```bash
curl -fsSL https://raw.githubusercontent.com/drzioner/gitwise/main/install.sh | bash
```

**uv** (si ya usas [uv](https://docs.astral.sh/uv/)):

```bash
uv tool install gitwise-cli
```

**Desde el source** (solo desarrollo):

```bash
git clone https://github.com/drzioner/gitwise.git
cd gitwise
uv sync
uv run python -m gitwise doctor
```

**Windows** (PowerShell 5.1+, auto-instala `uv` si no está):

```powershell
irm https://raw.githubusercontent.com/drzioner/gitwise/main/install.ps1 | iex
```

Para fijar una versión (p. ej. en setups reproducibles), consulta `Get-Help .\install.ps1 -Detailed` tras la descarga.

Actualizar una instalación existente:

```bash
brew upgrade gitwise                   # si se instaló via Homebrew (macOS/Linux)
uv tool upgrade gitwise-cli            # si se instaló via uv (cualquier OS)
# o vuelve a ejecutar el instalador curl | bash, siempre baja la última
```

Desinstalar:

```bash
brew uninstall gitwise                 # si se instaló via Homebrew
uv tool uninstall gitwise-cli          # si se instaló via uv (cualquier OS)
```

## Inicio rápido

```bash
gitwise doctor
gitwise setup-agents --local --dry-run
gitwise guard install --dry-run
gitwise guard check --json
```

## Los cuatro pilares

gitwise es una capa de política, no un frontal de Git. Cuatro comandos
sostienen el producto; el resto es soporte.

| Comando | Para qué sirve |
|---|---|
| `gitwise guard` | Evalúa la política del repositorio e instala los hooks que la aplican, para que la protección no dependa de que el agente decida preguntar |
| `gitwise commit` | La vía de escritura segura: formato conventional, GPG, escaneo de secretos, protección de amend |
| `gitwise worktree` | Aísla agentes paralelos en worktrees propios y limpia los huérfanos |
| `gitwise setup-agents` | Instala el layout canónico de agentes y la configuración por provider |

Comandos de soporte: `doctor`, `setup`, `audit`, `summarize`, `context`,
`diff`, `conflicts`, `commands`, `schema`, `completions`.

Todos los comandos responden a `--json` con el mismo envelope v3
(`{v, ok, command, data, hints, errors}`), incluidas sus rutas de error y los
fallos por argumento inválido. Un solo parser lee los 31.

Diecisiete wrappers finos sobre `git` y `gh` (`log`, `show`, `status`, `stash`,
`tag`, `pick`, `undo`, `branches`, `sync`, `merge`, `pr`, `clean`, `optimize`,
`health`, `suggest`, `snapshot`, `update`) están deprecados. Siguen
funcionando y están ocultos de `--help`; `gitwise commands --json` informa de
cada uno con su reemplazo. Se eliminarán en 1.0.

Para todos los comandos, ejemplos, aliases y uso JSON:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Español)](docs/es/reference/commands.md)
- [Policy guard (English)](docs/reference/guard.md)
- [Cortafuegos de políticas (Español)](docs/es/reference/guard.md)
- [Guía de migración (0.36)](docs/es/MIGRATION-0.36.md)

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

## Modelo de seguridad y GPG

`setup` y `setup-agents` nunca modifican `commit.gpgsign` ni `user.signingkey`.

- Capa Git: `setup` gestiona hooks de forma segura (`--hooks-mode preserve|native|legacy|skip`) para validar disponibilidad de la clave y conventional commits.
- Capa agente: deny-rules bloquean `--no-gpg-sign`, `--no-verify` y `-c commit.gpgsign=false`.

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

## Demo

[![asciicast](https://asciinema.org/a/6tm4TnYMygEQT7ef.svg)](https://asciinema.org/a/6tm4TnYMygEQT7ef)

## Licencia

[MIT](LICENSE) - Deiner
