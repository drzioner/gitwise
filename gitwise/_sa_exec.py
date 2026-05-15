"""Execution phase for setup-agents: file writes, symlinks, rollback."""

import json
import os
from pathlib import Path
from typing import Any

from ._sa_state import _AGENTS_MD, _CLAUDE_MD
from .i18n import t
from .output import debug, ok, warn


class SymlinkConflict(Exception):
    pass


class PlanExecutionError(Exception):
    pass


def _safe_create_symlink(link: Path, target_relative: str, root: Path) -> None:
    """Creates a relative symlink safely: idempotency + sandbox + TOCTOU re-check."""
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


def _undo_partial(actions_done: list[dict], root: Path) -> None:
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
            elif act in ("create",) and action.get("_created") and path.exists():
                path.unlink()
                debug(t("debug_rollback_deleted", file=file_key))
        except OSError as e:
            debug(t("debug_rollback_failed", file=file_key, error=str(e)))


def _apply_managed_block(action: dict) -> None:
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


def _execute_actions(root: Path, actions: list[dict[str, Any]]) -> None:
    (root / ".claude").mkdir(parents=True, exist_ok=True)

    actions_done: list[dict] = []
    try:
        for action in actions:
            file_key: str = action["file"]
            act: str = action["action"]

            if act in ("skip", "symlink-skip", "managed-block-skip"):
                debug(t("debug_skip", file=file_key))
                actions_done.append(action)
                continue

            if file_key == _CLAUDE_MD:
                path = root / _CLAUDE_MD
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

            elif file_key == _AGENTS_MD:
                path = root / _AGENTS_MD
                if act == "append":
                    existing = path.read_text(encoding="utf-8")
                    sep = "\n" if existing.endswith("\n") else "\n\n"
                    path.write_text(existing + sep + action["content"], encoding="utf-8")
                    ok(t("updated_git_conventions", file=_AGENTS_MD))

            elif file_key == ".claude/settings.json":
                path = root / ".claude" / "settings.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(action["data"], ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                if act == "create":
                    ok(t("created", file=".claude/settings.json"))
                else:
                    ok(t("settings_updated_merged"))

            elif file_key == ".claude/skills":
                if act == "symlink-create":
                    target_dir = Path(
                        os.path.normpath(root / ".claude" / action["target_relative"])
                    )
                    target_dir.mkdir(parents=True, exist_ok=True)
                    _safe_create_symlink(
                        root / ".claude" / "skills", action["target_relative"], root
                    )
                    ok(
                        t(
                            "symlink_created_msg",
                            file=".claude/skills",
                            target=action["target_relative"],
                        )
                    )

            elif file_key.startswith(".agents/skills/") and file_key.count("/") == 2:
                if act == "mkdir":
                    (root / file_key).mkdir(parents=True, exist_ok=True)
                    debug(t("debug_mkdir", file=file_key))

            elif file_key.startswith(".claude/skills/") and file_key.count("/") == 2:
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

            elif file_key.startswith(".claude/skills/") and file_key.endswith("/SKILL.md"):
                rel = Path(file_key).relative_to(".claude")
                target = root / ".claude" / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(action["content"], encoding="utf-8")
                ok(t("created", file=file_key))

            elif file_key.startswith(".claude/rules/") and file_key.endswith(".md"):
                path = root / file_key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(action["content"], encoding="utf-8")
                action["_created"] = True
                ok(t("created", file=file_key))

            elif file_key == ".claude/git-snapshot.md":
                from .snapshot import generate_snapshot as _gen_snapshot

                _gen_snapshot(root, frozen_time=action.get("frozen_time", False))
                ok(t("snapshot_generated", path=".claude/git-snapshot.md"))

            elif act in ("managed-block-create", "managed-block-replace"):
                _apply_managed_block(action)
                msg_key = (
                    "managed_block_created"
                    if act == "managed-block-create"
                    else "managed_block_updated"
                )
                ok(t(msg_key, file=file_key))

            else:
                warn(t("unknown_action", action=act, file=file_key))

            actions_done.append(action)

    except (SymlinkConflict, OSError) as exc:
        warn(t("action_failed", error=str(exc), count=str(len(actions_done))))
        _undo_partial(actions_done, root)
        raise PlanExecutionError(str(exc))
