"""Tests for gitwise pick command."""

from conftest import run_gitwise


def test_pick_no_refs(tmp_git_repo):
    r = run_gitwise("pick", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_pick_not_git(tmp_path):
    r = run_gitwise("pick", "abc123", cwd=tmp_path)
    assert r.returncode == 1


def test_pick_dry_run(tmp_git_repo):
    r = run_gitwise("pick", "HEAD", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0
