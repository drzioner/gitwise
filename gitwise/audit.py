"""Read-only repo diagnostics with human/JSON dual output."""

import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gitwise.utils.json_envelope import ok_envelope

from .git import (
    gpg_status,
    has_commit_graph,
    has_remote,
    has_upstream,
    require_root,
    stale_branches,
)
from .git import run as git_run
from .i18n import t
from .output import (
    debug,
    ok,
    print_blank,
    print_bracket,
    print_dim,
    print_error_styled,
    print_header,
    print_json,
    status,
)

_STALE_DAYS = 30
_LARGE_BLOB_MIN_BYTES = 1_000_000  # 1MB


def _check_fsmonitor(cwd: Path) -> bool:
    """Return True if core.fsmonitor is enabled (``true`` or ``1``)."""
    r = git_run(["config", "--get", "core.fsmonitor"], cwd=cwd, check=False)
    return r.returncode == 0 and r.stdout.strip().lower() in ("true", "1")


def _find_old_stashes(cwd: Path) -> list[dict]:
    """Return stash entries older than ``_STALE_DAYS`` days."""
    r = git_run(
        ["reflog", "show", "--format=%gd|%ci|%gs", "stash"],
        cwd=cwd,
        check=False,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return []
    now = datetime.now(timezone.utc)
    old: list[dict] = []
    for line in r.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        ref, date_str, subject = parts
        try:
            date = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S %z")
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            age = (now - date).days
            if age >= _STALE_DAYS:
                old.append({"ref": ref.strip(), "age_days": age, "subject": subject.strip()})
        except (ValueError, TypeError):
            debug(f"stash date parse failed: {line!r}")
            continue
    return old


def _find_large_blobs(cwd: Path, top_n: int = 3) -> list[dict]:
    """Return the *top_n* largest blobs in HEAD, each >= 1 MB."""
    if git_run(["rev-parse", "HEAD"], cwd=cwd, check=False).returncode != 0:
        return []
    r = git_run(["ls-tree", "-r", "--long", "HEAD"], cwd=cwd, check=False)
    if r.returncode != 0:
        return []
    blobs: list[dict] = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            size = int(parts[3])
            path = " ".join(parts[4:])
            if size >= _LARGE_BLOB_MIN_BYTES:
                blobs.append({"path": path, "size": size, "size_mb": round(size / 1_048_576, 2)})
        except (ValueError, IndexError):
            debug(f"ls-tree line parse failed: {line!r}")
            continue
    blobs.sort(key=lambda b: b["size"], reverse=True)
    return blobs[:top_n]


def _check_mixed_staging(cwd: Path) -> bool:
    """Return True when the index has both staged and unstaged changes."""
    r = git_run(["status", "--porcelain"], cwd=cwd, check=False)
    if r.returncode != 0:
        return False
    has_staged = has_unstaged = False
    for line in r.stdout.splitlines():
        if len(line) >= 2:
            if line[0] not in (" ", "?", "!"):
                has_staged = True
            if line[1] not in (" ", "?", "!"):
                has_unstaged = True
    return has_staged and has_unstaged


def _run_git_sizer(cwd: Path) -> dict | None:
    """Run ``git-sizer`` if available and return its JSON output, or None."""
    if not shutil.which("git-sizer"):
        return None
    r = subprocess.run(
        ["git-sizer", "--threshold=2", "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode not in (0, 1):
        return None
    import json

    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _check_gpg_findings(gpg: dict) -> list[dict]:
    """Translate GPG readiness flags into audit findings."""
    if gpg["gpgsign_enabled"] and not gpg["gpg_binary"]:
        return [
            {
                "type": "gpg_binary_missing",
                "severity": "high",
                "message": t("gpg_binary_missing_audit"),
                "fix": t("gpg_binary_missing_fix"),
                "cost_of_fix": t("trivial"),
                "cost_of_ignore": t("gpg_binary_missing_cost"),
            }
        ]
    if gpg["gpgsign_enabled"] and not gpg["signing_key_set"]:
        return [
            {
                "type": "gpg_key_missing",
                "severity": "high",
                "message": t("gpg_key_missing_audit"),
                "fix": t("gpg_key_missing_fix"),
                "cost_of_fix": t("trivial"),
                "cost_of_ignore": t("gpg_key_missing_cost"),
            }
        ]
    if not gpg["gpgsign_enabled"]:
        return [
            {
                "type": "gpg_not_configured",
                "severity": "info",
                "message": t("gpg_not_configured_audit"),
                "fix": t("gpg_not_configured_fix"),
                "cost_of_fix": t("gpg_not_configured_fix_cost"),
                "cost_of_ignore": t("gpg_not_configured_cost"),
            }
        ]
    return []


_SEVERITY_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}


def run_audit(*, quick: bool = False, as_json: bool = False) -> int:
    """Run all diagnostic checks and report findings.

    Returns 0 when no critical/high/medium findings exist, 1 otherwise.
    ``--quick`` skips large-blob scanning and git-sizer.
    """
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1
    cwd = root

    findings: list[dict[str, Any]] = []

    gpg = gpg_status(cwd)
    findings.extend(_check_gpg_findings(gpg))

    stale = stale_branches(cwd)
    if stale:
        findings.append(
            {
                "type": "stale_branches",
                "severity": "medium",
                "count": len(stale),
                "branches": stale,
                "message": t("stale_branches_audit", count=str(len(stale))),
                "fix": t("clean_fix"),
                "cost_of_fix": t("stale_branches_fix_cost"),
                "cost_of_ignore": t("stale_branches_cost"),
            }
        )

    has_commit_graph_val = has_commit_graph(cwd)
    if not has_commit_graph_val:
        findings.append(
            {
                "type": "missing_commit_graph",
                "severity": "medium",
                "message": t("commit_graph_ausente"),
                "fix": t("commit_graph_fix"),
                "cost_of_fix": t("commit_graph_fix_cost"),
                "cost_of_ignore": t("commit_graph_cost"),
            }
        )

    if platform.system() == "Darwin":
        if not _check_fsmonitor(cwd):
            findings.append(
                {
                    "type": "fsmonitor_disabled",
                    "severity": "low",
                    "message": t("fsmonitor_disabled"),
                    "fix": t("fsmonitor_fix"),
                    "cost_of_fix": t("fsmonitor_fix_cost"),
                    "cost_of_ignore": t("fsmonitor_cost"),
                }
            )

    with status(t("status_audit_stashes")):
        old_stashes = _find_old_stashes(cwd)
    if old_stashes:
        findings.append(
            {
                "type": "old_stashes",
                "severity": "low",
                "count": len(old_stashes),
                "stashes": old_stashes,
                "message": t(
                    "old_stashes_msg", count=str(len(old_stashes)), days=str(_STALE_DAYS)
                ),
                "fix": t("stash_fix"),
                "cost_of_fix": t("stash_fix_cost"),
                "cost_of_ignore": t("stash_cost"),
            }
        )

    large_blobs: list[dict] = []
    if not quick:
        with status(t("status_audit_blobs")):
            large_blobs = _find_large_blobs(cwd)
        if large_blobs:
            findings.append(
                {
                    "type": "large_blobs",
                    "severity": "low",
                    "count": len(large_blobs),
                    "blobs": large_blobs,
                    "message": t("large_blobs", count=str(len(large_blobs))),
                    "fix": t("large_blobs_fix"),
                    "cost_of_fix": t("large_blobs_fix_cost"),
                    "cost_of_ignore": t("large_blobs_cost"),
                }
            )

    if _check_mixed_staging(cwd):
        findings.append(
            {
                "type": "mixed_staging",
                "severity": "info",
                "message": t("mixed_staging"),
                "fix": t("mixed_staging_fix"),
                "cost_of_fix": t("mixed_staging_fix_cost"),
                "cost_of_ignore": t("mixed_staging_cost"),
            }
        )

    if quick:
        sizer = None
    else:
        with status(t("status_audit_sizer")):
            sizer = _run_git_sizer(cwd)

    _has_remote = has_remote(cwd)
    _has_upstream = has_upstream(cwd)
    if _has_remote and not _has_upstream:
        findings.append(
            {
                "type": "no_upstream",
                "severity": "low",
                "message": t("no_upstream_audit"),
                "fix": t("no_upstream_fix"),
                "cost_of_ignore": t("trivial"),
            }
        )

    from .health import compute_health

    health = compute_health(
        cwd,
        _gpg_override=gpg,
        _has_commit_graph=has_commit_graph_val,
        _has_remote=_has_remote,
        _has_upstream=_has_upstream,
        _stale_branches=stale,
    )

    has_issues = any(f["severity"] in ("critical", "high", "medium") for f in findings)

    result: dict[str, Any] = {
        "quick": quick,
        "findings": findings,
        "summary": {
            "stale_branches": len(stale),
            "commit_graph": has_commit_graph_val,
            "old_stashes": len(old_stashes),
            "large_blobs": len(large_blobs),
            "gpg_ready": gpg["ready"],
        },
        "git_sizer": sizer,
        "health": {"score": health["score"], "grade": health["grade"]},
    }

    if as_json:
        env = ok_envelope("audit", data=result)
        env["ok"] = not has_issues
        print_json(env)
        return 0 if not has_issues else 1

    if not findings:
        ok(t("repo_good_shape", suffix="  (quick)" if quick else ""))
        return 0

    print_header(t("diagnostic", suffix=" quick" if quick else "", count=str(len(findings))))
    print_blank()
    for f in findings:
        sev = f["severity"]
        if sev in ("critical", "high"):
            print_error_styled(f"  [{sev.upper()}] {f['message']}")
        elif sev == "medium":
            print_bracket(sev.upper(), f["message"])
        else:
            print_dim(f"  [{sev.upper()}] {f['message']}")
        print_dim(f"     {t('audit_fix_label')}:    `{f['fix']}`")
        print_dim(f"     {t('audit_ignore_label')}: {f['cost_of_ignore']}")
        print_blank()

    return 0 if not has_issues else 1
