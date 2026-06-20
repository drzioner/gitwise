"""Tests for gitwise branches."""

import json
from pathlib import Path

from conftest import run_gitwise


def test_branches_basic(tmp_git_repo: Path) -> None:
    r = run_gitwise("branches", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "main" in r.stdout


def test_branches_json(tmp_git_repo: Path) -> None:
    r = run_gitwise("branches", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert '"branches"' in r.stdout
    assert '"count"' in r.stdout


def test_branches_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("branches", cwd=tmp_path)
    assert r.returncode == 1


def test_branches_stale_none(tmp_git_repo: Path) -> None:
    r = run_gitwise("branches", "--stale", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "stale" in r.stdout.lower() or "no " in r.stdout.lower()


def test_branches_stale(tmp_git_repo_with_stale: Path) -> None:
    r = run_gitwise("branches", "--stale", cwd=tmp_git_repo_with_stale)
    assert r.returncode == 0
    assert "stale" in r.stdout.lower()


def test_branches_stale_json(tmp_git_repo_with_stale: Path) -> None:
    r = run_gitwise("branches", "--stale", "--json", cwd=tmp_git_repo_with_stale)
    assert r.returncode == 0
    assert '"stale_branches"' in r.stdout


def test_branches_remote(tmp_git_repo_with_stale: Path) -> None:
    r = run_gitwise("branches", "--remote", cwd=tmp_git_repo_with_stale)
    assert r.returncode == 0


def test_branches_json_has_age(tmp_git_repo: Path) -> None:
    r = run_gitwise("branches", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["data"]["count"] >= 1
    assert "age" in data["data"]["branches"][0]
