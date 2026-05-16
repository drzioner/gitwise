"""Tests for gitwise log."""

from pathlib import Path

from conftest import _init_repo, run_gitwise


def test_log_basic(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore: initial commit" in r.stdout


def test_log_json(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert '"commits"' in r.stdout
    assert '"count"' in r.stdout


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
    assert '"commits": []' in r.stdout


def test_log_author_filter(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--author=NonExistent", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_log_graph(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--graph", cwd=tmp_git_repo)
    assert r.returncode == 0
