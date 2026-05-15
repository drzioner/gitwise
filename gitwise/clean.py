"""Deletes stale [gone] branches with mandatory confirmation. Never silent."""

from pathlib import Path

from .git import (
    current_branch,
    is_repo,
    repo_root,
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
            skipped.append({"branch": branch, "reason": t("protegida")})
        elif branch == checked_out:
            skipped.append({"branch": branch, "reason": t("rama_actual")})
        elif branch in active_wt:
            skipped.append({"branch": branch, "reason": t("activa_worktree")})
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
        error(t("clean_refs_no_impl"))
        return 1

    if not branches:
        error(t("clean_especifica"))
        return 1

    if not is_repo():
        error(t("no_repo"))
        return 1

    cwd = repo_root()
    if cwd is None:
        error(t("no_root"))
        return 1

    deletable, skipped = _categorize(cwd)

    if as_json:
        print_json(
            {
                "v": 1,
                "dry_run": dry_run,
                "deletable": deletable,
                "skipped": skipped,
                "ok": True,
            }
        )
        return 0

    if not deletable and not skipped:
        ok(t("no_ramas_stale"))
        return 0

    if skipped:
        info(t("ramas_protegidas", count=str(len(skipped))))
        for s in skipped:
            info(f"  – {s['branch']}  ({s['reason']})")
        info("")

    if not deletable:
        ok(t("no_ramas_eliminables"))
        return 0

    info(t("ramas_a_eliminar", count=str(len(deletable))))
    for branch in deletable:
        info(f"  – {branch}")
    info("")

    if dry_run:
        info(t("dry_run_no_delete"))
        info(t("clean_para_eliminar"))
        return 0

    if not yes:
        if not confirm(t("confirm_eliminar", count=str(len(deletable)))):
            info(t("cancelado"))
            return 0
        info("")

    errors: list[str] = []
    for branch in deletable:
        r = git_run(["branch", "-D", branch], cwd=cwd, check=False)
        if r.returncode == 0:
            ok(t("eliminada", branch=branch))
        else:
            errors.append(branch)
            warn(t("no_se_pudo_eliminar", branch=branch, error=r.stderr.strip()))

    if errors:
        return 1
    info("")
    ok(t("eliminadas_count", count=str(len(deletable))))
    return 0
