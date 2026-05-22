# Design notes

[English](NOTES.md) | [Español](NOTES.es.md)

## Stack: Python package + 6-line Bash entry-point

Alternative considered: pure Bash. Rejected because `clean --branches` and
`setup` need robust error handling, pathlib, and pytest tests. Python startup
(~50ms) is irrelevant for an interactive CLI.

## GPG enforcement: Git hooks strategy, not Claude Code hooks

Issues `#6305`/`#24327` confirm that PreToolUse/PostToolUse are unreliable on
macOS. GPG protection lives in `share/hooks/pre-commit` and is installed by
`setup` using a safe strategy: `--hooks-mode preserve|native|legacy|skip`.

`setup` NEVER modifies `commit.gpgsign`. It only reports status.

## setup-agents vs setup: intentional separation

`setup-agents` generates static files (CLAUDE.md, settings.json, slash-commands).
`setup` modifies git config (fetch.prune, diff.algorithm, etc.).
They are independent — one can be used without the other.

## summarize and context are complementary

`summarize` and `context` are both supported.

- `summarize` focuses on compact status + commit history for day-to-day use.
- `context` provides an enriched repository snapshot for LLM workflows.

Keeping both avoids overloading one command with two different intents.

## eza is not used for branch listings

`eza` is a directory lister with colors. For arbitrary branch name strings,
Python's structured output is more appropriate. `eza` could be used for
directory output in `worktree new`, if applicable.

## fsmonitor: macOS/Windows only

`git config core.fsmonitor true` has no backend on Linux (PR `git/git#1352`
still in `seen` as of May 2026). `setup` detects `platform.system()` before
applying.

## feature.manyFiles: gated on git >= 2.40

`feature.manyFiles=true` activates sparse index and extra untracked cache that
can break git clients < 2.40. `setup` checks the version before applying.

## Audit log: XDG, not .git/

`.git/gitwise-audit.log` is lost with `git clone --mirror`. The log goes in
`~/.local/share/gitwise/audit.log` (XDG Base Dir spec).

## Tests: --no-gpg-sign only in synthetic fixtures

Test fixtures use `git commit --no-gpg-sign` because they are temporary
synthetic repos. Real user repos have `commit.gpgsign=true` protected by the
pre-commit hook.

## bat/delta: IS_TTY as gate

`bat_pipe()` in `output.py` checks `IS_TTY` before launching the subprocess.
This ensures tests (which use `capture_output=True`, no TTY) never invoke bat,
and piped output doesn't either. `--language` is passed explicitly because bat
cannot infer content type from stdin.

- `summarize`: log → `Git Log`, status → `Git Output`
- `audit`: findings → `Markdown` (backticks in `fix:` commands get highlighted)
