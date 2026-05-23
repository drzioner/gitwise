"""Backward-compatible shim for provider registry imports."""

from gitwise.setup_agents.providers import (
    ADAPTERS,
    list_adapters,
    plan_adapter_actions,
    resolve_adapter_selection,
)
from gitwise.setup_agents.providers.base import AdapterConfig

__all__ = [
    "ADAPTERS",
    "AdapterConfig",
    "list_adapters",
    "plan_adapter_actions",
    "resolve_adapter_selection",
]
