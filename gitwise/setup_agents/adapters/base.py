"""Base types for the adapter registry system."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterConfig:
    name: str
    display_name: str
    config_paths: tuple[str, ...]
    template_paths: tuple[str, ...]
    template_dir: str
