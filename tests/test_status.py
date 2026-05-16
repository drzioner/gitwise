"""Tests for gitwise status command."""

import json

from conftest import run_gitwise


def test_status_clean(tmp_git_repo):
    r = run_gitwise("status", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "clean" in r.stdout.lower() or "limpio" in r.stdout.lower()


def test_status_json(tmp_git_repo):
    r = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 2
    assert data["ok"] is True
    assert "branch" in data
    assert "staged" in data
    assert "untracked" in data


def test_status_not_git(tmp_path):
    r = run_gitwise("status", cwd=tmp_path)
    assert r.returncode == 1
