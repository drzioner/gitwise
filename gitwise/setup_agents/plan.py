"""Planning phase for setup-agents: action generation without side effects."""

from pathlib import Path

from gitwise.i18n import t
from gitwise.setup_agents.plan_gitfiles import (
    gitattributes_block_basic,
    gitattributes_block_extended,
    gitignore_block_basic,
    gitignore_block_extended,
    plan_managed_block,
)
from gitwise.setup_agents.plan_skills import (
    _SKILLS,
    _read_skill_template,
    plan_skills,
)
from gitwise.setup_agents.providers import detect_global_skills
from gitwise.setup_agents.providers.claude import ADAPTER as CLAUDE_PROVIDER
from gitwise.setup_agents.state import (
    _detect_state,
)
from gitwise.setup_agents.types import StateDict


def _snapshot_file_for_state(*, has_agents_layout: bool) -> str:
    """Return the snapshot file path based on whether agents layout is active."""
    if has_agents_layout:
        return ".agents/git-snapshot.md"
    return ".claude/git-snapshot.md"


def _is_clean_repo_for_canonical_default(
    *,
    state: StateDict,
    migrate_legacy_claude: bool,
    force_claude_core: bool,
) -> bool:
    """Return True when the repo has no existing convention docs and no migration override."""
    if migrate_legacy_claude or force_claude_core:
        return False
    return state["a_state"] == "absent" and state["c_state"] == "absent"


def _plan_canonical_skills(root: Path) -> list[dict]:
    """Plan creation of canonical .agents/skills/ entries for the three built-in gitwise skills."""
    actions: list[dict] = []
    for skill in _SKILLS:
        skill_dir = root / ".agents" / "skills" / skill
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.exists():
            actions.append({"file": f".agents/skills/{skill}", "action": "mkdir"})
        if skill_file.exists():
            actions.append(
                {
                    "file": f".agents/skills/{skill}/SKILL.md",
                    "action": "skip",
                    "reason": t("already_exists"),
                }
            )
        else:
            actions.append(
                {
                    "file": f".agents/skills/{skill}/SKILL.md",
                    "action": "create",
                    "content": _read_skill_template(skill),
                }
            )
    return actions


def _legacy_skill_warnings(root: Path) -> list[str]:
    """Warn about legacy .claude/commands/*.md files that shadow built-in skills."""
    warnings: list[str] = []
    legacy_dir = root / ".claude" / "commands"
    for skill in _SKILLS:
        if (legacy_dir / f"{skill}.md").exists():
            warnings.append(t("legacy_commands", skill=skill))
    return warnings


def _plan_settings_json(root: Path) -> tuple[list[dict], list[str]]:
    """Delegate settings.json planning to the Claude provider."""
    return CLAUDE_PROVIDER.plan_settings(root)


def _plan_rules(root: Path) -> tuple[list[dict], list[str]]:
    """Delegate rules planning to the Claude provider."""
    return CLAUDE_PROVIDER.plan_rules(root)


def _plan_actions_global(
    home: Path,
    no_skills: bool = False,
) -> tuple[list[dict], list[str], list[dict]]:
    """Delegate global planning (settings, rules, skills) to the Claude provider."""
    return CLAUDE_PROVIDER.plan_global(home, no_skills=no_skills)


def _bucket1_no_agents(
    state: StateDict,
    root: Path,
    template: str,
) -> tuple[int, list[dict], list[str]]:
    """Bucket 1: no AGENTS.md exists; create or append CLAUDE.md."""
    return CLAUDE_PROVIDER.bucket1_no_agents(state, root, template)


def _bucket2_agents_no_claude(
    _state: StateDict,
    root: Path,
    supports_symlinks: bool,
    template: str,
) -> tuple[int, list[dict], list[str]]:
    """Bucket 2: AGENTS.md exists but no CLAUDE.md; append + symlink or pointer."""
    return CLAUDE_PROVIDER.bucket2_agents_no_claude(root, supports_symlinks, template)


def _bucket3(
    state: StateDict,
    claude_md: Path,
    agents_md: Path,
    agents_actions: list[dict],
) -> tuple[int, list[dict], list[str]]:
    """Bucket 3: both docs exist; verify CLAUDE.md is symlink or identical to AGENTS.md."""
    return CLAUDE_PROVIDER.bucket3(state, claude_md, agents_md, agents_actions)


def _bucket4_default(
    state: StateDict,
    claude_md: Path,
    agents_actions: list[dict],
) -> tuple[int, list[dict], list[str]]:
    """Bucket 4 default: CLAUDE.md diverges from AGENTS.md; keep both with a warning."""
    return CLAUDE_PROVIDER.bucket4_default(state, claude_md, agents_actions)


def _bucket4_replace(
    agents_actions: list[dict],
    claude_md: Path,
) -> tuple[int, list[dict], list[str]]:
    """Bucket 4 replace: back up CLAUDE.md and replace it with a symlink to AGENTS.md."""
    return CLAUDE_PROVIDER.bucket4_replace(agents_actions, claude_md)


def _resolve_canonical_doc(
    root: Path,
    state: StateDict,
    no_symlinks: bool = False,
    replace_claude_with_symlink: bool = False,
    migrate_legacy_claude: bool = False,
) -> tuple[int, list[dict], list[str]]:
    """Route to the correct bucket based on the 5-bucket model (AGENTS.md + CLAUDE.md states)."""
    return CLAUDE_PROVIDER.resolve_canonical_doc(
        root,
        state,
        no_symlinks=no_symlinks,
        replace_claude_with_symlink=replace_claude_with_symlink,
        migrate_legacy_claude=migrate_legacy_claude,
    )


def _plan_actions(
    root: Path,
    no_symlinks: bool = False,
    replace_claude_with_symlink: bool = False,
    migrate_legacy_claude: bool = False,
    force_claude_core: bool = False,
    no_git_files: bool = False,
    frozen_time: bool = False,
) -> tuple[list[dict], list[str], list[dict], int, StateDict]:
    """Build the full plan for a local setup-agents run (docs, settings, skills, rules, gitfiles, snapshot).

    Returns (actions, warnings, errors, bucket, state).
    """
    state = _detect_state(root)
    if state["errors"]:
        err_actions: list[dict] = [
            {"file": "", "action": "error", "reason": r} for r in state["errors"]
        ]
        return [], [], err_actions, 5, state

    canonical_clean = _is_clean_repo_for_canonical_default(
        state=state,
        migrate_legacy_claude=migrate_legacy_claude,
        force_claude_core=force_claude_core,
    )

    global_skills = detect_global_skills()

    if canonical_clean:
        bucket = 1
        doc_actions = [
            {
                "file": "AGENTS.md",
                "action": "create",
                "content": CLAUDE_PROVIDER.build_template(root),
            }
        ]
        doc_warnings: list[str] = []
        settings_actions: list[dict] = []
        settings_warnings: list[str] = []
        skills_actions = _plan_canonical_skills(root)
        skills_warnings = [t("skill_globally_available", skill=skill) for skill in global_skills]
        skills_warnings += _legacy_skill_warnings(root)
        rules_actions: list[dict] = []
        rules_warnings: list[str] = []
        has_agents_layout = True
    else:
        bucket, doc_actions, doc_warnings = _resolve_canonical_doc(
            root,
            state,
            no_symlinks=no_symlinks,
            replace_claude_with_symlink=replace_claude_with_symlink,
            migrate_legacy_claude=migrate_legacy_claude,
        )
        settings_actions, settings_warnings = _plan_settings_json(root)
        has_agents_layout = state["agents_dir"] or migrate_legacy_claude
        skills_actions, skills_warnings = plan_skills(
            root,
            state,
            global_skills=global_skills,
            force_agents_layout=has_agents_layout,
        )
        rules_actions, rules_warnings = _plan_rules(root)

    has_agents_md = state["a_state"] != "absent" or canonical_clean
    has_agents_dir = has_agents_layout

    git_file_actions: list[dict] = []
    git_file_warnings: list[str] = []
    if not no_git_files and bucket != 5:
        if has_agents_md or has_agents_dir:
            gi_block = gitignore_block_extended(has_agents_md, has_agents_dir=has_agents_dir)
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
        + [
            {
                "file": _snapshot_file_for_state(has_agents_layout=has_agents_layout),
                "action": "generate",
                "frozen_time": frozen_time,
            }
        ]
    )
    warnings = (
        doc_warnings
        + settings_warnings
        + skills_warnings
        + rules_warnings
        + git_file_warnings
        + state["rules_warnings"]
    )
    if migrate_legacy_claude:
        warnings.append(t("legacy_migration_mode"))
    return actions, warnings, [], bucket, state
