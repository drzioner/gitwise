# Why gitwise

## The problem

Claude Code consumes unnecessary context with verbose git operations:
- `git diff` without `--stat` can generate thousands of lines
- `git log` without a limit pulls the entire history
- No native way to tell Claude "only use git diff --stat"

Issue [claude-code#21892](https://github.com/anthropics/claude-code/issues/21892) (closed as duplicate, no official fix as of May 2026).

## gitwise's solution

Three layers of protection:

1. **CLAUDE.md** (`setup-agents`) — instructions in the repo so Claude uses
   compact commands: `git diff --stat`, `git --no-pager log --oneline -n 20`
2. **settings.json** (`setup-agents`) — `allow` only safe git commands,
   `deny` for GPG bypass and dangerous commands
3. **Git hooks strategy** (`setup`) — git hooks (pre-commit, commit-msg) managed
   with `--hooks-mode preserve|native|legacy|skip` to validate GPG and
   conventional commits independently of Claude Code

## Why not Claude Code's PreToolUse/PostToolUse hooks

Issues [#6305](https://github.com/anthropics/claude-code/issues/6305), [#24327](https://github.com/anthropics/claude-code/issues/24327), [#34859](https://github.com/anthropics/claude-code/issues/34859) document that hooks don't execute reliably on macOS. GPG protection must live at the git layer (native Git hooks or `core.hooksPath`), not in Claude Code.

## Design decisions

See [AGENTS.md](../AGENTS.md) for architecture details.
