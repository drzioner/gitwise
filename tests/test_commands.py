"""Smoke tests for the ``commands`` and ``completions`` meta subcommands."""

import json

from conftest import run_gitwise


def test_commands_json_is_parseable_envelope() -> None:
    r = run_gitwise("commands", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["command"] == "commands"
    assert isinstance(data["data"]["commands"], list)
    names = {c["name"] for c in data["data"]["commands"]}
    # A few stable commands must be discoverable.
    assert {"diff", "log", "commit", "status"} <= names
    # supports_json_lines is part of the contract this branch added; assert it
    # for the two NDJSON-streaming commands so a regression can't slip through.
    by_name = {c["name"]: c for c in data["data"]["commands"]}
    assert by_name["diff"]["supports_json_lines"] is True
    assert by_name["log"]["supports_json_lines"] is True


def test_completions_emits_script() -> None:
    r = run_gitwise("completions", "bash")
    # shtab is an optional dependency. Either it emits a completion script, or
    # it fails with the specific missing-dependency message -- but never a
    # crash/traceback. Pin the exact failure mode so a silent rc=1 can't pass.
    if r.returncode == 0:
        assert "gitwise" in r.stdout
        assert "Traceback" not in r.stderr
    else:
        assert r.returncode == 1
        assert "Traceback" not in r.stderr
        from gitwise.i18n import t

        assert t("missing_dependency_completions_shtab") in r.stderr
