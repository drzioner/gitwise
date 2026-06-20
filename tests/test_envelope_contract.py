"""Contract test: every --json command emits the canonical v3 envelope.

This is the single source of truth for envelope invariants. It catches any
command that forgets to migrate to the nested ``{v, ok, command, data, hints,
errors}`` shape. Commands are exercised via subprocess against a synthetic repo
(no mocks), per the repo testing conventions.
"""

import json

from conftest import run_gitwise

REQUIRED_KEYS = {"v", "ok", "command", "data", "hints", "errors"}

# Commands that produce a JSON envelope in a clean one-commit repo without
# extra setup or write-mode flags. Each tuple is the argv (without --json).
JSON_COMMANDS: list[tuple[str, ...]] = [
    ("status",),
    ("log",),
    ("diff",),
    ("branches",),
    ("summarize",),
    ("stash",),
    ("tag",),
    ("health",),
    ("context",),
    ("snapshot",),
    ("doctor",),
    ("audit", "--quick"),
    ("commands",),
    ("schema", "status"),
]


def test_every_json_command_emits_v3_envelope(tmp_git_repo):
    last_cmd = None
    for cmd in JSON_COMMANDS:
        last_cmd = cmd
        result = run_gitwise(*cmd, "--json", cwd=tmp_git_repo)
        # doctor/audit legitimately return 1 when they find issues; the envelope
        # is still emitted. rc>=2 would mean a real error (e.g. yes_required).
        assert result.returncode in (0, 1), f"{cmd} exited {result.returncode}: {result.stderr}"
        env = json.loads(result.stdout)
        missing = REQUIRED_KEYS - set(env)
        assert not missing, f"{cmd} missing envelope keys: {missing}"
        assert env["v"] == 3, f"{cmd} still emits v={env['v']}"
        assert isinstance(env["ok"], bool)
        assert env["command"] == cmd[0], f"{cmd} emitted command={env['command']!r}"
        assert isinstance(env["data"], dict)
        assert isinstance(env["hints"], list)
        assert isinstance(env["errors"], list)
    assert last_cmd is not None


def test_schema_output_flag_emits_envelope(tmp_git_repo):
    result = run_gitwise("schema", "log", "--output", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["v"] == 3
    assert env["data"]["schema_kind"] == "cli_output"


def test_doctor_ok_reflects_computed_status(tmp_git_repo):
    """doctor/audit override top-level ok to report health, not command success."""
    result = run_gitwise("doctor", "--json", cwd=tmp_git_repo)
    env = json.loads(result.stdout)
    assert env["v"] == 3
    # ok is a real bool (computed from git/python version checks), not absent
    assert isinstance(env["ok"], bool)
