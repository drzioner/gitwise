# gitwise

[English](README.md) | [Espanol](README.es.md)

Python CLI for optimized Git workflows and Claude Code integration.

[![CI](https://github.com/drzioner/gitwise/actions/workflows/ci.yml/badge.svg)](https://github.com/drzioner/gitwise/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/drzioner/gitwise/graph/badge.svg)](https://codecov.io/gh/drzioner/gitwise)
[![Version](https://img.shields.io/github/v/tag/drzioner/gitwise?label=version)](https://github.com/drzioner/gitwise/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docs: EN/ES](https://img.shields.io/badge/docs-EN%20%7C%20ES-0A7EA4)](docs/README.md)

gitwise addresses three daily pain points:

1. AI context bloat from raw `git diff`
2. Slow repositories without modern Git maintenance settings
3. Unsafe commit flows that bypass GPG signing rules

## Requirements

- Python >= 3.10
- git >= 2.29
- macOS or Linux

## Install

```bash
git clone https://github.com/drzioner/gitwise.git ~/.local/share/gitwise
bash ~/.local/share/gitwise/install.sh
```

Update an existing installation:

```bash
gitwise update
```

## Quick Start

```bash
gitwise doctor
gitwise setup --dry-run
gitwise setup-agents --local --dry-run
gitwise summarize
```

## Most Used Commands

| Command | Purpose |
|---|---|
| `gitwise doctor` | Check Python, git, platform, optional tools |
| `gitwise setup` | Apply modern Git defaults safely |
| `gitwise setup-agents` | Install Claude/adapters config globally or locally |
| `gitwise audit` | Detect stale branches, graph/cache gaps, large blobs |
| `gitwise summarize` | Compact context for humans and AI |
| `gitwise diff` | Focused changed-file view (`--stat`, `--staged`, `--patch`) |
| `gitwise worktree` | Create and clean worktree-based branch setups |
| `gitwise status` | Enhanced status with staged/unstaged and ahead/behind |
| `gitwise pr` | List/check/view PRs via GitHub CLI |

For all commands, examples, aliases, and JSON usage, see:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Espanol)](docs/es/reference/commands.md)

## Documentation

- [Documentation index (English)](docs/README.md)
- [Indice de documentacion (Espanol)](docs/es/README.md)
- [Contributing guide](CONTRIBUTING.md)
- [Guia de contribucion](CONTRIBUTING.es.md)
- [Security policy](SECURITY.md)
- [Politica de seguridad](SECURITY.es.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Codigo de conducta](CODE_OF_CONDUCT.es.md)

## GPG and Safety Model

`setup` and `setup-agents` never modify `commit.gpgsign` or `user.signingkey`.

- Git layer: `core.hooksPath` hook validates signing key availability.
- Agent layer: deny-rules block `--no-gpg-sign`, `--no-verify`, and `-c commit.gpgsign=false`.

## Environment Variables

| Variable | Description |
|---|---|
| `GITWISE_DEBUG=1` | Print each `git` subprocess command to stderr |
| `GITWISE_BIN_DIR` | Install location (default: `~/.local/bin`) |

## Demo

[![asciicast](https://asciinema.org/a/6tm4TnYMygEQT7ef.svg)](https://asciinema.org/a/6tm4TnYMygEQT7ef)

## License

[MIT](LICENSE) - Deiner
