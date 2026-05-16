"""Unified skills planning for setup-agents (local + global)."""

import os
from pathlib import Path

from ._sa_state import _classify_path
from .i18n import t

_SHARE_DIR = Path(__file__).parent.parent / "share" / "claude"
_SKILLS: tuple[str, ...] = ("git-audit", "git-clean", "git-optimize")


def _read_template(name: str) -> str:
    path = _SHARE_DIR / name
    if not path.exists():
        raise FileNotFoundError(t("template_not_found", path=str(path)))
    return path.read_text(encoding="utf-8")


def _plan_single_skill(
    *,
    skill: str,
    root: Path,
    has_agents_dir: bool,
    global_skills: frozenset[str],
    check_global_available: bool,
    symlink_mismatch_key: str,
    symlink_broken_key: str,
    dir_regular_with_agents_key: str,
) -> tuple[list[dict], list[str]]:
    actions: list[dict] = []
    warnings: list[str] = []

    agents_skills_dir = root / ".agents" / "skills"
    claude_skills = root / ".claude" / "skills"
    claude_skill = claude_skills / skill
    skill_file = f".claude/skills/{skill}/SKILL.md"
    c_skill_state = _classify_path(claude_skill)

    if has_agents_dir:
        agents_skill = agents_skills_dir / skill
        target_rel = os.path.relpath(str(agents_skill), str(claude_skill.parent))

        if c_skill_state == "absent":
            if skill in global_skills:
                if check_global_available:
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
                warnings.append(
                    t(
                        symlink_mismatch_key,
                        skill=skill,
                        existing=existing_target,
                        expected=target_rel,
                    )
                )
        elif c_skill_state == "symlink_broken":
            warnings.append(t(symlink_broken_key, skill=skill))
        else:
            if check_global_available and agents_skill.exists():
                warnings.append(t("skill_conflict_dir_agents", skill=skill))
                actions.append(
                    {"file": skill_file, "action": "skip", "reason": t("conflict_dir_agents")}
                )
            elif check_global_available and not agents_skill.exists():
                actions.append(
                    {
                        "file": f".claude/skills/{skill}",
                        "action": "skill-migrate-to-agents",
                        "target_relative": target_rel,
                        "agents_skill": str(agents_skill),
                    }
                )
            else:
                warnings.append(t(dir_regular_with_agents_key, skill=skill))
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
                {"file": skill_file, "action": "skip", "reason": t("installed_globally")}
            )
        elif (claude_skill / "SKILL.md").exists():
            actions.append({"file": skill_file, "action": "skip", "reason": t("already_exists")})
        else:
            actions.append(
                {
                    "file": skill_file,
                    "action": "create",
                    "content": _read_template(f"skills/{skill}/SKILL.md"),
                }
            )

    return actions, warnings


def plan_skills(
    root: Path,
    state: dict,
    global_skills: frozenset[str] = frozenset(),
) -> tuple[list[dict], list[str]]:
    actions: list[dict] = []
    warnings: list[str] = []

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
            sk_actions, sk_warnings = _plan_single_skill(
                skill=skill,
                root=root,
                has_agents_dir=has_agents_dir,
                global_skills=global_skills,
                check_global_available=False,
                symlink_mismatch_key="skill_symlink_diferente",
                symlink_broken_key="skill_symlink_broken",
                dir_regular_with_agents_key="skill_dir_regular_with_agents",
            )
            actions += sk_actions
            warnings += sk_warnings

    legacy_dir = root / ".claude" / "commands"
    for skill in _SKILLS:
        if (legacy_dir / f"{skill}.md").exists():
            warnings.append(t("legacy_commands", skill=skill))

    return actions, warnings


def plan_global_skills(home: Path) -> tuple[list[dict], list[str]]:
    actions: list[dict] = []
    warnings: list[str] = []

    agents_dir = home / ".agents"
    has_agents_dir = agents_dir.is_dir() and not agents_dir.is_symlink()
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
            sk_actions, sk_warnings = _plan_single_skill(
                skill=skill,
                root=home,
                has_agents_dir=has_agents_dir,
                global_skills=frozenset(),
                check_global_available=True,
                symlink_mismatch_key="global_skill_symlink_diferente",
                symlink_broken_key="global_skill_symlink_broken",
                dir_regular_with_agents_key="skill_dir_regular_with_agents",
            )
            actions += sk_actions
            warnings += sk_warnings

    return actions, warnings
