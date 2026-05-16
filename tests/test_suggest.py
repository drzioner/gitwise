"""Tests for gitwise suggest command."""

from conftest import run_gitwise


def test_suggest_no_staged(tmp_git_repo):
    r = run_gitwise("suggest", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_suggest_not_git(tmp_path):
    r = run_gitwise("suggest", cwd=tmp_path)
    assert r.returncode == 1


def test_suggest_json(tmp_git_repo):
    r = run_gitwise("suggest", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
