"""Adapter registry: multi-agent tool support for setup-agents."""

import os
from pathlib import Path
from typing import Literal

from gitwise.i18n import t
from gitwise.setup_agents.adapters.aider import ADAPTER as AIDER
from gitwise.setup_agents.adapters.base import AdapterConfig, AdapterState
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

PathState = Literal["absent", "regular", "symlink_valid", "symlink_broken"]


def _classify_path(path: Path) -> PathState:
    if not path.exists() and not path.is_symlink():
        return "absent"
    if path.is_symlink():
        return "symlink_valid" if Path(os.path.realpath(str(path))).exists() else "symlink_broken"
    return "regular"


def list_adapters() -> list[str]:
    return sorted(ADAPTERS.keys())


def resolve_adapter_selection(
    names: list[str] | None,
) -> tuple[list[AdapterConfig], list[str]]:
    if not names:
        return [], []
    if "none" in names or "claude-only" in names:
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


def detect_adapter_state(cfg: AdapterConfig, root: Path) -> AdapterState:
    configs: dict[str, PathState] = {}
    has_gitwise: dict[str, bool] = {}
    for cp in cfg.config_paths:
        p = root / cp
        configs[cp] = _classify_path(p)
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="replace")
            has_gitwise[cp] = "gitwise" in content.lower()
        else:
            has_gitwise[cp] = False
    return AdapterState(name=cfg.name, configs=configs, has_gitwise=has_gitwise)


def _read_adapter_template(cfg: AdapterConfig, template_name: str) -> str:
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    template_path = project_root / cfg.template_dir / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Adapter template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def _plan_single_adapter(
    cfg: AdapterConfig, root: Path, actions: list[dict], warnings: list[str]
) -> None:
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
