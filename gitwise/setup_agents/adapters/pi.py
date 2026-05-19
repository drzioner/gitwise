"""Pi adapter — .pi/agent/skills/gitwise.md."""

from gitwise.setup_agents.adapters.base import AdapterConfig

ADAPTER = AdapterConfig(
    name="pi",
    display_name="Pi",
    config_paths=(".pi/agent/skills/gitwise.md",),
    template_paths=("skills/gitwise.md.template",),
    template_dir="share/pi",
)
