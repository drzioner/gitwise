# Python Guidelines — gitwise

> Compatible with: `python@3.10+` · `ruff` · `basedpyright`
> Zero dependencies. Only stdlib.
> Last reviewed: 2026-05-15

Python code standards for the project. Every rule is mandatory.

---

## 1. Type hints on ALL public signatures

**ALWAYS** annotate return types on public functions. Type hints are the project's executable documentation.

```python
# CORRECT — full signature
def run_clean(
    branches: bool = False,
    refs: bool = False,
    *,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
) -> int:
    ...

def _classify_path(p: Path) -> Literal["absent", "regular", "symlink_valid", "symlink_broken"]:
    ...

# PROHIBITED — no return type
def run_clean(branches=False, dry_run=False, yes=False, as_json=False):
    ...
```

### When to skip

- Trivial private functions where the type is obvious (e.g., `def _key(self) -> str`)
- Lambdas (already inline)

---

## 2. Named types for complex Literals

When a `Literal` appears in 2+ places, extract it to a named variable:

```python
# CORRECT — extracted type
from typing import Literal

_PathState = Literal["absent", "regular", "symlink_valid", "symlink_broken"]

def _classify_path(p: Path) -> _PathState:
    ...

def _detect_state(root: Path) -> dict[str, _PathState]:
    ...

# PROHIBITED — inline type repeated in 2+ functions
def _classify_path(p: Path) -> Literal["absent", "regular", "symlink_valid", "symlink_broken"]:
    ...

def _detect_state(root: Path) -> dict[str, Literal["absent", "regular", "symlink_valid", "symlink_broken"]]:
    ...
```

### Extraction rule

| Times used | Action |
|------------|--------|
| 1 time | Inline in signature — acceptable |
| 2+ times | **Mandatory** extract to named variable at module level |

---

## 3. Literal unions instead of `str`

Use `Literal` for finite values. Never use generic `str` when the domain is known.

```python
# CORRECT
from typing import Literal

_Severity = Literal["info", "warning", "error"]
_FindingType = Literal["stale_branches", "commit_graph", "fsmonitor", "old_stashes", "large_blobs", "mixed_staging", "gpg"]

def _add_finding(findings: list[dict[str, Any]], ftype: _FindingType, severity: _Severity, msg: str) -> None:
    ...

# PROHIBITED — generic str allows any value
def _add_finding(findings: list[dict[str, Any]], ftype: str, severity: str, msg: str) -> None:
    ...
```

Exception: `str` is correct when the value is free-form (paths, user messages, git output).

---

## 4. `pathlib.Path` over `os.path`

`pathlib.Path` is the project standard. The only exception is `os.path.realpath()` for symlink resolution in security contexts.

```python
# CORRECT — pathlib everywhere
root = repo_root()  # returns Path | None
agents_md = root / "AGENTS.md"
if agents_md.exists():
    ...

# CORRECT — os.path.realpath for deterministic resolution, Path.is_relative_to for sandbox
import os
root_real = Path(os.path.realpath(str(root)))
target_real = Path(os.path.realpath(str(link.parent / target_relative)))
if not target_real.is_relative_to(root_real):
    raise SymlinkConflict(t("symlink_escapes_root", target=target_relative))

# PROHIBITED — os.path for path manipulation
import os.path
agents_md = os.path.join(str(repo_root), "AGENTS.md")
```

### Why `os.path.realpath` instead of `Path.resolve()`

`Path.resolve()` has inconsistent behavior across OS/filesystem combinations (e.g., `/var` vs `/private/var` on macOS, network mounts on Linux). `os.path.realpath()` provides deterministic resolution that works the same everywhere, which is critical for symlink sandbox checks.

---

## 5. No external dependencies

**NEVER** add imports from packages other than stdlib in `gitwise/`.

```python
# CORRECT — stdlib only
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

# PROHIBITED — any external package
import requests        # NO
import click            # NO
import rich             # NO
import toml             # NO (use tomllib in 3.11+)
import yaml             # NO
```

Zero-dep is a hard constraint. If new functionality is needed, implement it with stdlib or git subprocess.

---

## 6. Relative imports within the package

Modules inside `gitwise/` use relative imports with each other:

```python
# CORRECT — relative imports (project convention)
from .git import config as git_config
from .git import is_repo, repo_root
from .i18n import t
from .output import debug, error, info, ok, print_json, warn

# DO NOT USE — absolute imports from within the package
from gitwise.git import config as git_config
from gitwise.i18n import t
```

Relative imports keep the package relocatable and avoid coupling to the package name.

---

## 7. Magic strings — extract to constants

**NEVER** use string literals with semantic meaning directly in code. Extract to descriptively named constants.

### Extraction threshold

| Times used | Action |
|------------|--------|
| 1 time | Inline acceptable if meaning is obvious |
| 2 times | **Evaluate** — extract if value is non-trivial |
| 3+ times | **Mandatory** extract to constant |

### Where to place constants

| Scope | Location |
|-------|----------|
| Single module | Module-level constant (`_` prefix if private) |
| 2+ modules | Consider shared module |

```python
# CORRECT — semantic constants (actual names from the project)
_SHARE_DIR = Path(__file__).parent.parent / "share" / "claude"
_AGENTS_MD = "AGENTS.md"
_CLAUDE_MD = "CLAUDE.md"
_GITIGNORE_MARKER_START = "# >>> gitwise managed (do not edit between markers) >>>"
_GITIGNORE_MARKER_END = "# <<< gitwise managed <<<"

# PROHIBITED — unnamed magic strings
if line.strip() == "# >>> gitwise managed (do not edit between markers) >>>":
    ...
target = root / "AGENTS.md"
```

### Strings in i18n

User-facing strings belong in `i18n.py`, not as loose literals:

```python
# CORRECT — use i18n
from .i18n import t
ok(t("setup_agents.created", path=str(target)))

# PROHIBITED — literal user-facing string
ok(f"Created {target}")
```

---

## 8. Magic numbers — extract to constants

Every number with semantic meaning must be a named constant.

```python
# CORRECT — named constants
_LARGE_BLOB_MIN_BYTES = 1_000_000  # 1 MB
_MAX_SNAPSHOT_BYTES = 8192         # 8 KB
_STASH_MAX_AGE_DAYS = 90

# PROHIBITED — magic numbers
if blob_size > 1000000:
    ...
if len(content.encode()) > 8192:
    ...
```

### Numbers allowed inline

| Number | When it's acceptable |
|--------|----------------------|
| `0`, `1` | Counters, indices, trivial comparisons |
| `-1` | Sentinel for "not found" |
| `True`, `False` | Booleans |
| `None` | Sentinel |
| `""` | Empty string as default |

---

## 9. SRP — One module, one responsibility

Each file in `gitwise/` has one and only one responsibility.

### Length limits

| Element | Limit | Action if exceeded |
|---------|-------|--------------------|
| Module `gitwise/*.py` | ~300 lines | Extract helpers to a new module |
| Exception: `setup_agents.py` | ~1400 lines | Justified by cohesive 5-bucket model |
| Function `run_<cmd>()` | ~50 lines | Delegate to `_plan_actions` and `_execute_actions` |
| Private function `_helper()` | ~30 lines | Consider splitting |

### SRP diagnostic

If you need "and" to describe what a module does, it probably needs splitting.

| Current module | Responsibility | Lines | OK? |
|----------------|---------------|-------|-----|
| `git.py` | Git subprocess wrappers | ~118 | OK |
| `output.py` | Output formatting + JSON | ~129 | OK |
| `i18n.py` | es/en translations | ~692 | OK (string catalog) |
| `setup_agents.py` | Cohesive 5-bucket model | ~1390 | Justified exception |
| `audit.py` | Repo diagnostics | ~296 | OK |
| `clean.py` | Stale branch cleanup | ~129 | OK |
| `optimize.py` | Git optimization | ~138 | OK |
| `summarize.py` | Compact status + log | ~96 | OK |
| `diff.py` | Changed file list | ~90 | OK |
| `worktree.py` | Worktree helpers | ~177 | OK |
| `doctor.py` | Environment checks | ~104 | OK |
| `snapshot.py` | Snapshot generator | ~83 | OK |
| `__main__.py` | CLI router + update cmd | ~243 | OK |

---

## 10. Function pattern: Plan → Execute → Rollback

Every `run_<cmd>()` that modifies the filesystem follows strict separation between planning (pure) and execution (I/O).

```python
def run_setup_agents(
    local: bool = False,
    no_skills: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    ...
) -> int:
    # 1. Validate preconditions
    if not is_repo():
        error(t("errors.not_a_repo"))
        return 1

    # 2. Plan — pure, no I/O
    actions, warnings, errors, bucket = _plan_actions(root, ...)

    # 3. Dry-run: print plan, return 0
    if dry_run:
        _print_plan(actions, warnings)
        return 0

    # 4. Confirm (unless --yes)
    if not yes and not confirm(t("confirm.proceed")):
        return 0

    # 5. Execute with rollback
    return _execute_actions(root, actions)
```

### Exit codes

Exit codes are literal `0`, `1`, `2`:
- `0` = ok
- `1` = error
- `2` = strict warnings (with `--strict` flag)

---

## 11. Git subprocess — safe pattern

All git invocations use functions from `git.py`, never `subprocess` directly.

```python
# CORRECT — use git.py helpers
from .git import run as git_run, config as git_config, is_repo, repo_root

root = repo_root()
r = git_run(["branch", "--format=%(refname:short)"], cwd=root)
branches = r.stdout.splitlines()
v = version()  # returns tuple[int, int, int]

# PROHIBITED — direct subprocess (except audit.py and summarize.py for non-git commands)
import subprocess
result = subprocess.run(["git", "status"], capture_output=True, text=True)
```

### git.py signatures

```python
def run(args: list[str], cwd: Path | None = None, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run git command, return CompletedProcess."""

def config(key: str, cwd: Path | None = None) -> str | None:
    """Read a git config value."""

def is_repo(path: Path | None = None) -> bool:
    """Check if path is inside a git repo."""

def repo_root(path: Path | None = None) -> Path | None:
    """Return repo root Path, or None."""

def git_dir(cwd: Path | None = None) -> Path | None:
    """Return .git directory Path."""

def current_branch(cwd: Path | None = None) -> str | None:
    """Return current branch name."""

def stale_branches(cwd: Path | None = None) -> list[str]:
    """Return branch names whose upstream is gone."""

def worktree_branches(cwd: Path | None = None) -> set[str]:
    """Return branches checked out in any worktree."""

def gpg_status(cwd: Path | None = None) -> dict[str, bool]:
    """Return GPG signing readiness."""

def version() -> tuple[int, int, int]:
    """Return parsed git version (cached)."""
```

### `_GIT_ENV` — deterministic environment

`git.py` configures a deterministic environment for all calls:

```python
_GIT_ENV = {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}
```

- `LC_ALL=C`: Git output always in English, parseable, consistent
- `GIT_TERMINAL_PROMPT=0`: No interactive prompts

**NEVER** use `subprocess.run(["git", ...], env=os.environ)` without `_GIT_ENV`.

### Documented exception

`audit.py` and `summarize.py` use `subprocess` directly for non-git commands (`bat`, `delta`, `du`). These are the only permitted exceptions.

---

## 12. DRY — Don't repeat yourself

### Rule of Three (Martin Fowler)

When the same code block appears for the third time, extract it. One or two repetitions can stay inline.

```python
# CORRECT — shared helper (actual project pattern)
def _classify_path(p: Path) -> Literal["absent", "regular", "symlink_valid", "symlink_broken"]:
    if p.is_symlink():
        return "symlink_valid" if p.exists() else "symlink_broken"
    if p.exists():
        return "regular"
    return "absent"

# Used in _detect_state() for each path:
state = {
    "agents_md": _classify_path(root / _AGENTS_MD),
    "claude_md": _classify_path(root / _CLAUDE_MD),
    ...
}
```

### Shared types

If two or more functions operate on the same data shape, a shared type **MUST** exist.

---

## 13. Comments — only the WHY

Comments explain non-obvious invariants, not what the code does.

```python
# CORRECT — explains WHY
# os.path.realpath resolves /var→/private/var and other platform aliases
# that Path.resolve() may handle inconsistently across OS/filesystems.
real = os.path.realpath(str(link))

# CORRECT — documents non-obvious invariant
# Test repos use --no-gpg-sign intentionally: GPG enforcement is for real repos
_git(["commit", "--no-gpg-sign", "-m", "chore: initial commit"], path)

# PROHIBITED — describes what the code already says
# Check if file exists
if agents_md.exists():
    ...

# PROHIBITED — commented-out code
# old approach:
# if os.path.exists(path):
#     ...
```

---

## 14. Imports — stdlib order

Imports grouped by PEP 8. There's only one group (stdlib) since there are no external dependencies:

```python
# CORRECT — alphabetically sorted, grouped by type
import functools
import os
import subprocess
from pathlib import Path
from typing import Any, Literal

# Second group: relative imports from the package
from .git import config as git_config
from .git import is_repo, repo_root
from .i18n import t
from .output import debug, error, info, ok, print_json, warn
```

---

## 15. Custom exceptions

The project defines specific exceptions for flow control between plan and execute:

```python
class SymlinkConflict(Exception):
    """Raised when symlink target escapes repo sandbox."""
    pass


class PlanExecutionError(Exception):
    """Raised when _execute_actions encounters a partial failure."""
    pass
```

- **NEVER** use `ValueError` or `RuntimeError` for these cases
- **ALWAYS** catch `SymlinkConflict` in `_execute_actions` for rollback
- Error messages use `t()` for i18n

---

## Quick summary

| Category | Required | Prohibited |
|----------|----------|------------|
| Type hints | On all public signatures | Signatures without return type |
| Types | Extract Literal to variable if 2+ uses | Inline type repeated |
| Finite values | `Literal["a", "b"]` | Generic `str` |
| Paths | `pathlib.Path` | `os.path` (except `realpath`) |
| Dependencies | stdlib only | Any external package |
| Imports | Relative `from .x import y` | Absolute `from gitwise.x` |
| Semantic strings | Named constant | Literal in 2+ places |
| Semantic numbers | Named constant | Literal anywhere |
| Comments | Only the WHY | What the code already says |
| i18n | `t("key")` for user text | Literal strings in output |
| Exceptions | `SymlinkConflict`, `PlanExecutionError` | Generic `ValueError` |
