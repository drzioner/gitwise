"""Deletes stale [gone] branches with mandatory confirmation. Never silent."""

from pathlib import Path

from .git import (
    current_branch,
    require_root,
    stale_branches,
    worktree_branches,
)
from .git import (
    run as git_run,
)
from .i18n import t
from .output import confirm, error, info, ok, print_json, warn

_DEFAULT_PROTECTED: frozenset[str] = frozenset(
    {"main", "master", "develop", "dev", "trunk", "release"}
)


def _categorize(
    cwd: Path, extra_protected: set[str] | None = None
) -> tuple[list[str], list[dict]]:
    """Returns (deletable, skipped_with_reasons) for all stale branches."""
    protected = _DEFAULT_PROTECTED | (extra_protected or set())
    checked_out = current_branch(cwd)
    active_wt = worktree_branches(cwd)

    deletable: list[str] = []
    skipped: list[dict] = []

    for branch in stale_branches(cwd):
        if branch in protected:
            skipped.append({"branch": branch, "reason": t("protected_branch")})
        elif branch == checked_out:
            skipped.append({"branch": branch, "reason": t("current_branch_msg")})
        elif branch in active_wt:
            skipped.append({"branch": branch, "reason": t("active_in_worktree")})
        else:
            deletable.append(branch)

    return deletable, skipped


def run_clean(
    *,
    branches: bool = False,
    refs: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
) -> int:
    if refs:
        error(t("clean_refs_not_implemented"))
        return 1

    if not branches:
        error(t("clean_specify_flag"))
        return 1

    root, err = require_root()
    if err:
        return err
    assert root is not None
    cwd = root

    deletable, skipped = _categorize(cwd)

    if as_json:
        print_json(
            {
                "v": 2,
                "dry_run": dry_run,
                "deletable": deletable,
                "skipped": skipped,
                "ok": True,
            }
        )
        return 0

    if not deletable and not skipped:
        ok(t("no_stale_branches"))
        return 0

    if skipped:
        info(t("protected_stale_branches", count=str(len(skipped))))
        for s in skipped:
            info(f"  – {s['branch']}  ({s['reason']})")
        info("")

    if not deletable:
        ok(t("no_deletable_branches"))
        return 0

    info(t("branches_to_delete", count=str(len(deletable))))
    for branch in deletable:
        info(f"  – {branch}")
    info("")

    if dry_run:
        info(t("dry_run_no_delete"))
        info(t("clean_to_delete"))
        return 0

    if not yes:
        if not confirm(t("confirm_delete_branches", count=str(len(deletable)))):
            info(t("cancelled"))
            return 0
        info("")

    errors: list[str] = []
    for branch in deletable:
        r = git_run(["branch", "-D", branch], cwd=cwd, check=False)
        if r.returncode == 0:
            ok(t("branch_deleted", branch=branch))
        else:
            errors.append(branch)
            warn(t("could_not_delete", branch=branch, error=r.stderr.strip()))

    if errors:
        return 1
    info("")
    ok(t("deleted_count", count=str(len(deletable))))
    return 0
