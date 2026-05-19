"""Worktree helpers for multi-agent Claude Code workflows."""

import re
from pathlib import Path

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import (
    error,
    info,
    ok,
    print_bracket,
    print_dim,
    print_header,
    print_json,
)


def _list_worktrees(cwd: Path) -> list[dict]:
    r = git_run(["worktree", "list", "--porcelain"], cwd=cwd, check=False)
    if r.returncode != 0:
        return []
    worktrees: list[dict] = []
    current: dict = {}
    for line in r.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {
                "path": line.removeprefix("worktree "),
                "branch": None,
                "locked": False,
                "prunable": False,
            }
        elif line.startswith("branch refs/heads/"):
            current["branch"] = line.removeprefix("branch refs/heads/")
        elif line == "locked":
            current["locked"] = True
        elif line.startswith("prunable"):
            current["prunable"] = True
    if current:
        worktrees.append(current)
    return worktrees


def _find_orphaned(cwd: Path) -> list[dict]:
    """Worktrees registered in git but whose directory no longer exists."""
    return [wt for wt in _list_worktrees(cwd) if not Path(wt["path"]).exists()]


def _worktree_create(branch: str, root: Path) -> tuple[int, str | None, dict]:
    """Core worktree creation logic. Returns (rc, path, error_or_data)."""
    safe_name = re.sub(r"^\.+", "", branch.replace("/", "-"))
    wt_path = root.parent / (safe_name or "worktree")

    if wt_path.exists():
        return 1, None, {"ok": False, "error": t("directory_exists", path=str(wt_path))}

    branch_exists = (
        git_run(
            ["rev-parse", "--verify", f"refs/heads/{branch}"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )

    if branch_exists:
        r = git_run(["worktree", "add", str(wt_path), branch], cwd=root, check=False)
    else:
        r = git_run(["worktree", "add", "-b", branch, str(wt_path)], cwd=root, check=False)

    if r.returncode != 0:
        return 1, None, {"ok": False, "error": r.stderr.strip()}

    return 0, str(wt_path), {"ok": True, "path": str(wt_path), "branch": branch}


def _worktree_new(branch: str, root: Path) -> int:
    rc, path, data = _worktree_create(branch, root)
    if rc != 0:
        error(data.get("error", t("worktree_failed", error="unknown")))
        return rc
    ok(t("worktree_created", path=path or ""))
    print_header(t("worktree_branch_msg", branch=branch))
    print_dim(t("worktree_to_use", path=path or ""))
    return 0


def _worktree_new_json(branch: str, root: Path) -> tuple[int, dict]:
    rc, _path, data = _worktree_create(branch, root)
    return rc, data


def _worktree_clean(cwd: Path, *, dry_run: bool = False) -> int:
    # git worktree prune removes stale admin files
    prune_args = ["worktree", "prune"]
    if dry_run:
        prune_args.append("--dry-run")
    prune_r = git_run(prune_args, cwd=cwd, check=False)

    if prune_r.returncode == 0 and prune_r.stdout.strip():
        print_bracket(t("worktrees_to_clean"))
        for line in prune_r.stdout.splitlines():
            print_dim(f"  {line}")

    # Detect orphaned worktrees (missing directory)
    orphaned = _find_orphaned(cwd)

    if not orphaned:
        ok(t("no_orphaned_worktrees", suffix=" (dry-run)" if dry_run else ""))
        return 0

    info(t("orphaned_worktrees", count=str(len(orphaned))))
    for wt in orphaned:
        print_bracket(wt["path"], t("branch_label", branch=wt["branch"] or t("unknown_branch")))

    if dry_run:
        print_dim(t("dry_run_no_clean"))
        return 0

    git_run(["worktree", "prune"], cwd=cwd, check=False)
    ok(t("worktrees_cleaned", count=str(len(orphaned))))
    return 0


def run_worktree(
    action: str | None,
    branch: str | None,
    *,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    if action == "new":
        if not branch:
            error(t("worktree_usage"))
            return 1
        if as_json:
            rc, data = _worktree_new_json(branch, root)
            print_json({"v": 2, **data})
            return rc
        return _worktree_new(branch, root)

    elif action == "clean":
        return _worktree_clean(root, dry_run=dry_run)

    else:
        error(t("worktree_usage_full"))
        return 1
