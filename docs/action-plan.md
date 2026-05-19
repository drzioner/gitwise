# Action Plan — Priority 1: Review Actions

**Branch:** `feat/priority-1-review-actions`
**Date:** 2026-05-18
**Source:** Review analysis report (`docs/review-analysis-report.md`)

---

## Priority 1 Items (Quick Wins)

All items in this priority are **high impact + low effort**.

---

### P1.1: Update ROADMAP.md

**Problem:** ROADMAP.md still shows "Estado Actual (v0.7.0)" with outdated metrics (241 tests, 304 i18n keys). This is the first document evaluators read and it undermines credibility.

**Current state:**
```
## Estado Actual (v0.7.0)
...
**Phases 1-7 completadas.** 241 tests, 304 i18n keys (es/en), 1 runtime dep (`rich>=13.0`).
```

**Target state:**
```
## Estado Actual (v0.10.3)
...
**Phases 1-10 completadas.** 411 tests, 624+ i18n keys (es/en), 1 runtime dep (`rich>=13.0`).
```

**Files to modify:**
- `ROADMAP.md` — update header and metrics
- Add Phases 8-10 entries (currently documented in CHANGELOG but not in ROADMAP)

**Verification:**
- `grep "v0.10.3" ROADMAP.md` succeeds
- `grep "326 tests" ROADMAP.md` succeeds
- `grep "624 i18n" ROADMAP.md` succeeds

---

### P1.2: Document Coverage Measurement Gap

**Problem:** AGENTS.md section "Testing" mentions `uv run pytest --cov=gitwise` without explaining that the 22% reported coverage is misleading due to subprocess testing. ROADMAP mentions "241 tests" without coverage context.

**Current state (AGENTS.md:36):**
```bash
uv run pytest --cov=gitwise        # with coverage
```

**Target state (AGENTS.md):**
Add a note after the coverage command explaining:
- Tests run via `subprocess.run()` (155 invocations)
- `--cov` only measures modules imported in the test process
- Reported 22% is misleading — 24 command modules show 0% despite being tested
- Real coverage is unknown without subprocess-aware coverage tools

**Files to modify:**
- `AGENTS.md` — add coverage measurement note in Testing section

**Verification:**
- `grep "subprocess" AGENTS.md` finds the new note
- `grep "coverage" AGENTS.md` finds the new note

---

### P1.3: Verify CI Badge in README

**Problem:** README line 5 has a CI badge. Need to verify it's valid and update the AGENTS.md project structure to reflect v0.10.3 changes (setup_agents/ package, _runtime_config.py).

**Current state (AGENTS.md:54-61):**
```
gitwise/             # Python package — one module per subcommand
  __main__.py        # argparse router → dispatches to run_<cmd>()
  setup_agents.py    # entry point: run_setup_agents → _run_setup_local/global
  _sa_state.py       # state detection
  ...
```

**Target state:**
```
gitwise/             # Python package — one module per subcommand
  __main__.py        # argparse router → dispatches to run_<cmd>()
  setup_agents/      # setup-agents sub-package (plan, state, exec, types, format)
  _cli_setup_agents.py  # CLI adapter for setup-agents
  _runtime_config.py  # immutable runtime settings (theme, color, TTY, bat/delta)
  i18n.py            # t(), confirm_responses(), reset_cache()
  _i18n_data.json    # i18n string catalog (es/en, 624 keys)
  ...
```

**Files to modify:**
- `AGENTS.md` — update Project Structure section
- `AGENTS.md` — update "setup_agents.py — key functions" section to reference new package structure
- `AGENTS.md` — update `_i18n_data.json` description from "220+ keys" to "624 keys"

**Verification:**
- `grep "setup_agents/" AGENTS.md` finds the new package reference
- `grep "_runtime_config" AGENTS.md` finds the new module
- `grep "624" AGENTS.md` finds the updated key count

---

### P1.4: Remove Re-export Stubs

**Problem:** 6 `_sa_*.py` files exist as thin re-export stubs after the v0.10.3 refactor. They add import indirection without value. Only `tests/test_sa_unit.py` imports from them.

**Current stubs:**
- `gitwise/_sa_exec.py` (10 LOC) — re-exports from `setup_agents.exec`
- `gitwise/_sa_state.py` (11 LOC) — re-exports from `setup_agents.state`
- `gitwise/_sa_plan.py` (12 LOC) — re-exports from `setup_agents.plan`
- `gitwise/_sa_plan_skills.py` (9 LOC) — re-exports from `setup_agents.plan_skills`
- `gitwise/_sa_plan_gitfiles.py` (12 LOC) — re-exports from `setup_agents.plan_gitfiles`
- `gitwise/_sa_types.py` (9 LOC) — re-exports from `setup_agents.types`

**Action:**
1. Update `tests/test_sa_unit.py` imports to use `gitwise.setup_agents.exec` and `gitwise.setup_agents.state` directly
2. Verify `tests/test_sa_plan.py` imports (already uses `gitwise.setup_agents.*` directly)
3. Delete all 6 stub files
4. Update `AGENTS.md` if any stub references remain

**Files to modify:**
- `tests/test_sa_unit.py` — change imports
- Delete: `gitwise/_sa_exec.py`, `_sa_state.py`, `_sa_plan.py`, `_sa_plan_skills.py`, `_sa_plan_gitfiles.py`, `_sa_types.py`

**Verification:**
- `uv run pytest tests/test_sa_unit.py -v` passes
- `ruff check gitwise/ tests/` passes
- `ls gitwise/_sa_*.py` fails (files deleted)

---

### P1.5: Tag v0.10.3

**Problem:** Commit `5767e55` bumps version to 0.10.3 but no git tag exists. This breaks the semver convention and release tracking.

**Action:**
- Create git tag `v0.10.3` pointing to commit `5767e55`
- This is a tag-only action, no code changes

**Verification:**
- `git tag -l v0.10.3` succeeds
- `git log --oneline v0.10.3 -1` shows the bump commit

---

## Priority 2 Items (Strategic — Not in This Branch)

| # | Item | Effort | Impact |
|---|------|--------|--------|
| P2.1 | Publish to PyPI (`hatch publish`) | Medium | Critical for adoption |
| P2.2 | Fix coverage measurement (subprocess-aware) | Large | Critical for credibility |
| P2.3 | Add agent adapters (Cursor, Aider, Continue) | Large | High for market expansion |
| P2.4 | Screenshots/demo (asciinema) | Small | High for discoverability |

## Priority 3 Items (Fill-Ins — Not in This Branch)

| # | Item | Effort | Impact |
|---|------|--------|--------|
| P3.1 | CODE_OF_CONDUCT.md | Trivial | Medium for community |
| P3.2 | Good-first-issues labels | Trivial | Medium for contributors |
| P3.3 | README bilingüe (es) | Medium | Medium for LATAM reach |

## Priority 4 Items (Deprioritized)

| # | Item | Effort | Impact |
|---|------|--------|--------|
| P4.1 | Windows support | Very Large | Low (target is macOS/Linux) |
| P4.2 | Manpage/Sphinx docs | Large | Low (--help sufficient) |
| P4.3 | Streaming JSON | Large | Low (correctly deprioritized) |

---

## Execution Checklist

- [ ] P1.1: Update ROADMAP.md
- [ ] P1.2: Document coverage gap in AGENTS.md
- [ ] P1.3: Update AGENTS.md project structure
- [ ] P1.4: Remove stubs + migrate test imports
- [ ] P1.5: Tag v0.10.3
- [ ] Run full test suite
- [ ] Run ruff check + format
- [ ] Run autoresearch cross-validation
- [ ] Run multi-review cross-validation
- [ ] Fix any issues found
- [ ] Final verification
