"""Tests for gitwise clean --branches."""

import json
import subprocess
from pathlib import Path

import pytest
from gitwise.clean import run_clean
from gitwise.git import stale_branches


def test_dry_run_does_not_delete(
    monkeypatch: pytest.MonkeyPatch, tmp_git_repo_with_stale: Path
) -> None:
    monkeypatch.chdir(tmp_git_repo_with_stale)
    before = stale_branches(tmp_git_repo_with_stale)
    assert len(before) == 3

    rc = run_clean(branches=True, refs=False, dry_run=True, yes=True, as_json=False)
    assert rc == 0

    assert stale_branches(tmp_git_repo_with_stale) == before


def test_dry_run_lists_stale_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_git_repo_with_stale: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.chdir(tmp_git_repo_with_stale)
    run_clean(branches=True, refs=False, dry_run=True, yes=True, as_json=False)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    for i in range(1, 4):
        assert f"stale-{i}" in output


def test_apply_deletes_only_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_git_repo_with_stale: Path
) -> None:
    monkeypatch.chdir(tmp_git_repo_with_stale)
    assert len(stale_branches(tmp_git_repo_with_stale)) == 3

    rc = run_clean(branches=True, refs=False, dry_run=False, yes=True, as_json=False)
    assert rc == 0

    assert stale_branches(tmp_git_repo_with_stale) == []

    r = subprocess.run(
        ["git", "branch", "--list", "main"],
        cwd=tmp_git_repo_with_stale,
        capture_output=True,
        text=True,
    )
    assert "main" in r.stdout


def _build_stale_repo_with_branch(tmp_path: Path, branch_name: str) -> Path:
    """Helper: creates a repo with one stale branch of the given name."""
    from tests.conftest import _GIT_ENV

    remote = tmp_path / "remote.git"
    local = tmp_path / "local"

    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True
    )

    working = tmp_path / "working"
    subprocess.run(
        ["git", "clone", str(remote), str(working)], check=True, capture_output=True, env=_GIT_ENV
    )
    for cfg in [
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test User"],
    ]:
        subprocess.run(["git"] + cfg, cwd=working, check=True, capture_output=True, env=_GIT_ENV)

    (working / "README.md").write_text("main\n")
    subprocess.run(["git", "add", "."], cwd=working, check=True, capture_output=True, env=_GIT_ENV)
    subprocess.run(
        ["git", "commit", "--no-gpg-sign", "-m", "chore: init"],
        cwd=working,
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=working,
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )

    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=working,
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    (working / "branch.txt").write_text("work\n")
    subprocess.run(["git", "add", "."], cwd=working, check=True, capture_output=True, env=_GIT_ENV)
    subprocess.run(
        ["git", "commit", "--no-gpg-sign", "-m", "feat: branch"],
        cwd=working,
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    subprocess.run(
        ["git", "push", "origin", branch_name],
        cwd=working,
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )

    subprocess.run(
        ["git", "clone", str(remote), str(local)], check=True, capture_output=True, env=_GIT_ENV
    )
    for cfg in [
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test User"],
    ]:
        subprocess.run(["git"] + cfg, cwd=local, check=True, capture_output=True, env=_GIT_ENV)
    subprocess.run(
        ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
        cwd=local,
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    subprocess.run(
        ["git", "checkout", "main"], cwd=local, check=True, capture_output=True, env=_GIT_ENV
    )

    subprocess.run(
        ["git", "push", "origin", "--delete", branch_name],
        cwd=working,
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    subprocess.run(
        ["git", "fetch", "--prune"], cwd=local, check=True, capture_output=True, env=_GIT_ENV
    )

    return local


def test_protected_branch_not_deleted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A stale branch named 'develop' must not be deleted (default protected list)."""
    local = _build_stale_repo_with_branch(tmp_path, "develop")
    monkeypatch.chdir(local)

    assert "develop" in stale_branches(local)

    rc = run_clean(branches=True, refs=False, dry_run=False, yes=True, as_json=False)
    assert rc == 0

    r = subprocess.run(
        ["git", "branch", "--list", "develop"], cwd=local, capture_output=True, text=True
    )
    assert "develop" in r.stdout


def test_json_output_structure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_git_repo_with_stale: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """as_json=True outputs parseable JSON with deletable/skipped keys."""
    monkeypatch.chdir(tmp_git_repo_with_stale)

    rc = run_clean(branches=True, refs=False, dry_run=True, yes=True, as_json=True)
    assert rc == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "deletable" in data
    assert "skipped" in data
    assert len(data["deletable"]) == 3


def test_active_worktree_protected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_git_repo_with_stale: Path,
    tmp_path: Path,
) -> None:
    """A stale branch checked out in a worktree must not be deleted."""
    repo = tmp_git_repo_with_stale
    wt_path = tmp_path / "wt-stale-1"

    subprocess.run(
        ["git", "worktree", "add", str(wt_path), "stale-1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(repo)

    try:
        rc = run_clean(branches=True, refs=False, dry_run=False, yes=True, as_json=False)
        assert rc == 0

        r = subprocess.run(
            ["git", "branch", "--list", "stale-1"], cwd=repo, capture_output=True, text=True
        )
        assert "stale-1" in r.stdout

        for i in (2, 3):
            r2 = subprocess.run(
                ["git", "branch", "--list", f"stale-{i}"], cwd=repo, capture_output=True, text=True
            )
            assert f"stale-{i}" not in r2.stdout
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)], cwd=repo, capture_output=True
        )
