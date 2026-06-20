"""Tests for gitwise sync."""

import json
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


def test_sync_push_protected_json_includes_hint(tmp_git_repo: Path) -> None:
    r = run_gitwise("sync", "--push", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert "errors" in data
    assert data["errors"][0]["code"] == "sync_push_protected"
    assert "hint" in data["errors"][0]


def test_sync_no_remote(tmp_git_repo: Path) -> None:
    r = run_gitwise("sync", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "main" in r.stdout


def test_sync_pull_diverged_json_hint(tmp_path: Path) -> None:
    """Regression for Issue #43: divergence returns actionable hint + suggested_commands."""
    import subprocess as sp

    bare = tmp_path / "remote.git"
    work = tmp_path / "work"
    sp.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    sp.run(["git", "clone", "-q", str(bare), str(work)], check=True)
    env = {
        **__import__("os").environ,
        "GIT_AUTHOR_NAME": "T",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "T",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    sp.run(["git", "checkout", "-q", "-b", "main"], cwd=work, env=env, check=True)
    (work / "a.txt").write_text("a")
    sp.run(["git", "add", "a.txt"], cwd=work, env=env, check=True)
    sp.run(["git", "commit", "-q", "--no-gpg-sign", "-m", "a"], cwd=work, env=env, check=True)
    sp.run(["git", "push", "-q", "-u", "origin", "main"], cwd=work, env=env, check=True)
    (work / "b.txt").write_text("b")
    sp.run(["git", "add", "b.txt"], cwd=work, env=env, check=True)
    sp.run(["git", "commit", "-q", "--no-gpg-sign", "-m", "b"], cwd=work, env=env, check=True)
    sp.run(["git", "push", "-q"], cwd=work, env=env, check=True)
    sp.run(["git", "reset", "-q", "--hard", "HEAD~1"], cwd=work, env=env, check=True)
    (work / "c.txt").write_text("c")
    sp.run(["git", "add", "c.txt"], cwd=work, env=env, check=True)
    sp.run(["git", "commit", "-q", "--no-gpg-sign", "-m", "c"], cwd=work, env=env, check=True)

    r = run_gitwise("sync", "--pull", "--json", cwd=work)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["ok"] is False
    err = data["errors"][0]
    assert err["code"] == "sync_pull_diverged"
    assert "rebase" in err["hint"].lower()
    assert "git pull --rebase" in data["data"]["suggested_commands"]
    assert "gitwise sync --dry-run --json" in data["data"]["suggested_commands"]
