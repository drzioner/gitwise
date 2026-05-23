"""Claude provider wrapper for staged migration from plan.py."""

import json
import os
import time
from pathlib import Path

from gitwise.i18n import t
from gitwise.setup_agents.plan_skills import _read_template, plan_global_skills
from gitwise.setup_agents.providers.base import AdapterConfig, AdapterContext
from gitwise.setup_agents.state import (
    _AGENTS_MD,
    _CLAUDE_MD,
    _files_equal,
    _gpg_ready,
    _has_marker,
)
from gitwise.setup_agents.types import ActionDict, StateDict


class ClaudeAdapter(AdapterConfig):
    def __init__(self) -> None:
        super().__init__(
            name="claude",
            display_name="Claude",
            config_paths=(),
            template_paths=(),
            template_dir="share/claude",
        )

    def plan_settings(self, root: Path) -> tuple[list[ActionDict], list[str]]:
        settings_path = root / ".claude" / "settings.json"
        settings_template: dict = json.loads(_read_template("settings.json.template"))
        if settings_path.exists():
            try:
                existing_settings: dict = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return [
                    {
                        "file": ".claude/settings.json",
                        "action": "create",
                        "data": settings_template,
                    }
                ], [t("invalid_json")]

            existing_deny: list = existing_settings.get("permissions", {}).get("deny", [])
            new_deny: list = settings_template.get("permissions", {}).get("deny", [])
            merged_deny = list(dict.fromkeys(existing_deny + new_deny))
            existing_settings.setdefault("permissions", {})["deny"] = merged_deny
            gpg_rules = [r for r in merged_deny if "gpgsign" in r or "no-gpg-sign" in r]
            warnings: list[str] = []
            if not gpg_rules:
                warnings.append(t("settings_sin_gpg_deny"))
            return [
                {
                    "file": ".claude/settings.json",
                    "action": "merge",
                    "data": existing_settings,
                }
            ], warnings

        return [
            {
                "file": ".claude/settings.json",
                "action": "create",
                "data": settings_template,
            }
        ], []

    def pointer_template(self) -> str:
        return t("conventions_heading") + t("conventions_pointer")

    def compute_backup_path(self, path: Path) -> Path:
        backup = path.with_suffix(".md.bak")
        if backup.exists():
            suffix = int(time.time())
            backup = path.parent / f"{path.stem}.md.bak.{suffix}"
        return backup

    def build_template(self, root: Path) -> str:
        raw = _read_template("CLAUDE.md.template")
        if _gpg_ready(root):
            return raw
        return (
            "\n".join(
                line
                for line in raw.splitlines()
                if "GPG" not in line and "gpg-sign" not in line.lower()
            )
            + "\n"
        )

    def bucket1_no_agents(
        self,
        state: StateDict,
        root: Path,
        template: str,
    ) -> tuple[int, list[ActionDict], list[str]]:
        c_state = state["c_state"]
        claude_md = root / _CLAUDE_MD
        if c_state == "absent":
            return 1, [{"file": _CLAUDE_MD, "action": "create", "content": template}], []
        if c_state in ("symlink_valid", "regular"):
            if _has_marker(claude_md):
                return (
                    1,
                    [
                        {
                            "file": _CLAUDE_MD,
                            "action": "skip",
                            "reason": t("already_contains_conventions"),
                        }
                    ],
                    [],
                )
            return 1, [{"file": _CLAUDE_MD, "action": "append", "content": template}], []
        return 1, [], []

    def bucket2_agents_no_claude(
        self,
        root: Path,
        supports_symlinks: bool,
        template: str,
    ) -> tuple[int, list[ActionDict], list[str]]:
        agents_actions: list[ActionDict] = []
        agents_md = root / _AGENTS_MD
        if not _has_marker(agents_md):
            agents_actions.append({"file": _AGENTS_MD, "action": "append", "content": template})
        if supports_symlinks:
            claude_actions: list[ActionDict] = [
                {"file": _CLAUDE_MD, "action": "symlink-create", "target_relative": _AGENTS_MD}
            ]
        else:
            claude_actions = [
                {"file": _CLAUDE_MD, "action": "create", "content": self.pointer_template()}
            ]
        return 2, agents_actions + claude_actions, []

    def bucket4_default(
        self,
        state: StateDict,
        claude_md: Path,
        agents_actions: list[ActionDict],
    ) -> tuple[int, list[ActionDict], list[str]]:
        c_state = state["c_state"]
        if c_state == "symlink_valid":
            try:
                link_target = os.readlink(claude_md)
            except OSError:
                link_target = ""
            return (
                4,
                agents_actions,
                [
                    t(
                        "claude_md_symlink_other",
                        file=_CLAUDE_MD,
                        existing=link_target,
                        expected=_AGENTS_MD,
                    )
                ],
            )
        if c_state == "regular":
            return 4, agents_actions, [t("claude_md_separate", c=_CLAUDE_MD, a=_AGENTS_MD)]
        return 5, [], []

    def bucket4_replace(
        self,
        agents_actions: list[ActionDict],
        claude_md: Path,
    ) -> tuple[int, list[ActionDict], list[str]]:
        backup_path = self.compute_backup_path(claude_md)
        return (
            4,
            agents_actions
            + [
                {
                    "file": _CLAUDE_MD,
                    "action": "claude-md-replace-with-symlink",
                    "target_relative": _AGENTS_MD,
                    "backup_path": str(backup_path),
                }
            ],
            [
                t(
                    "claude_md_replaced",
                    file=_CLAUDE_MD,
                    target=_AGENTS_MD,
                    backup=backup_path.name,
                )
            ],
        )

    def bucket3(
        self,
        state: StateDict,
        claude_md: Path,
        agents_md: Path,
        agents_actions: list[ActionDict],
    ) -> tuple[int, list[ActionDict], list[str]]:
        c_state = state["c_state"]
        if c_state == "symlink_valid":
            try:
                link_target = os.readlink(claude_md)
            except OSError:
                link_target = ""
            points_to_agents = link_target == _AGENTS_MD or Path(
                os.path.realpath(str(claude_md.parent / link_target))
            ) == Path(os.path.realpath(str(agents_md)))
            if points_to_agents:
                return (
                    3,
                    agents_actions
                    + [
                        {
                            "file": _CLAUDE_MD,
                            "action": "symlink-skip",
                            "reason": t("already_points_to_agents"),
                        }
                    ],
                    [],
                )
        if c_state == "regular" and _files_equal(claude_md, agents_md):
            return (
                3,
                agents_actions
                + [
                    {
                        "file": _CLAUDE_MD,
                        "action": "skip",
                        "reason": t("claude_md_identical_content"),
                    }
                ],
                [],
            )
        return self.bucket4_default(state, claude_md, agents_actions)

    def resolve_canonical_doc(
        self,
        root: Path,
        state: StateDict,
        *,
        no_symlinks: bool = False,
        replace_claude_with_symlink: bool = False,
    ) -> tuple[int, list[ActionDict], list[str]]:
        a_state = state["a_state"]
        c_state = state["c_state"]
        claude_md = root / _CLAUDE_MD
        agents_md = root / _AGENTS_MD
        supports_symlinks = state["supports_symlinks"] and not no_symlinks
        template = self.build_template(root)

        if a_state == "absent":
            return self.bucket1_no_agents(state, root, template)

        agents_actions: list[ActionDict] = []
        if not _has_marker(agents_md):
            agents_actions.append({"file": _AGENTS_MD, "action": "append", "content": template})

        if c_state == "absent":
            return self.bucket2_agents_no_claude(root, supports_symlinks, template)

        if c_state in ("symlink_valid", "regular"):
            if c_state == "regular" and replace_claude_with_symlink:
                return self.bucket4_replace(agents_actions, claude_md)
            return self.bucket3(state, claude_md, agents_md, agents_actions)

        return 5, [], []

    def plan_rules(self, root: Path) -> tuple[list[ActionDict], list[str]]:
        rule_path = root / ".claude" / "rules" / "gitwise.md"
        if rule_path.exists():
            return [
                {
                    "file": ".claude/rules/gitwise.md",
                    "action": "skip",
                    "reason": t("already_exists"),
                }
            ], []
        return [
            {
                "file": ".claude/rules/gitwise.md",
                "action": "create",
                "content": _read_template("rules/gitwise.md"),
            }
        ], []

    def plan_snapshot(self, *, frozen_time: bool = False) -> list[ActionDict]:
        return [
            {"file": ".claude/git-snapshot.md", "action": "generate", "frozen_time": frozen_time}
        ]

    def plan_global(
        self,
        home: Path,
        *,
        no_skills: bool = False,
    ) -> tuple[list[ActionDict], list[str], list[ActionDict]]:
        actions: list[ActionDict] = []
        warnings: list[str] = []

        settings_actions, settings_warnings = self.plan_settings(home)
        actions += settings_actions
        warnings += settings_warnings

        rules_actions, rules_warnings = self.plan_rules(home)
        actions += rules_actions
        warnings += rules_warnings

        if not no_skills:
            skills_actions, skills_warnings = plan_global_skills(home)
            actions += skills_actions
            warnings += skills_warnings

        return actions, warnings, []

    def plan(self, root: Path, context: AdapterContext) -> tuple[list[ActionDict], list[str]]:
        if self.name != "claude":
            return [], []
        if context["flags"].get("core_claude_planned", False):
            return [], []
        actions: list[ActionDict] = []
        warnings: list[str] = []

        settings_actions, settings_warnings = self.plan_settings(root)
        rules_actions, rules_warnings = self.plan_rules(root)

        actions += settings_actions
        actions += rules_actions
        actions += self.plan_snapshot(frozen_time=context["flags"].get("frozen_time", False))

        warnings += settings_warnings
        warnings += rules_warnings
        return actions, warnings


ADAPTER = ClaudeAdapter()
