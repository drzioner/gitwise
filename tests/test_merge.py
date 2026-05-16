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


def test_merge_feature_branch(tmp_git_repo):
    _git(["checkout", "-b", "feature-x"], cwd=tmp_git_repo)
    (tmp_git_repo / "feature.txt").write_text("x\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: add feature"], cwd=tmp_git_repo)
    _git(["checkout", "main"], cwd=tmp_git_repo)
    r = run_gitwise("merge", "feature-x", "--yes", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert (tmp_git_repo / "feature.txt").exists()


def test_merge_feature_json(tmp_git_repo):
    _git(["checkout", "-b", "feature-y"], cwd=tmp_git_repo)
    (tmp_git_repo / "y.txt").write_text("y\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: add y"], cwd=tmp_git_repo)
    _git(["checkout", "main"], cwd=tmp_git_repo)
    r = run_gitwise("merge", "feature-y", "--yes", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["merged"] == "feature-y"
