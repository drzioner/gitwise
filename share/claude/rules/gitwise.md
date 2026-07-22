---
name: gitwise
description: Use gitwise CLI for git operations — gitwise diff, summarize, worktree
globs: "**/*"
---

## Use gitwise commands in tool calls

- Changed files: `gitwise diff` — never raw `git diff`
- Status + log: `gitwise summarize` — never raw `git status` or `git log`
- Branch switch: `gitwise worktree new <branch>` — never `git stash + checkout`
- Snapshot: `gitwise snapshot`; writes `.agents/git-snapshot.md` when `.agents/` exists, otherwise `.claude/git-snapshot.md`

## Shell note

`gw`, `gitwise`, and `python -m gitwise` all work in Bash tool calls.
