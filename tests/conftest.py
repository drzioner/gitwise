"""pytest fixtures — synthetic git repos for testing."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))  # so test files can import from conftest

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}

PROJECT_ROOT = Path(__file__).parent.parent


def run_gitwise(
    *args: str, cwd: Path | None = None, env: dict | None = None
) -> subprocess.CompletedProcess:
    """Invoke gitwise as a subprocess. Shared by all test modules."""
    base_env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    if env:
        base_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "gitwise"] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd or PROJECT_ROOT,
        env=base_env,
    )


def _git(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        check=True,
        capture_output=True,
        env=env or _GIT_ENV,
    )


def _init_repo(path: Path) -> None:
    _git(["init", "-b", "main"], path, env={**_GIT_ENV})
    _git(["config", "user.email", "test@example.com"], path)
    _git(["config", "user.name", "Test User"], path)


def _initial_commit(path: Path) -> None:
    (path / "README.md").write_text("# Test\n")
    _git(["add", "."], path)
    # Test repos use --no-gpg-sign intentionally: GPG enforcement is for real repos
    _git(["commit", "--no-gpg-sign", "-m", "chore: initial commit"], path)


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Clean repo with one commit. No GPG (synthetic test fixtures)."""
    _init_repo(tmp_path)
    _initial_commit(tmp_path)
    return tmp_path


@pytest.fixture
def tmp_git_repo_with_commit_graph(tmp_git_repo: Path) -> Path:
    """Clean repo with commit-graph present (no missing_commit_graph finding)."""
    _git(["commit-graph", "write", "--reachable"], tmp_git_repo)
    return tmp_git_repo


@pytest.fixture
def tmp_git_repo_with_gpg_config(tmp_git_repo: Path) -> Path:
    """Repo with commit.gpgsign=true and user.signingkey set."""
    _git(["config", "commit.gpgsign", "true"], tmp_git_repo)
    _git(["config", "user.signingkey", "TESTKEY123ABC"], tmp_git_repo)
    return tmp_git_repo


@pytest.fixture
def tmp_git_repo_with_stale(tmp_path: Path) -> Path:
    """Repo with 3 [gone] branches (uses local remote to simulate push+delete)."""
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"

    # Bare remote
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True
    )

    # Working copy to push from
    working = tmp_path / "working"
    subprocess.run(["git", "clone", str(remote), str(working)], check=True, capture_output=True)
    _git(["config", "user.email", "test@example.com"], working)
    _git(["config", "user.name", "Test User"], working)
    (working / "README.md").write_text("main\n")
    _git(["add", "."], working)
    _git(["commit", "--no-gpg-sign", "-m", "chore: init"], working)
    _git(["push", "origin", "main"], working)

    # Create and push stale branches
    for i in range(1, 4):
        _git(["checkout", "-b", f"stale-{i}"], working)
        (working / f"stale-{i}.txt").write_text(f"work {i}\n")
        _git(["add", "."], working)
        _git(["commit", "--no-gpg-sign", "-m", f"feat: stale {i}"], working)
        _git(["push", "origin", f"stale-{i}"], working)
        _git(["checkout", "main"], working)

    # Clone locally and track stale branches
    subprocess.run(["git", "clone", str(remote), str(local)], check=True, capture_output=True)
    _git(["config", "user.email", "test@example.com"], local)
    _git(["config", "user.name", "Test User"], local)
    for i in range(1, 4):
        _git(["checkout", "-b", f"stale-{i}", f"origin/stale-{i}"], local)
        _git(["checkout", "main"], local)

    # Delete stale branches from remote
    for i in range(1, 4):
        _git(["push", "origin", "--delete", f"stale-{i}"], working)

    # Fetch --prune to mark as [gone]
    _git(["fetch", "--prune"], local)

    return local


@pytest.fixture
def tmp_git_repo_with_large_blob(tmp_git_repo: Path) -> Path:
    """Repo with a 2MB file in HEAD."""
    large = tmp_git_repo / "large-file.bin"
    large.write_bytes(b"x" * 2_000_000)
    _git(["add", "."], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: add large file"], tmp_git_repo)
    return tmp_git_repo
