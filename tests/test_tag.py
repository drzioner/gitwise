"""Tests for gitwise tag command."""

import json

from conftest import run_gitwise


def test_tag_list_empty(tmp_git_repo):
    r = run_gitwise("tag", "list", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "No tags" in r.stdout or "No hay" in r.stdout


def test_tag_list_json(tmp_git_repo):
    r = run_gitwise("tag", "list", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 1
    assert data["count"] == 0


def test_tag_create_and_list(tmp_git_repo):
    r = run_gitwise("tag", "create", "v0.1.0", cwd=tmp_git_repo)
    assert r.returncode == 0
    r = run_gitwise("tag", "list", cwd=tmp_git_repo)
    assert "v0.1.0" in r.stdout


def test_tag_create_dry(tmp_git_repo):
    r = run_gitwise("tag", "create", "v0.1.0", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0
    r = run_gitwise("tag", "list", "--json", cwd=tmp_git_repo)
    assert json.loads(r.stdout)["count"] == 0


def test_tag_not_git(tmp_path):
    r = run_gitwise("tag", cwd=tmp_path)
    assert r.returncode == 1
