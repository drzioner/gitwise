# gitwise

[English](README.md) | [Español](README.es.md)

Python CLI for optimized Git workflows and coding agents integration.

[![CI](https://github.com/drzioner/gitwise/actions/workflows/ci.yml/badge.svg)](https://github.com/drzioner/gitwise/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/drzioner/gitwise/graph/badge.svg)](https://codecov.io/gh/drzioner/gitwise)
[![Version](https://img.shields.io/github/v/release/drzioner/gitwise?display_name=tag)](https://github.com/drzioner/gitwise/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docs: EN/ES](https://img.shields.io/badge/docs-EN%20%7C%20ES-0A7EA4)](docs/README.md)

gitwise gives coding agents bounded repository context, isolated branch workflows,
and safe commit paths without hiding the underlying Git operations. Every command
supports machine-readable JSON, and destructive operations expose dry-run or
confirmation gates.

## Requirements

- Python >= 3.10
- git >= 2.29
- macOS, Linux, or Windows

## Install

Choose the channel you already trust:

**Homebrew** (macOS/Linux, recommended if you already use [Homebrew](https://brew.sh)):

```bash
brew install drzioner/tap/gitwise
```

Update later with `brew upgrade gitwise`. Uninstall with `brew uninstall gitwise`.

**Installer script** (auto-installs `uv` if needed):

```bash
curl -fsSL https://raw.githubusercontent.com/drzioner/gitwise/main/install.sh | bash
```

**uv** (if you already use [uv](https://docs.astral.sh/uv/)):

```bash
uv tool install gitwise-cli
```

**Windows PowerShell** (PowerShell 5.1+):

```powershell
irm https://raw.githubusercontent.com/drzioner/gitwise/main/install.ps1 | iex
```

**From source** (contributors only):

```bash
git clone https://github.com/drzioner/gitwise.git
cd gitwise
uv sync
uv run python -m gitwise doctor
```

Update through the same channel used to install:

```bash
brew upgrade gitwise                   # if installed via Homebrew (macOS/Linux)
uv tool upgrade gitwise-cli            # if installed via uv (any OS)
# or rerun the installer script
```

Uninstall:

```bash
brew uninstall gitwise                 # if installed via Homebrew
uv tool uninstall gitwise-cli          # if installed via uv (any OS)
```

## Quick start

```bash
gitwise doctor
gitwise setup --dry-run
gitwise setup-agents --local --dry-run
gitwise summarize
```

The first three commands inspect or plan changes. Add `--yes` only after reviewing
the plan.

## Five workflows

### 1. Prepare a repository

Check the environment, preview modern Git defaults, and install the canonical
agent layout:

```bash
gitwise doctor --json
gitwise setup --dry-run
gitwise setup --yes
gitwise setup-agents --local --dry-run
gitwise setup-agents --local --yes
```

`setup` and `setup-agents` do not change `commit.gpgsign` or `user.signingkey`.

### 2. Give an agent bounded context

Use structured summaries instead of feeding an agent an unbounded raw diff:

```bash
gitwise context --json
gitwise context --max-entries 50 --json
gitwise summarize --json
gitwise diff --stat --json
```

`context --json` defaults to 100 tree entries and reports `tree_total` plus
`tree_truncated` when it omits entries.

### 3. Isolate agent work

Create a sibling worktree for a branch and use the path printed by the command:

```bash
gitwise worktree new feature/agent-task
gitwise worktree list --json
```

Use `gitwise worktree remove feature/agent-task --dry-run` before removal.

### 4. Review and commit safely

Inspect staged changes, scan for likely secrets, then create a conventional,
GPG-signed commit through the repository's Git configuration:

```bash
gitwise diff --staged --scan-secrets
gitwise commit -m "fix: handle empty configuration"
```

gitwise blocks known signing and hook bypasses in generated agent rules. It does
not create or replace signing keys.

### 5. Maintain the repo and check a PR

Keep maintenance explicit and inspect GitHub state without changing it:

```bash
gitwise audit --quick
gitwise clean --branches --dry-run
gitwise optimize --dry-run
gitwise pr checks
gitwise pr create --fill
```

`pr` delegates GitHub operations to `gh`; authenticate `gh` before using it.

## Core commands

| Command | Purpose |
|---|---|
| `setup-agents` | Install the canonical multi-agent layout and provider templates |
| `worktree` | Isolate branch work in sibling directories |
| `summarize` | Produce compact status, log, and optional diff context |
| `context` | Produce bounded repository context with truncation metadata |
| `diff` | Inspect focused, staged, statistical, or patch output |
| `commit` | Guard and create conventional commits |
| `audit` | Diagnose stale branches, repository structure, and maintenance gaps |

Support commands such as `doctor`, `setup`, `status`, `clean`, `optimize`, `pr`,
`commands`, and `schema` serve those workflows. For all 30 commands, aliases,
flags, and examples, see:

- [Command reference (English)](docs/reference/commands.md)
- [Referencia de comandos (Español)](docs/es/reference/commands.md)

## JSON contract for agents

Global machine flags work before or after the subcommand:

```bash
gitwise --json status
gitwise status --json
gitwise commands --json
gitwise schema diff --json
```

Most JSON commands use the standard v3 envelope:

```json
{"v":3,"ok":true,"command":"status","data":{},"hints":[],"errors":[]}
```

Use `command` and stable error `code` values for branching. Treat `data` as the
command-specific payload. `setup-agents` retains versioned compatibility fields;
inspect its current contract with `gitwise schema setup-agents --json`.

## Safety model

- Git subprocesses scrub executable/config injection variables and use explicit timeouts.
- Destructive batch commands require confirmation; JSON mode returns an explicit gate.
- `diff --scan-secrets` and `commit` detect high-confidence credential patterns.
- setup-agents symlink creation is sandboxed to the target repository.
- CI runs ruff, basedpyright, pytest with a 75% coverage floor, pip-audit, and shellcheck.

See [Security Policy](SECURITY.md) for vulnerability reporting.

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

Run the non-destructive current demo from a Git repository:

```bash
bash demo/script.sh
```

## License

[MIT](LICENSE) - Deiner
