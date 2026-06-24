"""Tests for gitwise show."""

from pathlib import Path

from conftest import run_gitwise


def test_show_head(tmp_git_repo: Path) -> None:
    r = run_gitwise("show", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore: initial commit" in r.stdout


def test_show_json(tmp_git_repo: Path) -> None:
    r = run_gitwise("show", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert '"hash"' in r.stdout


def test_show_stat(tmp_git_repo: Path) -> None:
    r = run_gitwise("show", "--stat", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_show_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("show", cwd=tmp_path)
    assert r.returncode == 1


def test_show_specific_ref(tmp_git_repo: Path) -> None:
    r = run_gitwise("show", "HEAD", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_show_invalid_ref(tmp_git_repo: Path) -> None:
    r = run_gitwise("show", "nonexistent123", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_show_git_failure_json_emits_envelope(tmp_git_repo: Path) -> None:
    """A git failure during JSON show must surface as an error envelope."""
    import json

    r = run_gitwise("show", "deadbeefnotacommit", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "git_show_failed"


def test_show_git_arg_denies_dangerous_option(tmp_git_repo):
    r = run_gitwise("show", "--git-arg=--output", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    import json

    assert json.loads(r.stdout)["errors"][0]["code"] == "git_arg_denied"
