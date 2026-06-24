"""Git repo optimizations: commit-graph, repack, prune."""

import os
import subprocess
import time
from pathlib import Path

from gitwise.git import git_dir as get_git_dir
from gitwise.git import require_root
from gitwise.git import run as git_run
from gitwise.git import version as git_version
from gitwise.i18n import t
from gitwise.output import (
    confirm,
    debug,
    ok,
    print_blank,
    print_dim,
    print_header,
    print_json,
    print_section,
    print_status_line,
    status,
    warn,
)
from gitwise.utils.json_envelope import error_envelope, ok_envelope


def _gc_is_running(cwd: Path) -> bool:
    """Return True if a git gc process is actively running in the repo."""
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
    """Return the ``.git`` directory size in KiB via ``du -sk``."""
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
    """Write a commit-graph for all reachable objects.  Returns True on success."""
    args = ["commit-graph", "write", "--reachable"]
    if git_version() >= (2, 31, 0):
        args.append("--changed-paths")
    r = git_run(args, cwd=cwd, check=False)
    return r.returncode == 0


def _repack(cwd: Path) -> bool:
    """Repack with ``-A -d``; retries without bitmap-index on failure."""
    r = git_run(["repack", "-A", "-d", "--write-bitmap-index"], cwd=cwd, check=False)
    if r.returncode != 0:
        debug(t("repack_fallo_bitmap"))
        r = git_run(["repack", "-A", "-d"], cwd=cwd, check=False)
    return r.returncode == 0


def _prune(cwd: Path) -> bool:
    """Run ``git prune`` to remove unreachable loose objects."""
    return git_run(["prune"], cwd=cwd, check=False).returncode == 0


def _get_steps() -> list[tuple[str, str]]:
    """Return the ordered list of optimization steps (name, description)."""
    return [
        ("commit-graph", t("step_commit_graph")),
        ("repack", t("step_repack")),
        ("prune", t("step_prune")),
    ]


def run_optimize(*, dry_run: bool = False, yes: bool = False, as_json: bool = False) -> int:
    """Run commit-graph write, repack, and prune on the repo.

    Returns 0 when all steps succeed, 1 when commit-graph or repack fails,
    2 when only prune fails.  Returns 2 when ``--json`` is used without
    ``--yes``.
    """
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

    if dry_run:
        if as_json:
            print_json(
                ok_envelope(
                    "optimize",
                    data={
                        "dry_run": True,
                        "applied": False,
                        "steps": [{"name": n, "desc": d} for n, d in steps],
                    },
                )
            )
            return 0
        print_header(t("optimizing", root=str(cwd)))
        print_blank()
        for _name, desc in steps:
            print_status_line("›", desc, t("pending"), ok_flag=False)
        print_blank()
        print_dim(t("dry_run_no_exec"))
        return 0

    if as_json and not yes:
        print_json(
            error_envelope(
                "optimize",
                error=t("yes_required_with_json"),
                code="yes_required",
                hint=t("yes_required_hint"),
            )
        )
        return 2

    if not as_json:
        print_header(t("optimizing", root=str(cwd)))
        print_blank()
        for _name, desc in steps:
            print_status_line("›", desc, t("pending"), ok_flag=False)
        print_blank()
        if not yes:
            if not confirm(t("confirm_optimize")):
                # Cancel returns 0 by project convention (matches setup/undo).
                # Agent callers never reach here: --json without --yes is rejected
                # upstream with the `yes_required` envelope, so an agent always
                # gets an explicit, distinguishable response.
                print_dim(t("cancelled"))
                return 0
            print_blank()

    size_before = _repo_size_kb(cwd)

    if as_json:
        graph_ok = _write_commit_graph(cwd)
        repack_ok = _repack(cwd)
        prune_ok = _prune(cwd)
    else:
        with status(t("status_optimize_commit_graph")):
            graph_ok = _write_commit_graph(cwd)
        if graph_ok:
            ok(t("commit_graph_updated"))
        else:
            warn(t("commit_graph_failed"))

        with status(t("status_optimize_repack")):
            repack_ok = _repack(cwd)
        if repack_ok:
            ok(t("repack_complete"))
        else:
            warn(t("repack_failed"))

        with status(t("status_optimize_prune")):
            prune_ok = _prune(cwd)
        if prune_ok:
            ok(t("prune_complete"))
        else:
            warn(t("prune_not_critical"))

    size_after = _repo_size_kb(cwd)
    saved = size_before - size_after

    if not graph_ok and not repack_ok:
        rc = 1
    elif not prune_ok:
        rc = 2
    else:
        rc = 0

    if as_json:
        payload: dict[str, object] = {
            "dry_run": False,
            "applied": True,
            "steps": [
                {"name": "commit-graph", "desc": t("step_commit_graph"), "ok": graph_ok},
                {"name": "repack", "desc": t("step_repack"), "ok": repack_ok},
                {"name": "prune", "desc": t("step_prune"), "ok": prune_ok},
            ],
            "size_before_kb": size_before,
            "size_after_kb": size_after,
            "saved_kb": saved,
            "rc": rc,
        }
        if rc == 0:
            print_json(ok_envelope("optimize", data=payload))
        else:
            print_json(
                error_envelope(
                    "optimize",
                    error=t("optimize_partial_failure"),
                    code="optimize_partial_failure",
                    data=payload,
                )
            )
    else:
        print_section(t("summary"))
        if saved > 0:
            ok(t("space_freed", saved=str(saved), before=str(size_before), after=str(size_after)))
        else:
            ok(t("repo_size", size=str(size_after)))

    return rc
