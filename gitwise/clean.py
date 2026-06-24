"""Deletes stale [gone] branches with mandatory confirmation. Never silent."""

from pathlib import Path

from gitwise.git import (
    current_branch,
    require_root,
    stale_branches,
    worktree_branches,
)
from gitwise.git import (
    run as git_run,
)
from gitwise.i18n import t
from gitwise.output import (
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
from gitwise.utils.json_envelope import error_envelope, ok_envelope

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
    """Delete stale branches whose upstream tracking ref is gone.

    Requires ``--branches`` to be set.  Returns 0 on success (including
    user-cancelled), 1 on delete failures or missing flag, 2 when
    ``--json`` is used without ``--yes``.
    """
    if refs:
        error(t("clean_refs_not_implemented"))
        return 1

    if not branches:
        error(t("clean_specify_flag"))
        return 1

    root = require_root()
    if root is None:
        return 1
    cwd = root

    with status(t("status_scanning_stale")):
        deletable, skipped = _categorize(cwd)

    if dry_run:
        if as_json:
            print_json(
                ok_envelope(
                    "clean",
                    data={
                        "dry_run": True,
                        "applied": False,
                        "deletable": deletable,
                        "skipped": skipped,
                    },
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
        # Why clean/optimize gate --json behind --yes but commit/sync/merge/tag/pick
        # do not: clean and optimize are destructive, multi-item, irreversible
        # operations (delete branches, gc/repack) where a confirmation gate adds
        # real safety. The single-intent write verbs have their intent fully
        # specified by their arguments (the commit message, the push target), so
        # a --yes gate there would add friction without safety value.
        print_json(
            error_envelope(
                "clean",
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
                # Cancel returns 0 by project convention (matches setup/undo).
                # Agent callers never reach here: --json without --yes is rejected
                # upstream with the `yes_required` envelope, so an agent always
                # gets an explicit, distinguishable response.
                print_dim(t("cancelled"))
                return 0
            print_blank()
    elif not deletable:
        print_json(
            ok_envelope(
                "clean",
                data={
                    "dry_run": False,
                    "applied": True,
                    "deleted": [],
                    "skipped": skipped,
                    "delete_errors": [],
                },
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
                    "clean",
                    error=t("clean_delete_failures", count=str(len(delete_errors))),
                    code="clean_delete_failures",
                    data=payload,
                )
            )
            return 1
        print_json(ok_envelope("clean", data=payload))
        return 0

    if delete_errors:
        return 1
    print_blank()
    ok(t("deleted_count", count=str(len(deletable))))
    return 0
