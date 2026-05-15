"""Worktree helpers for multi-agent Claude Code workflows."""

import re
from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
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
        error("no se pudo determinar la raíz del repositorio")
        return 1

    # Place worktree as sibling directory of repo root; sanitize branch name for filesystem
    safe_name = re.sub(r"^\.+", "", branch.replace("/", "-"))
    wt_path = root.parent / (safe_name or "worktree")

    if wt_path.exists():
        error(f"el directorio ya existe: {wt_path}")
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
        error(f"no se pudo crear worktree: {r.stderr.strip()}")
        return 1

    ok(f"worktree creado: {wt_path}")
    info(f"  rama: {branch}")
    info(f"  para usarlo: cd {wt_path}")
    return 0


def _worktree_new_json(branch: str, cwd: Path) -> tuple[int, dict]:
    root = repo_root(cwd)
    if root is None:
        return 1, {"ok": False, "error": "no se pudo determinar la raíz del repositorio"}

    safe_name = re.sub(r"^\.+", "", branch.replace("/", "-"))
    wt_path = root.parent / (safe_name or "worktree")

    if wt_path.exists():
        return 1, {"ok": False, "error": f"el directorio ya existe: {wt_path}"}

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
        info("worktrees a limpiar:")
        for line in prune_r.stdout.splitlines():
            info(f"  {line}")
        info("")

    # Detect orphaned worktrees (missing directory)
    orphaned = _find_orphaned(cwd)

    if not orphaned:
        ok("no hay worktrees huérfanos" + (" (dry-run)" if dry_run else ""))
        return 0

    info(f"worktrees huérfanos detectados ({len(orphaned)}) — directorio inexistente:")
    for wt in orphaned:
        info(f"  – {wt['path']}  (rama: {wt['branch'] or 'desconocida'})")
    info("")

    if dry_run:
        info("modo dry-run — no se limpiará nada")
        return 0

    git_run(["worktree", "prune"], cwd=cwd, check=False)
    ok(f"limpiados {len(orphaned)} worktree(s) huérfano(s)")
    return 0


def run_worktree(
    action: str | None,
    branch: str | None,
    *,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    if not is_repo():
        error("no es un repositorio git")
        return 1

    cwd = repo_root()
    if cwd is None:
        error("no se pudo determinar la raíz del repositorio")
        return 1

    if action == "new":
        if not branch:
            error("uso: gitwise worktree new <branch>")
            return 1
        if as_json:
            rc, data = _worktree_new_json(branch, cwd)
            print_json({"v": 1, **data})
            return rc
        return _worktree_new(branch, cwd)

    elif action == "clean":
        return _worktree_clean(cwd, dry_run=dry_run)

    else:
        error("uso: gitwise worktree new <branch>  |  gitwise worktree clean [--dry-run]")
        return 1
