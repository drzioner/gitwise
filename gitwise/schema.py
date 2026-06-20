"""Schema catalog loader for versioned CLI schemas."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SCHEMA_VERSION_DEFAULT = "v1"


@lru_cache(maxsize=1)
def _schema_roots() -> tuple[Path, ...]:
    """Return the ordered list of schema root directories."""
    from ._paths import share_dir

    return (share_dir() / "schemas",)


def schema_root(version: str = SCHEMA_VERSION_DEFAULT) -> Path:
    """Return the schema directory for *version*, falling back to the first root."""
    roots = _schema_roots()
    for candidate in roots:
        version_root = candidate / version
        if version_root.is_dir():
            return version_root
    return roots[0] / version


def command_input_schema_path(*, command: str, version: str = SCHEMA_VERSION_DEFAULT) -> Path:
    """Return the path to the JSON schema for *command* input."""
    return schema_root(version) / "input" / f"{command}.json"


def command_output_schema_path(*, command: str, version: str = SCHEMA_VERSION_DEFAULT) -> Path:
    """Return the path to the JSON schema describing *command* ``--json`` output."""
    return schema_root(version) / "output" / f"{command}.json"


def load_command_output_schema(
    *, command: str, version: str = SCHEMA_VERSION_DEFAULT
) -> dict | None:
    """Load the output schema for *command*, or None if no specific file exists."""
    path = command_output_schema_path(command=command, version=version)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"schema file is not a JSON object: {path}")
    return payload


def generic_output_schema(*, command: str, version: str = SCHEMA_VERSION_DEFAULT) -> dict:
    """Build a generic v3 envelope schema for commands lacking a specific output file.

    Every ``--json`` output is the canonical envelope
    ``{v, ok, command, data, hints, errors}``; commands without a bespoke
    output schema still get a valid, command-scoped envelope description.
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://gitwise.dev/schemas/{version}/output/{command}.json",
        "title": f"gitwise {command} cli output",
        "description": "Generic v3 envelope; command-specific data fields are not enumerated.",
        "type": "object",
        "required": ["v", "ok", "command", "data", "hints", "errors"],
        "additionalProperties": False,
        "properties": {
            "v": {"const": 3, "description": "envelope version"},
            "ok": {"type": "boolean"},
            "command": {"const": command},
            "data": {"type": "object"},
            "hints": {"type": "array", "items": {"type": "string"}},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["code", "message"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "hint": {"type": "string"},
                    },
                },
            },
        },
    }


def load_command_input_schema(
    *, command: str, version: str = SCHEMA_VERSION_DEFAULT
) -> dict | None:
    """Load and return the JSON schema for *command*, or None if missing."""
    path = command_input_schema_path(command=command, version=version)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"schema file is not a JSON object: {path}")
    return payload


def list_command_input_schema_files(*, version: str = SCHEMA_VERSION_DEFAULT) -> list[Path]:
    """Return sorted paths of all command input schema JSON files."""
    input_dir = schema_root(version) / "input"
    if not input_dir.is_dir():
        return []
    return sorted(input_dir.glob("*.json"))
