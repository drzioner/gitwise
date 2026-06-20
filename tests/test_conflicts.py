"""Tests for gitwise conflicts command."""

import json
import subprocess

from conftest import _git, run_gitwise


def test_conflicts_none(tmp_git_repo):
    r = run_gitwise("conflicts", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "No conflict" in r.stdout or "No hay" in r.stdout


def test_conflicts_json(tmp_git_repo):
    r = run_gitwise("conflicts", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["count"] == 0


def test_conflicts_not_git(tmp_path):
    r = run_gitwise("conflicts", cwd=tmp_path)
    assert r.returncode == 1


def test_conflicts_detect_markers(tmp_git_repo):
    _git(["checkout", "-b", "conflict-branch"], cwd=tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("branch content\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "change on branch"], cwd=tmp_git_repo)
    _git(["checkout", "main"], cwd=tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("main content\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "change on main"], cwd=tmp_git_repo)
    subprocess.run(
        ["git", "merge", "conflict-branch"],
        cwd=tmp_git_repo,
        capture_output=True,
    )

    r = run_gitwise("conflicts", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["count"] >= 1
