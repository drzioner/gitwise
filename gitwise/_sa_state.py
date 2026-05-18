"""Backward-compatible re-export stub — use gitwise.setup_agents.state instead."""

from gitwise.setup_agents.state import (  # noqa: F401
    _classify_path,
    _detect_rules,
    _detect_state,
    _files_equal,
    _gpg_ready,
    _has_marker,
    reset_caches,
)
