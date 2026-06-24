"""Thin wrappers over subprocess for git operations."""

import functools
import os
import re
import subprocess
from pathlib import Path

_NESTED_QUANTIFIER_RE = re.compile(
    r"(\([^)]*[+*][^)]*\)[+*{])"
    r"|(\[[^\]]*[+*][^\]]*\][+*{])"
    r"|(\(.+\|.+\)[+*{])"
)

_GREP_MAX_LEN = 200


# In-process git config overrides (``GIT_CONFIG`` file and the ``GIT_CONFIG_*``
# inline family) let an attacker-controlled environment inject arbitrary config
# (e.g. force a credential helper that exfiltrates secrets). Scrub them so the
# subprocess only reads the real repo/global config. ``GIT_DIR``/``GIT_WORK_TREE``
# are intentionally preserved: they are legitimate path overrides, not config
# injection vectors, and stripping them would break worktree/alternate workflows.
_GIT_ENV_SCRUB_PREFIXES: tuple[str, ...] = ("GIT_CONFIG",)


def _build_git_env() -> dict[str, str]:
    """Return os.environ with locale/credential hardening and config injection scrubbed."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(k == prefix or k.startswith(prefix + "_") for prefix in _GIT_ENV_SCRUB_PREFIXES)
    }
    env["LC_ALL"] = "C"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


_GIT_ENV = _build_git_env()

_DEFAULT_TIMEOUT = 120

_NETWORK_TIMEOUT = 60

_CMD_TIMEOUTS: dict[str, int] = {
    "diff-tree": 30,
    "diff": 30,
    "log": 30,
    "status": 10,
    "branch": 10,
    "stash": 10,
    "ls-files": 10,
    "rev-list": 30,
    "shortlog": 30,
    "grep": 30,
    "for-each-ref": 10,
    "rev-parse": 10,
    "config": 5,
    "tag": 10,
    "commit": 30,
    "fetch": _NETWORK_TIMEOUT,
    "push": _NETWORK_TIMEOUT,
    "pull": _NETWORK_TIMEOUT,
    "clone": _NETWORK_TIMEOUT,
}


def _get_timeout(cmd: str | None = None) -> int:
    """Resolve the timeout for a git subcommand.

    Checks ``GITWISE_GIT_TIMEOUT`` env-var first, then the per-command
    table, then falls back to the default (120 s).
    """
    val = os.environ.get("GITWISE_GIT_TIMEOUT", "")
    if val.isdigit() and int(val) > 0:
        return int(val)
    if cmd and cmd in _CMD_TIMEOUTS:
        return _CMD_TIMEOUTS[cmd]
    return _DEFAULT_TIMEOUT


def run(
    args: list[str],
    cwd: Path | None = None,
    check: bool = False,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand and return the completed process.

    Sets ``LC_ALL=C`` and ``GIT_TERMINAL_PROMPT=0`` so output is
    locale-stable and git never prompts for credentials.  Returns
    returncode 127 with a descriptive stderr when the ``git`` binary
    is not found in ``PATH``.
    """
    from .output import debug

    cmd_name = next((arg for arg in args if not arg.startswith("-")), None)
    actual_timeout = timeout if timeout is not None else _get_timeout(cmd_name)
    debug(f"git {' '.join(args)}")
    try:
        return subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
            check=check,
            env=_GIT_ENV,
            timeout=actual_timeout,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=127,
            stdout="",
            stderr="git executable not found in PATH",
        )
    except subprocess.TimeoutExpired as exc:
        # Mirror the `timeout` coreutil convention (124) so callers can
        # distinguish a timed-out git operation from a real git failure (128+)
        # or a missing binary (127).
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=124,
            stdout=exc.stdout.decode("utf-8", "replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or ""),
            stderr=(
                f"git {' '.join(args)} timed out after {actual_timeout}s"
                if not exc.stderr
                else exc.stderr.decode("utf-8", "replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr
            ),
        )


def config(key: str, cwd: Path | None = None) -> str | None:
    """Return the single git config value for *key*, or None if unset."""
    result = run(["config", "--get", key], cwd=cwd, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def config_all(key: str, cwd: Path | None = None) -> list[str]:
    """Return all git config values for *key* (multi-valued keys)."""
    result = run(["config", "--get-all", key], cwd=cwd, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_repo(path: Path | None = None) -> bool:
    """Return True if *path* (or cwd) is inside a git repository."""
    result = run(["rev-parse", "--git-dir"], cwd=path, check=False)
    return result.returncode == 0


def repo_root(path: Path | None = None) -> Path | None:
    """Return the repository root, or None if not inside a git repo."""
    result = run(["rev-parse", "--show-toplevel"], cwd=path, check=False)
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def git_dir(cwd: Path | None = None) -> Path | None:
    """Return the absolute ``.git`` directory, or None."""
    r = run(["rev-parse", "--absolute-git-dir"], cwd=cwd, check=False)
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def current_branch(cwd: Path | None = None) -> str | None:
    """Return the current branch name, or None when detached HEAD."""
    r = run(["branch", "--show-current"], cwd=cwd, check=False)
    val = r.stdout.strip()
    return val if (r.returncode == 0 and val) else None


def stale_branches(cwd: Path | None = None) -> list[str]:
    """Returns branch names whose upstream is [gone]."""
    r = run(
        ["for-each-ref", "--format=%(refname:short)\t%(upstream:track)", "refs/heads/"],
        cwd=cwd,
        check=False,
    )
    if r.returncode != 0:
        return []
    result = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and "[gone]" in parts[1]:
            result.append(parts[0])
    return result


def worktree_branches(cwd: Path | None = None) -> set[str]:
    """Returns set of branch names currently checked out in any worktree."""
    r = run(["worktree", "list", "--porcelain"], cwd=cwd, check=False)
    if r.returncode != 0:
        return set()
    return {
        line.removeprefix("branch refs/heads/")
        for line in r.stdout.splitlines()
        if line.startswith("branch refs/heads/")
    }


def gpg_status(cwd: Path | None = None) -> dict[str, bool]:
    """Returns GPG signing readiness for cwd (falls back to global git config)."""
    import shutil

    gpg_bin = bool(shutil.which("gpg") or shutil.which("gpg2"))
    gpgsign = config("commit.gpgsign", cwd=cwd)
    signing_key = config("user.signingkey", cwd=cwd)
    return {
        "gpg_binary": gpg_bin,
        "gpgsign_enabled": gpgsign == "true",
        "signing_key_set": bool(signing_key),
        "ready": gpg_bin and gpgsign == "true" and bool(signing_key),
    }


@functools.lru_cache(maxsize=1)
def version() -> tuple[int, int, int]:
    """Return the git version as a ``(major, minor, patch)`` tuple.

    Cached after the first call.  Returns ``(0, 0, 0)`` when parsing
    fails.
    """
    result = run(["--version"], check=False)
    # "git version 2.45.0" -> (2, 45, 0)
    parts = result.stdout.strip().split()
    if len(parts) >= 3:
        nums = parts[2].split(".")
        try:
            return (
                int(nums[0]),
                int(nums[1]) if len(nums) > 1 else 0,
                int(nums[2]) if len(nums) > 2 else 0,
            )
        except (ValueError, IndexError):
            from .output import debug as _debug

            _debug(f"git version parse failed: {result.stdout.strip()!r}")
    return (0, 0, 0)


def supports_config_hooks(cwd: Path | None = None) -> bool:
    """Return True if ``git hook run`` is available (git >= 2.36)."""
    if version() < (2, 36, 0):
        return False
    result = run(["hook", "run", "--ignore-missing", "pre-commit"], cwd=cwd, check=False)
    return result.returncode == 0


def validate_ref(ref: str) -> bool:
    """Return False for empty strings or refs that look like flags."""
    return bool(ref) and not ref.startswith("-")


# Git options that the --git-arg passthrough must refuse. These can write to
# arbitrary files (--output), execute arbitrary commands (--upload-pack,
# --receive-pack, --exec), inject config (-c/--config), or redirect which
# repository git operates on (--git-dir/--work-tree/--namespace). Denying them
# keeps the passthrough an escape hatch for read options (filters, -U, etc.)
# without opening a code-execution or arbitrary-write vector.
_GIT_PASSTHROUGH_DENY: frozenset[str] = frozenset(
    {
        "--output",
        "-c",
        "--config",
        "--upload-pack",
        "--receive-pack",
        "--exec",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--bare",
        "-C",
    }
)


def validate_passthrough_arg(arg: str) -> str | None:
    """Return an error message if *arg* is a denied passthrough option, else None.

    Compares the option token (the part before ``=`` for ``--opt=value`` forms)
    against the deny list. Empty args are rejected. Standalone values (paths,
    numbers) are allowed -- they are positional operands, not options.
    """
    if not arg:
        return "empty --git-arg value"
    token = arg.split("=", 1)[0]
    if token in _GIT_PASSTHROUGH_DENY:
        return f"--git-arg refuses '{token}' (can execute code, write files, or redirect the repo)"
    return None


def validate_passthrough_args(args: list[str] | None) -> str | None:
    """Validate a list of passthrough args; return the first error message or None."""
    if not args:
        return None
    for arg in args:
        err = validate_passthrough_arg(arg)
        if err is not None:
            return err
    return None


def validate_branch_name(name: str) -> bool:
    """Return True if *name* passes ``git check-ref-format``."""
    if not name or name.startswith("-"):
        return False
    result = run(["check-ref-format", f"refs/heads/{name}"], check=False)
    return result.returncode == 0


def validate_grep_pattern(pattern: str) -> bool:
    """Return True if *pattern* is safe for ``git log --grep``.

    Rejects patterns longer than 200 chars, nested quantifiers that
    trigger git's PCRE engine bugs, and patterns that are not valid
    Python regex.
    """
    if len(pattern) > _GREP_MAX_LEN:
        return False
    if _NESTED_QUANTIFIER_RE.search(pattern):
        return False
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


def validate_author_pattern(pattern: str) -> bool:
    """Return True if *pattern* is safe for ``git log --author``.

    Same length and nested-quantifier guards as ``validate_grep_pattern``,
    plus rejects newlines and null bytes.
    """
    if len(pattern) > _GREP_MAX_LEN:
        return False
    if "\n" in pattern or "\r" in pattern or "\x00" in pattern:
        return False
    if _NESTED_QUANTIFIER_RE.search(pattern):
        return False
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


PROTECTED_BRANCHES: frozenset[str] = frozenset(
    {"main", "master", "develop", "dev", "trunk", "release"}
)


def require_root(path: Path | None = None) -> tuple[Path, None] | tuple[None, int]:
    """Validate git repo and return (root, None) or (None, exit_code)."""
    from .i18n import t
    from .output import error

    root = repo_root(path)
    if root is None:
        error(t("not_a_git_repo"))
        return None, 1
    return root, None


def has_remote(cwd: Path | None = None) -> bool:
    """Return True if at least one remote is configured."""
    r = run(["remote"], cwd=cwd, check=False)
    return r.returncode == 0 and bool(r.stdout.strip())


def has_upstream(cwd: Path | None = None) -> bool:
    """Return True if the current branch has an upstream tracking ref."""
    r = run(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=cwd, check=False)
    return r.returncode == 0 and bool(r.stdout.strip())


def has_commit_graph(cwd: Path | None = None) -> bool:
    """Return True if a commit-graph file or chain exists in the repo."""
    gd = git_dir(cwd)
    if gd is None:
        return False
    return (gd / "objects" / "info" / "commit-graph").exists() or (
        gd / "objects" / "info" / "commit-graphs" / "commit-graph-chain"
    ).exists()
