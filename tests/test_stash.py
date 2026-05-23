"""Tests for gitwise stash command."""

import json

from conftest import run_gitwise


def test_stash_list_empty(tmp_git_repo):
    r = run_gitwise("stash", "list", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "No stashes" in r.stdout or "No hay" in r.stdout


def test_stash_list_json(tmp_git_repo):
    r = run_gitwise("stash", "list", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 2
    assert data["count"] == 0


def test_stash_show_missing(tmp_git_repo):
    r = run_gitwise("stash", "show", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert "hint" in data


def test_stash_clean_dry(tmp_git_repo):
    r = run_gitwise("stash", "clean", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_stash_not_git(tmp_path):
    r = run_gitwise("stash", cwd=tmp_path)
    assert r.returncode == 1


def test_stash_clear_alias(tmp_git_repo):
    r = run_gitwise("stash", "clear", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_stash_show_patch(tmp_git_repo):
    from conftest import _git

    (tmp_git_repo / "new.txt").write_text("stashme\n")
    _git(["add", "."], tmp_git_repo)
    _git(["stash"], tmp_git_repo)
    r = run_gitwise("stash", "show", "--patch", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "diff" in r.stdout or "stash@" in r.stdout
