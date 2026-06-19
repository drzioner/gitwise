"""Base types and planning behavior for the provider registry."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from gitwise.i18n import t
from gitwise.setup_agents.state import _classify_path
from gitwise.setup_agents.types import ActionDict, StateDict


class AdapterFlags(TypedDict, total=False):
    """Optional flags that modify provider planning behavior."""

    no_symlinks: bool
    replace_claude_with_symlink: bool
    migrate_legacy_claude: bool
    frozen_time: bool
    no_git_files: bool
    core_claude_planned: bool


class AdapterContext(TypedDict):
    """Shared context passed to all adapters during planning."""

    state: StateDict
    canonical_doc_path: str
    global_skills: frozenset[str]
    supports_symlinks: bool
    gpg_ready: bool
    flags: AdapterFlags


class AdapterConfig:
    """Base configuration for a multi-agent adapter (name, paths, template directory)."""

    def __init__(
        self,
        *,
        name: str,
        display_name: str,
        config_paths: tuple[str, ...],
        template_paths: tuple[str, ...],
        template_dir: str,
    ) -> None:
        """Initialize adapter metadata. Does not read filesystem."""
        self.name = name
        self.display_name = display_name
        self.config_paths = config_paths
        self.template_paths = template_paths
        self.template_dir = template_dir

    def _read_template(self, template_name: str) -> str:
        """Read a template file from the adapter's share directory."""
        from gitwise._paths import share_dir

        template_dir_str = str(self.template_dir)
        relative = (
            template_dir_str.removeprefix("share/")
            if template_dir_str.startswith("share/")
            else template_dir_str
        )
        template_path = share_dir() / relative / template_name
        if not template_path.exists():
            raise FileNotFoundError(t("adapter_no_template", path=str(template_path)))
        return template_path.read_text(encoding="utf-8")

    def plan(self, root: Path, _context: AdapterContext) -> tuple[list[ActionDict], list[str]]:
        """Plan adapter config creation: create each config file that is absent, warn if it exists."""
        actions: list[ActionDict] = []
        warnings: list[str] = []
        for config_path, template_path in zip(self.config_paths, self.template_paths, strict=True):
            target_path = root / config_path
            state = _classify_path(target_path)
            if state == "absent":
                content = self._read_template(template_path)
                actions.append(
                    {
                        "action": "adapter-create",
                        "file": config_path,
                        "content": content,
                        "adapter": self.display_name,
                    }
                )
            else:
                warnings.append(t("adapter_exists", adapter=self.display_name, file=config_path))
        return actions, warnings
