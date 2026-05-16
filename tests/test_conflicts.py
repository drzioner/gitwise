"""Tests for gitwise conflicts command."""

import json

from conftest import run_gitwise


def test_conflicts_none(tmp_git_repo):
    r = run_gitwise("conflicts", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "No conflict" in r.stdout or "No hay" in r.stdout


def test_conflicts_json(tmp_git_repo):
    r = run_gitwise("conflicts", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["count"] == 0


def test_conflicts_not_git(tmp_path):
    r = run_gitwise("conflicts", cwd=tmp_path)
    assert r.returncode == 1
