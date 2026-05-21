"""Tests for gitwise suggest command."""

import json

from conftest import _git, run_gitwise


def test_suggest_no_staged(tmp_git_repo):
    r = run_gitwise("suggest", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_suggest_not_git(tmp_path):
    r = run_gitwise("suggest", cwd=tmp_path)
    assert r.returncode == 1


def test_suggest_json(tmp_git_repo):
    r = run_gitwise("suggest", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert "error" in data


def test_suggest_json_pretty(tmp_git_repo):
    r = run_gitwise("suggest", "--json-pretty", cwd=tmp_git_repo)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert "error" in data


def test_suggest_with_staged(tmp_git_repo):
    (tmp_git_repo / "new_feature.py").write_text("print('hello')\n")
    _git(["add", "new_feature.py"], cwd=tmp_git_repo)
    r = run_gitwise("suggest", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_suggest_with_staged_json(tmp_git_repo):
    (tmp_git_repo / "fix_bug.py").write_text("pass\n")
    _git(["add", "fix_bug.py"], cwd=tmp_git_repo)
    r = run_gitwise("suggest", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert "message" in data


def test_suggest_with_staged_json_pretty(tmp_git_repo):
    (tmp_git_repo / "fix_bug_pretty.py").write_text("pass\n")
    _git(["add", "fix_bug_pretty.py"], cwd=tmp_git_repo)
    r = run_gitwise("suggest", "--json-pretty", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert "message" in data
