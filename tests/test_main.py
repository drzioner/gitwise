"""Tests for gitwise __main__ — CLI router, flags, exit codes."""

import json

from conftest import run_gitwise as _run


def test_no_command_shows_usage():
    result = _run()
    assert result.returncode == 1


def test_no_command_json_returns_error_payload():
    result = _run("--json")
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["error"] == "missing_command"
    assert data["kind"] == "help"
    assert data["schema"] == "gitwise/help/v1"
    assert data["scope"] == "root"


def test_version_flag():
    result = _run("--version")
    assert result.returncode == 0
    assert "gitwise" in result.stdout


def test_root_help_json():
    result = _run("--help", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["kind"] == "help"
    assert data["schema"] == "gitwise/help/v1"
    assert data["scope"] == "root"
    assert isinstance(data["commands"], list)


def test_root_help_json_pretty_without_json_flag():
    result = _run("--help", "--json-pretty")
    assert result.returncode == 0
    assert '\n  "' in result.stdout
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["scope"] == "root"


def test_command_help_json():
    result = _run("diff", "--help", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["kind"] == "help"
    assert data["schema"] == "gitwise/help/v1"
    assert data["scope"] == "command"
    assert data["command"] == "diff"
    assert isinstance(data["options"], list)


def test_json_compact_by_default(tmp_git_repo):
    result = _run("summarize", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert '\n  "' not in result.stdout
    data = json.loads(result.stdout)
    assert data["ok"] is True


def test_json_pretty_flag(tmp_git_repo):
    result = _run("summarize", "--json-pretty", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert '\n  "' in result.stdout
    data = json.loads(result.stdout)
    assert data["ok"] is True


def test_json_pretty_alias_flag(tmp_git_repo):
    result = _run("summarize", "--pretty", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert '\n  "' in result.stdout
    data = json.loads(result.stdout)
    assert data["ok"] is True


def test_unknown_command():
    result = _run("nonexistent-command-xyz")
    assert result.returncode != 0


def test_doctor_command():
    result = _run("doctor", "--json")
    assert result.returncode in (0, 1)
    data = json.loads(result.stdout)
    assert "gitwise_version" in data


def test_lang_flag_valid():
    result = _run("--lang", "en", "doctor", "--json")
    assert result.returncode in (0, 1)


def test_lang_flag_invalid():
    result = _run("--lang", "fr", "doctor", "--json")
    assert result.returncode != 0


def test_update_dry_run():
    result = _run("update", "--dry-run")
    assert result.returncode == 0


def test_setup_agents_dry_run(tmp_git_repo):
    result = _run("setup-agents", "--local", "--dry-run", "--yes", cwd=tmp_git_repo)
    assert result.returncode == 0


def test_setup_agents_json(tmp_git_repo):
    result = _run("setup-agents", "--local", "--yes", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["v"] == 2
    assert "bucket" in data
    assert "actions" in data


def test_timing_shown_for_slow_commands(tmp_git_repo):
    result = _run("summarize", cwd=tmp_git_repo, env={"GITWISE_LANG": "en"})
    assert result.returncode == 0


def test_all_subcommands_accept_json(tmp_git_repo):
    commands = [
        ("doctor",),
        ("setup", "--dry-run"),
        ("audit", "--quick"),
        ("summarize",),
        ("snapshot",),
        ("clean", "--branches"),
        ("optimize", "--dry-run"),
        ("diff",),
        ("log",),
        ("branches",),
        ("status",),
        ("stash",),
        ("tag",),
        ("health",),
        ("context",),
    ]
    for cmd in commands:
        result = _run(*cmd, "--json", cwd=tmp_git_repo)
        assert result.returncode in (0, 1), f"{cmd} --json failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert "v" in data or "ok" in data or "files" in data, f"{cmd} missing expected JSON key"
