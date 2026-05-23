"""Tests for gitwise log."""

import json
from pathlib import Path

from conftest import _git, _init_repo, run_gitwise


def test_log_basic(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore: initial commit" in r.stdout


def test_log_json(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert '"commits"' in r.stdout
    assert '"count"' in r.stdout


def test_log_json_has_stats(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert len(data["commits"]) >= 1
    commit = data["commits"][0]
    assert "hash" in commit
    assert "short_hash" in commit
    assert "author" in commit
    assert "date" in commit
    assert "subject" in commit
    assert "parents" in commit
    assert "stats" in commit


def test_log_json_root_commit_empty_parents(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("# Root\n")
    _git(["add", "."], tmp_path)
    _git(["commit", "--no-gpg-sign", "-m", "chore: root"], tmp_path)
    r = run_gitwise("log", "--json", cwd=tmp_path)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["count"] == 1
    assert data["commits"][0]["parents"] == ""


def test_log_oneline(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--oneline", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore: initial commit" in r.stdout


def test_log_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("log", cwd=tmp_path)
    assert r.returncode == 1


def test_log_empty_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    r = run_gitwise("log", cwd=tmp_path)
    assert r.returncode == 0


def test_log_json_empty_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    r = run_gitwise("log", "--json", cwd=tmp_path)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["commits"] == []


def test_log_author_filter(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--author=NonExistent", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_log_author_rejects_nested_quantifiers(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--author=(a+)+b", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_author_rejects_newline_injection(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--author=alice\nbob", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_grep_valid(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--grep=chore", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore" in r.stdout


def test_log_grep_rejects_nested_quantifiers(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--grep=(a+)+b", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_grep_rejects_invalid_regex(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--grep=[invalid", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_graph(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--graph", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_log_graph_oneline(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--graph", "--oneline", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "*" in r.stdout or "chore" in r.stdout
