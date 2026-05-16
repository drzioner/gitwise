"""Injects AGENTS.md awareness, CLAUDE.md, settings.json, slash-commands, and initial snapshot."""

from pathlib import Path

from ._sa_exec import PlanExecutionError, _execute_actions
from ._sa_plan import _SKILLS, _plan_actions, _plan_actions_global
from .git import config as git_config
from .git import is_repo, repo_root
from .i18n import confirm_responses, t
from .output import error, info, ok, print_json, warn


def _run_setup_global(
    home: Path,
    *,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    no_skills: bool = False,
) -> int:
    """Installs global Claude Code artifacts to ~/.claude/. No git repo required."""
    try:
        actions, warnings, _ = _plan_actions_global(home, no_skills=no_skills)
    except FileNotFoundError as e:
        error(str(e))
        return 1

    if as_json:
        summary: dict[str, int] = {
            "created": 0,
            "appended": 0,
            "symlinked": 0,
            "skipped": 0,
            "errored": 0,
        }
        for a in actions:
            match a["action"]:
                case "create" | "managed-block-create":
                    summary["created"] += 1
                case "append":
                    summary["appended"] += 1
                case "symlink-create":
                    summary["symlinked"] += 1
                case "skip" | "symlink-skip" | "managed-block-skip":
                    summary["skipped"] += 1
        print_json(
            {
                "v": 2,
                "v_compat": [1, 2],
                "dry_run": dry_run,
                "root": str(home / ".claude"),
                "mode": "global",
                "actions": [{"file": a["file"], "action": a["action"]} for a in actions],
                "warnings": warnings,
                "errors": [],
                "summary": summary,
                "ok": True,
            }
        )
        return 0

    info(t("configuring_agents_global", path=str(home / ".claude")))
    info("")

    for w in warnings:
        warn(w)
    if warnings:
        info("")

    if dry_run:
        info(t("dry_run_nothing"))
        info("")
        for a in actions:
            verb = a["action"].upper()
            reason = f" ({a['reason']})" if "reason" in a else ""
            info(f"  [{verb}] {a['file']}{reason}")
        return 0

    if not yes:
        info(t("actions_to_perform"))
        for a in actions:
            if a["action"] not in ("skip", "symlink-skip", "managed-block-skip"):
                info(f"  [{a['action'].upper()}] {a['file']}")
        info("")
        try:
            resp = input(t("continue_prompt")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = ""
        if resp not in confirm_responses():
            info(t("cancelled"))
            return 0
        info("")

    try:
        _execute_actions(home, actions)
    except PlanExecutionError as e:
        error(t("setup_agents_global_failed", error=str(e)))
        return 1

    info("")
    ok(t("setup_agents_global_complete"))
    return 0


def _run_setup_local(
    target: Path | None = None,
    *,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    no_symlinks: bool = False,
    strict: bool = False,
    replace_claude_with_symlink: bool = False,
    frozen_time: bool = False,
    no_git_files: bool = False,
) -> int:
    cwd = target or Path.cwd()

    if not is_repo(cwd):
        error(t("not_a_git_repo"))
        return 1

    root = repo_root(cwd)
    if root is None:
        error(t("no_repo_root"))
        return 1

    gpgsign = git_config("commit.gpgsign", cwd=root)
    gpg_warnings: list[str] = []
    if gpgsign == "true":
        signing_key = git_config("user.signingkey", cwd=root)
        if not signing_key:
            gpg_warnings.append(t("gpg_active_no_key_repo"))

    try:
        actions, warnings, plan_errors, bucket, state = _plan_actions(
            root,
            no_symlinks=no_symlinks,
            replace_claude_with_symlink=replace_claude_with_symlink,
            no_git_files=no_git_files,
            frozen_time=frozen_time,
        )
    except FileNotFoundError as e:
        error(str(e))
        return 1

    has_errors = bool(plan_errors)
    all_warnings = gpg_warnings + warnings

    has_agents_md = state.get("a_state", "absent") != "absent"
    has_agents_dir = state.get("agents_dir", False)
    supports_symlinks = state.get("supports_symlinks", False)

    if as_json:
        if has_errors:
            print_json(
                {
                    "v": 2,
                    "v_compat": [1, 2],
                    "dry_run": dry_run,
                    "root": str(root),
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
            )
            return 1

        summary: dict[str, int] = {
            "created": 0,
            "appended": 0,
            "symlinked": 0,
            "skipped": 0,
            "errored": 0,
        }
        for a in actions:
            match a["action"]:
                case "create" | "managed-block-create":
                    summary["created"] += 1
                case "append":
                    summary["appended"] += 1
                case "symlink-create":
                    summary["symlinked"] += 1
                case "skip" | "symlink-skip" | "managed-block-skip":
                    summary["skipped"] += 1

        print_json(
            {
                "v": 2,
                "v_compat": [1, 2],
                "dry_run": dry_run,
                "root": str(root),
                "bucket": bucket,
                "agents_md_detected": has_agents_md,
                "agents_dir_detected": has_agents_dir,
                "supports_symlinks": supports_symlinks,
                "actions": [{"file": a["file"], "action": a["action"]} for a in actions],
                "warnings": all_warnings,
                "rules_warnings": state.get("rules_warnings", []),
                "errors": [],
                "summary": summary,
                "ok": True,
            }
        )
        return 0

    if has_errors:
        for e in plan_errors:
            error(e["reason"])
        return 1

    info(t("configuring_agents_in", root=str(root)))
    info("")

    for w in all_warnings:
        warn(w)

    if all_warnings and strict:
        error(t("strict_warnings"))
        return 2

    if all_warnings:
        info("")

    if dry_run:
        info(t("dry_run_nothing"))
        info("")
        for a in actions:
            verb = a["action"].upper()
            reason = f" ({a['reason']})" if "reason" in a else ""
            info(f"  [{verb}] {a['file']}{reason}")
        return 0

    if not yes:
        info(t("actions_to_perform"))
        for a in actions:
            if a["action"] not in ("skip", "symlink-skip", "managed-block-skip"):
                info(f"  [{a['action'].upper()}] {a['file']}")
        info("")
        try:
            resp = input(t("continue_prompt")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = ""
        if resp not in confirm_responses():
            info(t("cancelled"))
            return 0
        info("")

    try:
        _execute_actions(root, actions)
    except PlanExecutionError as e:
        error(t("setup_agents_failed", error=str(e)))
        return 1

    skills_skipped = sum(
        1
        for a in actions
        if a.get("action") == "skip"
        and a.get("file", "").startswith(".claude/skills/")
        and a.get("file", "").endswith("/SKILL.md")
    )
    if skills_skipped == len(_SKILLS):
        ok(t("skills_already_configured", count=str(len(_SKILLS))))

    info("")
    ok(t("setup_agents_complete"))

    if strict and all_warnings:
        return 2

    return 0


def run_setup_agents(
    target: Path | None = None,
    *,
    local: bool = False,
    no_skills: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    no_symlinks: bool = False,
    strict: bool = False,
    replace_claude_with_symlink: bool = False,
    frozen_time: bool = False,
    no_git_files: bool = False,
) -> int:
    """Dispatcher: global mode (default) or per-repo mode (--local)."""
    if local:
        return _run_setup_local(
            target,
            dry_run=dry_run,
            yes=yes,
            as_json=as_json,
            no_symlinks=no_symlinks,
            strict=strict,
            replace_claude_with_symlink=replace_claude_with_symlink,
            frozen_time=frozen_time,
            no_git_files=no_git_files,
        )
    return _run_setup_global(
        Path.home(),
        dry_run=dry_run,
        yes=yes,
        as_json=as_json,
        no_skills=no_skills,
    )
