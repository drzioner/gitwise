"""gitwise status — enhanced git status for humans and AI agents."""

from pathlib import Path

from .git import current_branch, has_upstream, require_root
from .git import run as git_run
from .i18n import t
from .output import (
    info,
    ok,
    print_blank,
    print_bracket,
    print_commit_line,
    print_file_status,
    print_header,
    print_json,
    status,
)
from .utils.parsing import parse_two_ints


def _range_commits(root: Path, rev_range: str) -> list[dict[str, str]]:
    r = git_run(["log", "--format=%H%x09%h%x09%s", rev_range], cwd=root, check=False)
    if r.returncode != 0:
        return []
    commits: list[dict[str, str]] = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            commits.append({"hash": parts[0], "short_hash": parts[1], "subject": parts[2]})
    return commits


def run_status(*, as_json: bool = False) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    branch = current_branch(root) or t("detached_head")

    ahead = behind = 0
    ahead_commits: list[dict[str, str]] = []
    behind_commits: list[dict[str, str]] = []
    with status(t("status_reading_status")):
        status_r = git_run(["status", "--porcelain"], cwd=root, check=False)
        status_lines = status_r.stdout.splitlines() if status_r.returncode == 0 else []

        staged = [ln for ln in status_lines if ln and ln[0] not in (" ", "?")]
        unstaged = [ln for ln in status_lines if ln and ln[1] not in (" ", "?")]
        untracked = [ln for ln in status_lines if ln and ln.startswith("??")]

        upstream = has_upstream(root)
        if upstream:
            ab_r = git_run(
                ["rev-list", "--left-right", "--count", "HEAD...@{u}"],
                cwd=root,
                check=False,
            )
            if ab_r.returncode == 0:
                parsed = parse_two_ints(ab_r.stdout)
                if parsed is not None:
                    ahead, behind = parsed
            if ahead:
                ahead_commits = _range_commits(root, "@{u}..HEAD")
            if behind:
                behind_commits = _range_commits(root, "HEAD..@{u}")

    if as_json:
        print_json(
            {
                "v": 2,
                "ok": True,
                "branch": branch,
                "has_upstream": upstream,
                "ahead": ahead,
                "behind": behind,
                "ahead_commits": ahead_commits,
                "behind_commits": behind_commits,
                "staged": len(staged),
                "unstaged": len(unstaged),
                "untracked": len(untracked),
                "files": [ln[3:] for ln in status_lines],
            }
        )
        return 0

    print_header(t("branch_label", branch=branch))
    if ahead or behind:
        print_bracket(t("status_ahead_label"), str(ahead))
        for commit in ahead_commits:
            print_commit_line(f"{commit['short_hash']} {commit['subject']}", indent=4)
        print_bracket(t("status_behind_label"), str(behind))
        for commit in behind_commits:
            print_commit_line(f"{commit['short_hash']} {commit['subject']}", indent=4)

    if not status_lines:
        print_blank()
        ok(t("working_tree_clean"))
        return 0

    if staged:
        print_blank()
        print_header(f"{t('status_staged_label')} ({len(staged)}):")
        for line in staged:
            print_file_status(line[:2], line[3:])

    if unstaged:
        print_blank()
        print_header(f"{t('status_unstaged_label')} ({len(unstaged)}):")
        for line in unstaged:
            print_file_status(line[:2], line[3:])

    if untracked:
        print_blank()
        print_header(f"{t('status_untracked_label')} ({len(untracked)}):")
        for line in untracked[:10]:
            print_file_status("??", line[3:])
        if len(untracked) > 10:
            info(f"    {t('status_more_files', count=str(len(untracked) - 10))}")

    return 0
