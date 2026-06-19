"""Tests for gitwise commit."""

from pathlib import Path

from conftest import _git, run_gitwise


def test_commit_dry_run_invalid_format(tmp_git_repo: Path) -> None:
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


# -- secret-scan guard (D3) ---------------------------------------------------
# Sample secrets are assembled at runtime from fragments so the test source
# stays scanner-clean; otherwise the commit guard would flag this file.


def _aws_key() -> str:
    return "AK" + "IAIOSFODNN7EXAMPLE"


def test_commit_blocked_on_secret_high(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "config.py").write_text(f"aws_key = '{_aws_key()}'\n")
    _git(["add", "config.py"], tmp_git_repo)
    r = run_gitwise("commit", "-m", "feat: add config", cwd=tmp_git_repo)
    assert r.returncode == 1
    assert "secret" in r.stderr.lower() or "blocked" in r.stderr.lower()


def test_commit_blocked_on_secret_high_json(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "config.py").write_text(f"key = '{_aws_key()}'\n")
    _git(["add", "config.py"], tmp_git_repo)
    r = run_gitwise("commit", "-m", "feat: add config", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    import json

    data = json.loads(r.stdout)
    assert data["errors"][0]["code"] == "secret_leak_high"


def test_commit_allow_secret_json_proceeds(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "config.py").write_text(f"key = '{_aws_key()}'\n")
    _git(["add", "config.py"], tmp_git_repo)
    r = run_gitwise(
        "commit", "-m", "feat: add config", "--allow-secret", "--json", cwd=tmp_git_repo
    )
    assert r.returncode == 0
    # The commit was actually created despite the high-severity finding.
    log = _git(["--no-pager", "log", "--oneline"], tmp_git_repo).stdout.decode()
    assert "add config" in log


def test_commit_warns_on_secret_medium(tmp_git_repo: Path) -> None:
    body = "a" * 30
    (tmp_git_repo / "config.py").write_text(f'api_key = "{body}"\n')
    _git(["add", "config.py"], tmp_git_repo)
    r = run_gitwise("commit", "-m", "feat: add config", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "warning" in r.stderr.lower() or "secret" in r.stderr.lower()
