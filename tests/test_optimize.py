"""Tests for gitwise optimize."""

from pathlib import Path

import pytest
from gitwise.git import git_dir
from gitwise.optimize import run_optimize


def test_commit_graph_exists_after_optimize(
    monkeypatch: pytest.MonkeyPatch, tmp_git_repo: Path
) -> None:
    monkeypatch.chdir(tmp_git_repo)

    gd = git_dir(tmp_git_repo)
    assert gd is not None
    graph_path = gd / "objects" / "info" / "commit-graph"
    assert not graph_path.exists()

    rc = run_optimize(dry_run=False, yes=True, as_json=False)
    assert rc == 0

    assert graph_path.exists()


def test_optimize_dry_run_no_changes(monkeypatch: pytest.MonkeyPatch, tmp_git_repo: Path) -> None:
    monkeypatch.chdir(tmp_git_repo)

    gd = git_dir(tmp_git_repo)
    assert gd is not None
    graph_path = gd / "objects" / "info" / "commit-graph"

    rc = run_optimize(dry_run=True, yes=True, as_json=False)
    assert rc == 0
    assert not graph_path.exists()


def test_optimize_json_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_git_repo: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    import json

    monkeypatch.chdir(tmp_git_repo)

    rc = run_optimize(dry_run=True, yes=True, as_json=True)
    assert rc == 0

    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["data"]["dry_run"] is True
    assert data["data"]["applied"] is False
    assert "steps" in data["data"]
    assert len(data["data"]["steps"]) > 0


def test_optimize_json_executes_steps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_git_repo: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """Regression for Issue #45: --json must execute steps when --dry-run is absent."""
    import json

    monkeypatch.chdir(tmp_git_repo)

    gd = git_dir(tmp_git_repo)
    assert gd is not None
    graph_path = gd / "objects" / "info" / "commit-graph"
    assert not graph_path.exists()

    rc = run_optimize(dry_run=False, yes=True, as_json=True)
    assert rc == 0

    data = json.loads(capsys.readouterr().out)
    assert data["data"]["dry_run"] is False
    assert data["data"]["applied"] is True
    assert data["data"]["rc"] == 0
    assert data["ok"] is True
    assert all(s.get("ok") for s in data["data"]["steps"] if s["name"] == "commit-graph")
    assert graph_path.exists()


def test_optimize_json_requires_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_git_repo: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """Q1: --json on a write command must require --yes explicitly."""
    import json

    monkeypatch.chdir(tmp_git_repo)
    rc = run_optimize(dry_run=False, yes=False, as_json=True)
    assert rc == 2
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "yes_required"
    assert "hint" in data["errors"][0]
