"""JSON output formatting for setup-agents."""

from pathlib import Path

from gitwise.setup_agents.types import ActionDict, StateDict, build_action_summary

_SETUP_AGENTS_SCHEMA_VERSION = 3
_SETUP_AGENTS_SCHEMA_COMPAT = [1, 2, 3]


def _action_summaries(actions: list[ActionDict]) -> list[dict[str, str]]:
    return [{"file": a["file"], "action": a["action"]} for a in actions]


def _canonical_layout_local(state: StateDict) -> str:
    if state["agents_dir"]:
        return "agents_dir"
    if state["a_state"] != "absent":
        return "agents_md"
    return "claude_only"


def _canonical_layout_global(*, has_agents_dir: bool) -> str:
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
    summary = build_action_summary(actions)
    return {
        "v": _SETUP_AGENTS_SCHEMA_VERSION,
        "v_compat": _SETUP_AGENTS_SCHEMA_COMPAT,
        "dry_run": dry_run,
        "root": str(home / ".claude"),
        "mode": "global",
        "canonical_layout": _canonical_layout_global(has_agents_dir=has_agents_dir),
        "actions": _action_summaries(actions),
        "warnings": warnings,
        "errors": [],
        "summary": summary,
        "ok": True,
    }


def format_json_output_local_error(
    *,
    root: Path,
    dry_run: bool = False,
    plan_errors: list[dict[str, str]],
    all_warnings: list[str],
) -> dict[str, object]:
    return {
        "v": _SETUP_AGENTS_SCHEMA_VERSION,
        "v_compat": _SETUP_AGENTS_SCHEMA_COMPAT,
        "dry_run": dry_run,
        "root": str(root),
        "mode": "local",
        "canonical_layout": "unknown",
        "bucket": 5,
        "agents_md_detected": False,
        "agents_dir_detected": False,
        "supports_symlinks": False,
        "actions": [],
        "warnings": all_warnings,
        "rules_warnings": [],
        "errors": [e["reason"] for e in plan_errors],
        "summary": {
            "created": 0,
            "appended": 0,
            "symlinked": 0,
            "skipped": 0,
            "errored": len(plan_errors),
        },
        "ok": False,
    }


def format_json_output_local(
    *,
    root: Path,
    dry_run: bool = False,
    bucket: int,
    actions: list[ActionDict],
    all_warnings: list[str],
    rules_warnings: list[str],
    state: StateDict,
) -> dict[str, object]:
    summary = build_action_summary(actions)
    return {
        "v": _SETUP_AGENTS_SCHEMA_VERSION,
        "v_compat": _SETUP_AGENTS_SCHEMA_COMPAT,
        "dry_run": dry_run,
        "root": str(root),
        "mode": "local",
        "canonical_layout": _canonical_layout_local(state),
        "bucket": bucket,
        "agents_md_detected": state["a_state"] != "absent",
        "agents_dir_detected": state["agents_dir"],
        "supports_symlinks": state["supports_symlinks"],
        "actions": _action_summaries(actions),
        "warnings": all_warnings,
        "rules_warnings": rules_warnings,
        "errors": [],
        "summary": summary,
        "ok": True,
    }
