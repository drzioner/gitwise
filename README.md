# gitwise

[English](README.md) | [Español](README.es.md)

Python CLI for optimized Git workflows and coding agents integration.

[![CI](https://github.com/drzioner/gitwise/actions/workflows/ci.yml/badge.svg)](https://github.com/drzioner/gitwise/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/drzioner/gitwise/graph/badge.svg)](https://codecov.io/gh/drzioner/gitwise)
[![Version](https://img.shields.io/github/v/release/drzioner/gitwise?display_name=tag)](https://github.com/drzioner/gitwise/releases)
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

Pick one:

**Homebrew** (macOS/Linux, recommended if you already use [Homebrew](https://brew.sh)):

```bash
brew install drzioner/tap/gitwise
```

Update later with `brew upgrade gitwise`. Uninstall with `brew uninstall gitwise`.

**curl | bash** (auto-installs `uv` if missing, no package manager required):

```bash
curl -fsSL https://raw.githubusercontent.com/drzioner/gitwise/main/install.sh | bash
```

**uv** (if you already use [uv](https://docs.astral.sh/uv/)):

```bash
uv tool install gitwise-cli
```

**From source** (development only):

```bash
git clone https://github.com/drzioner/gitwise.git
cd gitwise
uv sync
uv run python -m gitwise doctor
```

Update an existing installation:

```bash
brew upgrade gitwise                   # if installed via Homebrew
uv tool upgrade gitwise-cli            # if installed via uv
# or re-run the curl | bash installer, which always pulls latest
```

Uninstall:

```bash
brew uninstall gitwise                 # if installed via Homebrew
uv tool uninstall gitwise-cli          # if installed via uv
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
| `gitwise setup-agents` | Install canonical agents layout + optional provider config |
| `gitwise audit` | Detect stale branches, graph/cache gaps, large blobs |
| `gitwise summarize` | Compact context for humans and AI |
| `gitwise diff` | Focused changed-file view (`--stat`, `--staged`, `--patch`) |
| `gitwise worktree` | Create and clean worktree-based branch setups |
| `gitwise status` | Enhanced status with staged/unstaged and ahead/behind |
| `gitwise commands --json` | List subcommands with aliases and metadata |
| `gitwise schema <command> --json` | Return versioned JSON Schema for command inputs |
| `gitwise completions <shell>` | Generate shell completion scripts (bash/zsh/fish) |
| `gitwise pr` | List/check/view PRs via GitHub CLI |

For all commands, examples, aliases, and JSON usage, see:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Español)](docs/es/reference/commands.md)

## Documentation

- [Documentation index (English)](docs/README.md)
- [Indice de documentacion (Español)](docs/es/README.md)
- [Contributing guide](CONTRIBUTING.md)
- [Guia de contribucion](CONTRIBUTING.es.md)
- [Security policy](SECURITY.md)
- [Politica de seguridad](SECURITY.es.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Código de conducta](CODE_OF_CONDUCT.es.md)
- [Git conventions](CONVENTIONS.md)
- [Convenciones Git](CONVENTIONS.es.md)

## GPG and Safety Model

`setup` and `setup-agents` never modify `commit.gpgsign` or `user.signingkey`.

- Git layer: `setup` manages hooks safely (`--hooks-mode preserve|native|legacy|skip`) to validate signing key availability and conventional commits.
- Agent layer: deny-rules block `--no-gpg-sign`, `--no-verify`, and `-c commit.gpgsign=false`.

## Environment Variables

| Variable | Description |
|---|---|
| `GITWISE_DEBUG=1` | Print each `git` subprocess command to stderr |
| `GITWISE_LOG_JSON=1` | Emit structured stderr logs as JSON lines |
| `GITWISE_JSON_PRETTY=1` | Pretty-print JSON output by default |
| `GITWISE_LANG=es` / `GITWISE_LANG=en` | Force output locale |
| `GITWISE_THEME=dark` / `GITWISE_THEME=light` / `GITWISE_THEME=auto` | Override color theme selection |
| `GITWISE_NO_COLOR=1` | Disable ANSI color output |
| `GITWISE_OUTPUT=agent` | Force machine-oriented output mode |
| `GITWISE_AGENT=1` | Alias to enable agent output mode |
| `GITWISE_GIT_TIMEOUT=<seconds>` | Override git subprocess timeout |
| `GITWISE_WIDTH=<columns>` | Override output width |

## Shell Completions

Generate completions script per shell:

```bash
gitwise completions bash > ~/.local/share/bash-completion/completions/gitwise
gitwise completions zsh > ~/.zsh/completions/_gitwise
gitwise completions fish > ~/.config/fish/completions/gitwise.fish
```

## Demo

[![asciicast](https://asciinema.org/a/6tm4TnYMygEQT7ef.svg)](https://asciinema.org/a/6tm4TnYMygEQT7ef)

## License

[MIT](LICENSE) - Deiner
