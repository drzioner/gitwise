"""Compact git status + log for Claude Code context reduction."""

import subprocess

from .git import is_repo, repo_root
from .git import run as git_run
from .output import HAS_DELTA, IS_TTY, bat_pipe, debug, error, info, ok, print_json, warn


def run_summarize(*, as_json: bool = False, diff: bool = False, max_commits: int = 10) -> int:
    if not is_repo():
        error("no es un repositorio git")
        return 1

    cwd = repo_root()
    if cwd is None:
        error("no se pudo determinar la raíz del repositorio")
        return 1

    branch_r = git_run(["branch", "--show-current"], cwd=cwd, check=False)
    branch = branch_r.stdout.strip() if branch_r.returncode == 0 else "detached-HEAD"

    status_r = git_run(["status", "--short"], cwd=cwd, check=False)
    status_lines = status_r.stdout.splitlines() if status_r.returncode == 0 else []

    log_r = git_run(
        ["--no-pager", "log", "--oneline", f"-n{max_commits}"],
        cwd=cwd,
        check=False,
    )
    log_lines = log_r.stdout.splitlines() if log_r.returncode == 0 else []

    shortstat_r = git_run(["--no-pager", "diff", "--shortstat"], cwd=cwd, check=False)
    shortstat = shortstat_r.stdout.strip() if shortstat_r.returncode == 0 else ""

    changed_r = git_run(["--no-pager", "diff", "--name-status", "HEAD"], cwd=cwd, check=False)
    changed_files = changed_r.stdout.splitlines() if changed_r.returncode == 0 else []

    if as_json:
        import json

        result = {
            "v": 1,
            "ok": True,
            "branch": branch,
            "status": status_lines,
            "log": log_lines,
            "shortstat": shortstat,
            "changed_files": changed_files,
        }
        print_json(result)
        output_size = len(json.dumps(result))
        if output_size > 8192:
            warn(f"output {output_size} bytes supera 8KB — usa --max-commits menor")
        return 0

    # Human output
    info(f"rama: {branch}")
    info("")

    if status_lines:
        info(f"estado ({len(status_lines)} archivos modificados):")
        bat_pipe("\n".join(status_lines), language="plain")
        info("")
    else:
        ok("working tree limpio")
        info("")

    if log_lines:
        info(f"últimos {len(log_lines)} commits:")
        bat_pipe("\n".join(log_lines), language="plain")
        info("")
    else:
        info("sin commits aún")
        info("")

    if shortstat:
        info(f"diff: {shortstat}")
        info("")

    if diff:
        diff_r = git_run(["--no-pager", "diff"], cwd=cwd, check=False)
        if diff_r.stdout:
            if HAS_DELTA and IS_TTY:
                debug("usando delta para mostrar diff")
                try:
                    delta = subprocess.Popen(["delta"], stdin=subprocess.PIPE, text=True)
                    delta.communicate(input=diff_r.stdout)
                except OSError:
                    bat_pipe(diff_r.stdout, language="diff")
            else:
                stat_r = git_run(["--no-pager", "diff", "--stat"], cwd=cwd, check=False)
                info(stat_r.stdout)

    return 0
