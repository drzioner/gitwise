"""Tests for gitwise worktree command."""

import json
from pathlib import Path

from conftest import _git, run_gitwise


def test_worktree_new_creates_sibling_directory(tmp_git_repo: Path) -> None:
    result = run_gitwise("worktree", "new", "feature/test-branch", cwd=tmp_git_repo)
    assert result.returncode == 0
    expected = tmp_git_repo.parent / "feature-test-branch"
    assert expected.exists()
    assert expected.is_dir()


def test_worktree_new_json_output(tmp_git_repo: Path) -> None:
    result = run_gitwise("worktree", "new", "feature/json-test", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["v"] == 1
    assert data["ok"] is True
    assert "path" in data
    assert data["branch"] == "feature/json-test"


def test_worktree_new_existing_branch(tmp_git_repo: Path) -> None:
    _git(["checkout", "-b", "existing-branch"], tmp_git_repo)
    _git(["checkout", "main"], tmp_git_repo)
    result = run_gitwise("worktree", "new", "existing-branch", cwd=tmp_git_repo)
    assert result.returncode == 0


def test_worktree_new_directory_exists(tmp_git_repo: Path) -> None:
    target = tmp_git_repo.parent / "feature-conflict"
    target.mkdir()
    result = run_gitwise("worktree", "new", "feature/conflict", cwd=tmp_git_repo)
    assert result.returncode == 1
    assert "ya existe" in result.stderr


def test_worktree_new_sanitizes_dot_prefix(tmp_git_repo: Path) -> None:
    result = run_gitwise("worktree", "new", "feature/dot-branch", cwd=tmp_git_repo)
    assert result.returncode == 0
    expected = tmp_git_repo.parent / "feature-dot-branch"
    assert expected.exists()


def test_worktree_clean_no_orphans(tmp_git_repo: Path) -> None:
    result = run_gitwise("worktree", "clean", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "no hay worktrees" in result.stdout


def test_worktree_clean_dry_run(tmp_git_repo: Path) -> None:
    result = run_gitwise("worktree", "clean", "--dry-run", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "dry-run" in result.stdout or "no hay worktrees" in result.stdout


def test_worktree_clean_detects_orphaned(tmp_git_repo: Path) -> None:
    wt_path = tmp_git_repo.parent / "orphan-wt"
    _git(["worktree", "add", str(wt_path), "-b", "orphan-branch"], tmp_git_repo)
    assert wt_path.exists()
    import shutil

    shutil.rmtree(wt_path)
    assert not wt_path.exists()

    result = run_gitwise("worktree", "clean", cwd=tmp_git_repo)
    assert result.returncode == 0


def test_worktree_no_subcommand(tmp_git_repo: Path) -> None:
    result = run_gitwise("worktree", cwd=tmp_git_repo)
    assert result.returncode == 1


def test_worktree_new_no_branch(tmp_git_repo: Path) -> None:
    result = run_gitwise("worktree", "new", cwd=tmp_git_repo)
    assert result.returncode == 1
