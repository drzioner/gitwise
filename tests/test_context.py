"""Tests for gitwise context command."""

import json

from conftest import run_gitwise


def test_context_json(tmp_git_repo):
    r = run_gitwise("context", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 3
    inner = data["data"]
    assert isinstance(inner["tree"], list)
    assert isinstance(inner["contributors"], list)
    assert isinstance(inner["file_types"], dict)
    assert "todo_fixme" in inner
    assert "branches" in inner


def test_context_human(tmp_git_repo):
    r = run_gitwise("context", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "Directory Tree" in r.stdout


def test_context_not_git(tmp_path):
    r = run_gitwise("context", cwd=tmp_path)
    assert r.returncode == 1
