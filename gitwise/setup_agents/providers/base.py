"""Base types and planning behavior for the provider registry."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from gitwise.i18n import t
from gitwise.setup_agents.state import _classify_path
from gitwise.setup_agents.types import ActionDict, StateDict


class AdapterFlags(TypedDict, total=False):
    no_symlinks: bool
    replace_claude_with_symlink: bool
    migrate_legacy_claude: bool
    frozen_time: bool
    no_git_files: bool
    core_claude_planned: bool


class AdapterContext(TypedDict):
    state: StateDict
    canonical_doc_path: str
    global_skills: frozenset[str]
    supports_symlinks: bool
    gpg_ready: bool
    flags: AdapterFlags


class AdapterConfig:
    def __init__(
        self,
        *,
        name: str,
        display_name: str,
        config_paths: tuple[str, ...],
        template_paths: tuple[str, ...],
        template_dir: str,
    ) -> None:
        self.name = name
        self.display_name = display_name
        self.config_paths = config_paths
        self.template_paths = template_paths
        self.template_dir = template_dir

    def _read_template(self, template_name: str) -> str:
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        template_path = project_root / self.template_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(t("adapter_no_template", path=str(template_path)))
        return template_path.read_text(encoding="utf-8")

    def plan(self, root: Path, _context: AdapterContext) -> tuple[list[ActionDict], list[str]]:
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
