"""Backward-compatible re-export stub — use gitwise.setup_agents.exec instead."""

from gitwise.setup_agents.exec import (  # noqa: F401
    PlanExecutionError,
    SymlinkConflict,
    _apply_managed_block,
    _execute_actions,
    _safe_create_symlink,
    _undo_partial,
)
