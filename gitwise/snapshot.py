"""Generates git snapshot file for session context."""

from datetime import datetime, timezone
from pathlib import Path

from gitwise.git import require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import debug, print_header, print_json, status
from gitwise.utils.json_envelope import ok_envelope


def _append_branch_section(lines: list[str], *, root: Path) -> None:
    """Append the current branch section to *lines*."""
    branch = git_run(["branch", "--show-current"], cwd=root, check=False)
    if branch.returncode != 0:
        return
    lines += [
        t("section_current_branch"),
        "```",
        branch.stdout.strip() or "(detached HEAD)",
        "```",
        "",
    ]


def _append_status_section(lines: list[str], *, root: Path) -> None:
    """Append the working-tree status section to *lines*."""
    status = git_run(["status", "--short"], cwd=root, check=False)
    if status.returncode != 0:
        return
    lines += [
        t("section_status"),
        "```",
        status.stdout.strip() or t("status_clean"),
        "```",
        "",
    ]


def _append_log_section(lines: list[str], *, root: Path) -> None:
    """Append the last 10 commits section to *lines*."""
    log = git_run(["--no-pager", "log", "--oneline", "-n", "10"], cwd=root, check=False)
    if log.returncode == 0 and log.stdout.strip():
        lines += [t("section_last_commits"), "```", log.stdout.strip(), "```", ""]


def _append_stash_section(lines: list[str], *, root: Path) -> None:
    """Append a stash count line to *lines* if stashes exist."""
    stash = git_run(["stash", "list"], cwd=root, check=False)
    if stash.returncode != 0 or not stash.stdout.strip():
        return
    stash_count = len(stash.stdout.strip().splitlines())
    lines += [t("stashes_section", count=str(stash_count)), ""]


def _append_worktrees_section(lines: list[str], *, root: Path) -> None:
    """Append a worktree count line to *lines* if more than one worktree exists."""
    worktrees = git_run(["worktree", "list", "--porcelain"], cwd=root, check=False)
    if worktrees.returncode != 0:
        return
    wt_count = worktrees.stdout.count("worktree ")
    if wt_count > 1:
        lines += [t("worktrees_active", count=str(wt_count)), ""]


def generate_snapshot(
    root: Path,
    *,
    frozen_time: bool = False,
    relative_path: str = ".claude/git-snapshot.md",
) -> Path:
    """Write snapshot markdown in repo root. Updates generated_at on every call."""
    snapshot_path = root / Path(relative_path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    if frozen_time:
        generated_at = "1970-01-01T00:00:00Z"
    else:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = ["# Git Snapshot", "", f"generated_at: {generated_at}", ""]

    _append_branch_section(lines, root=root)
    _append_status_section(lines, root=root)
    _append_log_section(lines, root=root)
    _append_stash_section(lines, root=root)
    _append_worktrees_section(lines, root=root)

    tmp = snapshot_path.with_suffix(".tmp")
    try:
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(snapshot_path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    debug(t("debug_snapshot_written", path=str(snapshot_path)))
    return snapshot_path


def run_snapshot(*, as_json: bool = False) -> int:
    """Entry point for the ``gitwise snapshot`` command."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    with status(t("status_snapshot_gen")):
        path = generate_snapshot(root)

    if as_json:
        print_json(ok_envelope("snapshot", path=str(path)))
        return 0

    print_header(t("snapshot_generated", path=str(path.relative_to(root))))
    return 0
