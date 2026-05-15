# Testing Guidelines — gitwise

> Compatible with: `pytest` · `subprocess` · `conftest.py`
> No mocks. Real integration tests on synthetic repos.
> Last reviewed: 2026-05-15

---

## 1. Stack

| Tool | Usage |
|------|-------|
| `pytest` | Test runner (only option) |
| `subprocess` | Invoke gitwise via `run_gitwise()` |
| `conftest.py` | Shared fixtures + `run_gitwise()` helper |
| `tempfile` | Temporary synthetic repos |

**NEVER** use `unittest`, `nose`, or any other test runner.

---

## 2. Philosophy: No mocks

Tests invoke gitwise as a real process via `run_gitwise()`. All git operations run on synthetic repos created by fixtures. There are no mocks for `subprocess`, filesystem, or git.

### Why

- gitwise is a thin wrapper over git — mocking git would mean mocking the core of the project
- Integration bugs (git version, flag behavior) are only caught with real git
- Synthetic repos are cheap to create and isolate

### Exception

There are no exceptions. If you need to mock something, you probably need to restructure the test.

---

## 3. The `run_gitwise()` helper

Defined in `conftest.py`. Returns a `subprocess.CompletedProcess`:

```python
def run_gitwise(
    *args: str, cwd: Path | None = None, env: dict | None = None
) -> subprocess.CompletedProcess:
    """Invoke gitwise as a subprocess. Shared by all test modules."""
    base_env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    if env:
        base_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "gitwise"] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd or PROJECT_ROOT,
        env=base_env,
    )
```

### Usage pattern in tests

```python
def test_clean_dry_run(tmp_git_repo_with_stale):
    result = run_gitwise("clean", "--branches", "--dry-run", "--json", cwd=tmp_git_repo_with_stale)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data["branches"]["stale"]) > 0
    assert data["branches"]["deleted"] == 0
```

### The `env` parameter

Override environment variables in tests:

```python
result = run_gitwise("doctor", "--json", env={"NO_COLOR": "1"})
```

---

## 4. Fixtures — synthetic repos

All fixtures create temporary git repos with pytest's `tmp_path`.

### Available fixtures

| Fixture | What it creates | Use case |
|---------|----------------|----------|
| `tmp_git_repo` | Clean repo with 1 commit (`--no-gpg-sign`) | Basic tests |
| `tmp_git_repo_with_commit_graph` | Repo with commit-graph written | Optimize tests |
| `tmp_git_repo_with_gpg_config` | Repo with `gpgsign=true` | GPG safety tests |
| `tmp_git_repo_with_stale` | Repo with 3 `[gone]` branches | Clean tests |
| `tmp_git_repo_with_large_blob` | Repo with 2MB blob | Audit tests |

### Internal conftest.py helpers

```python
def _git(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run git in test repo. Uses _GIT_ENV with test user config."""

def _init_repo(path: Path) -> None:
    """git init + user config."""

def _initial_commit(path: Path) -> None:
    """Create README.md + first commit (--no-gpg-sign)."""
```

### Creating new fixtures

When a test needs a specific repo state, create a fixture in `conftest.py`:

```python
@pytest.fixture
def tmp_git_repo_with_feature(tmp_git_repo):
    """Repo with a 'feature' branch diverged from main."""
    _git(["checkout", "-b", "feature"], tmp_git_repo)
    (tmp_git_repo / "feature.txt").write_text("feature work")
    _git(["add", "feature.txt"], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: add feature"], tmp_git_repo)
    _git(["checkout", "main"], tmp_git_repo)
    return tmp_git_repo
```

Rules:
- All new fixtures go in `conftest.py`
- All fixtures use `_git()` helper, not `subprocess` directly
- Cleanup is automatic via pytest's `tmp_path`
- **NEVER** create fixtures with real GPG signing — only `--no-gpg-sign` in test commits

---

## 5. Test structure

```
tests/
  conftest.py                   # Fixtures + run_gitwise() + _git()
  test_setup_agents.py          # 35 tests: buckets 1-5, symlinks, managed blocks
  test_setup.py                 # 5 tests: GPG safety, idempotency
  test_doctor.py                # 6 tests: version, JSON, optional tools
  test_audit.py                 # 9 tests: findings, timing, severity
  test_clean.py                 # 8 tests: dry-run, delete, protection
  test_optimize.py              # 3 tests: commit-graph, dry-run
  test_summarize.py             # 3 tests: JSON, 8KB limit
  test_diff.py                  # 13 tests: staged, unstaged, mutual exclusion
  test_snapshot.py              # 3 tests: creation, timestamp
  test_worktree.py              # 9 tests: new, clean, orphans
```

### Naming convention

```python
# CORRECT — descriptive scenario name
def test_bucket2_agents_present_claude_absent_creates_symlink(tmp_git_repo):
    ...

def test_clean_protects_current_branch(tmp_git_repo):
    ...

def test_audit_detects_large_blobs(tmp_git_repo_with_large_blob):
    ...

# PROHIBITED — generic name
def test_case_1(tmp_git_repo):
    ...

def test_it_works(tmp_git_repo):
    ...
```

---

## 6. Assertion patterns

### Exit code

```python
# CORRECT — explicit assertion
assert result.returncode == 0
assert result.returncode == 1

# PROHIBITED — assuming success
result = run_gitwise("setup-agents", cwd=str(repo))
# no returncode assert
```

### JSON output

```python
def test_json_output(tmp_git_repo):
    result = run_gitwise("audit", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0

    data = json.loads(result.stdout)

    # CORRECT — verify schema
    assert data["v"] == 2
    assert "findings" in data
    assert isinstance(data["findings"], list)

    # PROHIBITED — exact value matching (fragile when new fields are added)
    assert data == {"v": 2, "findings": [], ...}
```

### Human output

```python
def test_human_output(tmp_git_repo):
    result = run_gitwise("doctor", cwd=tmp_git_repo)
    assert result.returncode == 0

    # CORRECT — verify key text is present
    assert "git" in result.stdout.lower()
    assert "python" in result.stdout.lower()

    # AVOID — exact string matching (fragile with i18n)
    assert result.stdout == "git: 2.47.0\npython: 3.13.0\n"
```

---

## 7. GPG in tests

The **ONLY** situation where `--no-gpg-sign` is allowed: inside fixtures and tests.

```python
# CORRECT — in test fixture
_git(["commit", "--no-gpg-sign", "-m", "initial commit"], repo)

# PROHIBITED — in production code
subprocess.run(["git", "commit", "--no-gpg-sign", "-m", msg])
```

---

## 8. Test commands

```bash
# All tests
uv run pytest

# Specific module
uv run pytest tests/test_setup_agents.py -v

# Filter by name
uv run pytest -k test_bucket2

# With coverage
uv run pytest --cov=gitwise

# Single test
uv run pytest tests/test_setup.py::test_gpg_safety -v
```

### Before committing

```bash
# Always after changes to setup_agents.py or its tests
uv run pytest tests/test_setup_agents.py -v

# Always before commit
ruff check gitwise/ tests/
ruff format --check gitwise/ tests/
uv run pytest
```

---

## 9. Testing anti-patterns

| Anti-pattern | Alternative |
|-------------|-------------|
| `unittest.TestCase` | `def test_*()` functions with pytest |
| `mock.patch("gitwise.git.run")` | Synthetic repo with real git |
| `monkeypatch.setenv(...)` | `env=` parameter in `run_gitwise()` |
| Exact stdout assertion | Substring or JSON schema assertion |
| Test depending on another test | Each test is independent |
| `time.sleep()` waiting for git | Not needed — subprocess is synchronous |
| Hardcoded `/tmp/test-repo` | Use fixtures from `conftest.py` |
| `--no-gpg-sign` in production code | Only in fixtures and tests |
| `test.only` / `pytest -x` in CI | Only in local development |
| Copy/pasting repo setup between tests | Create fixture in `conftest.py` |
| Asserting exact finding count | Assert finding type or presence |
| Skipping tests without documented reason | All tests must always run |

---

## 10. Coverage

### What to cover

- All public `run_<cmd>()` functions
- All `_plan_actions()` and `_execute_actions()`
- All 5-bucket model buckets
- `_safe_create_symlink` (happy path + edge cases)
- Managed blocks (create, update, idempotency)
- `_classify_path` helper and state variants

### What NOT to cover

- Trivial single-return functions
- The string catalog in `i18n.py` (it's data, not logic)
- The `__main__.py` router module (its logic is pure dispatch)

### Coverage targets

- **Lines**: >80% in core modules (`setup_agents.py`, `setup.py`, `clean.py`)
- **Branches**: >70% in `_plan_*` and `_execute_*` functions
- **Don't** chase 100% — better integration tests than numeric coverage
