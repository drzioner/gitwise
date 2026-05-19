# Action Plan — gitwise v0.12.0

## Goal

Add multi-agent adapter support to setup-agents, enabling gitwise to configure rules/instructions for Cursor, Continue, opencode, Codex, Aider, and Pi — not just Claude Code.

## Phase 1: Adapter Registry

- [x] Create `gitwise/setup_agents/adapters/base.py` — AdapterConfig, AdapterState dataclasses
- [x] Create adapter modules: cursor.py, continue_adapter.py, opencode.py, codex.py, aider.py, pi.py
- [x] Create `gitwise/setup_agents/adapters/__init__.py` — registry with ADAPTERS dict, list_adapters(), resolve_adapter_selection(), detect_adapter_state(), plan_adapter_actions()

## Phase 2: Templates

- [x] Create `share/cursor/rules/gitwise.mdc`
- [x] Create `share/continue/rules/gitwise.md`
- [x] Create `share/opencode/agents/gitwise.md`
- [x] Create `share/codex/agents/gitwise.md`
- [x] Create `share/aider/gitwise.md`
- [x] Create `share/pi/skills/gitwise.md`

## Phase 3: CLI Integration

- [x] Add `--adapters` and `--list-adapters` flags to `__main__.py`
- [x] Add adapter parameter passthrough in `_cli_setup_agents.py`
- [x] Add `adapter-create` action type in `exec.py`
- [x] Add `adapter-create` to `build_action_summary()` in `types.py`

## Phase 4: i18n

- [x] Add keys: `adapter_created`, `unknown_adapter`, `adapters_available`, `adapter_exists`, `adapter_no_template`
- [x] All user-facing strings in adapters use `t()` — no f-strings or hardcoded English

## Phase 5: Tests

- [x] Create `tests/test_adapters.py` — list, dry-run, execution, idempotency, JSON, global mode rejection
- [x] All 430+ tests pass

## Phase 6: Documentation

- [x] Update AGENTS.md — coverage note, project structure, test count
- [x] Update ROADMAP.md — Phase 11 and Phase 12
- [x] Update README.md — demo section with asciinema badge
- [x] Create `docs/action-plan-v0.12.md`

## Verification

- `ruff check gitwise/ tests/` — clean
- `ruff format gitwise/ tests/` — clean
- `uv run pytest -q --tb=short` — all 430+ tests pass
- `uv run python -m gitwise setup-agents --list-adapters` — shows 6 adapters
- `uv run python -m gitwise setup-agents --local --dry-run --yes --adapters cursor` — adapter dry-run works
