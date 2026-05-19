"""Continue adapter — .continue/rules/*.md."""

from gitwise.setup_agents.adapters.base import AdapterConfig

ADAPTER = AdapterConfig(
    name="continue",
    display_name="Continue",
    config_paths=(".continue/rules/gitwise.md",),
    template_paths=("rules/gitwise.md.template",),
    template_dir="share/continue",
)
