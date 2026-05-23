# Refactor `gitwise setup-agents`: from Claude-centric to AI agents-first

## Document status

- Date: 2026-05-22
- Status: Approved for implementation
- Scope: design + rollout + risks + tests + acceptance criteria
- Execution rule: do not start implementation outside this plan

---

## Goal

Turn `gitwise setup-agents` into a command clearly focused on AI agents with this model:

1. Canonical by default: `AGENTS.md` + `.agents/skills/`
2. Providers (Claude/Cursor/etc.) as optional and explicit layer
3. Controlled compatibility for existing users

---

## Current problem (verified baseline)

Today `setup-agents` is still coupled to Claude layout:

- Public narrative centered on Claude (`README.md`, `README.es.md`, `pyproject.toml`)
- CLI help centered on `~/.claude/` as default (`gitwise/__main__.py`)
- Local/global planner adds `.claude/*` artifacts structurally (`gitwise/setup_agents/plan.py`)
- Skills sourced from `share/claude/skills/*` (`gitwise/setup_agents/plan_skills.py`)
- Adapters implemented as post-plan extras (`gitwise/_cli_setup_agents.py`)

Technical debt exists as well:

- Partial rollback on failures: not all action types are reverted (`gitwise/setup_agents/exec.py`)
- Flag semantics and UX inconsistencies (`--replace-claude-with-symlink`, multiple `--no-*` flags)

---

## Final decisions

### D1) Target architecture

- Canonical base: `AGENTS.md` + `.agents/skills/*`
- Claude becomes an explicit provider
- Other providers remain optional (`cursor`, `continue`, `opencode`, `codex`, `aider`, `pi`)

### D2) Compatibility and rollout

- Incremental rollout in 3 PRs
- No direct default flip in a single PR
- No full legacy test disable during transition

### D3) Flags

- Keep `--adapters`
- Add `claude` as explicit provider
- Deprecate `claude-only` for 2 minors and alias to `claude` (NOT to `none`)

### D4) JSON contract

- Move to `v=3` on behavior change
- Keep `v_compat` for existing consumers
- Keep `bucket` while compatibility window is open, with documented semantics

### D5) Auto-detection

- Out of scope for this refactor
- Providers remain explicit opt-in

---

## Non-goals

- Do not add provider auto-detection
- Do not break existing `--adapters` usage
- Do not remove legacy paths without migration
- Do not ship one mega-PR without checkpoints

---

## Approved technical design

## 1) Canonical + provider model

### Canonical layer

- `AGENTS.md` is the main convention document
- `.agents/skills/<skill>/SKILL.md` is the canonical skill location

### Provider layer

- Claude and other providers create their artifacts only when enabled
- When applicable, providers link/reference canonical artifacts

---

## 2) Alias compatibility rules

- `--adapters none`: canonical-only mode (no providers)
- `--adapters claude`: enables Claude provider
- `--adapters claude-only`: deprecated, treated as `claude`
- `--adapters cursor,aider`: enables only listed providers

---

## 3) Security and rollback (mandatory before default flip)

### Critical current risk

`_undo_partial()` does not fully revert managed-block, append, merge, and related actions.

### Required action

Before changing default to canonical:

1. Save prior state of all mutated files
2. Ensure full rollback per action type
3. Cover with mid-failure tests

Without this, behavior-change PR is blocked.

---

## Implementation plan (3 PRs)

## PR #1 - Foundations + bugfixes (no behavior change)

### Goal

Prepare provider architecture with no expected behavior change for current users.

### Changes

1. Fix inconsistent i18n keys in `plan.py`:
   - use `claude_md_symlink_other` and `claude_md_replaced`
2. Minimal adapter system refactor to support provider strategy
3. Rename internal namespace from `setup_agents/adapters` to `setup_agents/providers` with backward-compatible shims in `adapters/`
4. Introduce `providers/claude.py` as initial wrapper (without moving all logic yet)
5. Add regression tests for i18n bug
6. Register `claude` in providers registry (no behavior change)

### Acceptance criteria

- Functional output equivalent in current scenarios
- Existing tests + new regression tests pass

---

## PR #2 - Canonical switch + schema v3 (controlled behavior change)

### Goal

Enable canonical-first setup with explicit provider compatibility.

### Changes

1. Reorganize templates:
   - move canonical skills to `share/agents/skills/*`
   - keep provider-specific templates where appropriate
2. Planning refactor:
   - canonical planner first
   - provider planners second
3. Skills refactor:
   - canonical always in `.agents/skills/`
   - provider links/copies managed by adapter
4. Allow adapters in global mode as well
5. Update `format.py` to `v=3` with discriminator fields (`canonical_layout`)
6. Add clear non-destructive legacy warnings
7. Update docs and public messaging

### Acceptance criteria

- In clean repo, `setup-agents --local --yes` creates canonical layout without Claude dependency
- `--adapters claude` keeps equivalent Claude experience
- JSON contract documented and tested

---

## PR #3 - Legacy migration + cleanup

### Goal

Close transition path for users with old Claude-only layout.

### Changes

1. Add legacy migration flow (`--migrate-legacy-claude`)
2. Reuse existing `skill-migrate-to-agents` action with idempotency
3. Publish migration guide `docs/MIGRATION-0.17.md`
4. Keep `claude-only` deprecation window for 2 minors

### Acceptance criteria

- Legacy migration works in dry-run and real execution
- Re-run is idempotent

---

## Testing strategy

## Key rule

Do not mass-skip legacy suite in PR #2.

Use temporary dual coverage:

- keep relevant legacy coverage
- add v3 suite with canonical + providers matrix

## Mandatory minimum matrix

1. Local empty repo, no adapters
2. Local empty repo, with `claude`
3. Local empty repo, multi-adapter
4. Local repo with legacy Claude artifacts
5. Global mode, no adapters
6. Global mode, with `claude`
7. Mid-execution failure to validate full rollback

---

## Target files (implementation)

- `gitwise/setup_agents/plan.py`
- `gitwise/setup_agents/plan_skills.py`
- `gitwise/setup_agents/state.py`
- `gitwise/setup_agents/exec.py`
- `gitwise/setup_agents/plan_gitfiles.py`
- `gitwise/setup_agents/types.py`
- `gitwise/setup_agents/format.py`
- `gitwise/setup_agents/providers/base.py`
- `gitwise/setup_agents/providers/__init__.py`
- `gitwise/setup_agents/providers/claude.py` (new)
- `gitwise/setup_agents/adapters/*` (compatibility shims)
- `gitwise/_cli_setup_agents.py`
- `gitwise/__main__.py`
- `gitwise/_i18n_data.json`
- `share/agents/skills/*` (new canonical location)
- `README.md`, `README.es.md`
- `docs/reference/commands.md`, `docs/es/reference/commands.md`
- `docs/MIGRATION-0.17.md` (new)
- related tests

---

## Release criteria

## Technical gate

- `uv run pytest`
- `ruff check gitwise/ tests/`
- `ruff format --check gitwise/ tests/`
- `uv run basedpyright`

## Functional gate

- Local/global smoke tests from minimum matrix
- Deprecation behavior validated (`claude-only`)
- JSON v3 output validated

## Documentation gate

- README EN/ES updated
- Command reference EN/ES updated
- Migration guide published
- CHANGELOG/CHANGELOG.es updated with transition notes

---

## Open risks and mitigations

1. Incomplete rollback -> block PR #2 until transactional rollback is done
2. JSON consumer breakage -> schema v3 + compat + contract tests
3. Flag UX friction -> keep `--adapters`, gradual deprecation, clear messaging
4. Provider drift -> single canonical source + adapter-controlled links

---

## Implementation start checklist

- [x] Goal and scope closed
- [x] Technical decisions closed
- [x] PR-by-PR plan defined
- [x] Compatibility strategy defined
- [x] Critical risks identified
- [x] Acceptance and release criteria defined
- [x] PR #1 implementation started
