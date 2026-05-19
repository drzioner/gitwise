"""Adapter registry: multi-agent tool support for setup-agents."""

from pathlib import Path

from gitwise.i18n import t
from gitwise.setup_agents.adapters.aider import ADAPTER as AIDER
from gitwise.setup_agents.adapters.base import AdapterConfig
from gitwise.setup_agents.adapters.codex import ADAPTER as CODEX
from gitwise.setup_agents.adapters.continue_adapter import ADAPTER as CONTINUE
from gitwise.setup_agents.adapters.cursor import ADAPTER as CURSOR
from gitwise.setup_agents.adapters.opencode import ADAPTER as OPENCODE
from gitwise.setup_agents.adapters.pi import ADAPTER as PI

ADAPTERS: dict[str, AdapterConfig] = {
    "cursor": CURSOR,
    "continue": CONTINUE,
    "opencode": OPENCODE,
    "codex": CODEX,
    "aider": AIDER,
    "pi": PI,
}


def list_adapters() -> list[str]:
    return sorted(ADAPTERS.keys())


def resolve_adapter_selection(
    names: list[str] | None,
) -> tuple[list[AdapterConfig], list[str]]:
    if not names:
        return [], []
    if "none" in names or "claude-only" in names:
        if len(names) > 1:
            return [], [t("adapters_none_with_others")]
        return [], []
    resolved: list[AdapterConfig] = []
    errors: list[str] = []
    for name in names:
        cfg = ADAPTERS.get(name)
        if cfg is None:
            errors.append(t("unknown_adapter", name=name))
        else:
            resolved.append(cfg)
    return resolved, errors


def _read_adapter_template(cfg: AdapterConfig, template_name: str) -> str:
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    template_path = project_root / cfg.template_dir / template_name
    if not template_path.exists():
        raise FileNotFoundError(t("adapter_no_template", path=str(template_path)))
    return template_path.read_text(encoding="utf-8")


def _plan_single_adapter(
    cfg: AdapterConfig, root: Path, actions: list[dict], warnings: list[str]
) -> None:
    from gitwise.setup_agents.state import _classify_path

    for cp, tp in zip(cfg.config_paths, cfg.template_paths, strict=True):
        p = root / cp
        state = _classify_path(p)
        if state == "absent":
            content = _read_adapter_template(cfg, tp)
            actions.append(
                {
                    "action": "adapter-create",
                    "file": cp,
                    "content": content,
                    "adapter": cfg.display_name,
                }
            )
        else:
            warnings.append(t("adapter_exists", adapter=cfg.display_name, file=cp))


def plan_adapter_actions(
    adapter_names: list[str] | None,
    root: Path,
) -> tuple[list[dict], list[str], list[str]]:
    if not adapter_names:
        return [], [], []
    selected, errors = resolve_adapter_selection(adapter_names)
    if errors:
        return [], errors, []
    actions: list[dict] = []
    warnings: list[str] = []
    for cfg in selected:
        _plan_single_adapter(cfg, root, actions, warnings)
    return actions, [], warnings
