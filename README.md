# gitwise

Zero-dependency Python CLI for optimizing git workflows and Claude Code integration.

[![CI](https://github.com/drzioner/gitwise/actions/workflows/ci.yml/badge.svg)](https://github.com/drzioner/gitwise/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

Resolves three concrete friction points:

1. **Verbosity**: Claude Code uses raw `git diff` without filters, wasting context tokens
2. **Latency**: repos without `commit-graph`/`fsmonitor`/`maintenance` are slow
3. **GPG bypass**: Claude Code ignores `commit.gpgsign=true` ([#7711](https://github.com/anthropics/claude-code/issues/7711), [#38067](https://github.com/anthropics/claude-code/issues/38067))

## Requirements

- Python >= 3.10
- git >= 2.29 (October 2020)
- macOS (Linux works but `fsmonitor` is unavailable)

## Installation

```bash
git clone https://github.com/drzioner/gitwise.git ~/.local/share/gitwise
bash ~/.local/share/gitwise/install.sh
```

To update:

```bash
gitwise update
```

## Commands

### `gitwise doctor`

Checks your environment: git version, Python, platform, optional tools
(`bat`, `delta`, `rg`, `eza`, `git-sizer`, `watchman`).

```bash
gitwise doctor
gitwise doctor --json
```

### `gitwise setup-agents`

Injects Claude Code configuration into the current repo (`--local`, default)
or globally into `~/.claude/`: `CLAUDE.md` with git conventions,
`.claude/settings.json` with allow/deny rules, skills for `/git-audit`,
`/git-clean`, `/git-optimize`.

```bash
gitwise setup-agents --local --dry-run   # preview changes
gitwise setup-agents --local --yes       # run without confirmation
gitwise setup-agents                      # global mode (installs to ~/.claude/)
```

Idempotent. Never modifies `commit.gpgsign` or `user.signingkey`.

### `gitwise setup`

Applies modern git defaults: `fetch.prune`, `diff.algorithm=histogram`,
`push.autoSetupRemote`, `commit-graph`, `core.hooksPath` for GPG + conventional
commits, and more. Only enables `fsmonitor` on macOS (git >= 2.36).

```bash
gitwise setup --dry-run
gitwise setup --yes
```

Idempotent. Never touches `commit.gpgsign` or `user.signingkey`.

### `gitwise audit`

Read-only repository diagnostics: `[gone]` branches, missing commit-graph,
disabled `fsmonitor`, old stashes, large files in HEAD. Each finding includes
severity, suggested fix, and cost of ignoring it.

```bash
gitwise audit
gitwise audit --quick      # skip large blob search
gitwise audit --json       # structured output for Claude Code
```

### `gitwise summarize`

Compact status + log. Designed to give Claude Code context without consuming
tokens with full `git diff`. Uses `bat` for log highlighting and `delta` for
`--diff` when a TTY is available.

```bash
gitwise summarize
gitwise summarize --json           # for Claude Code
gitwise summarize --diff           # includes diff (via delta if available)
gitwise summarize --max-commits 5
```

### `gitwise snapshot`

Generates `.claude/git-snapshot.md` with repo state: current branch, status,
last 10 commits, stashes, worktrees. Claude Code reads it on session start.

```bash
gitwise snapshot
```

### `gitwise clean --branches`

Removes local branches whose upstream was deleted (`[gone]`). Protects by
default: `main`, `master`, `develop`, `dev`, `trunk`, `release`, the current
branch, and any branch active in a worktree.

```bash
gitwise clean --branches --dry-run   # preview deletions
gitwise clean --branches --yes       # delete without confirmation
gitwise clean --branches --json      # structured output
```

### `gitwise optimize`

Writes `commit-graph` (with `--changed-paths`), runs `git repack -A -d
--write-bitmap-index` and `git prune`. Checks the `gc.pid` lock before
repacking. Reports space saved in KB.

```bash
gitwise optimize --dry-run
gitwise optimize --yes
```

### `gitwise worktree`

Helpers for the "one Claude agent per worktree" workflow.

```bash
gitwise worktree new feature/my-branch   # creates worktree in sibling directory
gitwise worktree clean                   # prune + detect orphans
gitwise worktree clean --dry-run
```

### `gitwise diff`

Focused changed-file list — alias for `git diff --name-status HEAD`.

```bash
gitwise diff
```

### `gitwise update`

Updates gitwise by running `git pull` in the installation directory.

```bash
gitwise update
```

## GPG protection

`setup` and `setup-agents` **never** modify `commit.gpgsign` or
`user.signingkey`. They only report status. Protection lives in two layers:

- **`core.hooksPath`** (installed by `setup`): `pre-commit` hook validates that
  the signing key is available in the keyring before each commit.
- **`.claude/settings.json`** (installed by `setup-agents`): deny rules for
  `git commit --no-gpg-sign`, `git commit --no-verify`, `git -c commit.gpgsign=false`.

## Visual integration

When a TTY is available and tools are installed:

- **`bat`**: highlights log in `summarize` (`Git Log`) and status (`Git Output`).
  Audit findings render as Markdown.
- **`delta`**: renders diff in `summarize --diff`.

Degrades gracefully to plain output when unavailable.

## Environment variables

| Variable | Description |
|---|---|
| `GITWISE_DEBUG=1` | Prints each `git` command to stderr |
| `GITWISE_BIN_DIR` | Binary installation directory (default: `~/.local/bin`) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and feature requests welcome
at [GitHub Issues](https://github.com/drzioner/gitwise/issues).

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

[MIT](LICENSE) — Deiner
