"""Focused changed-file list for AI agents and humans."""

from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
from .output import error, info, print_json


def _has_commits(cwd: Path) -> bool:
    return git_run(["rev-parse", "HEAD"], cwd=cwd, check=False).returncode == 0


def run_diff(*, staged: bool = False, stat: bool = False, as_json: bool = False) -> int:
    if not is_repo():
        error("no es un repositorio git")
        return 1

    cwd = repo_root()
    if cwd is None:
        error("no se pudo determinar la raíz del repositorio")
        return 1

    if not staged and not _has_commits(cwd):
        if as_json:
            print_json({"files": [], "count": 0, "note": "no commits yet"})
            return 0
        info("no commits yet")
        return 0

    if stat:
        r = git_run(["--no-pager", "diff", "--stat", "HEAD"], cwd=cwd, check=False)
    elif staged:
        r = git_run(["--no-pager", "diff", "--name-status", "--staged"], cwd=cwd, check=False)
    else:
        r = git_run(["--no-pager", "diff", "--name-status", "HEAD"], cwd=cwd, check=False)

    if r.returncode != 0:
        error(f"git diff failed: {r.stderr.strip()}")
        return 1

    lines = [line for line in r.stdout.splitlines() if line.strip()]

    if stat:
        file_lines = [line for line in lines if "|" in line]
        files = []
        for fl in file_lines:
            parts = fl.split("|", 1)
            if len(parts) == 2:
                files.append({"path": parts[0].strip(), "changes": parts[1].strip()})
        if not files:
            if as_json:
                print_json({"files": [], "count": 0})
                return 0
            info("no uncommitted changes")
            return 0
        if as_json:
            print_json({"files": files, "count": len(files)})
            return 0
        info(f"changed files: ({len(files)})")
        for f in files:
            info(f"  {f['path']}  {f['changes']}")
        return 0

    # name-status mode (default and --staged)
    if not lines:
        if as_json:
            print_json({"files": [], "count": 0})
            return 0
        if staged:
            info("nothing staged")
        else:
            info("no uncommitted changes  (tip: --staged for staged files)")
        return 0

    files = []
    for line in lines:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            files.append({"status": parts[0].strip(), "path": parts[1].strip()})

    if as_json:
        print_json({"files": files, "count": len(files)})
        return 0

    info(f"changed files: ({len(files)})")
    for f in files:
        info(f"  {f['status']}  {f['path']}")
    return 0
