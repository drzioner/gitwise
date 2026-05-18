# Review Analysis Report — gitwise v0.10.3

**Date:** 2026-05-18
**Analyzed versions:** v0.10.2 (Claude Review, 2026-05-17), v0.10.3 (DeepSeek Review, 2026-05-18)
**Current version:** v0.10.3 (unreleased bump, commit 5767e55)
**Methodology:** Multi-perspective verification (8 expert profiles), autoresearch-style empirical checks

---

## 1. Sources Analyzed

| Document | Author | Date | Depth |
|----------|--------|------|-------|
| `review/claude_code_review_repo_drzioner_gitwise.md` | Claude Code | 2026-05-17 | Exhaustive (233 lines, 11 sections) |
| `review/deepseek_review_repo_gitwise.md` | DeepSeek | 2026-05-18 | Summary (62 lines) |

---

## 2. Verified Metrics (Empirical)

| Metric | ROADMAP (v0.7.0) | Actual (v0.10.3) | Method |
|--------|-------------------|-------------------|--------|
| Version | 0.7.0 | **0.10.3** | `gitwise/__init__.py` |
| Tests | 241 | **326** | `uv run pytest --co -q` |
| i18n keys | 304 | **624** | `python3 -c "import json; ..."` on `_i18n_data.json` |
| Commands (run_\*) | 27 | **27** + 3 aliases | `grep 'def run_' gitwise/*.py` |
| Dispatch entries | 27 | **30** | `__main__.py:_DISPATCH` |
| Source files (.py) | — | **47** | `find gitwise -name "*.py"` |
| Source LOC | — | **5,840** | `wc -l gitwise/*.py` |
| Test files | — | **35** | `find tests -name "*.py"` |
| Test LOC | — | **3,481** | `wc -l tests/*.py` |
| Commits | 46 | **47** | `git --no-pager log --oneline` |
| Tags | 16 | **16** (v0.1.0→v0.10.2) | `git tag --sort=-version:refname` |
| Zero runtime deps | Yes | **Yes** | No `[project.dependencies]` in pyproject.toml |
| Build system | hatchling | **hatchling** | pyproject.toml `[build-system]` |
| Python min | 3.10 | **3.10** | `requires-python = ">=3.10"` |
| Platform | macOS, Linux | **macOS, Linux** | Classifiers (no Windows) |
| License | MIT | **MIT** | pyproject.toml |
| Status | Beta (4) | **Beta (4)** | Classifier |
| CI badge | Present | **Present** | README line 5 |
| ruff check | Pass | **Pass** | `ruff check gitwise/ tests/` |
| ruff format | Pass | **Pass** | `ruff format --check gitwise/ tests/` |
| All tests pass | Yes | **Yes** | 326 passed in 55.82s |
| Coverage (reported) | — | **22%** | `uv run pytest --cov=gitwise` |
| Coverage (real) | — | **UNKNOWN** | subprocess testing pattern (see Section 5) |

---

## 3. Claude Code Review — Claim-by-Claim Verification

### 3.1 Accurate Claims (VERIFIED)

| # | Claim | Evidence |
|---|-------|----------|
| 1 | "27+ comandos implementados" | 27 `run_*` functions + 3 argparse aliases |
| 2 | "Zero runtime deps" | No `[project.dependencies]` in pyproject.toml |
| 3 | "hatchling build backend" | `build-backend = "hatchling.build"` |
| 4 | "Python >= 3.10" | `requires-python = ">=3.10"` |
| 5 | "Beta (Development Status 4)" | Classifier confirmed |
| 6 | "commitizen major_version_zero=true" | pyproject.toml line 83 |
| 7 | "lefthook pre-commit" | lefthook.yml with ruff + shellcheck + cz check + pytest |
| 8 | "pip-audit como dev dep" | In `[dependency-groups] dev` |
| 9 | "MIT License" | `license = "MIT"` |
| 10 | "i18n es/en" | _i18n_data.json confirmed |
| 11 | "Un solo autor" | `git shortlog` confirms 1 contributor |
| 12 | "Idempotente setup" | Code pattern: check before write |
| 13 | "setup-agents 5-bucket model" | AGENTS.md documents it |
| 14 | "No consume APIs de IA" | No external HTTP calls anywhere in codebase |
| 15 | "Sistema i18n propio" | 624 keys, t() function, es/en catalog |
| 16 | "Schema JSON v:2 con ok field" | Documented in AGENTS.md |
| 17 | "fsmonitor solo macOS" | AGENTS.md + code conditional |

### 3.2 Outdated Claims

| # | Claim | Review Value | Actual Value | Delta |
|---|-------|-------------|--------------|-------|
| 1 | "241 tests" | 241 (at v0.7.0) | **326** | +85 tests (+35%) |
| 2 | "304 i18n keys" | 304 (at v0.7.0) | **624** | +320 keys (+105%) |
| 3 | "46 commits" | 46 (at review time) | **47** | +1 commit |
| 4 | "16 releases" | 16 (v0.1.0→v0.10.2) | **16** + v0.10.3 untagged | +1 pending |

### 3.3 Claims Not Verified (Need External Access)

| # | Claim | Reason |
|---|-------|--------|
| 1 | "0 stars, 0 forks, 0 watchers" | Requires GitHub API |
| 2 | "CI badge green" | Requires GitHub Actions access |
| 3 | "Not published on PyPI" | Plausible but not confirmed |
| 4 | "12 followers, 71 following" (author profile) | Requires GitHub API |

### 3.4 Critical Finding NOT in Review

**Subprocess testing pattern makes coverage measurement misleading.** All 155 `run_gitwise()` invocations execute `python -m gitwise` as a subprocess. `pytest --cov` only measures modules imported in the test process, not subprocess code. The reported 22% coverage is therefore inaccurate — the real coverage is unknown but significantly higher. 24 of 27 command modules show 0% coverage in the report despite being tested via subprocess.

---

## 4. DeepSeek Review — Claim-by-Claim Verification

### 4.1 Accurate Claims (VERIFIED)

| # | Claim | Evidence |
|---|-------|----------|
| 1 | "v0.10.2" | True at review time (now v0.10.3) |
| 2 | "fsmonitor solo macOS" | Code confirms conditional |
| 3 | "bat y delta opcionales" | `_runtime_config.py` uses `shutil.which()` |
| 4 | "Sin comunidad" | No external evidence of adoption |

### 4.2 Subjective Claims (OPINION)

| # | Claim | Assessment |
|---|-------|------------|
| 1 | "Azúcar sintáctico en exceso" | Partially valid: commands are wrappers but add `--json`, `--dry-run`, `--yes` consistently — value is in uniformity, not novelty |
| 2 | "Confusión de nombres" | Valid: "gitwise" is a generic name, potential PyPI collision |
| 3 | "Para devs sin Claude Code, pocas ventajas" | Fair assessment for human-only users |

### 4.3 Missing Analysis

The DeepSeek review lacks:
- Empirical verification of any claim
- Code architecture analysis
- Comparison with alternatives
- Test quality assessment
- Security surface analysis
- Specific actionable recommendations

---

## 5. Critical Finding: Coverage Measurement Gap

### Root Cause

`tests/conftest.py:26-39` defines `run_gitwise()` which invokes:

```python
subprocess.run(
    [sys.executable, "-m", "gitwise"] + list(args),
    capture_output=True, text=True, ...
)
```

This runs gitwise as a **separate process**. `pytest --cov` instruments the parent process only.

### Impact

| Module | Reported Coverage | Actually Tested? |
|--------|-------------------|-----------------|
| audit.py | 0% | YES (via subprocess) |
| branches.py | 0% | YES (via subprocess) |
| commit.py | 0% | YES (via subprocess) |
| conflicts.py | 0% | YES (via subprocess) |
| context.py | 0% | YES (via subprocess) |
| diff.py | 0% | YES (via subprocess) |
| doctor.py | 0% | YES (via subprocess) |
| health.py | 0% | YES (via subprocess) |
| log.py | 0% | YES (via subprocess) |
| merge.py | 0% | YES (via subprocess) |
| pick.py | 0% | YES (via subprocess) |
| pr.py | 0% | YES (via subprocess) |
| setup.py | 0% | YES (via subprocess) |
| show.py | 0% | YES (via subprocess) |
| snapshot.py | 0% | YES (via subprocess) |
| stash.py | 0% | YES (via subprocess) |
| status.py | 0% | YES (via subprocess) |
| suggest.py | 0% | YES (via subprocess) |
| summarize.py | 0% | YES (via subprocess) |
| sync.py | 0% | YES (via subprocess) |
| tag.py | 0% | YES (via subprocess) |
| undo.py | 0% | YES (via subprocess) |
| update.py | 0% | YES (via subprocess) |
| worktree.py | 0% | YES (via subprocess) |

### Measured Coverage (Real)

Only modules directly imported in the test process show coverage:

| Module | Coverage | Reason |
|--------|----------|--------|
| setup_agents/ (package) | 57-97% | Directly imported in test_sa_plan.py, test_sa_unit.py |
| clean.py | 79% | Directly imported in test_clean.py |
| optimize.py | 73% | Directly imported in test_optimize.py |
| git.py | 69% | Directly imported in test_git.py, test_optimize.py |
| i18n.py | 80% | Directly imported in test_i18n.py |
| output.py | 65% | Directly imported in test_output.py |

### Recommended Fix (Priority 2)

Use `COVERAGE_PROCESS_START` environment variable or add complementary unit tests that call `run_*()` directly.

---

## 6. v0.10.3 Refactor Analysis

Commit `5767e55` (2026-05-18) performed a 6-phase architecture cleanup:

### Changes

| Category | Detail |
|----------|--------|
| Old monolith → Package | `_sa_exec.py` (248→10 LOC), `_sa_plan.py` (316→12), `_sa_state.py` (148→11), etc. → `setup_agents/` package (1,345 LOC across 8 modules) |
| New files | `_runtime_config.py` (63 LOC), `setup_agents/__init__.py`, `exec.py`, `plan.py`, `plan_skills.py`, `plan_gitfiles.py`, `state.py`, `types.py`, `format.py` |
| Stub files | 6 `_sa_*.py` files kept as thin re-export stubs (9-12 LOC each) |
| Test migration | `test_sa_unit.py` + `test_sa_plan.py` added (687 LOC), imports via stubs |
| Guidelines | 5 new files in `docs/guidelines/` (architecture, python-guidelines, testing-guidelines, anti-patterns, README) |
| AGENTS.md | Updated with new structure references |

### Assessment

- **Well executed**: Clean separation of concerns, proper package structure
- **Compatibility maintained**: Stubs preserve backward-compatible imports
- **No functional changes**: Pure refactor, all 326 tests pass
- **Risk**: Stubs create import indirection — should be cleaned up when no external consumers exist

---

## 7. Expert Perspectives Summary

### Principal Python Engineer
- **CRITICAL**: Coverage measurement gap (22% misleading)
- **HIGH**: ROADMAP outdated (v0.7.0 numbers)
- **MEDIUM**: Refactor well executed, stubs should eventually be removed

### Security Engineer
- **HIGH**: File write surface (hooksPath, settings.json, symlinks)
- **MEDIUM**: No telemetry/external calls = positive
- **LOW**: install.sh lacks integrity verification

### DevOps/SRE
- **CRITICAL**: No PyPI distribution
- **HIGH**: CI/CD pipeline quality unverified (no GitHub access)
- **MEDIUM**: `gitwise update` does unverified `git pull`

### Product Manager
- **HIGH**: Claude Code dependency is strategic risk
- **HIGH**: Generic name "gitwise" limits discoverability
- **MEDIUM**: 27 commands without clear prioritization of killer features

### QA Engineer
- **HIGH**: Cannot measure real test coverage
- **MEDIUM**: Good fixture design, no stress/fuzzing tests
- **LOW**: No visual regression testing

### Technical Writer
- **HIGH**: ROADMAP desynchronized from reality
- **MEDIUM**: No screenshots, demos, or rendered docs
- **LOW**: README is excellent for its depth

### Open Source Community Lead
- **CRITICAL**: Zero adoption validation
- **HIGH**: No CODE_OF_CONDUCT.md, no good-first-issues
- **MEDIUM**: Bus factor 1

### AI Integration Specialist
- **MEDIUM**: Claude Code integration well designed (5-bucket model)
- **MEDIUM**: No adapters for other agents (Cursor, Aider, Continue)
- **LOW**: JSON schema v:2 is clean for LLM consumption

---

## 8. Review Quality Comparison

| Dimension | Claude Review | DeepSeek Review |
|-----------|--------------|-----------------|
| Depth | Exhaustive (233 lines) | Summary (62 lines) |
| Technical rigor | High (code-level analysis) | Low (no code inspection) |
| Data verification | High (GitHub data, file inspection) | None (no verification) |
| Alternative comparison | 7 alternatives analyzed | None |
| Author profiling | Detailed | None |
| Actionable items | Yes (5 specific cases) | Generic |
| Coverage gap detection | **No** | **No** |
| ROADMAP staleness detection | **No** | **No** |
| Architecture analysis | Moderate | None |
| Overall trust score | **8.5/10** | **6/10** |
