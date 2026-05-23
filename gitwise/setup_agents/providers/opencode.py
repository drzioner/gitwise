"""OpenCode provider — .opencode/agents/*.md."""

from gitwise.setup_agents.providers.base import AdapterConfig

ADAPTER = AdapterConfig(
    name="opencode",
    display_name="OpenCode",
    config_paths=(".opencode/agents/gitwise.md",),
    template_paths=("agents/gitwise.md.template",),
    template_dir="share/opencode",
)
