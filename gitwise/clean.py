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
from .output import (
    confirm,
    error,
    ok,
    print_blank,
    print_bracket,
    print_dim,
    print_header,
    print_json,
    print_success,
    status,
    warn,
)
from .utils.json_envelope import error_envelope, ok_envelope

_DEFAULT_PROTECTED: frozenset[str] = frozenset(
    {"main", "master", "develop", "dev", "trunk", "release"}
)


def _categorize(
    cwd: Path, extra_protected: set[str] | None = None
) -> tuple[list[str], list[dict[str, str]]]:
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
    if root is None:
        return 1
    cwd = root

    with status(t("status_scanning_stale")):
        deletable, skipped = _categorize(cwd)

    if dry_run:
        if as_json:
            print_json(
                ok_envelope(
                    payload={
                        "dry_run": True,
                        "applied": False,
                        "deletable": deletable,
                        "skipped": skipped,
                    }
                )
            )
            return 0
        if not deletable and not skipped:
            ok(t("no_stale_branches"))
            return 0
        if skipped:
            print_header(t("protected_stale_branches", count=str(len(skipped))))
            for s in skipped:
                print_bracket(s["branch"], s["reason"])
            print_blank()
        if not deletable:
            ok(t("no_deletable_branches"))
            return 0
        print_header(t("branches_to_delete", count=str(len(deletable))))
        for branch in deletable:
            print_bracket(branch)
        print_blank()
        print_dim(t("dry_run_no_delete"))
        print_dim(t("clean_to_delete"))
        return 0

    if as_json and not yes:
        print_json(
            error_envelope(
                error=t("yes_required_with_json"),
                code="yes_required",
                hint=t("yes_required_hint"),
            )
        )
        return 2

    if not as_json:
        if not deletable and not skipped:
            ok(t("no_stale_branches"))
            return 0
        if skipped:
            print_header(t("protected_stale_branches", count=str(len(skipped))))
            for s in skipped:
                print_bracket(s["branch"], s["reason"])
            print_blank()
        if not deletable:
            ok(t("no_deletable_branches"))
            return 0
        print_header(t("branches_to_delete", count=str(len(deletable))))
        for branch in deletable:
            print_bracket(branch)
        print_blank()
        if not yes:
            if not confirm(t("confirm_delete_branches", count=str(len(deletable)))):
                print_dim(t("cancelled"))
                return 0
            print_blank()
    elif not deletable:
        print_json(
            ok_envelope(
                payload={
                    "dry_run": False,
                    "applied": True,
                    "deleted": [],
                    "skipped": skipped,
                    "delete_errors": [],
                }
            )
        )
        return 0

    deleted: list[str] = []
    delete_errors: list[dict[str, str]] = []
    for branch in deletable:
        r = git_run(["branch", "-D", branch], cwd=cwd, check=False)
        if r.returncode == 0:
            deleted.append(branch)
            if not as_json:
                print_success(t("branch_deleted", branch=branch))
        else:
            delete_errors.append({"branch": branch, "error": r.stderr.strip()})
            if not as_json:
                warn(t("could_not_delete", branch=branch, error=r.stderr.strip()))

    if as_json:
        payload: dict[str, object] = {
            "dry_run": False,
            "applied": True,
            "deleted": deleted,
            "skipped": skipped,
            "delete_errors": delete_errors,
        }
        if delete_errors:
            print_json(
                error_envelope(
                    error=t("clean_delete_failures", count=str(len(delete_errors))),
                    code="clean_delete_failures",
                    payload=payload,
                )
            )
            return 1
        print_json(ok_envelope(payload=payload))
        return 0

    if delete_errors:
        return 1
    print_blank()
    ok(t("deleted_count", count=str(len(deletable))))
    return 0
