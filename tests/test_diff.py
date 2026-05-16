"""Tests for gitwise diff command."""

import json
from pathlib import Path

from conftest import _git, _init_repo
from conftest import run_gitwise as _run


def _write_and_stage(repo: Path, filename: str, content: str = "change\n") -> None:
    (repo / filename).write_text(content)
    _git(["add", filename], repo)


# ── Empty repo (no commits) ──────────────────────────────────────────────────


def test_diff_no_commits(tmp_path):
    _init_repo(tmp_path)
    result = _run("diff", cwd=tmp_path)
    assert result.returncode == 0
    assert "no commits yet" in result.stdout


def test_diff_no_commits_json(tmp_path):
    _init_repo(tmp_path)
    result = _run("diff", "--json", cwd=tmp_path)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["files"] == []
    assert data["count"] == 0
    assert "note" in data


# ── Clean repo ───────────────────────────────────────────────────────────────


def test_diff_no_changes(tmp_git_repo):
    result = _run("diff", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "no uncommitted changes" in result.stdout


def test_diff_no_changes_json(tmp_git_repo):
    result = _run("diff", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["files"] == []
    assert data["count"] == 0


# ── Unstaged changes ─────────────────────────────────────────────────────────


def test_diff_unstaged_shows_file(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("modified\n")
    result = _run("diff", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout


def test_diff_unstaged_json(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("modified\n")
    result = _run("diff", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] >= 1
    assert any("README.md" in f.get("path", "") for f in data["files"])


# ── Staged changes ───────────────────────────────────────────────────────────


def test_diff_staged_shows_file(tmp_git_repo):
    _write_and_stage(tmp_git_repo, "newfile.txt")
    result = _run("diff", "--staged", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "changed files:" in result.stdout
    assert "newfile.txt" in result.stdout


def test_diff_staged_empty(tmp_git_repo):
    result = _run("diff", "--staged", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "nothing staged" in result.stdout


def test_diff_staged_json(tmp_git_repo):
    _write_and_stage(tmp_git_repo, "newfile.txt")
    result = _run("diff", "--staged", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] == 1
    assert any(f["path"] == "newfile.txt" for f in data["files"])


# ── --stat mode ──────────────────────────────────────────────────────────────


def test_diff_stat_shows_changes_column(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("line1\nline2\nline3\n")
    result = _run("diff", "--stat", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "changed files:" in result.stdout
    assert "README.md" in result.stdout


def test_diff_stat_json(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("line1\nline2\n")
    result = _run("diff", "--stat", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] >= 1
    assert all("path" in f and "changes" in f for f in data["files"])


# ── Mutual exclusion ─────────────────────────────────────────────────────────


def test_diff_name_only_exclusive(tmp_git_repo):
    result = _run("diff", "--name-only", cwd=tmp_git_repo)
    assert result.returncode == 0


def test_diff_full(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("changed content\n")
    _git(["add", "."], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: modify readme"], tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("more changes\n")
    result = _run("diff", "--full", cwd=tmp_git_repo)
    assert result.returncode == 0


def test_diff_full_json(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("changed content\n")
    _git(["add", "."], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: modify readme"], tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("more changes\n")
    result = _run("diff", "--full", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert '"diff"' in result.stdout


def test_diff_patch_alias(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("changed content\n")
    _git(["add", "."], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: modify readme"], tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("more changes\n")
    result = _run("diff", "--patch", cwd=tmp_git_repo)
    assert result.returncode == 0
