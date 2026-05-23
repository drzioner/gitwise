"""Planning phase for setup-agents: action generation without side effects."""

from pathlib import Path

from gitwise.setup_agents.plan_gitfiles import (
    gitattributes_block_basic,
    gitattributes_block_extended,
    gitignore_block_basic,
    gitignore_block_extended,
    plan_managed_block,
)
from gitwise.setup_agents.plan_skills import (
    plan_skills,
)
from gitwise.setup_agents.providers import detect_global_skills
from gitwise.setup_agents.providers.claude import ADAPTER as CLAUDE_PROVIDER
from gitwise.setup_agents.state import (
    _detect_state,
)
from gitwise.setup_agents.types import StateDict


def _snapshot_file_for_state(*, has_agents_layout: bool) -> str:
    if has_agents_layout:
        return ".agents/git-snapshot.md"
    return ".claude/git-snapshot.md"


def _plan_settings_json(root: Path) -> tuple[list[dict], list[str]]:
    return CLAUDE_PROVIDER.plan_settings(root)


def _plan_rules(root: Path) -> tuple[list[dict], list[str]]:
    return CLAUDE_PROVIDER.plan_rules(root)


def _plan_actions_global(
    home: Path,
    no_skills: bool = False,
) -> tuple[list[dict], list[str], list[dict]]:
    return CLAUDE_PROVIDER.plan_global(home, no_skills=no_skills)


def _bucket1_no_agents(
    state: StateDict,
    root: Path,
    template: str,
) -> tuple[int, list[dict], list[str]]:
    return CLAUDE_PROVIDER.bucket1_no_agents(state, root, template)


def _bucket2_agents_no_claude(
    _state: StateDict,
    root: Path,
    supports_symlinks: bool,
    template: str,
) -> tuple[int, list[dict], list[str]]:
    return CLAUDE_PROVIDER.bucket2_agents_no_claude(root, supports_symlinks, template)


def _bucket3(
    state: StateDict,
    claude_md: Path,
    agents_md: Path,
    agents_actions: list[dict],
) -> tuple[int, list[dict], list[str]]:
    return CLAUDE_PROVIDER.bucket3(state, claude_md, agents_md, agents_actions)


def _bucket4_default(
    state: StateDict,
    claude_md: Path,
    agents_actions: list[dict],
) -> tuple[int, list[dict], list[str]]:
    return CLAUDE_PROVIDER.bucket4_default(state, claude_md, agents_actions)


def _bucket4_replace(
    agents_actions: list[dict],
    claude_md: Path,
) -> tuple[int, list[dict], list[str]]:
    return CLAUDE_PROVIDER.bucket4_replace(agents_actions, claude_md)


def _resolve_canonical_doc(
    root: Path,
    state: StateDict,
    no_symlinks: bool = False,
    replace_claude_with_symlink: bool = False,
    migrate_legacy_claude: bool = False,
) -> tuple[int, list[dict], list[str]]:
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
    no_git_files: bool = False,
    frozen_time: bool = False,
) -> tuple[list[dict], list[str], list[dict], int, StateDict]:
    state = _detect_state(root)
    if state["errors"]:
        err_actions: list[dict] = [
            {"file": "", "action": "error", "reason": r} for r in state["errors"]
        ]
        return [], [], err_actions, 5, state

    bucket, doc_actions, doc_warnings = _resolve_canonical_doc(
        root,
        state,
        no_symlinks=no_symlinks,
        replace_claude_with_symlink=replace_claude_with_symlink,
        migrate_legacy_claude=migrate_legacy_claude,
    )
    settings_actions, settings_warnings = _plan_settings_json(root)
    global_skills = detect_global_skills()
    has_agents_layout = state["agents_dir"] or migrate_legacy_claude
    skills_actions, skills_warnings = plan_skills(
        root,
        state,
        global_skills=global_skills,
        force_agents_layout=has_agents_layout,
        migrate_legacy_claude=migrate_legacy_claude,
    )
    rules_actions, rules_warnings = _plan_rules(root)

    has_agents_md = state["a_state"] != "absent"
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
    return actions, warnings, [], bucket, state
