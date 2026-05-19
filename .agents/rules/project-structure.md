# Project Structure

```
gitwise/             # Python package — one module per subcommand
  __main__.py        # argparse router → dispatches to run_<cmd>()
  setup_agents/      # setup-agents sub-package (plan, state, exec, types, format)
  setup_agents/adapters/  # multi-agent adapter registry (cursor, continue, opencode, codex, aider, pi)
  _cli_setup_agents.py  # CLI adapter for setup-agents
  _runtime_config.py  # immutable runtime settings (theme, color, TTY, bat/delta)
  i18n.py            # t(), confirm_responses(), reset_cache() — loads from _i18n_data.json
  _i18n_data.json    # i18n string catalog (es/en, 630+ keys)
  git.py             # git subprocess helpers (is_repo, repo_root, config, run, _get_timeout)
  output.py          # Rich Console engine: ok/warn/error/info/debug/print_json/bat_pipe
  design.py          # ThemeTokens (hex), GitwiseHelpFormatter (raw ANSI), text utilities
  snapshot.py        # generates .claude/git-snapshot.md
  doctor.py          # environment checks
  audit.py           # repo diagnostics
  setup.py           # modern git defaults
  clean.py           # stale branch/ref cleanup
  optimize.py        # gc, pack-refs, commit-graph
  summarize.py       # compact status + log
  diff.py            # focused changed-file list (gitwise diff)
  worktree.py        # worktree helpers for Claude agents
share/claude/        # Templates copied/merged into target repos
share/cursor/        # Cursor adapter templates
share/continue/      # Continue adapter templates
share/opencode/      # opencode adapter templates
share/codex/         # Codex adapter templates
share/aider/         # Aider adapter templates
share/pi/            # Pi adapter templates
tests/               # pytest — mirrors gitwise/ modules
  conftest.py        # shared fixtures + run_gitwise() helper
  test_adapters.py   # adapter system tests (--adapters, --list-adapters)
bin/gitwise          # Shell wrapper → .venv/bin/python (or python3 fallback)
install.sh           # Installs to ~/.local/bin
```
