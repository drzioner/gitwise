"""Worktree helpers for multi-agent Claude Code workflows."""

import re
from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import error, info, ok, print_json


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


def _worktree_new(branch: str, cwd: Path) -> int:
    root = repo_root(cwd)
    if root is None:
        error(t("no_repo_root"))
        return 1

    safe_name = re.sub(r"^\.+", "", branch.replace("/", "-"))
    wt_path = root.parent / (safe_name or "worktree")

    if wt_path.exists():
        error(t("directory_exists", path=str(wt_path)))
        return 1

    branch_exists = (
        git_run(
            ["rev-parse", "--verify", f"refs/heads/{branch}"],
            cwd=cwd,
            check=False,
        ).returncode
        == 0
    )

    if branch_exists:
        r = git_run(["worktree", "add", str(wt_path), branch], cwd=cwd, check=False)
    else:
        r = git_run(["worktree", "add", "-b", branch, str(wt_path)], cwd=cwd, check=False)

    if r.returncode != 0:
        error(t("worktree_failed", error=r.stderr.strip()))
        return 1

    ok(t("worktree_created", path=str(wt_path)))
    info(t("worktree_branch_msg", branch=branch))
    info(t("worktree_to_use", path=str(wt_path)))
    return 0


def _worktree_new_json(branch: str, cwd: Path) -> tuple[int, dict]:
    root = repo_root(cwd)
    if root is None:
        return 1, {"ok": False, "error": t("no_repo_root")}

    safe_name = re.sub(r"^\.+", "", branch.replace("/", "-"))
    wt_path = root.parent / (safe_name or "worktree")

    if wt_path.exists():
        return 1, {"ok": False, "error": t("directory_exists", path=str(wt_path))}

    branch_exists = (
        git_run(
            ["rev-parse", "--verify", f"refs/heads/{branch}"],
            cwd=cwd,
            check=False,
        ).returncode
        == 0
    )

    if branch_exists:
        r = git_run(["worktree", "add", str(wt_path), branch], cwd=cwd, check=False)
    else:
        r = git_run(["worktree", "add", "-b", branch, str(wt_path)], cwd=cwd, check=False)

    if r.returncode != 0:
        return 1, {"ok": False, "error": r.stderr.strip()}

    return 0, {"ok": True, "path": str(wt_path), "branch": branch}


def _worktree_clean(cwd: Path, *, dry_run: bool = False) -> int:
    # git worktree prune removes stale admin files
    prune_args = ["worktree", "prune"]
    if dry_run:
        prune_args.append("--dry-run")
    prune_r = git_run(prune_args, cwd=cwd, check=False)

    if prune_r.returncode == 0 and prune_r.stdout.strip():
        info(t("worktrees_to_clean"))
        for line in prune_r.stdout.splitlines():
            info(f"  {line}")
        info("")

    # Detect orphaned worktrees (missing directory)
    orphaned = _find_orphaned(cwd)

    if not orphaned:
        ok(t("no_orphaned_worktrees", suffix=" (dry-run)" if dry_run else ""))
        return 0

    info(t("orphaned_worktrees", count=str(len(orphaned))))
    for wt in orphaned:
        info(
            f"  – {wt['path']}  ({t('branch_label', branch=wt['branch'] or t('unknown_branch'))})"
        )
    info("")

    if dry_run:
        info(t("dry_run_no_clean"))
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
    if not is_repo():
        error(t("not_a_git_repo"))
        return 1

    cwd = repo_root()
    if cwd is None:
        error(t("no_repo_root"))
        return 1

    if action == "new":
        if not branch:
            error(t("worktree_usage"))
            return 1
        if as_json:
            rc, data = _worktree_new_json(branch, cwd)
            print_json({"v": 2, **data})
            return rc
        return _worktree_new(branch, cwd)

    elif action == "clean":
        return _worktree_clean(cwd, dry_run=dry_run)

    else:
        error(t("worktree_usage_full"))
        return 1
