"""setup-agents sub-package: planning, state detection, and execution."""

from gitwise.setup_agents.exec import PlanExecutionError, SymlinkConflict, _execute_actions
from gitwise.setup_agents.format import (
    format_json_output_global,
    format_json_output_local,
    format_json_output_local_error,
)
from gitwise.setup_agents.plan import _plan_actions, _plan_actions_global
from gitwise.setup_agents.plan_skills import _SKILLS
from gitwise.setup_agents.types import (
    ActionDict,
    ActionSummary,
    PathState,
    StateDict,
    build_action_summary,
)

__all__ = [
    "_SKILLS",
    "ActionDict",
    "ActionSummary",
    "PathState",
    "PlanExecutionError",
    "StateDict",
    "SymlinkConflict",
    "_execute_actions",
    "_plan_actions",
    "_plan_actions_global",
    "build_action_summary",
    "format_json_output_global",
    "format_json_output_local",
    "format_json_output_local_error",
]
