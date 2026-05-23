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
    assert data["v"] == 2
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


def test_tag_bump_minor(tmp_git_repo):
    from conftest import _git

    _git(["tag", "v1.2.3"], tmp_git_repo)
    r = run_gitwise("tag", "create", "--bump", "minor", cwd=tmp_git_repo)
    assert r.returncode == 0
    r = run_gitwise("tag", "list", "--json", cwd=tmp_git_repo)
    data = json.loads(r.stdout)
    assert data["count"] == 2
    assert any(t["name"] == "v1.3.0" for t in data["tags"])


def test_tag_bump_major_json(tmp_git_repo):
    from conftest import _git

    _git(["tag", "v2.0.0"], tmp_git_repo)
    r = run_gitwise("tag", "create", "--bump", "major", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["created"].startswith("v3")


def test_tag_create_annotated(tmp_git_repo):
    r = run_gitwise("tag", "create", "v1.0.0", "-m", "Release 1.0", cwd=tmp_git_repo)
    assert r.returncode == 0
    r = run_gitwise("tag", "list", "--json", cwd=tmp_git_repo)
    data = json.loads(r.stdout)
    assert data["count"] == 1


def test_tag_delete_dry_run_non_interactive_succeeds_without_yes(tmp_git_repo):
    create = run_gitwise("tag", "create", "v0.1.0", cwd=tmp_git_repo)
    assert create.returncode == 0

    dry_run_delete = run_gitwise("tag", "delete", "v0.1.0", "--dry-run", cwd=tmp_git_repo)
    assert dry_run_delete.returncode == 0

    listed = run_gitwise("tag", "list", "--json", cwd=tmp_git_repo)
    data = json.loads(listed.stdout)
    assert any(tag["name"] == "v0.1.0" for tag in data["tags"])


def test_tag_delete_non_interactive_requires_yes(tmp_git_repo):
    create = run_gitwise("tag", "create", "v0.2.0", cwd=tmp_git_repo)
    assert create.returncode == 0

    delete = run_gitwise("tag", "delete", "v0.2.0", cwd=tmp_git_repo)
    assert delete.returncode == 1

    listed = run_gitwise("tag", "list", "--json", cwd=tmp_git_repo)
    data = json.loads(listed.stdout)
    assert any(tag["name"] == "v0.2.0" for tag in data["tags"])


def test_tag_delete_with_yes_non_interactive_succeeds(tmp_git_repo):
    create = run_gitwise("tag", "create", "v0.3.0", cwd=tmp_git_repo)
    assert create.returncode == 0

    delete = run_gitwise("tag", "delete", "v0.3.0", "--yes", cwd=tmp_git_repo)
    assert delete.returncode == 0

    listed = run_gitwise("tag", "list", "--json", cwd=tmp_git_repo)
    data = json.loads(listed.stdout)
    assert all(tag["name"] != "v0.3.0" for tag in data["tags"])
