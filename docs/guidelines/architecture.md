# Architecture Guidelines — gitwise

> Compatible with: `python@3.10+` · `argparse` · `stdlib`
> Last reviewed: 2026-05-15

Architectural patterns of the project. Every pattern exists for a documented reason.

---

## 1. Subcommand pattern: one module per command

Each gitwise subcommand is an independent module with a single entry function `run_<cmd>() -> int`.

### Structure

```
gitwise/
  __main__.py          # Router: argparse → lazy import → run_<cmd>()
  <command>.py         # Subcommand module
```

### Router (`__main__.py`)

The router defines argparse with lazy imports. **NEVER** import all modules at the top:

```python
# CORRECT — lazy import in the handler
if args.command == "setup-agents":
    from .setup_agents import run_setup_agents
    ret = run_setup_agents(
        local=args.local,
        no_skills=args.no_skills,
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
        ...
    )
```

### Standard `run_<cmd>()` signatures

Subcommands use keyword-only arguments via the router:

```python
def run_audit(*, quick: bool = False, as_json: bool = False) -> int:
def run_clean(branches: bool = False, refs: bool = False, *, dry_run: bool = False, yes: bool = False, as_json: bool = False) -> int:
def run_optimize(*, dry_run: bool = False, yes: bool = False, as_json: bool = False) -> int:
def run_diff(*, staged: bool = False, stat: bool = False, as_json: bool = False) -> int:
def run_snapshot(*, as_json: bool = False) -> int:
def run_worktree(action: str | None, branch: str | None, *, dry_run: bool = False, as_json: bool = False) -> int:
```

Conventions:
- `as_json` (not `json_output`) is the standard flag name
- Always returns `int` (exit code: 0=ok, 1=error, 2=strict)
- `root` is obtained internally via `repo_root()`, not passed as parameter
- `lang` is configured in the router via `set_locale()`, not passed to `run_<cmd>()`

### The `update` command

`__main__.py` includes an `update` subcommand that runs `git pull --ff-only` in the install directory. It's the only command defined directly in `__main__.py` (uses `print()` directly instead of `output.py`).

---

## 2. Plan → Execute → Rollback

Every operation that modifies the filesystem follows strict separation between planning (pure) and execution (I/O).

### Phases

```
run_<cmd>()
  ├── 1. Validate preconditions (is_repo, repo_root)
  ├── 2. _plan_actions() → (actions, warnings, errors, metadata)
  │       └── PURE: no I/O, no side effects
  ├── 3. Dry-run: print plan, return 0
  ├── 4. Confirm (unless --yes)
  └── 5. _execute_actions() → exit_code
          └── I/O: write files, create symlinks
          └── _undo_partial() on failure
```

### Invariants

| Invariant | Reason |
|-----------|--------|
| `_plan_actions` **never** does I/O | Enables dry-run without side effects |
| `_execute_actions` **never** plans | Separation of responsibilities |
| `_undo_partial` for rollback | If step 3 of 5 fails, undo 1-2 |
| Exit codes: `0`, `1`, `2` | Direct literals, clear semantics |

### Custom exceptions

```python
class SymlinkConflict(Exception):
    """Raised when symlink target escapes repo sandbox."""
    pass

class PlanExecutionError(Exception):
    """Raised during _execute_actions on partial failure."""
    pass
```

- `_safe_create_symlink` raises `SymlinkConflict` if target escapes the repo
- `_execute_actions` catches exceptions and calls `_undo_partial`

### `actions` structure

Actions use typed dictionaries with a `type` discriminator:

```python
from typing import Any, Literal, TypedDict

class WriteAction(TypedDict):
    type: Literal["write"]
    path: str
    content: str

class SymlinkAction(TypedDict):
    type: Literal["symlink"]
    link: str
    target_relative: str

class MkdirAction(TypedDict):
    type: Literal["mkdir"]
    path: str

class ManagedBlockAction(TypedDict):
    type: Literal["managed_block"]
    file: str
    content: str

Action = WriteAction | SymlinkAction | MkdirAction | ManagedBlockAction

actions: list[Action] = [
    {"type": "write", "path": "CLAUDE.md", "content": "..."},
    {"type": "symlink", "link": "CLAUDE.md", "target_relative": "AGENTS.md"},
    {"type": "mkdir", "path": ".claude/skills/git-audit"},
    {"type": "managed_block", "file": ".gitignore", "content": "..."},
]
```

`_execute_actions` processes sequentially and rolls back in reverse order on failure.

---

## 3. Managed Blocks — idempotent updates

`.gitignore` and `.gitattributes` are updated via managed blocks with markers:

```
# >>> gitwise managed (do not edit between markers) >>>
content managed by gitwise
# <<< gitwise managed <<<
```

### Constants

```python
_GITIGNORE_MARKER_START = "# >>> gitwise managed (do not edit between markers) >>>"
_GITIGNORE_MARKER_END = "# <<< gitwise managed <<<"
```

### Rules

- **ALWAYS** use the constants, never hardcode markers
- Updates are idempotent: running N times produces the same result
- If the block already exists with identical content, skip the write
- If the file doesn't exist, create it with the block
- If the file exists without the block, append the block

---

## 4. 5-Bucket Model (`setup_agents.py`)

The AGENTS.md/CLAUDE.md coexistence system classifies each repo into one of 5 states:

| Bucket | State | Action |
|--------|-------|--------|
| 1 | No AGENTS.md, no CLAUDE.md | Create CLAUDE.md from template |
| 2 | AGENTS.md present, CLAUDE.md absent | Create symlink or @import pointer |
| 3 | CLAUDE.md already points to AGENTS.md | Idempotent, do nothing |
| 4 | Both exist as separate files | Warn, offer --replace-claude-with-symlink |
| 5 | Broken symlinks or errors | Abort without changes |

### Global vs Local

`run_setup_agents()` dispatches to two modes:

| Mode | Flag | Target |
|------|------|--------|
| Global (default) | no `--local` | `~/.claude/` |
| Local | `--local` | `<repo>/.claude/` |

Planning logic (`_plan_actions`) differs between modes: global installs skills to `~/.claude/skills/`, local installs to `<repo>/.claude/skills/`.

### Invariants

- **NEVER** create AGENTS.md in a target repo — that's the user's content decision
- **NEVER** overwrite CLAUDE.md without confirmation
- **ALWAYS** use `_safe_create_symlink` to create symlinks (sandbox enforced)
- Bucket is determined in `_resolve_canonical_doc` (pure)
- Actions are generated in `_plan_actions` (pure)
- Changes are applied in `_execute_actions` (I/O)

---

## 5. Symlink Safety (`_safe_create_symlink`)

Symlink creation uses a sandbox to prevent path traversal:

```python
def _safe_create_symlink(link: Path, target_relative: str, root: Path) -> None:
    """Creates a relative symlink safely: idempotency + sandbox + TOCTOU re-check."""
    # Sandbox: target must not escape root (realpath resolves /var→/private/var etc.)
    root_real = Path(os.path.realpath(str(root)))
    target_real = Path(os.path.realpath(str(link.parent / target_relative)))
    if not target_real.is_relative_to(root_real):
        raise SymlinkConflict(t("symlink_escapes_root", target=target_relative))
    ...
```

### Rules

- **ALWAYS** use `os.path.realpath()` to resolve symlinks deterministically, then `Path.is_relative_to()` for the sandbox check
- `os.path.realpath()` resolves `/var` → `/private/var` and similar platform aliases that `Path.resolve()` may handle inconsistently across OS/filesystem combinations
- **NEVER** create symlinks without going through `_safe_create_symlink`
- TOCTOU validation is mitigated by realpath checks immediately before creation

### `_supports_symlinks` — platform detection

Before creating symlinks, verify that the filesystem supports them:

```python
def _supports_symlinks(root: Path) -> bool:
    if platform.system() == "Windows":
        return False
    # ... test symlink creation in temp dir ...
```

Results are cached in `_supports_symlinks_cache` by Path.

---

## 6. Dual output: Human + JSON

Each subcommand supports two output modes:

| Mode | When | Format |
|------|------|--------|
| Human | Default (no `--json`) | Colors, icons, tables via `output.py` |
| JSON | With `--json` | `{"v": 2, "v_compat": [1, 2], ...}` via `print_json()` |

### output.py functions

```python
from .output import ok, warn, error, info, debug, print_json

ok(t("setup.created"))         # green, ✓ prefix
warn(t("audit.stale_found"))   # yellow, ⚠ prefix
error(t("errors.not_a_repo"))  # red, ✗ prefix
info(t("doctor.checking"))     # cyan, ℹ prefix
debug(f"git {' '.join(args)}") # gray, only if env var enabled
print_json(data)               # dict → JSON stdout
```

### Color detection

`output.py` detects whether the terminal supports colors (dark/light theme) and adjusts ANSI codes automatically. **NEVER** hardcode ANSI codes outside `output.py`.

### `bat` / `delta` enhancement

`output.py` detects `bat` and `delta` CLI tools and can use them for improved display. Detection is automatic.

### JSON schema

```python
{
    "v": 2,
    "v_compat": [1, 2],
    "ok": True,
    ...
}
```

- `v=2` is the current version
- v1 mandatory keys must remain (don't remove them)
- New keys are optional (default to safe values)

---

## 7. i18n — centralized strings

All user-facing strings are in `i18n.py` with es/en translations.

```python
from .i18n import t

ok(t("setup_agents.created", path=str(target)))
warn(t("audit.stale_branches", count=len(stale)))
```

### Rules

- **NEVER** add user-facing string literals outside `i18n.py`
- **ALWAYS** add the key in both languages (es and en)
- Format uses `{placeholder}` style Python format strings
- Auto-detects from locale, overridable with `--lang`
- `set_locale()` is called in the router; modules don't need to handle language

---

## 8. GPG Safety Invariant

**NEVER** modify `commit.gpgsign` or `user.signingkey` from code.

### Multi-layer protection

1. `setup.py`: configures hooks and defaults, **never** touches GPG keys
2. `setup_agents.py`: injects `settings.json` with deny rules for `--no-gpg-sign`
3. `share/hooks/pre-commit`: verifies signing key is in the keyring
4. Tests: use `--no-gpg-sign` (only permitted exception)

### `gpg_status()` — read-only verification

```python
def gpg_status(cwd: Path | None = None) -> dict[str, bool]:
    """Returns GPG signing readiness — never modifies config."""
    return {
        "gpg_binary": gpg_bin,
        "gpgsign_enabled": gpgsign == "true",
        "signing_key_set": bool(signing_key),
        "ready": gpg_bin and gpgsign == "true" and bool(signing_key),
    }
```

---

## 9. `_GIT_ENV` — deterministic git environment

```python
_GIT_ENV = {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}
```

- `LC_ALL=C`: Git output always in English, parseable, consistent
- `GIT_TERMINAL_PROMPT=0`: No interactive prompts

**ALL** git calls via `git.run()` use `_GIT_ENV`. If a module uses `subprocess` directly (exceptions: `audit.py`, `summarize.py`), it must configure its own deterministic environment.

---

## 10. File length and when to split

### Limits

| Element | Suggested limit | Action |
|---------|----------------|--------|
| Module `gitwise/*.py` | ~300 lines | Extract helpers to new module |
| `setup_agents.py` | ~1400 lines (exception) | Don't split — 5-bucket is cohesive |
| `__main__.py` | ~250 lines | Router + argparse + update |
| Public function | ~50 lines | Delegate to private helpers |
| Private function | ~30 lines | Consider splitting |

### When to split

- **YES**: a private function grows beyond 50 lines
- **YES**: a module has 3+ functions forming a coherent sub-domain
- **NO**: if splitting breaks cohesion (setup_agents.py is an example)
- **NO**: "just in case" — split when it hurts, not before

### Diagnostic

If you can describe a module in a single sentence, it has good cohesion. If you need "and", consider splitting:

```
"setup_agents.py" → "Manages AGENTS.md/CLAUDE.md coexistence with the 5-bucket model"
→ Single cohesive responsibility. OK despite 1400 lines.

If it were → "Manages file coexistence AND generates snapshots AND handles i18n"
→ Three responsibilities. Split.
```

---

## 11. Inter-module communication

### Allowed dependencies

```
__main__.py → all modules (lazy import)
run_<cmd>()  → git.py, output.py, i18n.py
_plan_*()    → git.py (read-only), internal helpers
_execute_*() → git.py, output.py, filesystem (I/O)
```

### Prohibited dependencies

- **NEVER** import `setup_agents` from another command
- **NEVER** import `__main__` from a module
- **NEVER** create circular dependencies between modules

### Data between functions — explicit via parameters

```python
# CORRECT — explicit data
def _plan_actions(root: Path, ...) -> tuple[list[dict[str, Any]], list[str], list[str], int]:
    ...

def _execute_actions(root: Path, actions: list[dict[str, Any]]) -> int:
    ...

# PROHIBITED — global state
_plan_result = None  # global

def _plan_actions(root):
    global _plan_result
    ...
```
