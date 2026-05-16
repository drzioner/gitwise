"""Tests for gitwise pick command."""

import json

from conftest import _git, run_gitwise


def test_pick_no_refs(tmp_git_repo):
    r = run_gitwise("pick", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_pick_not_git(tmp_path):
    r = run_gitwise("pick", "abc123", cwd=tmp_path)
    assert r.returncode == 1


def test_pick_dry_run(tmp_git_repo):
    r = run_gitwise("pick", "HEAD", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_pick_cherry_pick(tmp_git_repo):
    _git(["checkout", "-b", "source"], cwd=tmp_git_repo)
    (tmp_git_repo / "picked.txt").write_text("cherry\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: add picked"], cwd=tmp_git_repo)
    sha = _git(["rev-parse", "HEAD"], cwd=tmp_git_repo).stdout.strip()
    _git(["checkout", "main"], cwd=tmp_git_repo)
    r = run_gitwise("pick", sha, cwd=tmp_git_repo)
    assert r.returncode == 0
    assert (tmp_git_repo / "picked.txt").exists()


def test_pick_dry_run_json(tmp_git_repo):
    r = run_gitwise("pick", "HEAD", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["dry_run"] is True


def test_cherry_pick_alias(tmp_git_repo):
    r = run_gitwise("cherry-pick", "HEAD", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0
