"""Tests for gitwise log."""

import json
from pathlib import Path

from conftest import _git, _init_repo, run_gitwise


def test_log_basic(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore: initial commit" in r.stdout


def test_log_json(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    env = json.loads(r.stdout)
    assert env["v"] == 3
    assert env["command"] == "log"
    assert "commits" in env["data"]
    assert "count" in env["data"]


def test_log_json_has_stats(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert len(data["commits"]) >= 1
    commit = data["commits"][0]
    assert "hash" in commit
    assert "date" in commit
    assert "subject" in commit
    assert isinstance(commit["parents"], list)
    assert isinstance(commit["stats"], list)
    if commit["stats"]:
        stat = commit["stats"][0]
        assert "path" in stat
        assert "insertions" in stat
        assert "deletions" in stat
        assert "binary" in stat


def test_log_json_iso_strict_date(tmp_git_repo: Path) -> None:
    """log --json emits commit dates in iso-strict format (T separator, Z or numeric offset)."""
    import re

    r = run_gitwise("log", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert len(data["commits"]) >= 1
    commit_date = data["commits"][0]["date"]
    # git --date=iso-strict emits "Z" for UTC and "+/-HH:MM" otherwise (RFC 3339 time-offset)
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+\-]\d{2}:\d{2})$",
        commit_date,
    ), f"expected iso-strict date (T separator + Z or numeric offset), got {commit_date!r}"


def test_log_json_parents_array_for_merge_commit(tmp_git_repo: Path) -> None:
    _git(["checkout", "-b", "topic"], cwd=tmp_git_repo)
    (tmp_git_repo / "a.txt").write_text("a\n")
    _git(["add", "."], cwd=tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "topic"], cwd=tmp_git_repo)
    _git(["checkout", "main"], cwd=tmp_git_repo)
    _git(["merge", "--no-ff", "topic"], cwd=tmp_git_repo)

    r = run_gitwise("log", "--json", "--max-count=1", cwd=tmp_git_repo)
    assert r.returncode == 0
    commit = json.loads(r.stdout)["data"]["commits"][0]
    assert len(commit["parents"]) == 2


def test_log_json_lines_streams_one_envelope_per_commit(tmp_git_repo: Path) -> None:
    for i in range(3):
        (tmp_git_repo / f"f{i}.txt").write_text(f"{i}\n")
        _git(["add", "."], cwd=tmp_git_repo)
        _git(["commit", "--no-gpg-sign", "-m", f"feat: {i}"], cwd=tmp_git_repo)

    r = run_gitwise("log", "--json-lines", "--max-count=3", cwd=tmp_git_repo)
    assert r.returncode == 0
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        env = json.loads(ln)
        assert env["v"] == 3
        assert env["command"] == "log"
        assert "commit" in env["data"]
        assert "hash" in env["data"]["commit"]


def test_log_json_truncation_meta(tmp_git_repo: Path) -> None:
    for i in range(5):
        (tmp_git_repo / f"f{i}.txt").write_text(f"{i}\n")
        _git(["add", "."], cwd=tmp_git_repo)
        _git(["commit", "--no-gpg-sign", "-m", f"feat: {i}"], cwd=tmp_git_repo)

    r = run_gitwise("log", "--json", "--max-count=2", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["count"] == 2
    assert data["truncated"] is True
    assert data["total"] > data["count"], "total must reflect pre-truncation commit count"
    assert len(data["commits"]) == 2


def test_log_json_root_commit_empty_parents(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("# Root\n")
    _git(["add", "."], tmp_path)
    _git(["commit", "--no-gpg-sign", "-m", "chore: root"], tmp_path)
    r = run_gitwise("log", "--json", cwd=tmp_path)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["count"] == 1
    assert data["commits"][0]["parents"] == []


def test_log_oneline(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--oneline", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore: initial commit" in r.stdout


def test_log_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("log", cwd=tmp_path)
    assert r.returncode == 1


def test_log_empty_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    r = run_gitwise("log", cwd=tmp_path)
    assert r.returncode == 0


def test_log_json_empty_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    r = run_gitwise("log", "--json", cwd=tmp_path)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["commits"] == []


def test_log_author_filter(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--author=NonExistent", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_log_author_rejects_nested_quantifiers(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--author=(a+)+b", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_author_rejects_newline_injection(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--author=alice\nbob", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_grep_valid(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--grep=chore", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "chore" in r.stdout


def test_log_grep_rejects_nested_quantifiers(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--grep=(a+)+b", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_grep_rejects_invalid_regex(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--grep=[invalid", cwd=tmp_git_repo)
    assert r.returncode == 1


def test_log_graph(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--graph", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_log_graph_oneline(tmp_git_repo: Path) -> None:
    r = run_gitwise("log", "--graph", "--oneline", cwd=tmp_git_repo)
    assert r.returncode == 0
    assert "*" in r.stdout or "chore" in r.stdout


def test_log_git_arg_denies_dangerous_option(tmp_git_repo):
    import json

    r = run_gitwise("log", "--git-arg=--output", "--json", cwd=tmp_git_repo)
    assert r.returncode == 1
    assert json.loads(r.stdout)["errors"][0]["code"] == "git_arg_denied"
