"""Aider provider — .aider.conf.yml + CONVENTIONS.md."""

from gitwise.setup_agents.providers.base import AdapterConfig

ADAPTER = AdapterConfig(
    name="aider",
    display_name="Aider",
    config_paths=(".aider.conf.yml", "CONVENTIONS.md"),
    template_paths=("aider.conf.yml.template", "CONVENTIONS.md.template"),
    template_dir="share/aider",
)
