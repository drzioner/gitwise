"""Focused changed-file list for AI agents and humans."""

from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import HAS_DELTA, bat_pipe, error, info, print_json


def _has_commits(cwd: Path) -> bool:
    return git_run(["rev-parse", "HEAD"], cwd=cwd, check=False).returncode == 0


def run_diff(
    *,
    staged: bool = False,
    stat: bool = False,
    full: bool = False,
    as_json: bool = False,
) -> int:
    if not is_repo():
        error(t("not_a_git_repo"))
        return 1

    cwd = repo_root()
    if cwd is None:
        error(t("no_repo_root"))
        return 1

    if not staged and not _has_commits(cwd):
        if as_json:
            print_json({"files": [], "count": 0, "note": t("no_commits_yet")})
            return 0
        info(t("no_commits_yet"))
        return 0

    if full:
        r = git_run(["--no-pager", "diff", "HEAD"], cwd=cwd, check=False)
        if r.returncode != 0:
            error(t("git_diff_failed", error=r.stderr.strip()))
            return 1
        if as_json:
            print_json({"diff": r.stdout, "ok": True})
        else:
            if HAS_DELTA:
                info(t("using_delta"))
            bat_pipe(r.stdout, language="diff")
        return 0

    if stat:
        r = git_run(["--no-pager", "diff", "--stat", "HEAD"], cwd=cwd, check=False)
    elif staged:
        r = git_run(["--no-pager", "diff", "--name-status", "--staged"], cwd=cwd, check=False)
    else:
        r = git_run(["--no-pager", "diff", "--name-status", "HEAD"], cwd=cwd, check=False)

    if r.returncode != 0:
        error(t("git_diff_failed", error=r.stderr.strip()))
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
            info(t("no_uncommitted_changes"))
            return 0
        if as_json:
            print_json({"files": files, "count": len(files)})
            return 0
        info(t("changed_files", count=str(len(files))))
        for f in files:
            info(f"  {f['path']}  {f['changes']}")
        return 0

    if not lines:
        if as_json:
            print_json({"files": [], "count": 0})
            return 0
        if staged:
            info(t("nothing_staged"))
        else:
            info(t("tip_staged"))
        return 0

    files = []
    for line in lines:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            files.append({"status": parts[0].strip(), "path": parts[1].strip()})

    if as_json:
        print_json({"files": files, "count": len(files)})
        return 0

    info(t("changed_files", count=str(len(files))))
    for f in files:
        info(f"  {f['status']}  {f['path']}")
    return 0
