"""Tests for gitwise snapshot."""

import json
import time

from conftest import run_gitwise as _run


def test_snapshot_creates_file(tmp_git_repo):
    result = _run("snapshot", cwd=tmp_git_repo)
    assert result.returncode == 0
    snapshot = tmp_git_repo / ".claude" / "git-snapshot.md"
    assert snapshot.exists()


def test_snapshot_uses_agents_layout_when_present(tmp_git_repo):
    (tmp_git_repo / ".agents").mkdir()

    result = _run("snapshot", "--json", cwd=tmp_git_repo)

    assert result.returncode == 0
    data = json.loads(result.stdout)["data"]
    assert data["path"].endswith(".agents/git-snapshot.md")
    assert (tmp_git_repo / ".agents" / "git-snapshot.md").exists()
    assert not (tmp_git_repo / ".claude" / "git-snapshot.md").exists()


def test_snapshot_has_generated_at(tmp_git_repo):
    _run("snapshot", cwd=tmp_git_repo)
    content = (tmp_git_repo / ".claude" / "git-snapshot.md").read_text()
    assert "generated_at:" in content
    assert "T" in content  # ISO timestamp contains T


def test_snapshot_updates_timestamp_on_rerun(tmp_git_repo):
    _run("snapshot", cwd=tmp_git_repo)
    first_mtime = (tmp_git_repo / ".claude" / "git-snapshot.md").stat().st_mtime
    # Exceed coarse (1s-granularity) filesystem mtime resolution so the second
    # write is reliably newer, even under parallel scheduler jitter.
    time.sleep(1.1)
    _run("snapshot", cwd=tmp_git_repo)
    second_mtime = (tmp_git_repo / ".claude" / "git-snapshot.md").stat().st_mtime
    assert second_mtime > first_mtime
