"""Compact git status + log for Claude Code context reduction."""

import subprocess

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import HAS_DELTA, IS_TTY, bat_pipe, debug, error, info, ok, print_json, warn


def run_summarize(*, as_json: bool = False, diff: bool = False, max_commits: int = 10) -> int:
    if not is_repo():
        error(t("not_a_git_repo"))
        return 1

    cwd = repo_root()
    if cwd is None:
        error(t("no_repo_root"))
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
            warn(t("output_superior_8kb", size=str(output_size)))
        return 0

    # Human output
    info(t("branch_label", branch=branch))
    info("")

    if status_lines:
        info(t("modified_files_status", count=str(len(status_lines))))
        print("\n".join(status_lines))
        info("")
    else:
        ok(t("working_tree_clean"))
        info("")

    if log_lines:
        info(t("last_commits", count=str(len(log_lines))))
        print("\n".join(log_lines))
        info("")
    else:
        info(t("no_commits_yet"))
        info("")

    if shortstat:
        info(t("diff_prefix", stat=shortstat))
        info("")

    if diff:
        diff_r = git_run(["--no-pager", "diff"], cwd=cwd, check=False)
        if diff_r.stdout:
            if HAS_DELTA and IS_TTY:
                debug(t("using_delta"))
                try:
                    delta = subprocess.Popen(["delta"], stdin=subprocess.PIPE, text=True)
                    delta.communicate(input=diff_r.stdout)
                except OSError:
                    bat_pipe(diff_r.stdout, language="diff")
            else:
                stat_r = git_run(["--no-pager", "diff", "--stat"], cwd=cwd, check=False)
                info(stat_r.stdout)

    return 0
