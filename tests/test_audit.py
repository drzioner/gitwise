"""Tests for gitwise audit — 9 cases."""

import json
import os
import platform
import subprocess
import time

from conftest import run_gitwise as _run


def test_audit_json_structure(tmp_git_repo):
    result = _run("audit", "--json", cwd=tmp_git_repo)
    assert result.returncode in (0, 1)  # 0=ok, 1=has issues
    data = json.loads(result.stdout)
    assert data["v"] == 3
    assert "ok" in data
    assert "findings" in data["data"]
    assert "summary" in data["data"]
    summary = data["data"]["summary"]
    assert "stale_branches" in summary
    assert "commit_graph" in summary
    assert "old_stashes" in summary
    assert "large_blobs" in summary


def test_audit_quick_under_5s(tmp_git_repo):
    start = time.monotonic()
    result = _run("audit", "--quick", "--json", cwd=tmp_git_repo)
    elapsed = time.monotonic() - start
    assert result.returncode in (0, 1)
    # Wall-clock is unreliable under xdist CPU contention; relax the budget when parallel
    # (still catches a genuine hang) but keep the strict SLA in serial runs.
    budget = 30.0 if os.environ.get("PYTEST_XDIST_WORKER") else 5.0
    assert elapsed < budget, f"audit --quick tardó {elapsed:.2f}s (límite: {budget}s)"


def test_audit_detects_stale_branches(tmp_git_repo_with_stale):
    result = _run("audit", "--json", cwd=tmp_git_repo_with_stale)
    data = json.loads(result.stdout)
    stale = [f for f in data["data"]["findings"] if f["type"] == "stale_branches"]
    assert len(stale) == 1
    assert stale[0]["count"] == 3
    assert len(stale[0]["branches"]) == 3


def test_audit_detects_missing_commit_graph(tmp_git_repo):
    result = _run("audit", "--json", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert data["data"]["summary"]["commit_graph"] is False
    missing = [f for f in data["data"]["findings"] if f["type"] == "missing_commit_graph"]
    assert len(missing) == 1


def test_audit_detects_large_blobs(tmp_git_repo_with_large_blob):
    result = _run("audit", "--json", cwd=tmp_git_repo_with_large_blob)
    data = json.loads(result.stdout)
    large = [f for f in data["data"]["findings"] if f["type"] == "large_blobs"]
    assert len(large) == 1
    assert large[0]["count"] >= 1
    assert large[0]["blobs"][0]["size"] >= 1_000_000


def test_audit_detects_fsmonitor_state(tmp_git_repo):
    result = _run("audit", "--json", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    if platform.system() == "Darwin":
        fsmonitor = [f for f in data["data"]["findings"] if f["type"] == "fsmonitor_disabled"]
        assert len(fsmonitor) == 1  # Fresh repo has no fsmonitor configured


def test_audit_clean_repo_no_medium_findings(tmp_git_repo_with_commit_graph):
    repo = tmp_git_repo_with_commit_graph
    # Also set fsmonitor to suppress that finding on macOS
    subprocess.run(["git", "config", "core.fsmonitor", "true"], cwd=repo, check=True)
    result = _run("audit", "--quick", "--json", cwd=repo)
    data = json.loads(result.stdout)
    medium_plus = [
        f for f in data["data"]["findings"] if f["severity"] in ("critical", "high", "medium")
    ]
    assert len(medium_plus) == 0
    assert data["ok"] is True


def test_audit_warns_mixed_staged_unstaged(tmp_git_repo):
    # Stage a new file
    (tmp_git_repo / "staged.txt").write_text("staged")
    subprocess.run(["git", "add", "staged.txt"], cwd=tmp_git_repo, check=True)
    # Modify an existing file without staging
    (tmp_git_repo / "README.md").write_text("modified unstaged")

    result = _run("audit", "--json", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    mixed = [f for f in data["data"]["findings"] if f["type"] == "mixed_staging"]
    assert len(mixed) == 1


def test_audit_quick_skips_large_blobs(tmp_git_repo_with_large_blob):
    result = _run("audit", "--quick", "--json", cwd=tmp_git_repo_with_large_blob)
    data = json.loads(result.stdout)
    large = [f for f in data["data"]["findings"] if f["type"] == "large_blobs"]
    assert len(large) == 0  # --quick skips blob search
    assert data["data"]["summary"]["large_blobs"] == 0
