"""Compact git status + log for Claude Code context reduction."""

import subprocess

from gitwise.utils.json_envelope import ok_envelope

from ._runtime_config import get_runtime_config
from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import (
    bat_pipe,
    debug,
    ok,
    print_blank,
    print_bullet,
    print_commit_line,
    print_file_status,
    print_header,
    print_json,
    status,
    warn,
)

_MAX_STATUS_LINES = 12


def _status_code(index: str, worktree: str) -> str:
    """Derive a two-char status code from index and worktree columns."""
    if index == "?" and worktree == "?":
        return "??"
    if worktree not in {" ", "?"}:
        return worktree
    if index not in {" ", "?"}:
        return index
    return "--"


def _parse_status_entries(status_lines: list[str]) -> list[dict[str, str]]:
    """Parse ``git status --short`` lines into structured dicts."""
    entries: list[dict[str, str]] = []
    for line in status_lines:
        if len(line) < 4:
            continue
        index = line[0]
        worktree = line[1]
        path_part = line[3:].strip()
        if not path_part:
            continue
        entry: dict[str, str] = {
            "index": index,
            "worktree": worktree,
            "status": _status_code(index, worktree),
        }
        if " -> " in path_part:
            old_path, new_path = path_part.split(" -> ", 1)
            entry["old_path"] = old_path
            entry["path"] = new_path
        else:
            entry["path"] = path_part
        entries.append(entry)
    return entries


def _parse_log_entries(log_lines: list[str]) -> list[dict[str, str]]:
    """Parse ``git log --oneline`` lines into ``{short_hash, subject}`` dicts."""
    entries: list[dict[str, str]] = []
    for line in log_lines:
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        entries.append({"short_hash": parts[0], "subject": parts[1]})
    return entries


def _parse_changed_entries(changed_files: list[str]) -> list[dict[str, str]]:
    """Parse ``git diff --name-status`` lines into structured dicts."""
    entries: list[dict[str, str]] = []
    for line in changed_files:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        code = status[:1].upper() if status else ""
        entry: dict[str, str] = {"status": status}
        if code and code != status:
            entry["code"] = code
        if code in {"R", "C"} and len(parts) >= 3:
            entry["old_path"] = parts[1].strip()
            entry["path"] = parts[2].strip()
        else:
            entry["path"] = parts[-1].strip()
        if len(status) > 1 and status[1:].isdigit():
            entry["score"] = status[1:]
        if entry["path"]:
            entries.append(entry)
    return entries


def run_summarize(*, as_json: bool = False, diff: bool = False, max_commits: int = 10) -> int:
    """Entry point for the ``gitwise summarize`` command."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1
    cwd = root

    with status(t("status_summarizing")):
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

    status_entries = _parse_status_entries(status_lines)
    status_map = {entry["path"]: entry["status"] for entry in status_entries}
    log_entries = _parse_log_entries(log_lines)
    log_map = {entry["short_hash"]: entry["subject"] for entry in log_entries}
    changed_entries = _parse_changed_entries(changed_files)

    if as_json:
        import json

        summarize_data: dict[str, object] = {
            "branch": branch,
            "status": status_map,
            "status_count": len(status_entries),
            "log": log_map,
            "log_count": len(log_entries),
            "shortstat": shortstat,
            "changed_files": changed_entries,
            "changed_count": len(changed_entries),
        }
        if diff:
            diff_r = git_run(["--no-pager", "diff"], cwd=cwd, check=False)
            summarize_data["diff"] = diff_r.stdout if diff_r.returncode == 0 else ""
        result = ok_envelope("summarize", data=summarize_data)
        print_json(result)
        output_size = len(json.dumps(result))
        if output_size > 8192:
            warn(t("output_exceeds_8kb", size=str(output_size)))
        return 0

    print_header(t("branch_label", branch=branch))
    print_blank()

    if status_lines:
        print_header(t("modified_files_status", count=str(len(status_lines))))
        for line in status_lines[:_MAX_STATUS_LINES]:
            print_file_status(line[:2], line[3:])
        if len(status_lines) > _MAX_STATUS_LINES:
            print_bullet(
                t("status_more_files", count=str(len(status_lines) - _MAX_STATUS_LINES)),
                icon="+",
                accent=False,
            )
        print_blank()
    else:
        ok(t("working_tree_clean"))
        print_blank()

    if log_lines:
        print_header(t("last_commits", count=str(len(log_lines))))
        for line in log_lines:
            print_commit_line(line)
        print_blank()
    else:
        print_bullet(t("no_commits_yet"), icon="-", accent=False)
        print_blank()

    if shortstat:
        print_header(t("diff_prefix", stat=shortstat))

    if diff:
        diff_r = git_run(["--no-pager", "diff"], cwd=cwd, check=False)
        if diff_r.stdout:
            cfg = get_runtime_config()
            if cfg.has_delta and cfg.is_tty:
                debug(t("using_delta"))
                try:
                    subprocess.run(
                        ["delta"],
                        input=diff_r.stdout,
                        text=True,
                        timeout=120,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    bat_pipe(diff_r.stdout, language="diff")
                except (FileNotFoundError, OSError):
                    bat_pipe(diff_r.stdout, language="diff")
            else:
                stat_r = git_run(["--no-pager", "diff", "--stat"], cwd=cwd, check=False)
                bat_pipe(stat_r.stdout, language="diff")

    return 0
