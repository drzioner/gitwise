# Anti-Patterns — gitwise

> Compatible with: `python@3.10+` · `stdlib` · `pytest` · `ruff`
> Last reviewed: 2026-05-18

List of **prohibited** patterns in this project, organized by category.

---

## 1. External dependencies

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `import requests` / `import httpx` | Breaks zero-dep | `urllib.request` from stdlib |
| `import click` / `import typer` | Breaks zero-dep, argparse is enough | `argparse` from stdlib |
| `import rich` | Breaks zero-dep | `output.py` with ANSI codes |
| `import yaml` / `import toml` | Breaks zero-dep | `json` from stdlib, `tomllib` in 3.11+ |
| `import colorama` | Breaks zero-dep | Direct ANSI codes in `output.py` |
| `pip install X` as runtime dependency | Hard constraint of the project | Implement with stdlib |

**Zero-dep is non-negotiable.** If functionality requires an external package, implement it with stdlib or git subprocess.

---

## 2. Over-engineering

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| Classes for stateless functions | Python doesn't need classes for everything | Pure functions |
| Abstract base classes for 1 implementation | Complexity without benefit | Direct function |
| Plugin system / extensibility hooks | YAGNI — no use case exists | Direct functions |
| Config objects for everything | Over-engineering | Direct parameters with defaults |
| Wrapper over `git.run()` "in case we change git" | `git.run()` IS already the wrapper | Use directly |
| `TypeAlias` annotation when not needed | The project uses simple assignment | `_PathState = Literal[...]` without annotation |

### Rule of three

Don't extract an abstraction until the pattern repeats 3 times. Three similar lines are better than a premature abstraction.

---

## 3. Scope creep

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| Adding extra logging "just in case" | Only log what the command needs | Log what's necessary |
| Refactoring adjacent code "while I'm here" | One change, one purpose | Separate commit |
| Adding type hints to files you didn't touch | Scope limited to your change | Only type what you changed |
| Creating tests for code you didn't change | Tests only for new or modified code | Test what you touched |
| Adding validations for impossible cases | Validate only at boundaries | Validate user inputs |
| "Improving" output of a command you didn't touch | Breaks user expectations | Only change what was requested |

### Rule: one commit, one purpose

Every change should have a clear, limited objective. If you want to improve something extra, do it in a separate commit.

---

## 4. Magic strings and magic numbers

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `if line.strip() == "# >>> gitwise managed ..."` | Fragile, silent typos | `_GITIGNORE_MARKER_START` constant |
| `if len(content.encode()) > 8192` | Opaque semantics | Named constant |
| `return {"v": 2, "v_compat": [1, 2]}` | Duplication, drift | Schema constants |
| `"--no-gpg-sign"` in production code | Only for tests | Remove from production paths |
| Literal strings in output | Not i18n, not localizable | `t("key")` from `i18n.py` |
| Path literals: `".claude/skills"` | Fragile to refactoring | `_SHARE_DIR / "skills"` |
| Defining `_AGENTS_MD = "AGENTS.md"` but using `"AGENTS.md"` directly | Inconsistency | Always use the constant |

### Extraction threshold

| Times used | Action |
|------------|--------|
| 1 time | Inline acceptable if meaning is obvious |
| 2 times | Evaluate — extract if non-trivial |
| 3+ times | **Mandatory** extract to named constant |

### Numbers allowed inline

`0`, `1`, `-1`, `True`, `False`, `None`, `""` — trivially obvious values.

---

## 5. Incorrect typing

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `def run(x):` without type hints | Loses executable documentation | `def run(x: Path) -> int:` |
| `dict` without type | `dict[str, Any]` is useless without known keys | `dict[str, bool]` or TypedDict |
| `str` for finite values | Allows any string | `Literal["info", "warn", "error"]` |
| `Any` as return type | Disables downstream type checking | Specific type |
| `Any` without justification comment | Even as parameter, disables type safety | Specific type or `TypeVar` |
| `as Any` cast | Hides real errors | Redesign the type |
| `# type: ignore` | Silences real errors | Fix the root type |
| `Optional[X]` | Pre-3.10 style | `X | None` (union syntax) |
| `List[X]`, `Dict[K, V]` | Pre-3.10 style | `list[X]`, `dict[K, V]` (lowercase generics) |
| `list` without type parameter | Generic container loses safety | `list[str]`, `list[Path]` |
| Plain tuple for multi-value returns | Opaque `(str, int, bool)` — what is each? | Named tuple or dataclass |
| Return type relying on inference | basedpyright can miss it, breaks docs | Always explicit `-> ReturnType` |

---

## 6. Error handling

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| Bare `except Exception: pass` | Silences failures, hides bugs forever | Catch specific `OSError`, `ValueError`, etc. |
| `except Exception as e: raise e` | Loses original traceback | `raise` (re-raise preserves traceback) |
| `except Exception: raise RuntimeError(msg)` | Loses original traceback | `raise RuntimeError(msg) from e` (chain) |
| Batch abort on first item error | One bad item kills entire operation | Track successes and failures separately |
| Error message without context | `"Failed"` — what? why? how to fix? | `"Failed to create symlink: target escapes repo root"` |
| Catching at wrong layer | Business logic catching I/O errors | I/O errors at I/O boundary, domain errors in domain |
| Generic `Exception` in `except` | Catches `KeyboardInterrupt`, `SystemExit` | Specific exception types only |
| Ignoring `subprocess` timeout errors | Git hang becomes silent failure | Handle `subprocess.TimeoutExpired` explicitly |

### Exception chaining rule

```python
# CORRECT — preserve debug trail
try:
    content = path.read_text(encoding="utf-8")
except OSError as e:
    raise PlanExecutionError(t("errors.read_failed", path=str(path))) from e

# PROHIBITED — original traceback lost
try:
    content = path.read_text(encoding="utf-8")
except OSError as e:
    raise PlanExecutionError(t("errors.read_failed", path=str(path)))
```

---

## 7. Resource management

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `f = open(path); f.read()` without `with` | File never closed on exception | `with open(path) as f:` |
| `subprocess.run()` without `timeout` | Git hang blocks forever | `timeout=120` (default in `git.run()`) |
| `subprocess.run()` without `capture_output=True` | Output leaks to terminal | Always capture |
| Temp files not cleaned up on failure | Disk pollution in test runs | `finally` block or fixture teardown |
| `__exit__` that doesn't run unconditionally | Resource leak on exception | `__exit__` must always clean up |
| Accumulating strings with `+=` in loops | O(n²) for large outputs | List append + `"".join()` |
| Multiple resources without `ExitStack` | Nested `with` gets unwieldy at 3+ | `contextlib.ExitStack` |

---

## 8. Path handling

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `os.path.join()` for path manipulation | Less readable than pathlib | `Path` / operator |
| `Path.resolve()` for symlink sandbox | Inconsistent behavior across OS/filesystem combinations | `os.path.realpath()` |
| String concatenation: `dir + "/" + file` | Fragile, not portable | `Path` / operator |
| `open(path_string)` without Path | Inconsistent with project | `Path` always |
| `os.path.exists()` / `os.path.isdir()` | Pre-Python 3 style | `Path.exists()` / `Path.is_dir()` |

---

## 9. Subprocess and Git

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `subprocess.run(["git", ...])` directly (in modules other than audit/summarize) | Bypasses deterministic `_GIT_ENV` | `git.run()` from `gitwise/git.py` |
| `os.system("git status")` | Insecure, no output capture | `git.run(["status"])` |
| `shell=True` in subprocess | Shell injection risk | `subprocess.run([...], shell=False)` |
| Not using `_GIT_ENV` | Non-deterministic output (i18n, prompts) | Pass `_GIT_ENV` to all git calls |
| `git.run("branch", "--format=...")` (variadic) | Wrong signature — `run()` takes `list[str]` | `git.run(["branch", "--format=..."])` |

### Documented exceptions

Only `audit.py` and `summarize.py` use `subprocess` directly for non-git commands (`bat`, `delta`, `du`). All other invocations must go through `git.py`.

---

## 10. Output and presentation

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `print()` directly (outside `__main__._run_update`) | Bypasses dual output system | `ok()`, `warn()`, `error()`, etc. |
| Hardcoded ANSI codes | Ignores color detection | `ok()` which detects theme |
| Literal user-facing strings | Not localizable | `t("key")` from `i18n.py` |
| `sys.exit()` inside business logic | Couples logic with CLI | Return exit code, let router exit |
| `input()` for confirmation | Ignores --yes, --json | `output.confirm()` |
| `--json` flag without JSON output | Inconsistency | Always support `as_json` |

---

## 11. GPG and security

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| Modifying `commit.gpgsign` from code | Breaks security invariant | Only via hooks and settings |
| Modifying `user.signingkey` from code | Interferes with user config | Only verify, never change |
| `--no-gpg-sign` in production | Only for tests | Remove from production paths |
| Logging secrets or tokens | Credential exposure | Never log sensitive values |
| `.env` or credentials in git | Security risk | `.gitignore` with secret patterns |

---

## 12. Testing

| Anti-pattern | Alternative |
|-------------|-------------|
| `mock.patch("gitwise.git.run")` | Hides integration bugs — use synthetic repo with real git |
| `unittest.TestCase` | Legacy style, less readable — use `def test_*()` with pytest |
| Test depending on another test | Order-dependent, fragile — each test is independent |
| Hardcoded `/tmp/test-repo` | Collisions, not portable — use fixtures from `conftest.py` |
| `pytest -x` in CI | Hides later failures — run all, report all |
| Exact stdout assertion | Fragile with i18n — use JSON schema or substring |
| `time.sleep()` waiting for git | Flaky, slow — subprocess is synchronous |
| Asserting exact finding count | Fragile to logic changes — assert type or presence |
| `--no-gpg-sign` in production code | Only for fixtures — limit to `conftest.py` |

---

## 13. Commits and Git

| Anti-pattern | Alternative |
|-------------|-------------|
| `git add .` or `git add -A` | `git add <specific files>` |
| `--no-verify` without justification | Fix the pre-commit hook |
| `--force` to main/master | Never force push to protected branches |
| Commits without descriptive messages | Conventional format |
| `git amend` after push | New commit with fix |
| `git stash + checkout` to switch branches | `gitwise worktree new <branch>` |

---

## 14. File structure

| Anti-pattern | Alternative |
|-------------|-------------|
| Module with 500+ lines and no cohesion | Split by responsibility |
| Function with 100+ lines | Delegate to private helpers |
| 3+ levels of `_internal_helper_nested()` | Extract to separate module |
| Absolute imports `from gitwise.x` | Relative `from .x import y` |
| Circular imports between modules | Redesign dependencies |
| `__init__.py` with logic | Only `__version__` in `__init__.py` |
| Catch-all `utils.py` file | Modules with single purpose |

---

## 15. JSON schema

| Anti-pattern | Alternative |
|-------------|-------------|
| Changing schema version without bump | Bump `v` and update `v_compat` |
| Removing mandatory v1 keys | Keep keys, mark deprecated |
| `data["new_key"]` without default | `data.get("new_key", default)` |
| Inconsistent schema between commands | Follow common template |

---

## 16. Comments

| Anti-pattern | Alternative |
|-------------|-------------|
| Comment describing WHAT the code does | Noise — the code already says it |
| Mixed Spanish/English comments | English only (project convention) |
| Commented-out code blocks | Delete — git preserves history |
| `# TODO` without context or issue | `# TODO(#N): description` with issue link |
| Docstrings on trivial private functions | Only docstrings on public functions |

---

## 17. AI slop in generated text

**NEVER** produce text with generic AI patterns. Applies to: commit messages, CLI output, documentation, i18n strings.

| Slop | Alternative |
|------|-------------|
| "deeply", "highlighting", "underscoring" | (remove or be specific) |
| "significant", "enriching", "invaluable" | (say what it is, not how important) |
| "in the current landscape" | (remove) |
| "it's worth noting that" | (remove, get to the point) |
| "leveraging", "empowering" | "using" |
| Chained gerunds | Direct to the point |
| Forced rule of three | Only if all 3 elements are real |

---

## 18. Over-engineering (configuration and observability)

| Anti-pattern | Why | Alternative |
|-------------|-----|-------------|
| `pydantic-settings` / `dotenv` for config | Breaks zero-dep | Direct `os.environ.get()` or `os.getenv()` |
| Structured logging library (`structlog`) | Breaks zero-dep | `output.py` functions (ok/warn/error/info/debug) |
| `prometheus_client` / OpenTelemetry | Breaks zero-dep, overkill for CLI | Exit codes + JSON output for machine parsing |
| Configuration class for 2 values | Premature abstraction | Direct parameters with defaults |
| Factory/registry pattern for formatters | Over-engineering | Simple dict mapping |

---

## Quick summary

| Category | Required | Prohibited |
|----------|----------|------------|
| Dependencies | stdlib only | Any external package |
| Subprocess | `git.run(["arg1", "arg2"])` | Direct `subprocess.run(["git", ...])` |
| Output | `ok()` / `t("key")` | `print()` / literal strings |
| Paths | `pathlib.Path` | `os.path` (except `realpath`) |
| Imports | Relative `from .x import y` | Absolute `from gitwise.x` |
| Types | Type hints on all signatures, explicit return types | `Any`, `def f(x):`, inferred returns |
| Finite values | `Literal["a", "b"]` | Generic `str` |
| Multi-value returns | Named tuple or dataclass | Plain tuple |
| Magic values | Named constant | Literal repeated in 2+ places |
| Error handling | Specific exceptions, `raise ... from e` | Bare `except`, lost traceback |
| Batch errors | Track successes/failures separately | Abort entire batch on single error |
| Resources | Context managers, `with`, `finally` | Unclosed files, no timeout on subprocess |
| GPG | Only verify, never modify | Changing gpgsign/signingkey |
| Testing | pytest + real subprocess | unittest, mocks |
| Comments | Only the WHY | What the code already says |
| JSON schema | Bump version, maintain compat | Removing keys, no default |
| Commits | Conventional format, GPG signed | `--no-gpg-sign` in production |
| Config | `os.environ.get()` | pydantic-settings, dotenv |
| Logging | `output.py` functions | structlog, logging library |
