---
name: gitwise
description: Use gitwise CLI for git operations — gitwise diff, summarize, worktree
globs: "**/*"
---

## Use gitwise commands in tool calls

- Changed files: `gitwise diff` — never raw `git diff`
- Status + log: `gitwise summarize` — never raw `git status` or `git log`
- Branch switch: `gitwise worktree new <branch>` — never `git stash + checkout`
- Snapshot: `gitwise snapshot` — regenerates `.claude/git-snapshot.md`

## Shell note

`gw` is a terminal alias only — use `gitwise` or `python -m gitwise` in Bash tool calls.
