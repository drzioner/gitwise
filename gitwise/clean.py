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
            skipped.append({"branch": branch, "reason": "protegida (lista por defecto)"})
        elif branch == checked_out:
            skipped.append({"branch": branch, "reason": "rama actual (checked out)"})
        elif branch in active_wt:
            skipped.append({"branch": branch, "reason": "activa en un worktree"})
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
        error("'clean --refs' no está implementado")
        return 1

    if not branches:
        error("especifica --branches  (o --refs)")
        return 1

    if not is_repo():
        error("no es un repositorio git")
        return 1

    cwd = repo_root()
    if cwd is None:
        error("no se pudo determinar la raíz del repositorio")
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
        ok("no hay ramas stale ([gone])")
        return 0

    if skipped:
        info(f"ramas stale protegidas ({len(skipped)}) — no se tocarán:")
        for s in skipped:
            info(f"  – {s['branch']}  ({s['reason']})")
        info("")

    if not deletable:
        ok("no hay ramas eliminables")
        return 0

    info(f"ramas stale a eliminar ({len(deletable)}):")
    for branch in deletable:
        info(f"  – {branch}")
    info("")

    if dry_run:
        info("modo dry-run — no se eliminará nada")
        info("para eliminar: gitwise clean --branches --yes")
        return 0

    if not yes:
        if not confirm(f"¿eliminar {len(deletable)} rama(s)? [s/N] "):
            info("cancelado.")
            return 0
        info("")

    errors: list[str] = []
    for branch in deletable:
        r = git_run(["branch", "-D", branch], cwd=cwd, check=False)
        if r.returncode == 0:
            ok(f"eliminada: {branch}")
        else:
            errors.append(branch)
            warn(f"no se pudo eliminar: {branch}  ({r.stderr.strip()})")

    if errors:
        return 1
    info("")
    ok(f"eliminadas {len(deletable)} rama(s) stale")
    return 0
