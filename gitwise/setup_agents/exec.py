"""Execution phase for setup-agents: file writes, symlinks, rollback."""

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gitwise.i18n import t
from gitwise.output import debug, ok, warn
from gitwise.setup_agents.state import _AGENTS_MD, _CLAUDE_MD


class SymlinkConflict(Exception):
    pass


class PlanExecutionError(Exception):
    pass


def _safe_create_symlink(link: Path, target_relative: str, root: Path) -> None:
    """Creates a relative symlink safely: idempotency + sandbox + TOCTOU re-check.

    Note: The sandbox check (os.path.realpath) and the os.symlink() call are not
    atomic. In a concurrent scenario (two gitwise processes), a TOCTOU race exists.
    This is acceptable because: (a) gitwise is a single-user CLI, (b) the idempotency
    check at the top prevents double-creation, (c) symlink targets are always relative
    paths within the repo root.
    """
    if link.is_symlink():
        existing = os.readlink(link)
        if existing == target_relative:
            return
        raise SymlinkConflict(
            t(
                "symlink_conflict_regular",
                file=link.name,
                existing=existing,
                expected=target_relative,
            )
        )
    if link.exists():
        raise SymlinkConflict(t("symlink_conflict_file", file=link.name))

    root_real = Path(os.path.realpath(str(root)))
    target_real = Path(os.path.realpath(str(link.parent / target_relative)))
    if not target_real.is_relative_to(root_real):
        raise SymlinkConflict(t("symlink_escapes_root", target=target_relative))

    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target_relative, link)


def _undo_partial(actions_done: list[dict[str, Any]], root: Path) -> None:
    """Minimal rollback: revert symlinks created and restore .bak files."""
    for action in reversed(actions_done):
        act = action.get("action", "")
        file_key = action.get("file", "")
        path = root / file_key
        try:
            if act == "symlink-create" and path.is_symlink():
                path.unlink()
                debug(t("debug_rollback_symlink", file=file_key))
            elif act == "claude-md-replace-with-symlink":
                if path.is_symlink():
                    path.unlink()
                bak = action.get("backup_path")
                if bak and Path(bak).exists():
                    Path(bak).rename(path)
                    debug(t("debug_rollback_restored", file=file_key, backup=Path(bak).name))
            elif act == "skill-migrate-to-agents":
                moved_from = action.get("_moved_from")
                agents_skill_str = action.get("agents_skill")
                if path.is_symlink():
                    path.unlink()
                if moved_from and agents_skill_str and Path(agents_skill_str).exists():
                    import shutil

                    shutil.move(str(agents_skill_str), moved_from)
                    debug(
                        t("debug_rollback_restored_skill", file=file_key, skill=agents_skill_str)
                    )
            elif act in ("create", "adapter-create") and action.get("_created") and path.exists():
                path.unlink()
                debug(t("debug_rollback_deleted", file=file_key))
        except OSError as e:
            warn(t("debug_rollback_failed", file=file_key, error=str(e)))


def _apply_managed_block(action: dict[str, Any]) -> None:
    path = Path(action["_path"])
    desired = action["content"]
    act = action["action"]

    if act == "managed-block-create":
        if not path.exists() or not action.get("_append"):
            path.write_text(desired, encoding="utf-8")
        else:
            current = path.read_text(encoding="utf-8")
            sep = "\n" if current.endswith("\n") else "\n\n"
            path.write_text(current + sep + desired, encoding="utf-8")
    elif act == "managed-block-replace":
        current = path.read_text(encoding="utf-8")
        start_idx = action["_start_idx"]
        end_idx = action["_end_idx"]
        new_content = current[:start_idx] + desired.rstrip("\n") + current[end_idx:]
        path.write_text(new_content, encoding="utf-8")


def _exec_claude_md(action: dict[str, Any], root: Path) -> None:
    path = root / _CLAUDE_MD
    act = action["action"]
    if act == "create":
        path.write_text(action["content"], encoding="utf-8")
        action["_created"] = True
        ok(t("created", file=_CLAUDE_MD))
    elif act == "append":
        existing = path.read_text(encoding="utf-8")
        sep = "\n" if existing.endswith("\n") else "\n\n"
        path.write_text(existing + sep + action["content"], encoding="utf-8")
        ok(t("updated_git_conventions", file=_CLAUDE_MD))
    elif act == "symlink-create":
        _safe_create_symlink(path, action["target_relative"], root)
        ok(t("symlink_created_msg", file=_CLAUDE_MD, target=action["target_relative"]))
    elif act == "claude-md-replace-with-symlink":
        backup = Path(action["backup_path"])
        path.rename(backup)
        _safe_create_symlink(path, action["target_relative"], root)
        ok(t("replaced", file=_CLAUDE_MD, backup=backup.name))


def _exec_agents_md(action: dict[str, Any], root: Path) -> None:
    path = root / _AGENTS_MD
    existing = path.read_text(encoding="utf-8")
    sep = "\n" if existing.endswith("\n") else "\n\n"
    path.write_text(existing + sep + action["content"], encoding="utf-8")
    ok(t("updated_git_conventions", file=_AGENTS_MD))


def _exec_settings_json(action: dict[str, Any], root: Path) -> None:
    path = root / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(action["data"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if action["action"] == "create":
        ok(t("created", file=".claude/settings.json"))
    else:
        ok(t("settings_updated_merged"))


def _exec_skills_dir(action: dict[str, Any], root: Path) -> None:
    target_dir = Path(os.path.normpath(root / ".claude" / action["target_relative"]))
    target_dir.mkdir(parents=True, exist_ok=True)
    _safe_create_symlink(root / ".claude" / "skills", action["target_relative"], root)
    ok(
        t(
            "symlink_created_msg",
            file=".claude/skills",
            target=action["target_relative"],
        )
    )


def _exec_agents_skills_dir(action: dict[str, Any], root: Path) -> None:
    (root / action["file"]).mkdir(parents=True, exist_ok=True)
    debug(t("debug_mkdir", file=action["file"]))


def _exec_claude_skill(action: dict[str, Any], root: Path) -> None:
    file_key = action["file"]
    act = action["action"]
    if act == "symlink-create":
        skill_link = root / file_key
        skill_link.parent.mkdir(parents=True, exist_ok=True)
        _safe_create_symlink(skill_link, action["target_relative"], root)
        ok(t("symlink_created_msg", file=file_key, target=action["target_relative"]))
    elif act == "skill-migrate-to-agents":
        import shutil

        skill_link = root / file_key
        agents_skill = Path(action["agents_skill"])
        agents_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(skill_link), str(agents_skill))
        action["_moved_from"] = str(skill_link)
        _safe_create_symlink(skill_link, action["target_relative"], root)
        ok(t("migrated_skill", file=file_key, target=action["target_relative"]))


def _exec_skill_md(action: dict[str, Any], root: Path) -> None:
    file_key = action["file"]
    rel = Path(file_key).relative_to(".claude")
    target = root / ".claude" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(action["content"], encoding="utf-8")
    ok(t("created", file=file_key))


def _exec_rule(action: dict[str, Any], root: Path) -> None:
    file_key = action["file"]
    path = root / file_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(action["content"], encoding="utf-8")
    action["_created"] = True
    ok(t("created", file=file_key))


def _exec_adapter_create(action: dict[str, Any], root: Path) -> None:
    file_key = action["file"]
    path = root / file_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(action["content"], encoding="utf-8")
    action["_created"] = True
    ok(t("adapter_created", adapter=action.get("adapter", file_key), file=file_key))


def _exec_snapshot(action: dict[str, Any], root: Path) -> None:
    from gitwise.snapshot import generate_snapshot as _gen_snapshot

    _gen_snapshot(root, frozen_time=action.get("frozen_time", False))
    ok(t("snapshot_generated", path=".claude/git-snapshot.md"))


def _exec_managed_block(action: dict[str, Any], root: Path) -> None:
    _apply_managed_block(action)
    act = action["action"]
    msg_key = "managed_block_created" if act == "managed-block-create" else "managed_block_updated"
    ok(t(msg_key, file=action["file"]))


def _match_file_key(file_key: str, act: str) -> Callable[[dict[str, Any], Path], None] | None:
    if file_key == _CLAUDE_MD:
        return _exec_claude_md
    if file_key == _AGENTS_MD:
        return _exec_agents_md
    if file_key == ".claude/settings.json":
        return _exec_settings_json
    if file_key == ".claude/skills":
        return _exec_skills_dir
    if file_key.startswith(".agents/skills/") and file_key.count("/") == 2:
        return _exec_agents_skills_dir
    if file_key.startswith(".claude/skills/") and file_key.count("/") == 2:
        return _exec_claude_skill
    if file_key.startswith(".claude/skills/") and file_key.endswith("/SKILL.md"):
        return _exec_skill_md
    if file_key.startswith(".claude/rules/") and file_key.endswith(".md"):
        return _exec_rule
    if file_key == ".claude/git-snapshot.md":
        return _exec_snapshot
    if act in ("managed-block-create", "managed-block-replace"):
        return _exec_managed_block
    if act == "adapter-create":
        return _exec_adapter_create
    return None


def _execute_actions(root: Path, actions: list[dict[str, Any]]) -> None:
    (root / ".claude").mkdir(parents=True, exist_ok=True)

    actions_done: list[dict[str, Any]] = []
    try:
        for action in actions:
            file_key: str = action["file"]
            act: str = action["action"]

            if act in ("skip", "symlink-skip", "managed-block-skip"):
                debug(t("debug_skip", file=file_key))
                actions_done.append(action)
                continue

            handler = _match_file_key(file_key, act)
            if handler is not None:
                handler(action, root)
            else:
                warn(t("unknown_action", action=act, file=file_key))

            actions_done.append(action)

    except (SymlinkConflict, OSError) as exc:
        warn(t("action_failed", error=str(exc), count=str(len(actions_done))))
        _undo_partial(actions_done, root)
        raise PlanExecutionError(str(exc)) from exc
