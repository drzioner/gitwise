"""Tests for gitwise merge command."""

import json

from conftest import _git, run_gitwise


def test_merge_same_branch(tmp_git_repo):
    r = run_gitwise("merge", "main", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_merge_not_found(tmp_git_repo):
    r = run_gitwise("merge", "nonexistent", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_merge_dry_run(tmp_git_repo):
    _git(["checkout", "-b", "feature-test"], cwd=tmp_git_repo)
    _git(["checkout", "main"], cwd=tmp_git_repo)
    r = run_gitwise("merge", "feature-test", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["dry_run"] is True


def test_merge_not_git(tmp_path):
    r = run_gitwise("merge", "main", cwd=tmp_path)
    assert r.returncode == 1
