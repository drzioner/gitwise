"""Tests for gitwise undo."""

from pathlib import Path

from conftest import _git, run_gitwise


def test_undo_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("undo", cwd=tmp_path)
    assert r.returncode == 1


def test_undo_dry_run(tmp_git_repo: Path) -> None:
    _git(["commit", "--allow-empty", "--no-gpg-sign", "-m", "chore: second commit"], tmp_git_repo)
    r = run_gitwise("undo", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_undo_dry_run_json(tmp_git_repo: Path) -> None:
    _git(["commit", "--allow-empty", "--no-gpg-sign", "-m", "chore: second commit"], tmp_git_repo)
    r = run_gitwise("undo", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert '"dry_run"' in r.stdout


def test_undo_soft_dry_run(tmp_git_repo: Path) -> None:
    _git(["commit", "--allow-empty", "--no-gpg-sign", "-m", "chore: second commit"], tmp_git_repo)
    r = run_gitwise("undo", "--soft", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_undo_with_ref(tmp_git_repo: Path) -> None:
    r = _git(["rev-parse", "HEAD"], tmp_git_repo)
    head = r.stdout.strip()
    r2 = run_gitwise("undo", head, "--dry-run", cwd=tmp_git_repo)
    assert r2.returncode == 0
