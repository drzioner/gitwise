"""Worktree helpers for multi-agent Claude Code workflows."""

import re
from pathlib import Path

from gitwise.git import require_root, validate_branch_name
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import (
    error,
    info,
    ok,
    print_bracket,
    print_dim,
    print_header,
    print_json,
    status,
)
from gitwise.utils.json_envelope import error_envelope, ok_envelope


def _list_worktrees(cwd: Path) -> list[dict]:
    """Parse ``git worktree list --porcelain`` into dicts with path/branch/locked/prunable."""
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
        elif line.startswith("locked"):
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
    if branch.startswith("/") or branch.startswith("../") or "/../" in branch:
        return 1, None, {"ok": False, "error": t("invalid_branch_name", name=branch)}

    safe_name = re.sub(r"^\.+", "", branch.replace("/", "-"))
    wt_path = root.parent / (safe_name or "worktree")

    if not validate_branch_name(branch):
        return 1, None, {"ok": False, "error": t("invalid_branch_name", name=branch)}

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

    with status(t("status_worktree_add", branch=branch)):
        if branch_exists:
            r = git_run(["worktree", "add", "--", str(wt_path), branch], cwd=root, check=False)
        else:
            r = git_run(
                ["worktree", "add", "-b", branch, "--", str(wt_path)], cwd=root, check=False
            )

    if r.returncode != 0:
        return 1, None, {"ok": False, "error": r.stderr.strip()}

    return 0, str(wt_path), {"ok": True, "path": str(wt_path), "branch": branch}


def _worktree_new(branch: str, root: Path) -> int:
    """Create a worktree for *branch* and print human output."""
    rc, path, data = _worktree_create(branch, root)
    if rc != 0:
        error(data.get("error", t("worktree_failed", error="unknown")))
        return rc
    ok(t("worktree_created", path=path or ""))
    print_header(t("worktree_branch_msg", branch=branch))
    print_dim(t("worktree_to_use", path=path or ""))
    return 0


def _worktree_new_json(branch: str, root: Path) -> tuple[int, dict]:
    """Create a worktree for *branch* and return a JSON-ready dict."""
    rc, _path, data = _worktree_create(branch, root)
    return rc, data


def _worktree_list(cwd: Path, *, as_json: bool = False) -> int:
    """List registered worktrees (human table or v3 JSON envelope)."""
    worktrees = _list_worktrees(cwd)
    if as_json:
        print_json(ok_envelope("worktree", worktrees=worktrees, count=len(worktrees)))
        return 0
    if not worktrees:
        info(t("worktree_list_empty"))
        return 0
    print_header(t("worktree_list_header", count=str(len(worktrees))))
    for wt in worktrees:
        branch = wt["branch"] or t("unknown_branch")
        flags = []
        if wt["locked"]:
            flags.append(t("worktree_flag_locked"))
        if wt["prunable"]:
            flags.append(t("worktree_flag_prunable"))
        suffix = f"  [{', '.join(flags)}]" if flags else ""
        print_bracket(wt["path"], t("branch_label", branch=branch) + suffix)
    return 0


def _worktree_clean(cwd: Path, *, dry_run: bool = False, as_json: bool = False) -> int:
    """Prune stale worktree admin files and report orphaned worktrees."""
    # git worktree prune removes stale admin files
    prune_args = ["worktree", "prune"]
    if dry_run:
        prune_args.append("--dry-run")
    prune_r = git_run(prune_args, cwd=cwd, check=False)

    pruned_lines = prune_r.stdout.strip().splitlines() if prune_r.stdout.strip() else []

    # Detect orphaned worktrees (missing directory)
    orphaned = _find_orphaned(cwd)

    if not orphaned and not pruned_lines:
        if as_json:
            print_json(ok_envelope("worktree", cleaned=0, orphaned=0, dry_run=dry_run))
        else:
            ok(t("no_orphaned_worktrees", suffix=" (dry-run)" if dry_run else ""))
        return 0

    if as_json:
        print_json(
            ok_envelope(
                "worktree",
                pruned=len(pruned_lines),
                orphaned=len(orphaned),
                orphaned_branches=[wt["branch"] for wt in orphaned],
                dry_run=dry_run,
            )
        )
        return 0

    if pruned_lines:
        print_bracket(t("worktrees_to_clean"))
        for line in pruned_lines:
            print_dim(f"  {line}")

    info(t("orphaned_worktrees", count=str(len(orphaned))))
    for wt in orphaned:
        print_bracket(wt["path"], t("branch_label", branch=wt["branch"] or t("unknown_branch")))

    if dry_run:
        print_dim(t("dry_run_no_clean"))
        return 0

    git_run(["worktree", "prune"], cwd=cwd, check=False)
    ok(t("worktrees_cleaned", count=str(len(orphaned))))
    return 0


def _worktree_remove(
    target: str, root: Path, *, force: bool = False, as_json: bool = False
) -> int:
    """Remove a worktree identified by path or checked-out branch name."""
    if not target:
        msg = t("worktree_usage")
        if as_json:
            print_json(error_envelope("worktree", error=msg, code="worktree_target_required"))
        else:
            error(msg)
        return 1

    worktrees = _list_worktrees(root)
    match = None
    for wt in worktrees:
        if wt["path"] == target or wt["branch"] == target or wt["path"].endswith("/" + target):
            match = wt
            break
    if match is None:
        msg = t("worktree_not_found", target=target)
        if as_json:
            print_json(error_envelope("worktree", error=msg, code="worktree_not_found"))
        else:
            error(msg)
        return 1
    # Never remove the primary worktree (the repo root itself).
    if Path(match["path"]) == root:
        msg = t("worktree_remove_primary")
        if as_json:
            print_json(error_envelope("worktree", error=msg, code="worktree_remove_primary"))
        else:
            error(msg)
        return 1

    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(match["path"])
    r = git_run(args, cwd=root, check=False)
    if r.returncode != 0:
        msg = r.stderr.strip() or t("worktree_failed", error="remove")
        if as_json:
            print_json(error_envelope("worktree", error=msg, code="worktree_remove_failed"))
        else:
            error(msg)
        return 1
    if as_json:
        print_json(
            ok_envelope("worktree", removed=match["path"], branch=match.get("branch") or "")
        )
        return 0
    ok(t("worktree_removed", path=match["path"]))
    return 0


def run_worktree(
    action: str | None,
    branch: str | None,
    *,
    dry_run: bool = False,
    as_json: bool = False,
    force: bool = False,
) -> int:
    """Entry point for the ``gitwise worktree`` command."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    if action == "new":
        if not branch:
            error(t("worktree_usage"))
            return 1
        if as_json:
            rc, data = _worktree_new_json(branch, root)
            if rc == 0:
                print_json(ok_envelope("worktree", data={"path": data["path"], "branch": branch}))
            else:
                print_json(
                    error_envelope(
                        "worktree",
                        error=str(data.get("error", t("worktree_failed", error="unknown"))),
                        code=str(data.get("code", "worktree_failed")),
                        data=data,
                    )
                )
            return rc
        return _worktree_new(branch, root)

    elif action == "clean":
        return _worktree_clean(root, dry_run=dry_run, as_json=as_json)

    elif action == "remove":
        return _worktree_remove(branch or "", root, force=force, as_json=as_json)

    elif action == "list":
        return _worktree_list(root, as_json=as_json)

    else:
        error(t("worktree_usage_full"))
        return 1
