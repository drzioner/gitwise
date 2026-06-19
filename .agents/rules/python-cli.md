---
alwaysApply: true
---

# Python CLI — Windows & CI Conventions

> **Loading:** This rule has `alwaysApply: true` frontmatter and no path scope, so it loads **Always** and applies unconditionally across all supported agents (Claude Code, opencode, etc.). Any change to a Python entry point or to the CLI's exception handling must satisfy these conventions.

This project ships `gitwise-cli` to PyPI and is consumed on macOS, Linux, and Windows. The rules below come from real regressions caught in PRs #62–#63.

## Required: UTF-8 stdio in every entry point

Windows defaults to a system codepage (typically `cp1252` on English Windows) for Python's embedded stdout/stderr. The codepage cannot encode characters above U+00FF, but gitwise prints U+2713 (`✓`), U+2717 (`✗`), em dashes, etc. throughout its status output. Without forcing UTF-8, every `print()` of a non-cp1252 character raises `UnicodeEncodeError` on Windows.

`Verified: https://docs.python.org/3/library/sys.html#sys.stdout.reconfigure` — `sys.stdout.reconfigure()` exists on Python 3.7+; our `requires-python` is `>=3.10`.

**Required pattern** at the top of every `main()` (CLI entry point):

```python
def _ensure_utf8_stdio() -> None:
    """Force stdout/stderr to UTF-8.

    Windows defaults to cp1252 (or similar) for embedded Python stdout.
    macOS/Linux are already UTF-8 by default — this is a no-op there.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (TypeError, ValueError):
                # Stream does not accept these kwargs or is closed; ignore.
                pass


def main() -> int:
    _ensure_utf8_stdio()
    # ... rest of CLI setup
```

`errors="replace"` ensures the CLI never crashes on an exotic character even if the underlying stream cannot be fully reconfigured.

## Required: print traceback in every non-tty exception handler

GitHub Actions runners and most CI environments run with stderr piped (not a TTY). The conventional Rich-traceback UX only triggers when `sys.stderr.isatty()` returns `True`. Without an explicit fallback, the CI log shows only `error: unexpected error. Run with GITWISE_DEBUG=1 for details.` — which is useless for diagnosis because:

- `GITWISE_DEBUG=1` only enables subprocess command logging in `_runtime_config.py`; it does NOT enable the handler's traceback.
- The actual exception is swallowed silently.

**Required pattern**:

```python
try:
    ret = handler(args)
except KeyboardInterrupt:
    ret = 130
except SystemExit:
    raise
except Exception:
    if _should_show_rich_traceback():
        # tty + no JSON mode: Rich handles the pretty traceback
        raise
    # Non-tty (CI, pipes, JSON mode): emit raw traceback to stderr so the
    # log is diagnostic. Without this, CI logs say only "unexpected error".
    import traceback as _traceback
    _traceback.print_exc()
    from .output import error as _error
    _error(t("unexpected_error"))
    ret = 1
```

## Required: don't propagate PowerShell `$LASTEXITCODE` as the script's exit code

When a PowerShell script wraps a native command (e.g. `gitwise doctor`), the command's exit code lands in `$LASTEXITCODE`. If the script does not call `exit` explicitly afterwards, PowerShell uses `$LASTEXITCODE` as the script's exit code — meaning a `doctor` exit code of `1` propagates as the script's exit code, and GitHub Actions marks the step failed even if the script's logic intended to accept that as success.

**Required pattern** for any GitHub Actions PowerShell step that calls a native command and treats non-zero as OK:

```powershell
$output = & gitwise doctor 2>&1 | Out-String
Write-Host $output
if ($LASTEXITCODE -notin 0, 1, 2) {
    Write-Host "Error: exit code $LASTEXITCODE (not 0/1/2)" -ForegroundColor Red
    exit 1
}
# Explicit exit 0 so $LASTEXITCODE from the native call doesn't leak.
exit 0
```

The `exit 0` is not optional. Without it, GitHub Actions will mark the step as failed whenever the wrapped command returns anything other than 0, regardless of the surrounding `if` logic.

## Required: validate output content, not just exit code

Exit codes lie. A CLI can crash with exit code 1 (its catch-all handler) while still producing valid-looking output. Always grep the output for known error patterns in CI checks.

**Required pattern** for any CI smoke test:

```powershell
$output = & gitwise doctor 2>&1 | Out-String
Write-Host $output

# Hard-fail patterns: presence means a Python-level crash OR the CLI's
# "unexpected error" handler firing — either is a real bug the test
# must surface, not swallow.
if ($output -match 'Traceback \(most recent call last\)|UnicodeEncodeError|UnicodeDecodeError|unexpected error\.') {
    Write-Host "Error: doctor output contains an error pattern." -ForegroundColor Red
    exit 1
}

if ($LASTEXITCODE -notin 0, 1, 2) {
    Write-Host "Error: exit code $LASTEXITCODE not in 0/1/2." -ForegroundColor Red
    exit 1
}
exit 0
```

The output check is what catches silent regressions where the CLI's exception handler fires but still returns exit code 1 (which a naive `0/1/2` check would accept).

## Don't confuse `GITWISE_DEBUG=1` with `traceback.print_exc()`

Two different debug surfaces:

| Variable / call | Effect | Where |
|-----------------|--------|-------|
| `GITWISE_DEBUG=1` (env var) | Prints subprocess commands gitwise runs (`git config --get ...`) | `_runtime_config.py` |
| `traceback.print_exc()` (handler call) | Prints Python exception tracebacks | `__main__.py:main()` exception handler |

Setting `GITWISE_DEBUG=1` in CI does NOT surface handler tracebacks. The traceback-printing fix must be in the source code itself (see the "Required: print traceback" pattern above).

## Diagnosis playbook for "gitwise doctor crashes on platform X"

When CI reports a doctor failure on a platform you cannot reproduce locally:

1. **Force the traceback.** Either add `traceback.print_exc()` to the handler (see pattern above) OR temporarily replace the CLI invocation in CI with `uv run python -m gitwise doctor` (bypasses the handler entirely, surfaces the raw exception).
2. **Run doctor from source.** If CI uses `install.ps1` or `install.sh` (which pull from PyPI), add a step `uv tool install --reinstall --from . gitwise-cli` so CI exercises the branch code, not the published artifact.
3. **Don't `if: always()` your way out.** `if: always()` is for diagnostic steps that must run regardless of prior failures. It is not a fix — the underlying failure still needs to be addressed.
4. **Read the traceback before writing the fix.** A surprising fraction of "iterations" come from guessing at the bug from the error message alone. Open the CI log, scroll to the `Traceback (most recent call last):` block, and read the actual exception type and line.

## See also

- [shell-scripts.md](shell-scripts.md) — `install.sh` / `install.ps1` conventions (different threat model: shell portability, native command exit codes).
- [github-actions.md](github-actions.md) — workflow conventions including TDD with installers that download from PyPI.
- `gitwise/__main__.py` — canonical example of the UTF-8 + traceback patterns above.
