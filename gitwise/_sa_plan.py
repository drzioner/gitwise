"""Planning phase for setup-agents: action generation without side effects."""

import json
import os
import time
from pathlib import Path

from ._sa_state import (
    _AGENTS_MD,
    _CLAUDE_MD,
    _classify_path,
    _detect_state,
    _files_equal,
    _gpg_ready,
    _has_marker,
)
from .i18n import t

_SHARE_DIR = Path(__file__).parent.parent / "share" / "claude"
_SKILLS: tuple[str, ...] = ("git-audit", "git-clean", "git-optimize")

_POINTER_TEMPLATE = "## Convenciones git para este proyecto\n\n@AGENTS.md\n"
_MANAGED_MARKER_START = "# >>> gitwise managed (do not edit between markers) >>>"
_MANAGED_MARKER_END = "# <<< gitwise managed <<<"


def _read_template(name: str) -> str:
    path = _SHARE_DIR / name
    if not path.exists():
        raise FileNotFoundError(t("template_not_found", path=str(path)))
    return path.read_text(encoding="utf-8")


def _gitignore_block_basic() -> str:
    lines = [
        _MANAGED_MARKER_START,
        "# Claude Code local/personal files (do not commit)",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
        "# Snapshot regenerated each gitwise run (timestamps change)",
        ".claude/git-snapshot.md",
        "# Backups from gitwise setup-agents",
        "*.bak",
        "CLAUDE.md.bak*",
        _MANAGED_MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def _gitignore_block_extended(has_agents_md: bool) -> str:
    lines = [
        _MANAGED_MARKER_START,
        "# Claude Code local/personal files (do not commit)",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
        "# Snapshot regenerated each gitwise run (timestamps change)",
        ".claude/git-snapshot.md",
        "# Backups from gitwise setup-agents",
        "*.bak",
        "CLAUDE.md.bak*",
    ]
    if has_agents_md:
        lines.append("AGENTS.md.bak*")
    lines.append(_MANAGED_MARKER_END)
    return "\n".join(lines) + "\n"


def _gitattributes_block_basic() -> str:
    lines = [
        _MANAGED_MARKER_START,
        "# Generated snapshot: use local version on merge",
        ".claude/git-snapshot.md merge=ours linguist-generated=true",
        "# Convention files: force LF for cross-platform consistency",
        "CLAUDE.md text=auto eol=lf",
        ".claude/skills/**/SKILL.md text=auto eol=lf",
        _MANAGED_MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def _gitattributes_block_extended(has_agents_md: bool, has_agents_dir: bool) -> str:
    lines = [
        _MANAGED_MARKER_START,
        "# Generated snapshot: use local version on merge",
        ".claude/git-snapshot.md merge=ours linguist-generated=true",
        "# Convention files: force LF for cross-platform consistency",
        "CLAUDE.md text=auto eol=lf",
    ]
    if has_agents_md:
        lines.append("AGENTS.md text=auto eol=lf")
    lines.append(".claude/skills/**/SKILL.md text=auto eol=lf")
    if has_agents_dir:
        lines.append(".agents/skills/**/SKILL.md text=auto eol=lf")
    lines.append(_MANAGED_MARKER_END)
    return "\n".join(lines) + "\n"


def _gitattributes_conflicts(existing_text: str, desired_block: str) -> list[str]:
    """Warns on .gitattributes entries outside the managed block that conflict
    (same path pattern, different attributes). Exact path-key match only —
    glob overlaps are not detected. Only scans content before the managed block."""
    block_start = existing_text.find(_MANAGED_MARKER_START)
    outside_text = existing_text[:block_start] if block_start != -1 else existing_text

    def _parse(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split(None, 1)
            if len(parts) > 1:
                result[parts[0]] = s
        return result

    outside = _parse(outside_text)
    block = _parse(desired_block)
    warnings: list[str] = []
    for pattern, block_line in block.items():
        if pattern in outside and outside[pattern] != block_line:
            warnings.append(
                t(
                    "gitattributes_conflict",
                    pattern=pattern,
                    existing=outside[pattern],
                    desired=block_line,
                )
            )
    return warnings


def _plan_managed_block(
    path: Path, desired_block: str, file_key: str
) -> tuple[list[dict], list[str]]:
    """Returns (actions, warnings) for idempotent managed block in path."""
    if not path.exists():
        return [
            {
                "file": file_key,
                "action": "managed-block-create",
                "content": desired_block,
                "_path": str(path),
            }
        ], []

    try:
        current = path.read_text(encoding="utf-8")
    except OSError:
        return [], []

    conflict_warnings = (
        _gitattributes_conflicts(current, desired_block) if file_key == ".gitattributes" else []
    )

    if _MANAGED_MARKER_START not in current:
        return [
            {
                "file": file_key,
                "action": "managed-block-create",
                "content": desired_block,
                "_path": str(path),
                "_append": True,
            }
        ], conflict_warnings

    start_idx = current.index(_MANAGED_MARKER_START)
    end_marker_idx = current.find(_MANAGED_MARKER_END, start_idx)
    if end_marker_idx == -1:
        return [], [t("managed_block_unclosed", file=file_key)] + conflict_warnings

    end_idx = end_marker_idx + len(_MANAGED_MARKER_END)
    existing_block = current[start_idx:end_idx]

    if existing_block.rstrip() == desired_block.rstrip():
        return [
            {"file": file_key, "action": "managed-block-skip", "_path": str(path)}
        ], conflict_warnings

    return [
        {
            "file": file_key,
            "action": "managed-block-replace",
            "content": desired_block,
            "_path": str(path),
            "_start_idx": start_idx,
            "_end_idx": end_idx,
        }
    ], conflict_warnings


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


def _plan_skills(
    root: Path,
    state: dict,
    global_skills: frozenset[str] = frozenset(),
) -> tuple[list[dict], list[str]]:
    """Plans per-skill symlinks when .agents/ exists, or regular dirs otherwise.

    global_skills: set of skill names already installed in ~/.claude/skills/.
    Skills in this set are skipped with a warning (user > project priority).
    """
    actions: list[dict] = []
    warnings: list[str] = []

    agents_skills_dir = root / ".agents" / "skills"
    claude_skills = root / ".claude" / "skills"
    skills_state = state["skills_state"]
    has_agents_dir = state["agents_dir"]

    if skills_state == "symlink_valid":
        for skill in _SKILLS:
            skill_file = f".claude/skills/{skill}/SKILL.md"
            if skill in global_skills:
                actions.append(
                    {"file": skill_file, "action": "skip", "reason": t("installed_globally")}
                )
            elif (claude_skills / skill / "SKILL.md").exists():
                actions.append(
                    {"file": skill_file, "action": "skip", "reason": t("already_exists")}
                )
            else:
                actions.append(
                    {
                        "file": skill_file,
                        "action": "create",
                        "content": _read_template(f"skills/{skill}/SKILL.md"),
                    }
                )
    else:
        for skill in _SKILLS:
            claude_skill = claude_skills / skill
            skill_file = f".claude/skills/{skill}/SKILL.md"
            c_skill_state = _classify_path(claude_skill)

            if has_agents_dir:
                agents_skill = agents_skills_dir / skill
                target_rel = os.path.relpath(str(agents_skill), str(claude_skill.parent))

                if c_skill_state == "absent":
                    if skill in global_skills:
                        warnings.append(t("skill_globally_available", skill=skill))
                    else:
                        if not agents_skill.exists():
                            actions.append({"file": f".agents/skills/{skill}", "action": "mkdir"})
                        actions.append(
                            {
                                "file": f".claude/skills/{skill}",
                                "action": "symlink-create",
                                "target_relative": target_rel,
                            }
                        )
                        actions.append(
                            {
                                "file": skill_file,
                                "action": "create",
                                "content": _read_template(f"skills/{skill}/SKILL.md"),
                            }
                        )
                elif c_skill_state == "symlink_valid":
                    try:
                        existing_target = os.readlink(str(claude_skill))
                    except OSError:
                        existing_target = ""
                    if existing_target == target_rel:
                        if (claude_skill / "SKILL.md").exists():
                            actions.append(
                                {
                                    "file": skill_file,
                                    "action": "skip",
                                    "reason": t("already_exists"),
                                }
                            )
                        else:
                            actions.append(
                                {
                                    "file": skill_file,
                                    "action": "create",
                                    "content": _read_template(f"skills/{skill}/SKILL.md"),
                                }
                            )
                    else:
                        warnings.append(
                            t(
                                "skill_symlink_diferente",
                                skill=skill,
                                existing=existing_target,
                                expected=target_rel,
                            )
                        )
                elif c_skill_state == "symlink_broken":
                    warnings.append(t("skill_symlink_broken", skill=skill))
                else:  # regular
                    warnings.append(t("skill_dir_regular_with_agents", skill=skill))
                    if (claude_skill / "SKILL.md").exists():
                        actions.append(
                            {"file": skill_file, "action": "skip", "reason": t("already_exists")}
                        )
                    else:
                        actions.append(
                            {
                                "file": skill_file,
                                "action": "create",
                                "content": _read_template(f"skills/{skill}/SKILL.md"),
                            }
                        )
            else:
                if skill in global_skills and not (claude_skill / "SKILL.md").exists():
                    warnings.append(t("skill_globally_available", skill=skill))
                    actions.append(
                        {
                            "file": skill_file,
                            "action": "skip",
                            "reason": t("installed_globally"),
                        }
                    )
                elif (claude_skill / "SKILL.md").exists():
                    actions.append(
                        {"file": skill_file, "action": "skip", "reason": t("already_exists")}
                    )
                else:
                    actions.append(
                        {
                            "file": skill_file,
                            "action": "create",
                            "content": _read_template(f"skills/{skill}/SKILL.md"),
                        }
                    )

    legacy_dir = root / ".claude" / "commands"
    for skill in _SKILLS:
        if (legacy_dir / f"{skill}.md").exists():
            warnings.append(t("legacy_commands", skill=skill))

    return actions, warnings


def _plan_rules(root: Path) -> tuple[list[dict], list[str]]:
    """Plans gitwise rule file in .claude/rules/."""
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


def _plan_global_skills(home: Path) -> tuple[list[dict], list[str]]:
    """Plans skills for ~/.claude/skills/. Mirrors local per-skill symlink logic when ~/.agents/ exists."""
    actions: list[dict] = []
    warnings: list[str] = []

    agents_dir = home / ".agents"
    has_agents_dir = agents_dir.is_dir() and not agents_dir.is_symlink()
    agents_skills_dir = home / ".agents" / "skills"
    claude_skills = home / ".claude" / "skills"
    claude_skills_state = _classify_path(claude_skills)

    if claude_skills_state == "symlink_valid":
        for skill in _SKILLS:
            skill_file = f".claude/skills/{skill}/SKILL.md"
            if (claude_skills / skill / "SKILL.md").exists():
                actions.append(
                    {"file": skill_file, "action": "skip", "reason": t("already_exists")}
                )
            else:
                actions.append(
                    {
                        "file": skill_file,
                        "action": "create",
                        "content": _read_template(f"skills/{skill}/SKILL.md"),
                    }
                )
    else:
        for skill in _SKILLS:
            claude_skill = claude_skills / skill
            skill_file = f".claude/skills/{skill}/SKILL.md"
            c_skill_state = _classify_path(claude_skill)

            if has_agents_dir:
                agents_skill = agents_skills_dir / skill
                target_rel = os.path.relpath(str(agents_skill), str(claude_skill.parent))

                if c_skill_state == "absent":
                    if not agents_skill.exists():
                        actions.append({"file": f".agents/skills/{skill}", "action": "mkdir"})
                    actions.append(
                        {
                            "file": f".claude/skills/{skill}",
                            "action": "symlink-create",
                            "target_relative": target_rel,
                        }
                    )
                    actions.append(
                        {
                            "file": skill_file,
                            "action": "create",
                            "content": _read_template(f"skills/{skill}/SKILL.md"),
                        }
                    )
                elif c_skill_state == "symlink_valid":
                    try:
                        existing_target = os.readlink(str(claude_skill))
                    except OSError:
                        existing_target = ""
                    if existing_target == target_rel:
                        if (claude_skill / "SKILL.md").exists():
                            actions.append(
                                {
                                    "file": skill_file,
                                    "action": "skip",
                                    "reason": t("already_exists"),
                                }
                            )
                        else:
                            actions.append(
                                {
                                    "file": skill_file,
                                    "action": "create",
                                    "content": _read_template(f"skills/{skill}/SKILL.md"),
                                }
                            )
                    else:
                        warnings.append(
                            t(
                                "global_skill_symlink_diferente",
                                skill=skill,
                                existing=existing_target,
                                expected=target_rel,
                            )
                        )
                elif c_skill_state == "symlink_broken":
                    warnings.append(t("global_skill_symlink_broken", skill=skill))
                else:  # regular dir — auto-migrate to .agents/ since ~/.agents/ is present
                    if agents_skill.exists():
                        warnings.append(t("skill_conflict_dir_agents", skill=skill))
                        actions.append(
                            {
                                "file": skill_file,
                                "action": "skip",
                                "reason": t("conflict_dir_agents"),
                            }
                        )
                    else:
                        actions.append(
                            {
                                "file": f".claude/skills/{skill}",
                                "action": "skill-migrate-to-agents",
                                "target_relative": target_rel,
                                "agents_skill": str(agents_skill),
                            }
                        )
            else:
                if (claude_skill / "SKILL.md").exists():
                    actions.append(
                        {"file": skill_file, "action": "skip", "reason": t("already_exists")}
                    )
                else:
                    actions.append(
                        {
                            "file": skill_file,
                            "action": "create",
                            "content": _read_template(f"skills/{skill}/SKILL.md"),
                        }
                    )

    return actions, warnings


def _plan_actions_global(
    home: Path,
    no_skills: bool = False,
) -> tuple[list[dict], list[str], list[dict]]:
    """Plans ~/.claude/ global artifacts. home = Path.home(). No git repo required."""
    actions: list[dict] = []
    warnings: list[str] = []

    s_actions, s_warnings = _plan_settings_json(home)
    actions += s_actions
    warnings += s_warnings

    r_actions, r_warnings = _plan_rules(home)
    actions += r_actions
    warnings += r_warnings

    if not no_skills:
        sk_actions, sk_warnings = _plan_global_skills(home)
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
    """Returns (bucket, actions, warnings) per the 5-bucket model."""
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
                {"file": _CLAUDE_MD, "action": "create", "content": _POINTER_TEMPLATE}
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
    """Returns (actions, warnings, errors, bucket, state). Non-empty errors blocks execution."""
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
    skills_actions, skills_warnings = _plan_skills(root, state, global_skills=global_skills)
    rules_actions, rules_warnings = _plan_rules(root)

    has_agents_md = state["a_state"] != "absent"
    has_agents_dir = state["agents_dir"]

    git_file_actions: list[dict] = []
    git_file_warnings: list[str] = []
    if not no_git_files and bucket != 5:
        if has_agents_md or has_agents_dir:
            gi_block = _gitignore_block_extended(has_agents_md)
            ga_block = _gitattributes_block_extended(has_agents_md, has_agents_dir)
        else:
            gi_block = _gitignore_block_basic()
            ga_block = _gitattributes_block_basic()

        gi_actions, gi_warnings = _plan_managed_block(root / ".gitignore", gi_block, ".gitignore")
        ga_actions, ga_warnings = _plan_managed_block(
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
