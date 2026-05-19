"""Cursor adapter — .cursor/rules/*.mdc (MDC format with YAML frontmatter)."""

from gitwise.setup_agents.adapters.base import AdapterConfig

ADAPTER = AdapterConfig(
    name="cursor",
    display_name="Cursor",
    config_paths=(".cursor/rules/gitwise.mdc",),
    template_paths=("rules/gitwise.mdc.template",),
    template_dir="share/cursor",
)
