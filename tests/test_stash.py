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
    assert data["v"] == 3
    assert data["data"]["count"] == 0


def test_stash_show_missing(tmp_git_repo):
    r = run_gitwise("stash", "show", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert "errors" in data
    assert data["errors"][0]["code"] == "stash_not_found"
    assert "hint" in data["errors"][0]


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


def test_stash_drop_non_interactive_requires_yes(tmp_git_repo):
    from conftest import _git

    (tmp_git_repo / "drop-me.txt").write_text("drop me\n")
    _git(["add", "."], tmp_git_repo)
    _git(["stash"], tmp_git_repo)

    r = run_gitwise("stash", "drop", cwd=tmp_git_repo)
    assert r.returncode == 1

    listed = run_gitwise("stash", "list", "--json", cwd=tmp_git_repo)
    data = json.loads(listed.stdout)
    assert data["data"]["count"] == 1


def test_stash_drop_with_yes_non_interactive_succeeds(tmp_git_repo):
    from conftest import _git

    (tmp_git_repo / "drop-yes.txt").write_text("drop yes\n")
    _git(["add", "."], tmp_git_repo)
    _git(["stash"], tmp_git_repo)

    r = run_gitwise("stash", "drop", "--yes", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_stash_push_and_apply(tmp_git_repo):
    from conftest import _git

    (tmp_git_repo / "f.txt").write_text("change\n")
    _git(["add", "f.txt"], tmp_git_repo)
    r = run_gitwise("stash", "push", "-m", "wip", cwd=tmp_git_repo)
    assert r.returncode == 0
    # the newly-added file is stashed away (removed from the working tree)
    assert not (tmp_git_repo / "f.txt").exists()
    r2 = run_gitwise("stash", "list", "--json", cwd=tmp_git_repo)
    data = json.loads(r2.stdout)
    assert data["data"]["count"] >= 1
    r3 = run_gitwise("stash", "apply", "--json", cwd=tmp_git_repo)
    assert r3.returncode == 0
    assert (tmp_git_repo / "f.txt").read_text() == "change\n"
