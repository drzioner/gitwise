"""Tests for gitwise status command."""

import json

from gitwise import status as status_module

from conftest import run_gitwise


def test_status_clean(tmp_git_repo):
    r = run_gitwise("status", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "clean" in r.stdout.lower() or "limpio" in r.stdout.lower()


def test_status_json(tmp_git_repo):
    r = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 2
    assert data["ok"] is True
    assert "branch" in data
    assert "staged" in data
    assert "untracked" in data


def test_status_not_git(tmp_path):
    r = run_gitwise("status", cwd=tmp_path)
    assert r.returncode == 1


def test_status_invalid_ahead_behind_falls_back_to_zero(monkeypatch, tmp_git_repo):
    monkeypatch.setattr(status_module, "require_root", lambda: (tmp_git_repo, None))
    monkeypatch.setattr(status_module, "current_branch", lambda cwd: "main")
    monkeypatch.setattr(status_module, "has_upstream", lambda cwd: True)

    class Result:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    def fake_git_run(args, cwd, check=False):
        if args == ["status", "--porcelain"]:
            return Result(0, "")
        if args == ["rev-list", "--left-right", "--count", "HEAD...@{u}"]:
            return Result(0, "x y")
        return Result(1, "")

    monkeypatch.setattr(status_module, "git_run", fake_git_run)

    rc = status_module.run_status(as_json=True)
    assert rc == 0
