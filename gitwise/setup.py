"""Applies modern git defaults. NEVER modifies GPG-related config."""

import os
import platform
from pathlib import Path
from typing import Literal, TypedDict

from ._paths import share_dir as _share_dir
from .git import config as git_config
from .git import config_all as git_config_all
from .git import git_dir, require_root, supports_config_hooks
from .git import run as git_run
from .git import version as git_version
from .i18n import t
from .output import (
    confirm,
    info,
    ok,
    print_blank,
    print_header,
    print_json,
    print_kv,
    print_status_line,
    warn,
)
from .utils.json_envelope import error_envelope, ok_envelope

HookMode = Literal["preserve", "native", "legacy", "skip"]


class SetupChange(TypedDict):
    op: Literal["set", "add", "unset"]
    key: str
    desired: str
    current: str | None
    note: str | None


# Modern git defaults (GitButler list, Chacon feb 2025)
_BASE_CONFIGS: list[tuple[str, str]] = [
    ("fetch.prune", "true"),
    ("fetch.prunetags", "true"),
    ("fetch.all", "true"),
    ("merge.conflictstyle", "zdiff3"),
    ("diff.algorithm", "histogram"),
    ("diff.colorMoved", "default"),
    ("rerere.enabled", "true"),
    ("rerere.autoupdate", "true"),
    ("branch.sort", "-committerdate"),
    ("tag.sort", "-version:refname"),
    ("push.default", "current"),
    ("push.autoSetupRemote", "true"),
    ("commit.verbose", "true"),
    ("maintenance.auto", "false"),
    ("maintenance.strategy", "incremental"),
    ("core.untrackedCache", "true"),
    ("core.preloadindex", "true"),
]

# These keys are NEVER modified by gitwise setup
_PROTECTED_KEYS = {"commit.gpgsign", "user.signingkey", "user.email", "user.name"}

_NATIVE_HOOKS: tuple[tuple[str, str], ...] = (
    ("gitwise-gpg", "pre-commit"),
    ("gitwise-conventional-commit", "commit-msg"),
)


def _check_gpg_state(cwd: Path) -> list[str]:
    """Returns warnings about GPG state. Never modifies anything."""
    warnings: list[str] = []
    gpgsign = git_config("commit.gpgsign", cwd=cwd)
    signingkey = git_config("user.signingkey", cwd=cwd)

    if gpgsign == "true":
        if not signingkey:
            warnings.append(t("gpg_signing_active_no_key"))
    elif gpgsign is None:
        warnings.append(t("gpg_signing_not_configured"))
    return warnings


def _plan_base_changes(cwd: Path) -> list[SetupChange]:
    changes: list[SetupChange] = []
    for key, desired in _BASE_CONFIGS:
        if key in _PROTECTED_KEYS:
            raise ValueError(t("protected_key", name=key))
        current = git_config(key, cwd=cwd)
        if current != desired:
            changes.append(
                {
                    "op": "set",
                    "key": key,
                    "desired": desired,
                    "current": current,
                    "note": None,
                }
            )
    return changes


def _plan_platform_feature_changes(cwd: Path) -> list[SetupChange]:
    changes: list[SetupChange] = []

    # fsmonitor: macOS only, requires git >= 2.36 (built-in FSEvents) or watchman
    if platform.system() == "Darwin":
        import shutil

        fsmonitor_ok = git_version() >= (2, 36, 0) or bool(shutil.which("watchman"))
        if fsmonitor_ok:
            current = git_config("core.fsmonitor", cwd=cwd)
            if current != "true":
                changes.append(
                    {
                        "op": "set",
                        "key": "core.fsmonitor",
                        "desired": "true",
                        "current": current,
                        "note": t("setup_note_fsmonitor"),
                    }
                )

    # feature.manyFiles: git >= 2.40 only (can break older clients)
    if git_version() >= (2, 40, 0):
        current = git_config("feature.manyFiles", cwd=cwd)
        if current != "true":
            changes.append(
                {
                    "op": "set",
                    "key": "feature.manyFiles",
                    "desired": "true",
                    "current": current,
                    "note": t("setup_note_manyfiles"),
                }
            )

    return changes


def _detect_hook_managers(cwd: Path) -> list[str]:
    managers: list[str] = []
    if (cwd / "lefthook.yml").exists() or (cwd / ".lefthook").exists():
        managers.append("lefthook")
    if (cwd / ".husky").exists():
        managers.append("husky")
    return managers


def _same_path(left: Path, right: Path) -> bool:
    return os.path.realpath(str(left)) == os.path.realpath(str(right))


def _active_hooks_dir(repo_root: Path) -> Path | None:
    configured = git_config("core.hooksPath", cwd=repo_root)
    if configured:
        configured_path = Path(configured)
        if configured_path.is_absolute():
            return configured_path
        return repo_root / configured_path

    repository_git_dir = git_dir(repo_root)
    if repository_git_dir is None:
        return None
    return repository_git_dir / "hooks"


def _detect_existing_hook_events(repo_root: Path, hooks_dir: Path) -> list[str]:
    active_dir = _active_hooks_dir(repo_root)
    if active_dir is None:
        return []
    if _same_path(active_dir, hooks_dir):
        return []

    existing_events: list[str] = []
    for _, event in _NATIVE_HOOKS:
        hook_file = active_dir / event
        if hook_file.exists() or hook_file.is_symlink():
            existing_events.append(event)
    return existing_events


def _plan_native_hooks(cwd: Path, hooks_dir: Path) -> list[SetupChange]:
    changes: list[SetupChange] = []

    current_hookspath = git_config("core.hooksPath", cwd=cwd)
    if current_hookspath == str(hooks_dir):
        changes.append(
            {
                "op": "unset",
                "key": "core.hooksPath",
                "current": current_hookspath,
                "desired": "",
                "note": t("setup_note_hooks_native_migrate"),
            }
        )

    for name, event in _NATIVE_HOOKS:
        hook_script = str(hooks_dir / event)
        command_key = f"hook.{name}.command"
        event_key = f"hook.{name}.event"

        current_command = git_config(command_key, cwd=cwd)
        if current_command != hook_script:
            changes.append(
                {
                    "op": "set",
                    "key": command_key,
                    "desired": hook_script,
                    "current": current_command,
                    "note": t("setup_note_hooks_native"),
                }
            )

        current_events = set(git_config_all(event_key, cwd=cwd))
        if event not in current_events:
            changes.append(
                {
                    "op": "add",
                    "key": event_key,
                    "desired": event,
                    "current": None,
                    "note": t("setup_note_hooks_native_event"),
                }
            )

    return changes


def _plan_legacy_hooks(cwd: Path, hooks_dir: Path) -> list[SetupChange]:
    current = git_config("core.hooksPath", cwd=cwd)
    desired = str(hooks_dir)
    if current == desired:
        return []
    return [
        {
            "op": "set",
            "key": "core.hooksPath",
            "desired": desired,
            "current": current,
            "note": t("setup_note_hooks_legacy"),
        }
    ]


def _choose_hooks_backend(
    *,
    cwd: Path,
    hooks_mode: HookMode,
    hooks_dir: Path,
    managers: list[str],
    existing_events: list[str],
) -> tuple[Literal["native", "legacy", "skip"], list[str]]:
    warnings: list[str] = []
    native_supported = supports_config_hooks(cwd=cwd)
    current = git_config("core.hooksPath", cwd=cwd)

    if hooks_mode == "skip":
        return "skip", warnings

    if hooks_mode == "native":
        if native_supported:
            return "native", warnings
        warnings.append(t("setup_hook_warning_native_unsupported"))
        return "skip", warnings

    if hooks_mode == "legacy":
        if current and current != str(hooks_dir):
            warnings.append(t("setup_hook_warning_legacy_overwrite", current=current))
        return "legacy", warnings

    if current == str(hooks_dir):
        return "legacy", warnings

    if managers:
        warnings.append(t("setup_hook_warning_managers_preserve", managers=", ".join(managers)))
        return "skip", warnings

    if current and current != str(hooks_dir):
        warnings.append(t("setup_hook_warning_legacy_conflict", current=current))
        return "skip", warnings

    if existing_events:
        warnings.append(
            t("setup_hook_warning_existing_scripts", hooks=", ".join(sorted(existing_events)))
        )
        return "skip", warnings

    if native_supported:
        return "native", warnings

    return "legacy", warnings


def _plan_hook_changes(
    *,
    repo_root: Path,
    hooks_mode: HookMode,
) -> tuple[list[SetupChange], list[str], list[str], Literal["native", "legacy", "skip"]]:
    hooks_dir = _share_dir() / "hooks"
    managers = _detect_hook_managers(repo_root)
    existing_events = _detect_existing_hook_events(repo_root, hooks_dir)
    backend, warnings = _choose_hooks_backend(
        cwd=repo_root,
        hooks_mode=hooks_mode,
        hooks_dir=hooks_dir,
        managers=managers,
        existing_events=existing_events,
    )

    if backend == "native":
        return _plan_native_hooks(repo_root, hooks_dir), warnings, managers, backend
    if backend == "legacy":
        return _plan_legacy_hooks(repo_root, hooks_dir), warnings, managers, backend
    return [], warnings, managers, backend


def _plan_changes(
    *,
    repo_root: Path,
    hooks_mode: HookMode,
) -> tuple[list[SetupChange], list[str], list[str], Literal["native", "legacy", "skip"]]:
    changes: list[SetupChange] = []
    changes.extend(_plan_base_changes(repo_root))
    changes.extend(_plan_platform_feature_changes(repo_root))
    hook_changes, hook_warnings, managers, backend = _plan_hook_changes(
        repo_root=repo_root,
        hooks_mode=hooks_mode,
    )
    changes.extend(hook_changes)
    return changes, hook_warnings, managers, backend


def _format_desired(change: SetupChange) -> str:
    op = change["op"]
    if op == "add":
        return f"+ {change['desired']}"
    if op == "unset":
        return t("unset_value")
    return change["desired"]


def _apply_change(change: SetupChange, cwd: Path) -> bool:
    op = change["op"]
    key = change["key"]

    if op == "add":
        result = git_run(["config", "--add", key, change["desired"]], cwd=cwd, check=False)
    elif op == "unset":
        result = git_run(["config", "--unset-all", key], cwd=cwd, check=False)
    else:
        result = git_run(["config", key, change["desired"]], cwd=cwd, check=False)
    return result.returncode == 0


def _json_report(
    *,
    dry_run: bool,
    root: Path,
    changes: list[SetupChange],
    warnings: list[str],
    managers: list[str],
    hooks_mode: HookMode,
    hooks_backend: Literal["native", "legacy", "skip"],
) -> dict[str, object]:
    return {
        "dry_run": dry_run,
        "root": str(root),
        "changes": changes,
        "warnings": warnings,
        "hook_managers": managers,
        "hooks_mode_requested": hooks_mode,
        "hooks_backend": hooks_backend,
    }


def _print_setup_context(
    *,
    gpg_warnings: list[str],
    hook_warnings: list[str],
    managers: list[str],
    hooks_backend: Literal["native", "legacy", "skip"],
    hooks_mode: HookMode,
) -> None:
    for warning_text in gpg_warnings + hook_warnings:
        warn(warning_text)
    info(t("setup_hook_backend_selected", backend=hooks_backend, requested=hooks_mode))
    if managers:
        info(t("setup_hook_managers_detected", managers=", ".join(managers)))
    if gpg_warnings or hook_warnings or managers:
        print_blank()


def _print_change_plan(changes: list[SetupChange]) -> None:
    print_header(t("planned_changes", count=str(len(changes))))
    for change in changes:
        note = f"  [{change['note']}]" if change["note"] else ""
        current = change["current"]
        current_str = (
            t("current_value", current=current) if current is not None else t("not_configured")
        )
        print_kv(change["key"], f"{_format_desired(change)}  {current_str}{note}")


def _apply_changes(
    changes: list[SetupChange], cwd: Path, *, quiet: bool = False
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for change in changes:
        desired_text = _format_desired(change)
        applied = _apply_change(change, cwd)
        results.append({"key": change["key"], "applied": applied})
        if quiet:
            continue
        if applied:
            print_status_line("✓", change["key"], desired_text)
        else:
            print_status_line(
                "✗",
                change["key"],
                t("config_failed", name=change["key"]),
                ok_flag=False,
            )
    return results


def run_setup(
    *,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    hooks_mode: HookMode = "preserve",
) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1
    cwd = root

    gpg_warnings = _check_gpg_state(cwd)
    changes, hook_warnings, managers, hooks_backend = _plan_changes(
        repo_root=cwd,
        hooks_mode=hooks_mode,
    )

    if dry_run:
        if as_json:
            print_json(
                ok_envelope(
                    payload=_json_report(
                        dry_run=True,
                        root=cwd,
                        changes=changes,
                        warnings=gpg_warnings + hook_warnings,
                        managers=managers,
                        hooks_mode=hooks_mode,
                        hooks_backend=hooks_backend,
                    ),
                    applied=False,
                )
            )
            return 0
        _print_setup_context(
            gpg_warnings=gpg_warnings,
            hook_warnings=hook_warnings,
            managers=managers,
            hooks_backend=hooks_backend,
            hooks_mode=hooks_mode,
        )
        if not changes:
            ok(t("config_up_to_date"))
            return 0
        _print_change_plan(changes)
        return 0

    if as_json and not yes:
        print_json(
            error_envelope(
                error=t("yes_required_with_json"),
                code="yes_required",
                hint=t("yes_required_hint"),
            )
        )
        return 2

    if not as_json:
        _print_setup_context(
            gpg_warnings=gpg_warnings,
            hook_warnings=hook_warnings,
            managers=managers,
            hooks_backend=hooks_backend,
            hooks_mode=hooks_mode,
        )
        if not changes:
            ok(t("config_up_to_date"))
            return 0
        _print_change_plan(changes)
        if not yes:
            if not confirm(t("confirm_setup_changes")):
                info(t("cancelled"))
                return 0
            print_blank()

    if not changes:
        if as_json:
            print_json(
                ok_envelope(
                    payload=_json_report(
                        dry_run=False,
                        root=cwd,
                        changes=[],
                        warnings=gpg_warnings + hook_warnings,
                        managers=managers,
                        hooks_mode=hooks_mode,
                        hooks_backend=hooks_backend,
                    ),
                    applied=True,
                    results=[],
                )
            )
        return 0

    results = _apply_changes(changes, cwd, quiet=as_json)

    if as_json:
        report = _json_report(
            dry_run=False,
            root=cwd,
            changes=changes,
            warnings=gpg_warnings + hook_warnings,
            managers=managers,
            hooks_mode=hooks_mode,
            hooks_backend=hooks_backend,
        )
        report["applied"] = True
        report["results"] = results
        all_ok = all(bool(r.get("applied")) for r in results)
        if all_ok:
            print_json(ok_envelope(payload=report))
            return 0
        print_json(
            error_envelope(
                error=t("setup_partial_failure"),
                code="setup_partial_failure",
                payload=report,
            )
        )
        return 1

    ok(t("setup_complete"))
    return 0
