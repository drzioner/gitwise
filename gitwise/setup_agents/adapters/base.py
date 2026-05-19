"""Base types for the adapter registry system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AdapterConfig:
    name: str
    display_name: str
    config_paths: tuple[str, ...]
    template_paths: tuple[str, ...]
    template_dir: str
    reads_agents_md: bool = True


@dataclass
class AdapterState:
    name: str
    configs: dict[str, Literal["absent", "regular", "symlink_valid", "symlink_broken"]]
    has_gitwise: dict[str, bool]
