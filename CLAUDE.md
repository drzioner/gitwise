@AGENTS.md

## Claude Code — Specific

- Claude Code's non-interactive shell does NOT source `~/.zshrc`. Use `python -m gitwise` or `uv run python -m gitwise`.
- `gw` alias is NOT available. Use `gitwise` or `python -m gitwise` in Bash tool calls.
- Scoped rules are loaded via `.claude/rules/` (symlinked from `.agents/rules/`).
- Run `ruff check` and `ruff format --check` before committing.
- Run `uv run pytest` after any change to `setup_agents/` or its tests.
- All commits must be GPG-signed (`git commit -S`). Never use `--no-gpg-sign`.
