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
from .utils.in_progress import detect_in_progress
from .utils.json_envelope import ok_envelope
from .utils.parsing import parse_two_ints
from .utils.types import CONFLICT_CODES, FileEntry, build_file_entry


def _split_rename(raw_path: str) -> tuple[str, str | None]:
    """Split a porcelain rename entry ``old -> new`` into (new, old)."""
    if " -> " in raw_path:
        old, new = raw_path.split(" -> ", 1)
        return new, old
    return raw_path, None


def _range_commits(root: Path, rev_range: str) -> list[dict[str, str]]:
    """Return commit dicts (hash, short_hash, subject) for the given rev-range."""
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
    """Print a compact, agent-friendly view of the working-tree state.

    Exposes branch, ahead/behind counts and commit lists, staged/unstaged/
    untracked file counts, and an ``in_progress`` snapshot of any paused
    merge/rebase/cherry-pick/revert/bisect operation.
    """
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

        files: list[FileEntry] = []
        staged_n = unstaged_n = untracked_n = conflicted_n = 0
        for ln in status_lines:
            if not ln:
                continue
            code = ln[:2]
            raw_path = ln[3:]
            is_conflict = code in CONFLICT_CODES
            in_index = code[0] not in (" ", "?")
            in_wtree = code[1] not in (" ", "?")
            path, old_path = _split_rename(raw_path)
            files.append(build_file_entry(path, code, staged=in_index, old_path=old_path))
            if is_conflict:
                conflicted_n += 1
            else:
                staged_n += int(in_index)
                unstaged_n += int(in_wtree)
                untracked_n += int(code.startswith("??"))

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

        in_progress = detect_in_progress(root)

    if as_json:
        print_json(
            ok_envelope(
                "status",
                branch=branch,
                has_upstream=upstream,
                ahead=ahead,
                behind=behind,
                ahead_commits=ahead_commits,
                behind_commits=behind_commits,
                in_progress=in_progress,
                staged=staged_n,
                unstaged=unstaged_n,
                untracked=untracked_n,
                conflicted=conflicted_n,
                files=files,
            )
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

    staged_disp = [
        ln
        for ln in status_lines
        if ln and ln[0] not in (" ", "?") and ln[:2] not in CONFLICT_CODES
    ]
    unstaged_disp = [
        ln
        for ln in status_lines
        if ln and ln[1] not in (" ", "?") and ln[:2] not in CONFLICT_CODES
    ]
    untracked_disp = [ln for ln in status_lines if ln.startswith("??")]
    conflicted_disp = [ln for ln in status_lines if ln[:2] in CONFLICT_CODES]

    if conflicted_disp:
        print_blank()
        print_header(f"{t('status_conflicted_label')} ({len(conflicted_disp)}):")
        for line in conflicted_disp:
            print_file_status(line[:2], line[3:])

    if staged_disp:
        print_blank()
        print_header(f"{t('status_staged_label')} ({len(staged_disp)}):")
        for line in staged_disp:
            print_file_status(line[:2], line[3:])

    if unstaged_disp:
        print_blank()
        print_header(f"{t('status_unstaged_label')} ({len(unstaged_disp)}):")
        for line in unstaged_disp:
            print_file_status(line[:2], line[3:])

    if untracked_disp:
        print_blank()
        print_header(f"{t('status_untracked_label')} ({len(untracked_disp)}):")
        for line in untracked_disp[:10]:
            print_file_status("??", line[3:])
        if len(untracked_disp) > 10:
            info(f"    {t('status_more_files', count=str(len(untracked_disp) - 10))}")

    return 0
