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


_GIT_ENV = {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}

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
    val = os.environ.get("GITWISE_GIT_TIMEOUT", "")
    if val.isdigit():
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
    from .output import debug

    cmd_name = args[0] if args else None
    actual_timeout = timeout if timeout is not None else _get_timeout(cmd_name)
    debug(f"git {' '.join(args)}")
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


def config(key: str, cwd: Path | None = None) -> str | None:
    result = run(["config", "--get", key], cwd=cwd, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def config_all(key: str, cwd: Path | None = None) -> list[str]:
    result = run(["config", "--get-all", key], cwd=cwd, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_repo(path: Path | None = None) -> bool:
    result = run(["rev-parse", "--git-dir"], cwd=path, check=False)
    return result.returncode == 0


def repo_root(path: Path | None = None) -> Path | None:
    result = run(["rev-parse", "--show-toplevel"], cwd=path, check=False)
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def git_dir(cwd: Path | None = None) -> Path | None:
    r = run(["rev-parse", "--absolute-git-dir"], cwd=cwd, check=False)
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def current_branch(cwd: Path | None = None) -> str | None:
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
    if version() < (2, 36, 0):
        return False
    result = run(["hook", "list", "pre-commit"], cwd=cwd, check=False)
    combined = f"{result.stdout}\n{result.stderr}".lower()
    return "not a git command" not in combined and "unknown subcommand" not in combined


def validate_ref(ref: str) -> bool:
    return bool(ref) and not ref.startswith("-")


def validate_branch_name(name: str) -> bool:
    if not name or name.startswith("-"):
        return False
    return not (".." in name or "~" in name or ":" in name or " " in name)


def validate_grep_pattern(pattern: str) -> bool:
    if len(pattern) > _GREP_MAX_LEN:
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
    r = run(["remote"], cwd=cwd, check=False)
    return r.returncode == 0 and bool(r.stdout.strip())


def has_upstream(cwd: Path | None = None) -> bool:
    r = run(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=cwd, check=False)
    return r.returncode == 0 and bool(r.stdout.strip())


def has_commit_graph(cwd: Path | None = None) -> bool:
    gd = git_dir(cwd)
    if gd is None:
        return False
    return (gd / "objects" / "info" / "commit-graph").exists() or (
        gd / "objects" / "info" / "commit-graphs" / "commit-graph-chain"
    ).exists()
