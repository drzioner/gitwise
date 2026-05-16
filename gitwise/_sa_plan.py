"""Planning phase for setup-agents: action generation without side effects."""

import json
import os
import time
from pathlib import Path

from ._sa_plan_gitfiles import (
    gitattributes_block_basic,
    gitattributes_block_extended,
    gitignore_block_basic,
    gitignore_block_extended,
    plan_managed_block,
)
from ._sa_plan_skills import (
    _SKILLS,
    _read_template,
    plan_global_skills,
    plan_skills,
)
from ._sa_state import (
    _AGENTS_MD,
    _CLAUDE_MD,
    _detect_state,
    _files_equal,
    _gpg_ready,
    _has_marker,
)
from .i18n import t


def _pointer_template() -> str:
    return t("conventions_heading") + t("conventions_pointer")


def _plan_settings_json(root: Path) -> tuple[list[dict], list[str]]:
    settings_path = root / ".claude" / "settings.json"
    settings_template: dict = json.loads(_read_template("settings.json.template"))
    if settings_path.exists():
        try:
            existing_settings: dict = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [
                {"file": ".claude/settings.json", "action": "create", "data": settings_template}
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
            {"file": ".claude/settings.json", "action": "merge", "data": existing_settings}
        ], warnings
    return [{"file": ".claude/settings.json", "action": "create", "data": settings_template}], []


def _plan_rules(root: Path) -> tuple[list[dict], list[str]]:
    rule_path = root / ".claude" / "rules" / "gitwise.md"
    if rule_path.exists():
        return [
            {"file": ".claude/rules/gitwise.md", "action": "skip", "reason": t("already_exists")}
        ], []
    return [
        {
            "file": ".claude/rules/gitwise.md",
            "action": "create",
            "content": _read_template("rules/gitwise.md"),
        }
    ], []


def _plan_actions_global(
    home: Path,
    no_skills: bool = False,
) -> tuple[list[dict], list[str], list[dict]]:
    actions: list[dict] = []
    warnings: list[str] = []

    s_actions, s_warnings = _plan_settings_json(home)
    actions += s_actions
    warnings += s_warnings

    r_actions, r_warnings = _plan_rules(home)
    actions += r_actions
    warnings += r_warnings

    if not no_skills:
        sk_actions, sk_warnings = plan_global_skills(home)
        actions += sk_actions
        warnings += sk_warnings

    return actions, warnings, []


def _compute_backup_path(path: Path) -> Path:
    backup = path.with_suffix(".md.bak")
    if backup.exists():
        backup = path.parent / f"{path.stem}.md.bak.{int(time.time())}"
    return backup


def _resolve_canonical_doc(
    root: Path,
    state: dict,
    no_symlinks: bool = False,
    replace_claude_with_symlink: bool = False,
) -> tuple[int, list[dict], list[str]]:
    a_state = state["a_state"]
    c_state = state["c_state"]
    agents_md = root / _AGENTS_MD
    claude_md = root / _CLAUDE_MD
    supports_symlinks = state["supports_symlinks"] and not no_symlinks

    gpg = _gpg_ready(root)

    def _template() -> str:
        raw = _read_template("CLAUDE.md.template")
        if gpg:
            return raw
        return (
            "\n".join(
                line
                for line in raw.splitlines()
                if "GPG" not in line and "gpg-sign" not in line.lower()
            )
            + "\n"
        )

    if a_state == "absent":
        content = _template()
        if c_state == "absent":
            return 1, [{"file": _CLAUDE_MD, "action": "create", "content": content}], []
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
            return 1, [{"file": _CLAUDE_MD, "action": "append", "content": content}], []
        return 1, [], []

    agents_actions: list[dict] = []
    if not _has_marker(agents_md):
        agents_actions.append({"file": _AGENTS_MD, "action": "append", "content": _template()})

    if c_state == "absent":
        if supports_symlinks:
            claude_actions: list[dict] = [
                {"file": _CLAUDE_MD, "action": "symlink-create", "target_relative": _AGENTS_MD}
            ]
        else:
            claude_actions = [
                {"file": _CLAUDE_MD, "action": "create", "content": _pointer_template()}
            ]
        return 2, agents_actions + claude_actions, []

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
        return (
            4,
            agents_actions,
            [
                t(
                    "claude_md_symlink_otro",
                    file=_CLAUDE_MD,
                    existing=link_target,
                    expected=_AGENTS_MD,
                )
            ],
        )

    if c_state == "regular":
        if replace_claude_with_symlink:
            backup_path = _compute_backup_path(claude_md)
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
                        "claude_md_reemplazado",
                        file=_CLAUDE_MD,
                        target=_AGENTS_MD,
                        backup=backup_path.name,
                    )
                ],
            )

        if _files_equal(claude_md, agents_md):
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

        return (
            4,
            agents_actions,
            [t("claude_md_separate", c=_CLAUDE_MD, a=_AGENTS_MD)],
        )

    return 5, [], []


def _plan_actions(
    root: Path,
    no_symlinks: bool = False,
    replace_claude_with_symlink: bool = False,
    no_git_files: bool = False,
    frozen_time: bool = False,
) -> tuple[list[dict], list[str], list[dict], int, dict]:
    state = _detect_state(root)
    if state["errors"]:
        err_actions = [{"file": "", "action": "error", "reason": r} for r in state["errors"]]
        return [], [], err_actions, 5, state

    bucket, doc_actions, doc_warnings = _resolve_canonical_doc(
        root,
        state,
        no_symlinks=no_symlinks,
        replace_claude_with_symlink=replace_claude_with_symlink,
    )
    settings_actions, settings_warnings = _plan_settings_json(root)
    home = Path.home()
    global_skills = frozenset(
        s for s in _SKILLS if (home / ".claude" / "skills" / s / "SKILL.md").exists()
    )
    skills_actions, skills_warnings = plan_skills(root, state, global_skills=global_skills)
    rules_actions, rules_warnings = _plan_rules(root)

    has_agents_md = state["a_state"] != "absent"
    has_agents_dir = state["agents_dir"]

    git_file_actions: list[dict] = []
    git_file_warnings: list[str] = []
    if not no_git_files and bucket != 5:
        if has_agents_md or has_agents_dir:
            gi_block = gitignore_block_extended(has_agents_md)
            ga_block = gitattributes_block_extended(has_agents_md, has_agents_dir)
        else:
            gi_block = gitignore_block_basic()
            ga_block = gitattributes_block_basic()

        gi_actions, gi_warnings = plan_managed_block(root / ".gitignore", gi_block, ".gitignore")
        ga_actions, ga_warnings = plan_managed_block(
            root / ".gitattributes", ga_block, ".gitattributes"
        )
        git_file_actions = gi_actions + ga_actions
        git_file_warnings = gi_warnings + ga_warnings

    actions = (
        doc_actions
        + settings_actions
        + skills_actions
        + rules_actions
        + git_file_actions
        + [{"file": ".claude/git-snapshot.md", "action": "generate", "frozen_time": frozen_time}]
    )
    warnings = (
        doc_warnings
        + settings_warnings
        + skills_warnings
        + rules_warnings
        + git_file_warnings
        + state["rules_warnings"]
    )
    return actions, warnings, [], bucket, state
