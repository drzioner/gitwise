---
alwaysApply: false
paths: gitwise/setup_agents/**
---

# setup_agents Package

Key modules:

- `setup_agents/state.py`: `_detect_state(root)` → state dict, `_classify_path()`, `_detect_rules()`, `reset_caches()`
- `setup_agents/plan.py`: `_resolve_canonical_doc()` → bucket 1-5, `_plan_actions()` → actions list
- `setup_agents/exec.py`: `_execute_actions()` — writes files, rolls back via `_undo_partial`; `_safe_create_symlink()` — sandbox + TOCTOU-safe
- `setup_agents/plan_skills.py`: `plan_skills()`, `plan_global_skills()` — skill installation planning
- `setup_agents/plan_gitfiles.py`: `plan_managed_block()` — .gitignore/.gitattributes managed blocks
- `setup_agents/types.py`: `ActionDict`, `StateDict`, `PathState`, `ActionSummary` — shared type definitions
- `setup_agents/format.py`: `format_json_output_local()`, `format_json_output_global()` — JSON output formatting

JSON output schema: `v=2`, `v_compat=[1,2]`. Keys: `bucket`, `agents_md_detected`, `agents_dir_detected`, `supports_symlinks`, `actions`, `warnings`, `rules_warnings`, `errors`, `summary`, `ok`.
