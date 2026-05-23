"""Schema catalog loader for versioned CLI schemas."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SCHEMA_VERSION_DEFAULT = "v1"


@lru_cache(maxsize=1)
def _schema_roots() -> tuple[Path, ...]:
    package_dir = Path(__file__).resolve().parent
    return (package_dir.parent / "share" / "schemas",)


def schema_root(version: str = SCHEMA_VERSION_DEFAULT) -> Path:
    roots = _schema_roots()
    for candidate in roots:
        version_root = candidate / version
        if version_root.is_dir():
            return version_root
    return roots[0] / version


def command_input_schema_path(*, command: str, version: str = SCHEMA_VERSION_DEFAULT) -> Path:
    return schema_root(version) / "input" / f"{command}.json"


def load_command_input_schema(
    *, command: str, version: str = SCHEMA_VERSION_DEFAULT
) -> dict | None:
    path = command_input_schema_path(command=command, version=version)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"schema file is not a JSON object: {path}")
    return payload


def list_command_input_schema_files(*, version: str = SCHEMA_VERSION_DEFAULT) -> list[Path]:
    input_dir = schema_root(version) / "input"
    if not input_dir.is_dir():
        return []
    return sorted(input_dir.glob("*.json"))
