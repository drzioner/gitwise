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
    assert r.returncode == 1
    data = json.loads(r.stdout)["data"]
    assert data["count"] >= 1


def _setup_text_conflict(tmp_git_repo):
    _git(["checkout", "-b", "union-branch"], cwd=tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("branch line\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "branch change"], cwd=tmp_git_repo)
    _git(["checkout", "main"], cwd=tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("main line\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "main change"], cwd=tmp_git_repo)
    subprocess.run(
        ["git", "merge", "union-branch"],
        cwd=tmp_git_repo,
        capture_output=True,
    )


def test_conflicts_union_resolves_and_keeps_both_sides(tmp_git_repo):
    _setup_text_conflict(tmp_git_repo)
    r = run_gitwise("conflicts", "--union", cwd=tmp_git_repo)
    assert r.returncode == 0
    merged = (tmp_git_repo / "README.md").read_text()
    assert "main line" in merged
    assert "branch line" in merged
    # union leaves no conflict markers
    assert "<<<<<<<" not in merged
    # result is staged
    staged = _git(["diff", "--cached", "--name-only"], cwd=tmp_git_repo)
    assert b"README.md" in staged.stdout


def test_conflicts_union_json_envelope(tmp_git_repo):
    _setup_text_conflict(tmp_git_repo)
    r = run_gitwise("conflicts", "--union", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    env = json.loads(r.stdout)
    assert env["v"] == 3
    assert env["command"] == "conflicts"
    assert env["data"]["strategy"] == "union"
    assert env["data"]["resolved"] >= 1


def test_conflicts_dry_run_does_not_touch_tree(tmp_git_repo):
    """--dry-run reports the plan but leaves conflict markers in place."""
    _setup_text_conflict(tmp_git_repo)
    r = run_gitwise("conflicts", "--ours", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    env = json.loads(r.stdout)
    assert env["data"]["dry_run"] is True
    assert env["data"]["strategy"] == "ours"
    assert env["data"]["count"] >= 1
    # The file still holds conflict markers (nothing was resolved).
    assert "<<<<<<<" in (tmp_git_repo / "README.md").read_text()


def test_conflicts_files_scopes_resolution(tmp_git_repo):
    """--files limits the dry-run plan to the requested subset."""
    _setup_text_conflict(tmp_git_repo)
    r = run_gitwise(
        "conflicts", "--ours", "--dry-run", "--files", "README.md", "--json", cwd=tmp_git_repo
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["dry_run"] is True
    assert data["strategy"] == "ours"
    assert "README.md" in data["would_resolve"]


def test_conflicts_files_none_match(tmp_git_repo):
    """--files with no matching conflicted path reports none cleanly."""
    _setup_text_conflict(tmp_git_repo)
    r = run_gitwise(
        "conflicts", "--ours", "--files", "does-not-exist.py", "--json", cwd=tmp_git_repo
    )
    assert r.returncode == 0
    assert json.loads(r.stdout)["data"]["count"] == 0
