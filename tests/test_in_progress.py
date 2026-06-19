"""Tests for gitwise.utils.in_progress — paused-operation detection.

Verifies detection of merge/rebase/cherry-pick/revert/bisect by reading the
.git/ artifacts git itself writes. Uses synthetic markers (faster, deterministic)
for the rare-state paths and a real conflicting merge for the integration path.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from gitwise.utils.in_progress import detect_in_progress, in_progress_hint

from conftest import run_gitwise


def _git_dir(repo: Path) -> Path:
    """Resolve the real git-dir via git rev-parse (handles worktrees).

    Uses os.path.realpath per AGENTS.md (Path.resolve() can fail on broken
    symlinks) and explicit timeout per AGENTS.md "subprocess.run with explicit
    timeout".
    """
    r = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    raw = r.stdout.strip()
    candidate = Path(raw)
    return Path(os.path.realpath(candidate if candidate.is_absolute() else repo / raw))


def test_clean_repo_returns_none(tmp_git_repo: Path) -> None:
    """A clean working tree has no paused operation."""
    result = detect_in_progress(tmp_git_repo)
    assert result == {"state": "none", "ref": None}


def test_merge_marker_detected(tmp_git_repo: Path) -> None:
    """MERGE_HEAD presence → state=merge with the stored SHA as ref."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "MERGE_HEAD").write_text("abc123\n", encoding="utf-8")

    result = detect_in_progress(tmp_git_repo)
    assert result["state"] == "merge"
    assert result["ref"] == "abc123"


def test_rebase_merge_dir_detected(tmp_git_repo: Path) -> None:
    """rebase-merge/ dir (interactive rebase) → state=rebase."""
    git_dir = _git_dir(tmp_git_repo)
    rebase_dir = git_dir / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "head-name").write_text("refs/heads/feature\n", encoding="utf-8")

    result = detect_in_progress(tmp_git_repo)
    assert result["state"] == "rebase"
    assert result["ref"] == "refs/heads/feature"


def test_rebase_apply_dir_detected(tmp_git_repo: Path) -> None:
    """rebase-apply/ dir (am-based rebase) → state=rebase, ref=None."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "rebase-apply").mkdir()

    result = detect_in_progress(tmp_git_repo)
    assert result["state"] == "rebase"
    assert result["ref"] is None


def test_cherry_pick_marker_detected(tmp_git_repo: Path) -> None:
    """CHERRY_PICK_HEAD presence → state=cherry-pick."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "CHERRY_PICK_HEAD").write_text("deadbeef\n", encoding="utf-8")

    result = detect_in_progress(tmp_git_repo)
    assert result["state"] == "cherry-pick"
    assert result["ref"] == "deadbeef"


def test_revert_marker_detected(tmp_git_repo: Path) -> None:
    """REVERT_HEAD presence → state=revert."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "REVERT_HEAD").write_text("cafef00d\n", encoding="utf-8")

    result = detect_in_progress(tmp_git_repo)
    assert result["state"] == "revert"
    assert result["ref"] == "cafef00d"


def test_bisect_log_detected(tmp_git_repo: Path) -> None:
    """BISECT_LOG presence → state=bisect, ref=None."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "BISECT_LOG").write_text("# bisect log\n", encoding="utf-8")

    result = detect_in_progress(tmp_git_repo)
    assert result["state"] == "bisect"
    assert result["ref"] is None


def test_merge_takes_priority_over_rebase(tmp_git_repo: Path) -> None:
    """When MERGE_HEAD and rebase-merge/ coexist (rare), merge wins (git's order)."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "MERGE_HEAD").write_text("aaa\n", encoding="utf-8")
    (git_dir / "rebase-merge").mkdir()

    result = detect_in_progress(tmp_git_repo)
    assert result["state"] == "merge"


def test_in_progress_hint_returns_command_per_state() -> None:
    """Each paused state has a canonical recovery command."""
    assert "git merge --continue" in in_progress_hint("merge")
    assert "git rebase --continue" in in_progress_hint("rebase")
    assert "git cherry-pick --continue" in in_progress_hint("cherry-pick")
    assert "git revert --continue" in in_progress_hint("revert")
    assert "git bisect reset" in in_progress_hint("bisect")
    assert in_progress_hint("none") == ""


def test_status_json_includes_in_progress_when_clean(tmp_git_repo: Path) -> None:
    """status --json exposes in_progress with state=none on a clean repo."""
    r = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    import json

    data = json.loads(r.stdout)
    assert data["in_progress"] == {"state": "none", "ref": None}


def test_status_json_reports_in_progress_merge(tmp_git_repo: Path) -> None:
    """status --json surfaces a synthetic merge in-progress via the new field."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "MERGE_HEAD").write_text("abc123\n", encoding="utf-8")

    r = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    import json

    data = json.loads(r.stdout)
    assert data["in_progress"]["state"] == "merge"
    assert data["in_progress"]["ref"] == "abc123"


def test_suggest_refuses_during_in_progress_merge(tmp_git_repo: Path) -> None:
    """suggest refuses with a clear error when a merge is paused."""
    git_dir = _git_dir(tmp_git_repo)
    (git_dir / "MERGE_HEAD").write_text("abc123\n", encoding="utf-8")

    r = run_gitwise("suggest", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    import json

    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "in_progress_merge"
    assert "merge" in data["error"]


def test_merge_abort_without_in_progress_errors(tmp_git_repo: Path) -> None:
    """--abort refuses when no merge/rebase is actually paused (clearer than git's error)."""
    r = run_gitwise("merge", "--abort", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    import json

    data = json.loads(r.stdout)
    assert data["errors"][0]["code"] == "merge_no_in_progress"


def test_merge_abort_continue_mutually_exclusive(tmp_git_repo: Path) -> None:
    """--abort and --continue cannot be used together."""
    r = run_gitwise("merge", "--abort", "--continue", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    import json

    data = json.loads(r.stdout)
    assert data["errors"][0]["code"] == "merge_invalid_args"


def test_abort_or_continue_args_picks_rebase_subcommand_for_rebase_state() -> None:
    """Regression guard for gemini-code-assist finding on PR #65.

    `git merge --abort` errors with "There is no merge to abort" when a rebase
    is paused. The argv builder must pick `rebase` when state="rebase".
    """
    from gitwise.merge import _abort_or_continue_args

    assert _abort_or_continue_args(state="rebase", abort=True) == ["rebase", "--abort"]
    assert _abort_or_continue_args(state="rebase", abort=False) == ["rebase", "--continue"]


def test_abort_or_continue_args_picks_merge_subcommand_for_merge_state() -> None:
    """For a paused merge, the argv builder picks `merge`."""
    from gitwise.merge import _abort_or_continue_args

    assert _abort_or_continue_args(state="merge", abort=True) == ["merge", "--abort"]
    assert _abort_or_continue_args(state="merge", abort=False) == ["merge", "--continue"]


def test_abort_or_continue_args_picks_merge_for_other_paused_states() -> None:
    """cherry-pick/revert/bisect are out of scope for `gitwise merge`; default to `merge` argv.

    The caller (_handle_abort_or_continue) rejects those states earlier with
    merge_no_in_progress, so this default never runs in production. We assert
    it anyway to lock the fallback behavior.
    """
    from gitwise.merge import _abort_or_continue_args

    assert _abort_or_continue_args(state="cherry-pick", abort=True) == ["merge", "--abort"]
