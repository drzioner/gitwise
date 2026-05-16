"""Tests for gitwise health command."""

import json

from conftest import run_gitwise


def test_health_json(tmp_git_repo):
    r = run_gitwise("health", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 1
    assert 0 <= data["score"] <= 100
    assert data["grade"] in ("A", "B", "C", "D", "F")
    assert isinstance(data["breakdown"], dict)
    assert isinstance(data["details"], dict)


def test_health_human(tmp_git_repo):
    r = run_gitwise("health", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "Health:" in r.stdout
    assert "Grade:" in r.stdout


def test_health_not_git(tmp_path):
    r = run_gitwise("health", cwd=tmp_path)
    assert r.returncode == 1
