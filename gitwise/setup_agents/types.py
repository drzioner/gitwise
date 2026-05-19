"""Typed structures for the setup-agents pipeline (actions, state, plan results)."""

from typing import Any, Literal, TypedDict

ActionDict = dict[str, Any]


PathState = Literal["absent", "regular", "symlink_valid", "symlink_broken"]


class StateDict(TypedDict):
    a_state: PathState
    c_state: PathState
    agents_dir: bool
    skills_state: PathState
    skills_target: str | None
    supports_symlinks: bool
    errors: list[str]
    rules_warnings: list[str]


class ActionSummary(TypedDict):
    created: int
    appended: int
    symlinked: int
    skipped: int
    errored: int


def build_action_summary(actions: list[ActionDict]) -> ActionSummary:
    summary: ActionSummary = {
        "created": 0,
        "appended": 0,
        "symlinked": 0,
        "skipped": 0,
        "errored": 0,
    }
    for a in actions:
        match a.get("action"):
            case "create" | "managed-block-create" | "adapter-create":
                summary["created"] += 1
            case "append" | "merge":
                summary["appended"] += 1
            case "symlink-create":
                summary["symlinked"] += 1
            case "skip" | "symlink-skip" | "managed-block-skip":
                summary["skipped"] += 1
    return summary
