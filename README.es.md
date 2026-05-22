# gitwise

Source: README.md
Last sync: 2026-05-22

[English](README.md) | [Español](README.es.md)

CLI de Python para optimizar flujos de Git e integracion con Claude Code.

[![CI](https://github.com/drzioner/gitwise/actions/workflows/ci.yml/badge.svg)](https://github.com/drzioner/gitwise/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/drzioner/gitwise/graph/badge.svg)](https://codecov.io/gh/drzioner/gitwise)
[![Version](https://img.shields.io/github/v/tag/drzioner/gitwise?label=version)](https://github.com/drzioner/gitwise/tags)
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

## Instalacion

```bash
git clone https://github.com/drzioner/gitwise.git ~/.local/share/gitwise
bash ~/.local/share/gitwise/install.sh
```

Actualizar una instalacion existente:

```bash
gitwise update
```

## Inicio rapido

```bash
gitwise doctor
gitwise setup --dry-run
gitwise setup-agents --local --dry-run
gitwise summarize
```

## Comandos mas usados

| Comando | Proposito |
|---|---|
| `gitwise doctor` | Verifica Python, git, plataforma y herramientas opcionales |
| `gitwise setup` | Aplica defaults modernos de Git de forma segura |
| `gitwise setup-agents` | Instala config de Claude/adapters en global o local |
| `gitwise audit` | Detecta ramas stale, gaps de graph/cache, blobs grandes |
| `gitwise summarize` | Contexto compacto para humanos y agentes |
| `gitwise diff` | Vista enfocada de cambios (`--stat`, `--staged`, `--patch`) |
| `gitwise worktree` | Crea y limpia flujos por worktree |
| `gitwise status` | Status mejorado con staged/unstaged y ahead/behind |
| `gitwise pr` | Lista/check/view de PRs con GitHub CLI |

Para todos los comandos, ejemplos, aliases y uso JSON:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Español)](docs/es/reference/commands.md)

## Documentacion

- [Documentation index (English)](docs/README.md)
- [Indice de documentacion (Español)](docs/es/README.md)
- [Contributing guide](CONTRIBUTING.md)
- [Guia de contribucion](CONTRIBUTING.es.md)
- [Security policy](SECURITY.md)
- [Politica de seguridad](SECURITY.es.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Codigo de conducta](CODE_OF_CONDUCT.es.md)

## Modelo de seguridad y GPG

`setup` y `setup-agents` nunca modifican `commit.gpgsign` ni `user.signingkey`.

- Capa Git: `setup` gestiona hooks de forma segura (`--hooks-mode preserve|native|legacy|skip`) para validar disponibilidad de la clave y conventional commits.
- Capa agente: deny-rules bloquean `--no-gpg-sign`, `--no-verify` y `-c commit.gpgsign=false`.

## Variables de entorno

| Variable | Descripcion |
|---|---|
| `GITWISE_DEBUG=1` | Muestra cada comando `git` ejecutado por subprocess en stderr |
| `GITWISE_BIN_DIR` | Directorio de instalacion (default: `~/.local/bin`) |

## Demo

[![asciicast](https://asciinema.org/a/6tm4TnYMygEQT7ef.svg)](https://asciinema.org/a/6tm4TnYMygEQT7ef)

## Licencia

[MIT](LICENSE) - Deiner
