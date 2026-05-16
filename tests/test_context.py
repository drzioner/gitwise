"""Tests for gitwise context command."""

import json

from conftest import run_gitwise


def test_context_json(tmp_git_repo):
    r = run_gitwise("context", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 2
    assert isinstance(data["tree"], list)
    assert isinstance(data["contributors"], list)
    assert isinstance(data["file_types"], dict)
    assert "todo_fixme" in data
    assert "branches" in data


def test_context_human(tmp_git_repo):
    r = run_gitwise("context", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "Directory Tree" in r.stdout


def test_context_not_git(tmp_path):
    r = run_gitwise("context", cwd=tmp_path)
    assert r.returncode == 1
