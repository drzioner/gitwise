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
gitwise setup --dry-run
gitwise setup-agents --local --dry-run
gitwise summarize
```

## Comandos más usados

| Comando | Propósito |
|---|---|
| `gitwise doctor` | Verifica Python, git, plataforma y herramientas opcionales |
| `gitwise setup` | Aplica defaults modernos de Git de forma segura |
| `gitwise setup-agents` | Instala layout canónico de agentes + configuración opcional de providers |
| `gitwise audit` | Detecta ramas stale, gaps de graph/cache, blobs grandes |
| `gitwise summarize` | Contexto compacto para humanos y agentes |
| `gitwise diff` | Vista enfocada de cambios (`--stat`, `--staged`, `--patch`) |
| `gitwise worktree` | Crea y limpia flujos por worktree |
| `gitwise status` | Status mejorado con staged/unstaged y ahead/behind |
| `gitwise commands --json` | Lista subcomandos con aliases y metadata |
| `gitwise schema <command> --json` | Retorna JSON Schema versionado para inputs de comandos |
| `gitwise completions <shell>` | Genera scripts de completions (bash/zsh/fish) |
| `gitwise pr` | Lista/check/view de PRs con GitHub CLI |

Para todos los comandos, ejemplos, aliases y uso JSON:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Español)](docs/es/reference/commands.md)

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
