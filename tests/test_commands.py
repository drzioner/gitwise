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


def test_completions_emits_script() -> None:
    r = run_gitwise("completions", "bash")
    # shtab is an optional dependency; accept either a script or a clean error.
    if r.returncode == 0:
        assert "gitwise" in r.stdout
    else:
        assert r.returncode == 1
