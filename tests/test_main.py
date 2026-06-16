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


def test_root_help_epilog_is_localized_en():
    result = _run("--help", env={"GITWISE_LANG": "en"})
    assert result.returncode == 0
    assert "Environment:" in result.stdout
    assert "GITWISE_DEBUG=1" in result.stdout


def test_root_help_epilog_is_localized_es():
    result = _run("--help", env={"GITWISE_LANG": "es"})
    assert result.returncode == 0
    assert "Entorno:" in result.stdout
    assert "GITWISE_DEBUG=1" in result.stdout


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


def test_commands_json_lists_metadata():
    result = _run("commands", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["kind"] == "commands"
    assert data["schema"] == "gitwise/commands/v1"
    assert isinstance(data["commands"], list)
    assert any(item["name"] == "status" for item in data["commands"])


def test_commands_human_output_localized_aliases_label():
    result = _run("commands", env={"GITWISE_LANG": "en"})
    assert result.returncode == 0
    assert "(aliases:" in result.stdout


def test_schema_json_for_known_command():
    result = _run("schema", "status", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["kind"] == "schema"
    assert data["schema"] == "gitwise/schema/v1"
    assert data["schema_version"] == "v1"
    assert data["command"] == "status"
    assert data["schema_kind"] == "cli_input"
    assert data["json_schema"]["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert data["json_schema"]["type"] == "object"


def test_schema_boolean_flags_are_boolean_not_array():
    result = _run("schema", "status", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["json_schema"]["properties"]["json"]["type"] == "boolean"
    assert data["json_schema"]["properties"]["json_pretty"]["type"] == "boolean"


def test_schema_json_for_unknown_command_returns_error_envelope():
    result = _run("schema", "nonexistent-command-xyz", "--json", env={"GITWISE_LANG": "en"})
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["error"] == "unknown command: nonexistent-command-xyz"
    assert data["errors"][0]["code"] == "unknown_command"


def test_schema_unknown_command_is_localized_es():
    result = _run("schema", "nonexistent-command-xyz", "--json", env={"GITWISE_LANG": "es"})
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["error"] == "comando desconocido: nonexistent-command-xyz"
    assert "ejecuta `gitwise commands --json`" in data["errors"][0]["hint"]


def test_schema_unknown_version_returns_schema_not_found():
    result = _run("schema", "status", "--version", "v999", "--json", env={"GITWISE_LANG": "en"})
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "schema_not_found"


def test_completions_bash_outputs_script():
    result = _run("completions", "bash")
    assert result.returncode == 0
    assert "_shtab_gitwise_option_strings" in result.stdout


def test_completions_zsh_outputs_script():
    result = _run("completions", "zsh")
    assert result.returncode == 0
    assert "#compdef gitwise" in result.stdout


def test_completions_fish_outputs_script():
    result = _run("completions", "fish")
    assert result.returncode == 0
    assert "complete -c 'gitwise'" in result.stdout


def test_completions_default_shell_is_bash():
    result = _run("completions")
    assert result.returncode == 0
    assert "_shtab_gitwise_option_strings" in result.stdout


def test_completions_respects_prog_name():
    result = _run("completions", "bash", "--prog", "gw")
    assert result.returncode == 0
    assert "_shtab_gw_option_strings" in result.stdout


def test_completions_json_returns_envelope():
    result = _run("completions", "bash", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["kind"] == "completions"
    assert data["schema"] == "gitwise/completions/v1"
    assert data["shell"] == "bash"
    assert "_shtab_gitwise_option_strings" in data["script"]


def test_completions_json_handles_missing_shtab(monkeypatch, capsys):
    from argparse import Namespace

    from gitwise import __main__ as main_mod

    def raise_missing_dependency(*, shell: str, prog: str) -> str:
        del shell, prog
        raise ModuleNotFoundError("No module named 'shtab'")

    monkeypatch.setattr(main_mod, "_build_completions_script", raise_missing_dependency)

    rc = main_mod._run_completions(Namespace(shell="bash", prog="gitwise", json=True))
    assert rc == 1

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "missing_dependency"
    assert "shtab" in data["error"]


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
    assert data["v"] == 3
    assert "bucket" in data
    assert "actions" in data


def test_setup_agents_list_providers_json(tmp_git_repo):
    result = _run("setup-agents", "--list-providers", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "providers" in data
    assert "adapters" in data
    assert "claude" in data["providers"]
    assert "claude" in data["adapters"]


def test_setup_agents_list_adapters_alias_json(tmp_git_repo):
    result = _run("setup-agents", "--list-adapters", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "providers" in data
    assert "adapters" in data
    assert "claude" in data["providers"]
    assert "claude" in data["adapters"]


def test_setup_agents_migrate_legacy_flag(tmp_git_repo):
    result = _run(
        "setup-agents",
        "--local",
        "--dry-run",
        "--yes",
        "--migrate-legacy-claude",
        "--json",
        cwd=tmp_git_repo,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["canonical_layout"] == "agents_dir"


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
        # rc=2 is legitimate "yes_required" envelope for write commands invoked
        # with --json and without --yes (e.g. clean --branches --json).
        assert result.returncode in (0, 1, 2), f"{cmd} --json failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert "v" in data or "ok" in data or "files" in data, f"{cmd} missing expected JSON key"
