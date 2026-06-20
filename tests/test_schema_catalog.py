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
