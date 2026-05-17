"""Edge case tests — detached HEAD, no remote, no upstream."""

import json

from conftest import _git, run_gitwise


def _detach_head(repo):
    _git(["checkout", "HEAD~0", "--detach"], repo)


class TestDetachedHead:
    def test_status_detached_head(self, tmp_git_repo):
        _detach_head(tmp_git_repo)
        r = run_gitwise("status", cwd=tmp_git_repo)
        assert r.returncode == 0
        assert "detached" in r.stdout.lower() or "desacoplado" in r.stdout.lower()

    def test_status_detached_head_json(self, tmp_git_repo):
        _detach_head(tmp_git_repo)
        r = run_gitwise("status", "--json", cwd=tmp_git_repo)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["v"] == 2
        assert data["ok"] is True
        assert "detached" in data["branch"].lower() or "desacoplado" in data["branch"].lower()
        assert data["has_upstream"] is False

    def test_log_detached_head(self, tmp_git_repo):
        _detach_head(tmp_git_repo)
        r = run_gitwise("log", cwd=tmp_git_repo)
        assert r.returncode == 0

    def test_show_detached_head(self, tmp_git_repo):
        _detach_head(tmp_git_repo)
        r = run_gitwise("show", cwd=tmp_git_repo)
        assert r.returncode == 0

    def test_merge_rejects_detached_head(self, tmp_git_repo):
        _detach_head(tmp_git_repo)
        _git(["checkout", "-b", "feature-x"], tmp_git_repo)
        (tmp_git_repo / "f.txt").write_text("x\n")
        _git(["add", "."], tmp_git_repo)
        _git(["commit", "--no-gpg-sign", "-m", "feat: x"], tmp_git_repo)
        _git(["checkout", "main"], tmp_git_repo)
        _detach_head(tmp_git_repo)
        r = run_gitwise("merge", "feature-x", "--yes", cwd=tmp_git_repo)
        assert r.returncode == 1


class TestNoUpstream:
    def test_status_no_upstream_json(self, tmp_git_repo):
        r = run_gitwise("status", "--json", cwd=tmp_git_repo)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["has_upstream"] is False
        assert data["ahead"] == 0
        assert data["behind"] == 0

    def test_branches_no_upstream(self, tmp_git_repo):
        r = run_gitwise("branches", cwd=tmp_git_repo)
        assert r.returncode == 0
        assert "main" in r.stdout

    def test_branches_no_upstream_json(self, tmp_git_repo):
        r = run_gitwise("branches", "--json", cwd=tmp_git_repo)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["v"] == 2
        assert data["ok"] is True
        assert len(data["branches"]) >= 1


class TestNoRemote:
    def test_sync_no_remote(self, tmp_git_repo):
        r = run_gitwise("sync", cwd=tmp_git_repo)
        assert r.returncode == 0

    def test_sync_no_remote_json(self, tmp_git_repo):
        r = run_gitwise("sync", "--json", cwd=tmp_git_repo)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["v"] == 2
        assert data["ok"] is True

    def test_branches_no_remote(self, tmp_git_repo):
        r = run_gitwise("branches", cwd=tmp_git_repo)
        assert r.returncode == 0
        assert "main" in r.stdout

    def test_pr_no_remote(self, tmp_git_repo):
        r = run_gitwise("pr", cwd=tmp_git_repo)
        assert r.returncode != 0
