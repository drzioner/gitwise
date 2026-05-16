"""Tests for gitwise commit."""

from pathlib import Path

from conftest import _git, run_gitwise


def test_commit_dry_run(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "file.txt").write_text("hello")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise("commit", "-m", "test message", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_commit_no_message(tmp_git_repo: Path) -> None:
    r = run_gitwise("commit", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_commit_conventional_type(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "file.txt").write_text("hello")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise("commit", "--type", "feat", "-m", "new feature", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_commit_with_scope(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "file.txt").write_text("hello")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise(
        "commit",
        "--type",
        "fix",
        "--scope",
        "core",
        "-m",
        "fix bug",
        "--dry-run",
        cwd=tmp_git_repo,
    )
    assert r.returncode == 0
    assert "fix(core): fix bug" in r.stdout


def test_commit_breaking(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "file.txt").write_text("hello")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise(
        "commit",
        "--type",
        "feat",
        "--breaking",
        "-m",
        "new api",
        "--dry-run",
        "--json",
        cwd=tmp_git_repo,
    )
    assert r.returncode == 0
    assert "feat!" in r.stdout


def test_commit_invalid_format(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "file.txt").write_text("hello")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise("commit", "-m", "bad message without type", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_commit_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("commit", "-m", "test", cwd=tmp_path)
    assert r.returncode == 1


def test_commit_amend(tmp_git_repo: Path) -> None:
    _git(["checkout", "-b", "feature-test"], tmp_git_repo)
    (tmp_git_repo / "file2.txt").write_text("change")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise(
        "commit", "--type", "fix", "-m", "amended", "--amend", "--dry-run", cwd=tmp_git_repo
    )
    assert r.returncode == 0


def test_commit_json_output(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "file.txt").write_text("hello")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise(
        "commit", "--type", "feat", "-m", "json test", "--dry-run", "--json", cwd=tmp_git_repo
    )
    assert r.returncode == 0
    assert '"message"' in r.stdout


def test_commit_no_duplicate_type(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "file.txt").write_text("hello")
    _git(["add", "."], tmp_git_repo)
    r = run_gitwise("commit", "-m", "feat: already typed", "--dry-run", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "feat: feat: already typed" not in r.stdout
