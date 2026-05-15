"""Git repo optimizations: commit-graph, repack, prune."""

import os
import time
from pathlib import Path

from .git import git_dir as get_git_dir
from .git import is_repo, repo_root
from .git import run as git_run
from .git import version as git_version
from .i18n import t
from .output import confirm, debug, error, info, ok, print_json, warn


def _gc_is_running(cwd: Path) -> bool:
    """Checks if git gc / maintenance is already running via .git/gc.pid.
    Advisory only — ignores stale locks older than 24h."""
    gd = get_git_dir(cwd)
    if gd is None:
        return False
    pid_file = gd / "gc.pid"
    if not pid_file.exists():
        return False
    try:
        # Treat locks older than 24h as stale (gc.pid left behind by crash)
        if (time.time() - pid_file.stat().st_mtime) > 86400:
            return False
        pid = int(pid_file.read_text().strip().splitlines()[0])
        os.kill(pid, 0)  # Signal 0 = check if process exists
        return True
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        return False


def _repo_size_kb(cwd: Path) -> int:
    gd = get_git_dir(cwd)
    if gd is None:
        return 0
    return sum(f.stat().st_size for f in gd.rglob("*") if f.is_file()) // 1024


def _write_commit_graph(cwd: Path) -> bool:
    args = ["commit-graph", "write", "--reachable"]
    if git_version() >= (2, 31, 0):
        args.append("--changed-paths")
    r = git_run(args, cwd=cwd, check=False)
    return r.returncode == 0


def _repack(cwd: Path) -> bool:
    # Try with bitmap index (faster future reads); fall back if unsupported
    r = git_run(["repack", "-A", "-d", "--write-bitmap-index"], cwd=cwd, check=False)
    if r.returncode != 0:
        debug(t("repack_fallo_bitmap"))
        r = git_run(["repack", "-A", "-d"], cwd=cwd, check=False)
    return r.returncode == 0


def _prune(cwd: Path) -> bool:
    return git_run(["prune"], cwd=cwd, check=False).returncode == 0


_STEPS = [
    ("commit-graph", "git commit-graph write --reachable --changed-paths"),
    ("repack", "git repack -A -d --write-bitmap-index"),
    ("prune", "git prune (elimina objetos no referenciados)"),
]


def run_optimize(*, dry_run: bool = False, yes: bool = False, as_json: bool = False) -> int:
    if not is_repo():
        error(t("not_a_git_repo"))
        return 1

    cwd = repo_root()
    if cwd is None:
        error(t("no_repo_root"))
        return 1

    if _gc_is_running(cwd):
        warn(t("gc_already_running"))
        return 1

    if as_json:
        print_json(
            {
                "v": 1,
                "dry_run": dry_run,
                "steps": [{"name": n, "desc": d} for n, d in _STEPS],
                "ok": True,
            }
        )
        return 0

    size_before = _repo_size_kb(cwd)
    info(t("optimizing", root=str(cwd)))
    info("")
    for _, desc in _STEPS:
        info(f"  › {desc}")
    info("")

    if dry_run:
        info(t("dry_run_no_exec"))
        return 0

    if not yes:
        if not confirm(t("confirm_optimize")):
            info(t("cancelled"))
            return 0
        info("")

    graph_ok = _write_commit_graph(cwd)
    if graph_ok:
        ok(t("commit_graph_updated"))
    else:
        warn(t("commit_graph_failed"))

    repack_ok = _repack(cwd)
    if repack_ok:
        ok(t("repack_complete"))
    else:
        warn(t("repack_failed"))

    prune_ok = _prune(cwd)
    if prune_ok:
        ok(t("prune_complete"))
    else:
        warn(t("prune_not_critical"))

    size_after = _repo_size_kb(cwd)
    saved = size_before - size_after
    info("")
    if saved > 0:
        ok(t("space_freed", saved=str(saved), before=str(size_before), after=str(size_after)))
    else:
        ok(t("repo_size", size=str(size_after)))

    return 0 if (graph_ok or repack_ok) else 1
