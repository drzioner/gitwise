"""Git repo optimizations: commit-graph, repack, prune."""

import os
import subprocess
import time
from pathlib import Path

from .git import git_dir as get_git_dir
from .git import require_root
from .git import run as git_run
from .git import version as git_version
from .i18n import t
from .output import (
    confirm,
    debug,
    ok,
    print_dim,
    print_header,
    print_json,
    print_section,
    print_status_line,
    warn,
)


def _gc_is_running(cwd: Path) -> bool:
    gd = get_git_dir(cwd)
    if gd is None:
        return False
    pid_file = gd / "gc.pid"
    if not pid_file.exists():
        return False
    try:
        if (time.time() - pid_file.stat().st_mtime) > 86400:
            return False
        pid = int(pid_file.read_text().strip().splitlines()[0])
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        return False


def _repo_size_kb(cwd: Path) -> int:
    gd = get_git_dir(cwd)
    if gd is None:
        return 0
    try:
        r = subprocess.run(
            ["du", "-sk", str(gd)], capture_output=True, text=True, check=True, timeout=120
        )
        return int(r.stdout.split()[0])
    except (subprocess.SubprocessError, ValueError, IndexError, FileNotFoundError):
        return sum(f.stat().st_size for f in gd.rglob("*") if f.is_file()) // 1024


def _write_commit_graph(cwd: Path) -> bool:
    args = ["commit-graph", "write", "--reachable"]
    if git_version() >= (2, 31, 0):
        args.append("--changed-paths")
    r = git_run(args, cwd=cwd, check=False)
    return r.returncode == 0


def _repack(cwd: Path) -> bool:
    r = git_run(["repack", "-A", "-d", "--write-bitmap-index"], cwd=cwd, check=False)
    if r.returncode != 0:
        debug(t("repack_fallo_bitmap"))
        r = git_run(["repack", "-A", "-d"], cwd=cwd, check=False)
    return r.returncode == 0


def _prune(cwd: Path) -> bool:
    return git_run(["prune"], cwd=cwd, check=False).returncode == 0


def _get_steps() -> list[tuple[str, str]]:
    return [
        ("commit-graph", t("step_commit_graph")),
        ("repack", t("step_repack")),
        ("prune", t("step_prune")),
    ]


def run_optimize(*, dry_run: bool = False, yes: bool = False, as_json: bool = False) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1
    cwd = root

    if _gc_is_running(cwd):
        warn(t("gc_already_running"))
        return 1

    steps = _get_steps()
    if as_json:
        print_json(
            {
                "v": 2,
                "dry_run": dry_run,
                "steps": [{"name": n, "desc": d} for n, d in steps],
                "ok": True,
            }
        )
        return 0

    size_before = _repo_size_kb(cwd)
    print_header(t("optimizing", root=str(cwd)))
    print()
    for _name, desc in steps:
        print_status_line("›", desc, t("pending"), ok_flag=False)

    print()

    if dry_run:
        print_dim(t("dry_run_no_exec"))
        return 0

    if not yes:
        if not confirm(t("confirm_optimize")):
            print_dim(t("cancelled"))
            return 0
        print()

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
    print_section(t("summary"))
    if saved > 0:
        ok(t("space_freed", saved=str(saved), before=str(size_before), after=str(size_after)))
    else:
        ok(t("repo_size", size=str(size_after)))

    if not graph_ok and not repack_ok:
        return 1
    return 2 if not prune_ok else 0
