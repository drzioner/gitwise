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
    # In --json mode require_root now emits a v3 error envelope (not bare stderr).
    env = json.loads(result.stdout)
    assert env["ok"] is False
    assert env["command"] == "audit"
    assert env["errors"][0]["code"] == "not_a_git_repo"


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


def test_get_timeout_rejects_nonpositive(monkeypatch):
    """GITWISE_GIT_TIMEOUT=0 must fall back to the default, not time out instantly."""
    from gitwise.git import _DEFAULT_TIMEOUT, _get_timeout

    monkeypatch.setenv("GITWISE_GIT_TIMEOUT", "0")
    assert _get_timeout() == _DEFAULT_TIMEOUT
    monkeypatch.setenv("GITWISE_GIT_TIMEOUT", "30")
    assert _get_timeout() == 30


def test_run_timeout_returns_124(tmp_git_repo):
    """A timed-out git operation returns rc 124 (timeout coreutil convention), not raise."""
    from gitwise.git import run

    result = run(["status"], cwd=tmp_git_repo, timeout=0)
    assert result.returncode == 124


def test_passthrough_denies_dangerous_options():
    """--git-arg passthrough must refuse code-exec / arbitrary-write / redirect options."""
    from gitwise.git import validate_passthrough_arg, validate_passthrough_args

    # Dangerous forms (with and without =value) are rejected.
    for bad in ["--output", "--output=/tmp/x", "-c", "--upload-pack=/bin/sh", "--git-dir=/x"]:
        assert validate_passthrough_arg(bad) is not None, bad
    # Legitimate read options pass through.
    for ok in ["-U5", "--diff-filter=AM", "--ignore-space-change", "--no-merges", "--all"]:
        assert validate_passthrough_arg(ok) is None, ok
    # Empty is rejected.
    assert validate_passthrough_arg("") is not None
    # List helper returns first error or None.
    assert validate_passthrough_args(["-U3", "--output"]) is not None
    assert validate_passthrough_args(["-U3", "--diff-filter=M"]) is None
    assert validate_passthrough_args(None) is None


def test_passthrough_denies_exec_path():
    """--exec-path (code-exec via alternate git binary) must be refused too."""
    from gitwise.git import validate_passthrough_arg

    assert validate_passthrough_arg("--exec-path") is not None
    assert validate_passthrough_arg("--exec-path=/tmp/evil") is not None


def test_build_git_env_scrubs_config_and_ssh():
    """_build_git_env must strip GIT_CONFIG* and GIT_SSH_COMMAND/GIT_ASKPASS."""
    import os

    from gitwise.git import _build_git_env

    saved = {
        k: os.environ.get(k)
        for k in ("GIT_CONFIG_COUNT", "GIT_SSH_COMMAND", "GIT_ASKPASS", "GIT_DIR")
    }
    os.environ["GIT_CONFIG_COUNT"] = "1"
    os.environ["GIT_SSH_COMMAND"] = "evil"
    os.environ["GIT_ASKPASS"] = "evil"
    os.environ["GIT_DIR"] = "/keep/me"
    try:
        env = _build_git_env()
        assert "GIT_CONFIG_COUNT" not in env
        assert "GIT_SSH_COMMAND" not in env
        assert "GIT_ASKPASS" not in env
        # legitimate path overrides are preserved.
        assert env.get("GIT_DIR") == "/keep/me"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
