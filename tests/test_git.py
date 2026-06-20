"""Tests for gitwise git helpers — is_repo, repo_root, config, branches."""

import json

from conftest import run_gitwise as _run


def test_is_repo_detects_git(tmp_git_repo):
    result = _run("audit", "--quick", "--json", cwd=tmp_git_repo)
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert "summary" in data["data"]


def test_not_a_git_repo(tmp_path):
    result = _run("audit", "--json", cwd=tmp_path)
    assert result.returncode == 1
    assert (
        "not a git repository" in result.stderr.lower()
        or "no es un repositorio" in result.stderr.lower()
    )


def test_repo_root_resolved(tmp_git_repo):
    result = _run("summarize", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True


def test_git_config_read(tmp_git_repo):
    result = _run("setup", "--dry-run", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "changes" in data["data"]


def test_stale_branches_empty(tmp_git_repo):
    result = _run("clean", "--branches", "--dry-run", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["data"]["deletable"] == []


def test_stale_branches_detected(tmp_git_repo_with_stale):
    result = _run("clean", "--branches", "--dry-run", "--json", cwd=tmp_git_repo_with_stale)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data["data"]["deletable"]) == 3


def test_worktree_branches(tmp_git_repo):
    result = _run("worktree", "--json", cwd=tmp_git_repo)
    assert result.returncode == 1


def test_gpg_status_in_doctor():
    result = _run("doctor", "--json")
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert "gpg" in data["data"]
    gpg = data["data"]["gpg"]
    assert "gpg_binary" in gpg
    assert "gpgsign_enabled" in gpg
    assert "signing_key_set" in gpg
    assert "ready" in gpg


def test_validate_ref_rejects_dash_prefix():
    from gitwise.git import validate_ref

    assert validate_ref("-evil") is False
    assert validate_ref("--option") is False


def test_validate_ref_accepts_git_revision_syntax():
    from gitwise.git import validate_ref

    assert validate_ref("HEAD..feature") is True
    assert validate_ref("HEAD~5") is True
    assert validate_ref("HEAD^{}") is True
    assert validate_ref("v1.0^{commit}") is True
    assert validate_ref("main@{2024-01-01}") is True


def test_validate_ref_accepts_valid():
    from gitwise.git import validate_ref

    assert validate_ref("HEAD") is True
    assert validate_ref("main") is True
    assert validate_ref("abc1234") is True
    assert validate_ref("feature/test-branch") is True


def test_validate_branch_name_rejects_invalid():
    from gitwise.git import validate_branch_name

    assert validate_branch_name("-evil") is False
    assert validate_branch_name("feature..test") is False
    assert validate_branch_name("feature~test") is False
    assert validate_branch_name("feature:ref") is False
    assert validate_branch_name("feature name") is False


def test_validate_branch_name_accepts_valid():
    from gitwise.git import validate_branch_name

    assert validate_branch_name("main") is True
    assert validate_branch_name("feature/test-branch") is True
    assert validate_branch_name("release/v1.0.0") is True


def test_validate_grep_pattern_rejects_nested_quantifiers():
    from gitwise.git import validate_grep_pattern

    assert validate_grep_pattern("(a+)+b") is False
    assert validate_grep_pattern("(a|b)+c") is False
    assert validate_grep_pattern("[a+]+b") is False


def test_validate_grep_pattern_rejects_too_long():
    from gitwise.git import validate_grep_pattern

    assert validate_grep_pattern("a" * 201) is False


def test_validate_grep_pattern_rejects_invalid_regex():
    from gitwise.git import validate_grep_pattern

    assert validate_grep_pattern("[invalid") is False
    assert validate_grep_pattern("(unclosed") is False


def test_validate_grep_pattern_accepts_valid():
    from gitwise.git import validate_grep_pattern

    assert validate_grep_pattern("feat") is True
    assert validate_grep_pattern("fix.*auth") is True
    assert validate_grep_pattern("^(feat|fix):") is True
    assert validate_grep_pattern("[0-9]+\\.[0-9]+") is True
