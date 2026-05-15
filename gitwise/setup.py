"""Applies modern git defaults. NEVER modifies GPG-related config."""

import platform
from pathlib import Path
from typing import Any

from .git import config as git_config
from .git import is_repo, repo_root
from .git import run as git_run
from .git import version as git_version
from .i18n import t
from .output import confirm, error, info, ok, print_json, warn

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
            warnings.append(
                "GPG signing activo pero sin user.signingkey — "
                "ejecuta: git config user.signingkey <id>"
            )
        # else: OK, nothing to report
    elif gpgsign is None:
        warnings.append(
            "GPG signing no configurado — si lo deseas: git config commit.gpgsign true"
        )
    # If gpgsign == "false" or other value: don't touch, don't warn loudly
    return warnings


def _plan_changes(cwd: Path) -> list[dict[str, Any]]:
    """Returns list of config changes needed (idempotent check)."""
    changes: list[dict[str, Any]] = []

    for key, desired in _BASE_CONFIGS:
        if key in _PROTECTED_KEYS:
            raise ValueError(t("clave_protegida", name=key))
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
                        "note": "macOS only",
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
                    "note": "opt-in, git ≥ 2.40",
                }
            )

    # core.hooksPath: install gitwise hooks (pre-commit + commit-msg)
    hooks_dir = Path(__file__).parent.parent / "share" / "hooks"
    current = git_config("core.hooksPath", cwd=cwd)
    if str(hooks_dir) != current:
        changes.append(
            {
                "key": "core.hooksPath",
                "desired": str(hooks_dir),
                "current": current,
                "note": "instala hooks GPG + conventional commits",
            }
        )

    return changes


def run_setup(*, dry_run: bool = False, yes: bool = False, as_json: bool = False) -> int:
    if not is_repo():
        error(t("no_repo"))
        return 1

    cwd = repo_root()
    if cwd is None:
        error(t("no_root"))
        return 1

    gpg_warnings = _check_gpg_state(cwd)
    changes = _plan_changes(cwd)

    if as_json:
        print_json(
            {
                "v": 1,
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
        info("")

    if not changes:
        ok(t("config_actualizada"))
        return 0

    info(t("cambios_planificados", count=str(len(changes))))
    info("")
    for c in changes:
        note = f"  [{c['note']}]" if c.get("note") else ""
        current_str = (
            t("actual", current=c["current"]) if c.get("current") else t("no_configurado")
        )
        info(f"  git config {c['key']} {c['desired']}{current_str}{note}")
    info("")

    if dry_run:
        return 0

    if not yes:
        if not confirm(t("confirm_setup")):
            info(t("cancelado"))
            return 0
        info("")

    for c in changes:
        r = git_run(["config", c["key"], c["desired"]], cwd=cwd, check=False)
        if r.returncode == 0:
            ok(f"git config {c['key']} = {c['desired']}")
        else:
            warn(t("config_fallo", name=c["key"]))

    info("")
    ok(t("setup_completado"))
    return 0
