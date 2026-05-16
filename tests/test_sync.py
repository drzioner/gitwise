"""Tests for gitwise sync."""

from pathlib import Path

from conftest import run_gitwise


def test_sync_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("sync", cwd=tmp_path)
    assert r.returncode == 1


def test_sync_dry_run(tmp_git_repo: Path) -> None:
    r = run_gitwise("sync", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "fetch" in r.stdout.lower() or "dry" in r.stdout.lower()


def test_sync_dry_run_json(tmp_git_repo: Path) -> None:
    r = run_gitwise("sync", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert '"dry_run"' in r.stdout


def test_sync_no_remote(tmp_git_repo: Path) -> None:
    r = run_gitwise("sync", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "main" in r.stdout
