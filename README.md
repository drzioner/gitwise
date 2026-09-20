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

**Windows** (PowerShell 5.1+, auto-installs `uv` if missing):

```powershell
irm https://raw.githubusercontent.com/drzioner/gitwise/main/install.ps1 | iex
```

For a version-pinned install (e.g. for reproducible setups), see `Get-Help .\install.ps1 -Detailed` after download.

Update an existing installation:

```bash
brew upgrade gitwise                   # if installed via Homebrew (macOS/Linux)
uv tool upgrade gitwise-cli            # if installed via uv (any OS)
# or re-run the curl | bash installer, which always pulls latest
```

Uninstall:

```bash
brew uninstall gitwise                 # if installed via Homebrew
uv tool uninstall gitwise-cli          # if installed via uv (any OS)
```

## Quick Start

```bash
gitwise doctor
gitwise setup-agents --local --dry-run
gitwise guard install --dry-run
gitwise guard check --json
```

## The four pillars

gitwise is a policy layer, not a Git front end. Four commands carry the
product; everything else is support.

| Command | What it is for |
|---|---|
| `gitwise guard` | Evaluate the repository policy and install the hooks that enforce it, so protection does not depend on the agent choosing to ask |
| `gitwise commit` | The safe write path: conventional format, GPG readiness, secret scan, amend protection |
| `gitwise worktree` | Isolate parallel agents on their own worktrees, and clean up orphans |
| `gitwise setup-agents` | Install the canonical agents layout and per-provider configuration |

Supporting commands: `doctor`, `setup`, `audit`, `summarize`, `context`,
`diff`, `conflicts`, `commands`, `schema`, `completions`.

Seventeen thin wrappers over `git` and `gh` (`log`, `show`, `status`, `stash`,
`tag`, `pick`, `undo`, `branches`, `sync`, `merge`, `pr`, `clean`, `optimize`,
`health`, `suggest`, `snapshot`, `update`) are deprecated. They still work and
are hidden from `--help`; `gitwise commands --json` reports each one with its
replacement. They will be removed in 1.0.

For all commands, examples, aliases, and JSON usage, see:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Español)](docs/es/reference/commands.md)
- [Policy guard (English)](docs/reference/guard.md)
- [Cortafuegos de políticas (Español)](docs/es/reference/guard.md)

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

**PowerShell** (Windows / PowerShell Core): generate and dot-source the
`Register-ArgumentCompleter` script. Add it to your `$PROFILE` for persistence:

```powershell
gitwise completions powershell > gitwise.ps1
. .\gitwise.ps1
# or, to load on every session:
Add-Content $PROFILE ('. ' + ((Resolve-Path 'gitwise.ps1').Path))
```

Completion covers subcommands as the first token and per-command flags
(`--json`, `--dry-run`, `--max-count`, etc.) thereafter.

## Demo

[![asciicast](https://asciinema.org/a/6tm4TnYMygEQT7ef.svg)](https://asciinema.org/a/6tm4TnYMygEQT7ef)

## License

[MIT](LICENSE) - Deiner
