"""Codex (OpenAI) provider — .codex/agents/*.toml."""

from gitwise.setup_agents.providers.base import AdapterConfig

ADAPTER = AdapterConfig(
    name="codex",
    display_name="Codex",
    config_paths=(".codex/agents/gitwise.toml",),
    template_paths=("agents/gitwise.toml.template",),
    template_dir="share/codex",
)
