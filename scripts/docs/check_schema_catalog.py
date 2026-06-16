#!/usr/bin/env python3
"""Validate versioned JSON schemas in share/schemas."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gitwise._cli_introspection import (
    command_input_schema,
    commands_metadata,
    resolve_command_parser,
)
from gitwise._cli_parser import build_parser
from gitwise.schema import (
    command_input_schema_path,
    list_command_input_schema_files,
    load_command_input_schema,
)
from jsonschema import Draft202012Validator


def _validate_schema_document(
    path: Path, payload: dict, *, command: str, version: str
) -> list[str]:
    errors: list[str] = []

    try:
        Draft202012Validator.check_schema(payload)
    except Exception as exc:
        errors.append(f"invalid JSON Schema in {path}: {exc}")

    expected_id = f"https://gitwise.dev/schemas/{version}/input/{command}.json"
    schema_id = payload.get("$id")
    if schema_id != expected_id:
        errors.append(f"{path}: $id mismatch (expected {expected_id}, got {schema_id})")

    expected_title = f"gitwise {command} cli input"
    schema_title = payload.get("title")
    if schema_title != expected_title:
        errors.append(f"{path}: title mismatch (expected {expected_title}, got {schema_title})")

    if payload.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append(f"{path}: missing or invalid $schema")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate gitwise schema catalog")
    parser.add_argument("--version", default="v1", help="schema catalog version (default: v1)")
    args = parser.parse_args()

    version = args.version
    schema_files = list_command_input_schema_files(version=version)

    errors: list[str] = []
    if not schema_files:
        errors.append(f"schema-catalog-check: no schema files found for version {version}")

    parser = build_parser()
    expected_commands = sorted(command["name"] for command in commands_metadata(parser))
    schema_commands = sorted(path.stem for path in schema_files)

    missing = sorted(set(expected_commands) - set(schema_commands))
    extra = sorted(set(schema_commands) - set(expected_commands))
    if missing:
        errors.append(f"schema-catalog-check: missing schemas for commands: {', '.join(missing)}")
    if extra:
        errors.append(
            f"schema-catalog-check: extra schemas not mapped to commands: {', '.join(extra)}"
        )

    for command in expected_commands:
        payload = load_command_input_schema(command=command, version=version)
        if payload is None:
            continue
        path = command_input_schema_path(command=command, version=version)
        errors.extend(_validate_schema_document(path, payload, command=command, version=version))

        command_parser = resolve_command_parser(parser=parser, name=command)
        if command_parser is None:
            errors.append(f"schema-catalog-check: parser not found for command: {command}")
            continue
        expected_schema = command_input_schema(command_parser)
        if payload != expected_schema:
            errors.append(
                "schema-catalog-check: schema drift detected for "
                f"{command} (regenerate share/schemas/{version}/input/{command}.json)"
            )

    if errors:
        for error in errors:
            print(error)
        return 1

    print(
        "schema-catalog-check: catalog aligned "
        f"(version={version}, commands={len(expected_commands)}, files={len(schema_files)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
