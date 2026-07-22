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


def test_context_json_limits_tree_and_reports_truncation(tmp_git_repo):
    for index in range(5):
        (tmp_git_repo / f"file-{index}.txt").write_text("x")

    r = run_gitwise("context", "--max-entries", "2", "--json", cwd=tmp_git_repo)

    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert len(data["tree"]) == 2
    assert data["tree_total"] >= 5
    assert data["tree_truncated"] is True


def test_context_json_rejects_non_positive_max_entries(tmp_git_repo):
    r = run_gitwise("context", "--max-entries", "0", "--json", cwd=tmp_git_repo)

    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["errors"][0]["code"] == "invalid_max_entries"


def test_context_json_default_limits_tree_to_one_hundred_entries(tmp_git_repo):
    for index in range(105):
        (tmp_git_repo / f"wide-file-{index:03d}.txt").write_text("x")

    r = run_gitwise("context", "--json", cwd=tmp_git_repo)

    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert len(data["tree"]) == 100
    assert data["tree_total"] >= 105
    assert data["tree_truncated"] is True


def test_context_not_git(tmp_path):
    r = run_gitwise("context", cwd=tmp_path)
    assert r.returncode == 1
