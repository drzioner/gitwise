"""Injects AGENTS.md awareness, CLAUDE.md, settings.json, slash-commands, and initial snapshot."""

from pathlib import Path

from gitwise.git import config as git_config
from gitwise.git import is_repo, repo_root
from gitwise.i18n import confirm_responses, t
from gitwise.output import error, info, ok, print_json, warn
from gitwise.setup_agents import (
    _SKILLS,
    PlanExecutionError,
    _execute_actions,
    _plan_actions,
    _plan_actions_global,
)
from gitwise.setup_agents.format import (
    format_json_output_global,
    format_json_output_global_error,
    format_json_output_local,
    format_json_output_local_error,
)
from gitwise.setup_agents.providers import detect_global_skills
from gitwise.setup_agents.providers.base import AdapterContext
from gitwise.setup_agents.state import _AGENTS_MD, _gpg_ready
from gitwise.setup_agents.types import StateDict


def _run_setup_global(
    home: Path,
    *,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    no_skills: bool = False,
    providers: list[str] | None = None,
    no_symlinks: bool = False,
    strict: bool = False,
    migrate_legacy_claude: bool = False,
) -> int:
    """Installs global setup-agents artifacts to home config dirs. No git repo required."""
    agents_dir = home / ".agents"
    has_agents_dir = agents_dir.is_dir() and not agents_dir.is_symlink()
    has_errors = False
    errors: list[str] = []
    all_warnings: list[str] = []
    try:
        actions, warnings, _ = _plan_actions_global(home, no_skills=no_skills)
    except FileNotFoundError as e:
        if as_json:
            print_json(
                format_json_output_global_error(
                    home=home,
                    warnings=[],
                    errors=[str(e)],
                    has_agents_dir=has_agents_dir,
                    dry_run=dry_run,
                )
            )
            return 1
        error(str(e))
        return 1

    all_warnings.extend(warnings)

    if providers:
        from gitwise.setup_agents.providers import plan_adapter_actions

        expanded = []
        for adapter in providers:
            expanded.extend(part.strip() for part in adapter.split(",") if part.strip())
        if "claude-only" in expanded:
            all_warnings.append(
                t("adapter_alias_deprecated", alias="claude-only", target="claude")
            )
        state: StateDict = {
            "a_state": "absent",
            "c_state": "regular",
            "agents_dir": has_agents_dir,
            "skills_state": "regular",
            "skills_target": None,
            "supports_symlinks": True,
            "errors": [],
            "rules_warnings": [],
        }
        adapter_context: AdapterContext = {
            "state": state,
            "canonical_doc_path": _AGENTS_MD,
            "global_skills": detect_global_skills(home),
            "supports_symlinks": True,
            "gpg_ready": False,
            "flags": {
                "no_symlinks": no_symlinks,
                "replace_claude_with_symlink": False,
                "migrate_legacy_claude": migrate_legacy_claude,
                "frozen_time": False,
                "no_git_files": False,
                "core_claude_planned": True,
            },
        }
        adapter_actions, adapter_errors, adapter_warnings = plan_adapter_actions(
            expanded,
            home,
            context=adapter_context,
        )
        if adapter_errors:
            errors.extend(adapter_errors)
            has_errors = True
        actions.extend(adapter_actions)
        all_warnings.extend(adapter_warnings)

    if strict and all_warnings:
        errors.append(t("strict_warnings"))
        has_errors = True

    if as_json:
        if has_errors:
            print_json(
                format_json_output_global_error(
                    home=home,
                    warnings=all_warnings,
                    errors=errors,
                    has_agents_dir=has_agents_dir,
                    dry_run=dry_run,
                )
            )
            return 1
        print_json(
            format_json_output_global(
                home=home,
                actions=actions,
                warnings=all_warnings,
                has_agents_dir=has_agents_dir,
                dry_run=dry_run,
            )
        )
        return 0

    info(t("configuring_agents_global", path=str(home / ".claude")))
    info("")

    for w in all_warnings:
        warn(w)
    if all_warnings:
        info("")

    if has_errors:
        for err_text in errors:
            error(err_text)
        return 1

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
    migrate_legacy_claude: bool = False,
    frozen_time: bool = False,
    no_git_files: bool = False,
    providers: list[str] | None = None,
    adapters_legacy_used: bool = False,
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
            migrate_legacy_claude=migrate_legacy_claude,
            no_git_files=no_git_files,
            frozen_time=frozen_time,
        )
    except FileNotFoundError as e:
        error(str(e))
        return 1

    has_errors = bool(plan_errors)
    all_warnings = gpg_warnings + warnings
    global_skills = detect_global_skills()

    if adapters_legacy_used:
        all_warnings.append(
            t("adapter_alias_deprecated", alias="--adapters", target="--providers")
        )

    if providers:
        from gitwise.setup_agents.providers import plan_adapter_actions

        expanded = []
        for a in providers:
            expanded.extend(part.strip() for part in a.split(",") if part.strip())
        if "claude-only" in expanded:
            all_warnings.append(
                t("adapter_alias_deprecated", alias="claude-only", target="claude")
            )
        adapter_context: AdapterContext = {
            "state": state,
            "canonical_doc_path": _AGENTS_MD,
            "global_skills": global_skills,
            "supports_symlinks": state["supports_symlinks"],
            "gpg_ready": _gpg_ready(root),
            "flags": {
                "no_symlinks": no_symlinks,
                "replace_claude_with_symlink": replace_claude_with_symlink,
                "migrate_legacy_claude": migrate_legacy_claude,
                "frozen_time": frozen_time,
                "no_git_files": no_git_files,
                "core_claude_planned": True,
            },
        }
        adapter_actions, adapter_errors, adapter_warnings = plan_adapter_actions(
            expanded, root, context=adapter_context
        )
        if adapter_errors:
            plan_errors.extend({"reason": e, "file": ""} for e in adapter_errors)
            has_errors = True
        actions.extend(adapter_actions)
        all_warnings.extend(adapter_warnings)

    if strict and all_warnings and as_json:
        plan_errors.append({"reason": t("strict_warnings"), "file": ""})
        has_errors = True

    if as_json:
        if has_errors:
            print_json(
                format_json_output_local_error(
                    root=root,
                    dry_run=dry_run,
                    plan_errors=plan_errors,
                    all_warnings=all_warnings,
                    migrate_legacy_claude=migrate_legacy_claude,
                )
            )
            return 1

        print_json(
            format_json_output_local(
                root=root,
                dry_run=dry_run,
                bucket=bucket,
                actions=actions,
                all_warnings=all_warnings,
                rules_warnings=state["rules_warnings"],
                state=state,
                migrate_legacy_claude=migrate_legacy_claude,
            )
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

    if strict and all_warnings:
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
    migrate_legacy_claude: bool = False,
    frozen_time: bool = False,
    no_git_files: bool = False,
    providers: list[str] | None = None,
    adapters_legacy_used: bool = False,
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
            migrate_legacy_claude=migrate_legacy_claude,
            frozen_time=frozen_time,
            no_git_files=no_git_files,
            providers=providers,
            adapters_legacy_used=adapters_legacy_used,
        )
    if migrate_legacy_claude:
        if as_json:
            print_json(
                format_json_output_global_error(
                    home=Path.home(),
                    warnings=[],
                    errors=[t("migrate_requires_local")],
                    has_agents_dir=False,
                    dry_run=dry_run,
                )
            )
            return 1
        error(t("migrate_requires_local"))
        return 1
    if providers:
        return _run_setup_global(
            Path.home(),
            dry_run=dry_run,
            yes=yes,
            as_json=as_json,
            no_skills=no_skills,
            providers=providers,
            no_symlinks=no_symlinks,
            strict=strict,
            migrate_legacy_claude=migrate_legacy_claude,
        )
    return _run_setup_global(
        Path.home(),
        dry_run=dry_run,
        yes=yes,
        as_json=as_json,
        no_skills=no_skills,
        providers=None,
        no_symlinks=no_symlinks,
        strict=strict,
        migrate_legacy_claude=migrate_legacy_claude,
    )
