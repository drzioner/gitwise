"""JSON output formatting for setup-agents."""

from pathlib import Path

from gitwise.setup_agents.types import ActionDict, StateDict, build_action_summary
from gitwise.utils.json_envelope import ENVELOPE_VERSION, error_envelope, ok_envelope

# Kept as aliases so callers that imported these keep working; setup-agents now
# emits the same v3 envelope as every other command, so there is no separate
# schema version to track.
_SETUP_AGENTS_SCHEMA_VERSION = ENVELOPE_VERSION
_SETUP_AGENTS_SCHEMA_COMPAT = [ENVELOPE_VERSION]


def _action_summaries(actions: list[ActionDict]) -> list[dict[str, str]]:
    """Extract a lightweight (file, action) summary from each action dict."""
    return [{"file": a["file"], "action": a["action"]} for a in actions]


def _canonical_layout_local(state: StateDict) -> str:
    """Determine the canonical layout label based on state alone."""
    if state["agents_dir"]:
        return "agents_dir"
    if state["a_state"] != "absent":
        return "agents_md"
    return "claude_only"


def _canonical_layout_local_with_actions(
    *,
    state: StateDict,
    actions: list[ActionDict],
    migrate_legacy_claude: bool,
) -> str:
    """Determine the canonical layout label considering both state and planned actions."""
    if migrate_legacy_claude:
        return "agents_dir"
    if any(a.get("file") == "AGENTS.md" for a in actions):
        return "agents_md"
    if any(str(a.get("file", "")).startswith(".agents/") for a in actions):
        return "agents_dir"
    return _canonical_layout_local(state)


def _canonical_layout_global(*, has_agents_dir: bool) -> str:
    """Determine the canonical layout label for global mode."""
    if has_agents_dir:
        return "agents_dir"
    return "claude_only"


def format_json_output_global(
    *,
    home: Path,
    actions: list[ActionDict],
    warnings: list[str],
    has_agents_dir: bool,
    dry_run: bool = False,
) -> dict[str, object]:
    """Build the JSON output dict for a successful global setup-agents run."""
    return ok_envelope(
        "setup-agents",
        data={
            "dry_run": dry_run,
            "root": str(home / ".claude"),
            "mode": "global",
            "canonical_layout": _canonical_layout_global(has_agents_dir=has_agents_dir),
            "actions": _action_summaries(actions),
            "warnings": warnings,
            "summary": build_action_summary(actions),
        },
    )


def format_json_output_global_error(
    *,
    home: Path,
    warnings: list[str],
    errors: list[str],
    has_agents_dir: bool,
    dry_run: bool = False,
) -> dict[str, object]:
    """Build the JSON output dict for a failed global setup-agents run."""
    return error_envelope(
        "setup-agents",
        error=errors[0] if errors else "setup-agents failed",
        code="setup_agents_failed",
        extra_errors=[
            {"code": "setup_agents_failed", "message": message} for message in errors[1:]
        ],
        data={
            "dry_run": dry_run,
            "root": str(home / ".claude"),
            "mode": "global",
            "canonical_layout": _canonical_layout_global(has_agents_dir=has_agents_dir),
            "actions": [],
            "warnings": warnings,
            "summary": {
                "created": 0,
                "appended": 0,
                "symlinked": 0,
                "skipped": 0,
                "errored": len(errors),
            },
        },
    )


def format_json_output_local_error(
    *,
    root: Path,
    dry_run: bool = False,
    plan_errors: list[dict[str, str]],
    all_warnings: list[str],
    migrate_legacy_claude: bool = False,
) -> dict[str, object]:
    """Build the JSON output dict for a failed local setup-agents run."""
    reasons = [e["reason"] for e in plan_errors]
    return error_envelope(
        "setup-agents",
        error=reasons[0] if reasons else "setup-agents failed",
        code="setup_agents_plan_failed",
        extra_errors=[
            {"code": "setup_agents_plan_failed", "message": reason} for reason in reasons[1:]
        ],
        data={
            "dry_run": dry_run,
            "root": str(root),
            "mode": "local",
            "canonical_layout": "agents_dir" if migrate_legacy_claude else "unknown",
            "bucket": 5,
            "agents_md_detected": False,
            "agents_dir_detected": False,
            "supports_symlinks": False,
            "actions": [],
            "warnings": all_warnings,
            "rules_warnings": [],
            "summary": {
                "created": 0,
                "appended": 0,
                "symlinked": 0,
                "skipped": 0,
                "errored": len(plan_errors),
            },
        },
    )


def format_json_output_local(
    *,
    root: Path,
    dry_run: bool = False,
    bucket: int,
    actions: list[ActionDict],
    all_warnings: list[str],
    rules_warnings: list[str],
    state: StateDict,
    migrate_legacy_claude: bool = False,
) -> dict[str, object]:
    """Build the JSON output dict for a successful local setup-agents run."""
    return ok_envelope(
        "setup-agents",
        data={
            "dry_run": dry_run,
            "root": str(root),
            "mode": "local",
            "canonical_layout": _canonical_layout_local_with_actions(
                state=state,
                actions=actions,
                migrate_legacy_claude=migrate_legacy_claude,
            ),
            "bucket": bucket,
            "agents_md_detected": state["a_state"] != "absent",
            "agents_dir_detected": state["agents_dir"],
            "supports_symlinks": state["supports_symlinks"],
            "actions": _action_summaries(actions),
            "warnings": all_warnings,
            "rules_warnings": rules_warnings,
            "summary": build_action_summary(actions),
        },
    )
