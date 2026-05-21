"""Tests for gitwise summarize."""

import json
import os
import subprocess

from conftest import run_gitwise


def test_summarize_json_ok(tmp_git_repo):
    result = run_gitwise("summarize", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["v"] == 3
    assert data["ok"] is True
    assert "branch" in data
    assert "status" in data
    assert "log" in data
    assert "status_count" in data
    assert "log_count" in data
    assert "changed_files" in data
    assert "changed_count" in data


def test_summarize_output_under_8kb(tmp_git_repo):
    result = run_gitwise("summarize", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert len(result.stdout) < 8192, f"output {len(result.stdout)} bytes > 8KB"


def test_summarize_max_commits_flag(tmp_git_repo):
    for i in range(5):
        (tmp_git_repo / f"file{i}.txt").write_text(f"content {i}\n")
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "--no-gpg-sign", "-m", f"feat: commit {i}"],
            cwd=tmp_git_repo,
            check=True,
            capture_output=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "T",
                "GIT_AUTHOR_EMAIL": "t@t.com",
                "GIT_COMMITTER_NAME": "T",
                "GIT_COMMITTER_EMAIL": "t@t.com",
            },
        )

    result_default = run_gitwise("summarize", "--json", cwd=tmp_git_repo)
    result_limited = run_gitwise("summarize", "--json", "--max-commits", "2", cwd=tmp_git_repo)
    d_default = json.loads(result_default.stdout)
    d_limited = json.loads(result_limited.stdout)
    assert d_limited["log_count"] <= 2
    assert d_default["log_count"] <= 10


def test_summarize_diff_json_includes_diff_field(tmp_git_repo):
    readme = tmp_git_repo / "README.md"
    readme.write_text("modified content\n")
    result = run_gitwise("summarize", "--diff", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "diff" in data
    assert "modified content" in data["diff"]


def test_summarize_json_without_diff(tmp_git_repo):
    result = run_gitwise("summarize", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "diff" not in data


def test_summarize_json_structured_fields_with_changes(tmp_git_repo):
    readme = tmp_git_repo / "README.md"
    readme.write_text("changed\n")

    result = run_gitwise("summarize", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)

    assert isinstance(data["status"], dict)
    assert isinstance(data["log"], dict)
    assert isinstance(data["changed_files"], list)

    assert data["status"].get("README.md") == "M"
    assert any(entry.get("path") == "README.md" for entry in data["changed_files"])

    if data["log"]:
        first_hash = next(iter(data["log"].keys()))
        assert first_hash
        assert isinstance(data["log"][first_hash], str)


def test_summarize_changed_files_omits_duplicate_code_when_not_needed(tmp_git_repo):
    readme = tmp_git_repo / "README.md"
    readme.write_text("changed\n")

    result = run_gitwise("summarize", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)

    readme_entry = next(
        (entry for entry in data["changed_files"] if entry.get("path") == "README.md"), None
    )
    assert readme_entry is not None
    assert readme_entry["status"] == "M"
    assert "code" not in readme_entry
