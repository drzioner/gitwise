"""Tests for gitwise status command."""

import json
import subprocess

from gitwise import status as status_module

from conftest import _git, run_gitwise


def test_status_clean(tmp_git_repo):
    r = run_gitwise("status", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "clean" in r.stdout.lower() or "limpio" in r.stdout.lower()


def test_status_json(tmp_git_repo):
    r = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    env = json.loads(r.stdout)
    assert env["v"] == 3
    assert env["ok"] is True
    assert env["command"] == "status"
    assert isinstance(env["data"], dict)
    assert isinstance(env["hints"], list)
    assert isinstance(env["errors"], list)
    data = env["data"]
    assert "branch" in data
    assert "staged" in data
    assert "untracked" in data
    assert "conflicted" in data
    assert isinstance(data["files"], list)


def test_status_json_conflicted_and_file_entries(tmp_git_repo):
    _git(["checkout", "-b", "topic"], cwd=tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("topic\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "topic change"], cwd=tmp_git_repo)
    _git(["checkout", "main"], cwd=tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("main\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "main change"], cwd=tmp_git_repo)
    subprocess.run(["git", "merge", "topic"], cwd=tmp_git_repo, capture_output=True)

    r = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["conflicted"] >= 1
    conflict_entry = next(
        f for f in data["files"] if f["code"] in ("UU", "AA", "DD", "AU", "UA", "UD", "DU")
    )
    assert conflict_entry["status"] == "conflict"
    assert "path" in conflict_entry
    assert "staged" in conflict_entry
    assert "binary" in conflict_entry


def test_status_json_file_entry_shape_for_modified(tmp_git_repo):
    (tmp_git_repo / "new.txt").write_text("hello\n")
    (tmp_git_repo / "README.md").write_text("# changed\n")
    _git(["add", "README.md"], cwd=tmp_git_repo)

    r = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    staged_entry = next(f for f in data["files"] if f["path"] == "README.md")
    assert staged_entry["code"] == "M "
    assert staged_entry["status"] == "modified"
    assert staged_entry["staged"] is True
    untracked_entry = next(f for f in data["files"] if f["path"] == "new.txt")
    assert untracked_entry["status"] == "untracked"


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
