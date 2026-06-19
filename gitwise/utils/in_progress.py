"""Detect in-progress git operations (merge/rebase/cherry-pick/revert/bisect).

Reads the same `.git/` artifacts git itself writes when an operation is
paused on conflicts or steps. Resolves the real git-dir via
`git rev-parse --git-dir` so worktrees (which keep their state under
`.git/worktrees/<name>/`) are handled correctly.

Marker reference (Verified against git source: builtin/am.c, sequencer.c,
builtin/merge.c, git-rebase--merge.sh, gitglossary(7)):
- MERGE_HEAD          → merge paused on conflicts
- rebase-merge/       → interactive rebase in progress (also `rebase -m`)
- rebase-apply/       → am/rebase--am in progress
- CHERRY_PICK_HEAD    → cherry-pick paused on conflicts
- REVERT_HEAD         → revert paused on conflicts
- BISECT_LOG          → bisect session active
- sequencer/todo      → multi-step cherry-pick/revert queue
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, TypedDict

from ..git import run as git_run

InProgressState = Literal["none", "merge", "rebase", "cherry-pick", "revert", "bisect"]


class InProgressInfo(TypedDict):
    """Snapshot of any paused git operation in the working tree."""

    state: InProgressState
    ref: str | None


def _resolve_git_dir(root: Path) -> Path | None:
    """Return the real git-dir for `root`, or None if git itself is unavailable.

    Uses `git rev-parse --git-dir` so worktrees resolve to their per-worktree
    state directory rather than the shared common dir.
    """
    result = git_run(["rev-parse", "--git-dir"], cwd=root, check=False)
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    # Use os.path.realpath (not Path.resolve()) per AGENTS.md: Path.resolve()
    # can fail on broken symlinks, which matters inside .git/worktrees/.
    candidate = Path(raw)
    git_dir = Path(os.path.realpath(candidate if candidate.is_absolute() else root / raw))
    return git_dir if git_dir.is_dir() else None


def _read_head_ref(git_dir: Path, marker: str) -> str | None:
    """Return the SHA stored in `<git_dir>/<marker>`, or None if absent/empty."""
    marker_path = git_dir / marker
    if not marker_path.is_file():
        return None
    content = marker_path.read_text(encoding="utf-8", errors="replace").strip()
    return content or None


def detect_in_progress(root: Path) -> InProgressInfo:
    """Inspect `root` for any paused git operation.

    Returns `{"state": "none", "ref": None}` when the working tree is clean
    of in-progress operations. Priority order: merge > rebase > cherry-pick >
    revert > bisect — matches the order git itself applies when multiple
    state dirs co-exist (which is rare but possible if a user aborts one op
    into another).
    """
    git_dir = _resolve_git_dir(root)
    if git_dir is None:
        return InProgressInfo(state="none", ref=None)

    merge_ref = _read_head_ref(git_dir, "MERGE_HEAD")
    if merge_ref is not None:
        return InProgressInfo(state="merge", ref=merge_ref)

    if (git_dir / "rebase-merge").is_dir() or (git_dir / "rebase-apply").is_dir():
        rebase_ref = _read_head_ref(git_dir / "rebase-merge", "head-name")
        return InProgressInfo(state="rebase", ref=rebase_ref)

    cherry_ref = _read_head_ref(git_dir, "CHERRY_PICK_HEAD")
    if cherry_ref is not None:
        return InProgressInfo(state="cherry-pick", ref=cherry_ref)

    revert_ref = _read_head_ref(git_dir, "REVERT_HEAD")
    if revert_ref is not None:
        return InProgressInfo(state="revert", ref=revert_ref)

    if (git_dir / "BISECT_LOG").is_file():
        return InProgressInfo(state="bisect", ref=None)

    return InProgressInfo(state="none", ref=None)


_HINT_COMMANDS: dict[InProgressState, str] = {
    "none": "",
    "merge": "git merge --continue  # or  git merge --abort",
    "rebase": "git rebase --continue  # or  git rebase --abort",
    "cherry-pick": "git cherry-pick --continue  # or  git cherry-pick --abort",
    "revert": "git revert --continue  # or  git revert --abort",
    "bisect": "git bisect reset",
}


def in_progress_hint(state: InProgressState) -> str:
    """Return the canonical recovery command for a paused operation state."""
    return _HINT_COMMANDS.get(state, "")
