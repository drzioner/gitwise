"""Tests for gitwise pr."""

from pathlib import Path

from conftest import run_gitwise


def test_pr_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("pr", cwd=tmp_path)
    assert r.returncode == 1


def test_pr_list(tmp_git_repo: Path) -> None:
    r = run_gitwise("pr", "list", cwd=tmp_git_repo)
    assert r.returncode in (0, 1)
