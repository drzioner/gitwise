"""Tests for versioned schema catalog helpers and docs checker."""

from __future__ import annotations

from pathlib import Path

from gitwise.schema import (
    command_input_schema_path,
    command_output_schema_path,
    generic_output_schema,
    list_command_input_schema_files,
    load_command_input_schema,
    load_command_output_schema,
)


def test_schema_catalog_has_files_for_v1() -> None:
    files = list_command_input_schema_files(version="v1")
    assert files
    assert all(path.suffix == ".json" for path in files)


def test_load_command_input_schema_status_v1() -> None:
    payload = load_command_input_schema(command="status", version="v1")
    assert payload is not None
    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert payload["type"] == "object"


def test_command_input_schema_path_points_to_share_catalog() -> None:
    path = command_input_schema_path(command="status", version="v1")
    assert path.as_posix().endswith("share/schemas/v1/input/status.json")


def test_load_command_output_schema_status_v1() -> None:
    payload = load_command_output_schema(command="status", version="v1")
    assert payload is not None
    assert payload["title"] == "gitwise status cli output"
    props = payload["properties"]
    assert props["v"]["const"] == 3
    assert props["command"]["const"] == "status"
    assert "conflicted" in props["data"]["properties"]


def test_load_command_output_schema_missing_returns_none() -> None:
    assert load_command_output_schema(command="nonexistent_cmd", version="v1") is None


def test_generic_output_schema_is_valid_envelope() -> None:
    schema = generic_output_schema(command="stash", version="v1")
    assert schema["properties"]["v"]["const"] == 3
    assert schema["properties"]["command"]["const"] == "stash"
    assert set(schema["required"]) == {"v", "ok", "command", "data", "hints", "errors"}


def test_command_output_schema_path_points_to_share_catalog() -> None:
    path = command_output_schema_path(command="log", version="v1")
    assert path.as_posix().endswith("share/schemas/v1/output/log.json")


def test_error_envelope_diff_validates_against_output_schema() -> None:
    """A real error_envelope("diff", ...) payload must satisfy diff output schema.

    Guards against schema/producer drift: the error path emits ``data: {}``,
    which the schema's oneOf must accept.
    """
    from gitwise.utils.json_envelope import error_envelope
    from jsonschema import Draft202012Validator

    schema = load_command_output_schema(command="diff", version="v1")
    assert schema is not None
    payload = error_envelope("diff", error="too_many_refs", code="too_many_refs")
    Draft202012Validator(schema).validate(payload)


def test_ok_envelope_diff_validates_against_output_schema() -> None:
    from gitwise.utils.json_envelope import ok_envelope
    from jsonschema import Draft202012Validator

    schema = load_command_output_schema(command="diff", version="v1")
    assert schema is not None
    payload = ok_envelope("diff", files=[], count=0)
    Draft202012Validator(schema).validate(payload)


def test_schema_catalog_checker_script_passes() -> None:
    import subprocess
    import sys

    root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "scripts/docs/check_schema_catalog.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "schema-catalog-check: catalog aligned" in result.stdout


def test_policy_schema_matches_default_policy() -> None:
    """The published policy schema and the loader's defaults must not drift."""
    import json

    from gitwise.policy import DEFAULT_POLICY
    from gitwise.schema import schema_root
    from jsonschema import Draft202012Validator

    path = schema_root("v1") / "policy.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    assert set(payload["properties"]) == set(DEFAULT_POLICY)
    assert payload["additionalProperties"] is False
    Draft202012Validator(payload).validate(DEFAULT_POLICY)


def test_policy_schema_rejects_unknown_key() -> None:
    import json

    import pytest
    from gitwise.schema import schema_root
    from jsonschema import Draft202012Validator, ValidationError

    payload = json.loads((schema_root("v1") / "policy.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        Draft202012Validator(payload).validate({"version": 1, "blok_secrets": True})


def test_setup_agents_output_validates_against_its_schema(tmp_git_repo) -> None:
    """The schema documented the old flat contract; keep it and the producer aligned."""
    import json

    from jsonschema import Draft202012Validator

    from conftest import run_gitwise

    schema = load_command_output_schema(command="setup-agents", version="v1")
    assert schema is not None
    result = run_gitwise(
        "setup-agents", "--local", "--dry-run", "--yes", "--json", cwd=tmp_git_repo
    )
    Draft202012Validator(schema).validate(json.loads(result.stdout))
