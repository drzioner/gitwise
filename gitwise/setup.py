"""Applies modern git defaults. NEVER modifies GPG-related config."""

import platform
from pathlib import Path
from typing import Any

from .git import config as git_config
from .git import require_root
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


def _plan_changes(cwd: Path) -> list[dict[str, Any]]:
    """Returns list of config changes needed (idempotent check)."""
    changes: list[dict[str, Any]] = []

    for key, desired in _BASE_CONFIGS:
        if key in _PROTECTED_KEYS:
            raise ValueError(t("protected_key", name=key))
        current = git_config(key, cwd=cwd)
        if current != desired:
            changes.append({"key": key, "desired": desired, "current": current})

    # fsmonitor: macOS only, requires git >= 2.36 (built-in FSEvents) or watchman
    if platform.system() == "Darwin":
        import shutil

        fsmonitor_ok = git_version() >= (2, 36, 0) or bool(shutil.which("watchman"))
        if fsmonitor_ok:
            current = git_config("core.fsmonitor", cwd=cwd)
            if current != "true":
                changes.append(
                    {
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
                    "key": "feature.manyFiles",
                    "desired": "true",
                    "current": current,
                    "note": t("setup_note_manyfiles"),
                }
            )

    hooks_dir = Path(__file__).parent.parent / "share" / "hooks"
    current = git_config("core.hooksPath", cwd=cwd)
    if str(hooks_dir) != current:
        changes.append(
            {
                "key": "core.hooksPath",
                "desired": str(hooks_dir),
                "current": current,
                "note": t("setup_note_hooks"),
            }
        )

    return changes


def run_setup(*, dry_run: bool = False, yes: bool = False, as_json: bool = False) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1
    cwd = root

    gpg_warnings = _check_gpg_state(cwd)
    changes = _plan_changes(cwd)

    if as_json:
        print_json(
            {
                "v": 2,
                "dry_run": dry_run,
                "root": str(cwd),
                "changes": changes,
                "warnings": gpg_warnings,
                "ok": True,
            }
        )
        return 0

    for w in gpg_warnings:
        warn(w)
    if gpg_warnings:
        print_blank()

    if not changes:
        ok(t("config_up_to_date"))
        return 0

    print_header(t("planned_changes", count=str(len(changes))))
    for c in changes:
        note = f"  [{c['note']}]" if c.get("note") else ""
        current_str = (
            t("current_value", current=c["current"]) if c.get("current") else t("not_configured")
        )
        print_kv(c["key"], f"{c['desired']}  {current_str}{note}")

    if dry_run:
        return 0

    if not yes:
        if not confirm(t("confirm_setup_changes")):
            info(t("cancelled"))
            return 0
        print_blank()

    for c in changes:
        r = git_run(["config", c["key"], c["desired"]], cwd=cwd, check=False)
        if r.returncode == 0:
            print_status_line("✓", c["key"], c["desired"])
        else:
            print_status_line("✗", c["key"], t("config_failed", name=c["key"]), ok_flag=False)

    ok(t("setup_complete"))
    return 0
