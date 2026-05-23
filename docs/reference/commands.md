# Command Reference

[English](commands.md) | [Español](../es/reference/commands.md)

Complete command reference for `gitwise`.

## Core setup and diagnostics

### `gitwise doctor`

Check runtime environment: Python, git, platform, and optional tools.

```bash
gitwise doctor
gitwise doctor --json
```

### `gitwise setup`

Apply modern Git defaults (`fetch.prune`, histogram diff, maintenance, safe hook strategy).

```bash
gitwise setup --dry-run
gitwise setup --yes
gitwise setup --hooks-mode preserve
gitwise setup --hooks-mode native
gitwise setup --hooks-mode legacy
gitwise setup --hooks-mode skip
```

`--hooks-mode` behavior:

- `preserve` (default): keep existing hook managers/config (`lefthook`, `husky`, custom `core.hooksPath`) and avoid conflicts.
- `native`: use Git config hooks (`hook.<name>.event` + `hook.<name>.command`) when supported by installed Git.
- `legacy`: force Gitwise hooks via `core.hooksPath`.
- `skip`: don't manage hooks in `setup`.

### `gitwise setup-agents`

Install canonical agents files globally (default) or in the current repo (`--local`).

- Canonical-first layout: `AGENTS.md` + `.agents/skills/`
- Provider integrations (Claude, Cursor, Continue, opencode, Codex, Aider, Pi) stay optional via `--providers`
- Deprecated compatibility alias: `--providers claude-only` is treated as `claude`
- `--migrate-legacy-claude` forces migration from legacy Claude-only layout to canonical layout in local mode
- `--json` output for this command uses schema `v=3` with `canonical_layout` and `v_compat: [1, 2, 3]`

```bash
gitwise setup-agents --local --dry-run
gitwise setup-agents --local --yes
gitwise setup-agents --local --yes --migrate-legacy-claude
gitwise setup-agents --list-providers
gitwise setup-agents --dry-run --providers cursor
gitwise setup-agents --local --yes --providers cursor aider
```

## Daily context and review

### `gitwise summarize`

Compact status + log output designed for human and AI context.

```bash
gitwise summarize
gitwise summarize --json
gitwise summarize --diff
gitwise summarize --max-commits 5
```

### `gitwise diff`

Focused changed-file view with diffstat by default.

```bash
gitwise diff
gitwise diff --staged
gitwise diff --name-only
gitwise diff --patch
gitwise diff --json
```

### `gitwise status`

Enhanced status with staged/unstaged/untracked and ahead/behind.

```bash
gitwise status
gitwise status --json
```

### `gitwise log`

Readable log with filters and JSON output.

```bash
gitwise log
gitwise log --oneline
gitwise log --author "user"
gitwise log --grep "fix"
gitwise log --since "2026-01-01"
gitwise log --file gitwise/diff.py
gitwise log --json
```

### `gitwise show`

Inspect commit details.

```bash
gitwise show
gitwise show abc123
gitwise show --json
```

### `gitwise context`

Enriched repo snapshot for LLM workflows.

```bash
gitwise context
gitwise context --json
```

### `gitwise health`

Repository health score and grade.

```bash
gitwise health
gitwise health --json
```

## Repository maintenance

### `gitwise audit`

Read-only diagnostics for stale branches, missing commit graph, fsmonitor, stashes, blobs.

```bash
gitwise audit
gitwise audit --quick
gitwise audit --json
```

### `gitwise clean`

Clean stale branches/refs.

```bash
gitwise clean --branches --dry-run
gitwise clean --branches --yes
gitwise clean --branches --json
```

### `gitwise optimize`

Optimize object database and commit graph.

```bash
gitwise optimize --dry-run
gitwise optimize --yes
```

### `gitwise snapshot`

Generate `.claude/git-snapshot.md` for session context.

```bash
gitwise snapshot
```

### `gitwise worktree`

Create and clean sibling worktrees.

```bash
gitwise worktree new feature/my-branch
gitwise worktree clean
gitwise worktree clean --dry-run
```

## Collaboration and release flow

### `gitwise commit`

Conventional commit helper.

```bash
gitwise commit -m "feat: add command"
gitwise commit --dry-run -m "fix: handle edge case"
gitwise commit --json -m "docs: update guide"
```

### `gitwise branches`

Branch dashboard with commit-age metadata.

```bash
gitwise branches
gitwise branches --stale
gitwise branches --remote
gitwise branches --json
```

### `gitwise sync`

Fetch + optional pull/push.

```bash
gitwise sync
gitwise sync --pull
gitwise sync --push
gitwise sync --dry-run
gitwise sync --json
```

### `gitwise pr`

GitHub PR wrapper (`gh` required).

```bash
gitwise pr list
gitwise pr checks 123
gitwise pr view 123
gitwise pr comments 123
gitwise pr view 123 --json
```

### `gitwise undo`

Undo recent commits with reflog-based safety.

```bash
gitwise undo
gitwise undo --soft
gitwise undo --json
```

### `gitwise stash`

Stash list/show/pop/drop/clear.

```bash
gitwise stash list
gitwise stash show --patch
gitwise stash pop
gitwise stash drop
gitwise stash clear --dry-run
gitwise stash list --json
```

### `gitwise tag`

Semver-aware tags with `--bump` support.

```bash
gitwise tag list
gitwise tag create v1.0.0
gitwise tag create --bump minor
gitwise tag create --bump major -m "Release 2.0"
gitwise tag list --json
```

### `gitwise merge`

Merge/rebase helper with preflight checks.

```bash
gitwise merge feature-branch
gitwise merge feature-branch --rebase
gitwise merge feature-branch --no-ff
gitwise merge feature-branch --dry-run
gitwise merge feature-branch --json
```

### `gitwise conflicts`

Conflict detection and optional auto-resolution.

```bash
gitwise conflicts
gitwise conflicts --ours
gitwise conflicts --theirs
gitwise conflicts --json
```

### `gitwise suggest`

Heuristic commit-message suggestion from staged diff.

```bash
gitwise suggest
gitwise suggest --json
```

### `gitwise pick`

Cherry-pick or revert with continue/abort support.

```bash
gitwise pick abc123
gitwise pick abc123 def456
gitwise pick --revert abc123
gitwise pick --continue
gitwise pick --abort
gitwise pick --dry-run
```

### `gitwise update`

Update gitwise from its install directory.

```bash
gitwise update
gitwise update --json
```
