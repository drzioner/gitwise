"""Compact git status + log for Claude Code context reduction."""

import subprocess

from ._runtime_config import get_runtime_config
from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import (
    bat_pipe,
    debug,
    info,
    ok,
    print_header,
    print_json,
    print_section,
    warn,
)


def run_summarize(*, as_json: bool = False, diff: bool = False, max_commits: int = 10) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None
    cwd = root

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
            "v": 2,
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
            warn(t("output_exceeds_8kb", size=str(output_size)))
        return 0

    print_header(t("branch_label", branch=branch))

    if status_lines:
        print_section(t("modified_files_status", count=str(len(status_lines))))
        for line in status_lines:
            info(line)
    else:
        ok(t("working_tree_clean"))

    if log_lines:
        print_section(t("last_commits", count=str(len(log_lines))))
        for line in log_lines:
            info(line)
    else:
        info(t("no_commits_yet"))

    if shortstat:
        print_section(t("diff_prefix", stat=shortstat))

    if diff:
        diff_r = git_run(["--no-pager", "diff"], cwd=cwd, check=False)
        if diff_r.stdout:
            cfg = get_runtime_config()
            if cfg.has_delta and cfg.is_tty:
                debug(t("using_delta"))
                try:
                    delta = subprocess.Popen(["delta"], stdin=subprocess.PIPE, text=True)
                    delta.communicate(input=diff_r.stdout, timeout=120)
                except OSError:
                    bat_pipe(diff_r.stdout, language="diff")
            else:
                stat_r = git_run(["--no-pager", "diff", "--stat"], cwd=cwd, check=False)
                bat_pipe(stat_r.stdout, language="diff")

    return 0
