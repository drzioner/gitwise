"""Provider registry: multi-agent tool support for setup-agents."""

from pathlib import Path

from gitwise.i18n import t
from gitwise.setup_agents.plan_skills import _SKILLS
from gitwise.setup_agents.providers.aider import ADAPTER as AIDER
from gitwise.setup_agents.providers.base import AdapterConfig, AdapterContext
from gitwise.setup_agents.providers.claude import ADAPTER as CLAUDE
from gitwise.setup_agents.providers.codex import ADAPTER as CODEX
from gitwise.setup_agents.providers.continue_adapter import ADAPTER as CONTINUE
from gitwise.setup_agents.providers.cursor import ADAPTER as CURSOR
from gitwise.setup_agents.providers.opencode import ADAPTER as OPENCODE
from gitwise.setup_agents.providers.pi import ADAPTER as PI
from gitwise.setup_agents.state import _AGENTS_MD, _detect_state, _gpg_ready

ADAPTERS: dict[str, AdapterConfig] = {
    "claude": CLAUDE,
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


def plan_adapter_actions(
    adapter_names: list[str] | None,
    root: Path,
    context: AdapterContext | None = None,
) -> tuple[list[dict], list[str], list[str]]:
    if not adapter_names:
        return [], [], []
    selected, errors = resolve_adapter_selection(adapter_names)
    if errors:
        return [], errors, []
    if context is None:
        state = _detect_state(root)
        home = Path.home()
        context = {
            "state": state,
            "canonical_doc_path": _AGENTS_MD,
            "global_skills": frozenset(
                s for s in _SKILLS if (home / ".claude" / "skills" / s / "SKILL.md").exists()
            ),
            "supports_symlinks": state["supports_symlinks"],
            "gpg_ready": _gpg_ready(root),
            "flags": {},
        }
    actions: list[dict] = []
    warnings: list[str] = []
    for cfg in selected:
        adapter_actions, adapter_warnings = cfg.plan(root, context)
        actions.extend(adapter_actions)
        warnings.extend(adapter_warnings)
    return actions, [], warnings
