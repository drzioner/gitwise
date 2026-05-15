"""Read-only repo diagnostics with human/JSON dual output."""

import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .git import git_dir, gpg_status, is_repo, repo_root, stale_branches
from .git import run as git_run
from .output import bat_pipe, error, ok, print_json

_STALE_DAYS = 30
_LARGE_BLOB_MIN_BYTES = 1_000_000  # 1MB


def _check_commit_graph(cwd: Path) -> bool:
    gd = git_dir(cwd)
    if gd is None:
        return False
    return (gd / "objects" / "info" / "commit-graph").exists() or (
        gd / "objects" / "info" / "commit-graphs" / "commit-graph-chain"
    ).exists()


def _check_fsmonitor(cwd: Path) -> bool:
    r = git_run(["config", "--get", "core.fsmonitor"], cwd=cwd, check=False)
    return r.returncode == 0 and r.stdout.strip().lower() in ("true", "1")


def _find_old_stashes(cwd: Path) -> list[dict]:
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
            continue
    return old


def _find_large_blobs(cwd: Path, top_n: int = 3) -> list[dict]:
    # Abort if no commits yet
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
            continue
    blobs.sort(key=lambda b: b["size"], reverse=True)
    return blobs[:top_n]


def _check_mixed_staging(cwd: Path) -> bool:
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
    if gpg["gpgsign_enabled"] and not gpg["gpg_binary"]:
        return [
            {
                "type": "gpg_binary_missing",
                "severity": "high",
                "message": "commit.gpgsign=true pero gpg no instalado — los commits fallarán",
                "fix": "brew install gnupg",
                "cost_of_fix": "trivial",
                "cost_of_ignore": "ningún git commit funcionará hasta instalarlo",
            }
        ]
    if gpg["gpgsign_enabled"] and not gpg["signing_key_set"]:
        return [
            {
                "type": "gpg_key_missing",
                "severity": "high",
                "message": "commit.gpgsign=true pero user.signingkey no configurado",
                "fix": "git config user.signingkey <key-id>",
                "cost_of_fix": "trivial",
                "cost_of_ignore": "ningún git commit funcionará",
            }
        ]
    if not gpg["gpgsign_enabled"]:
        return [
            {
                "type": "gpg_not_configured",
                "severity": "info",
                "message": "GPG no configurado — commits sin firma digital",
                "fix": "brew install gnupg  →  git config --global commit.gpgsign true",
                "cost_of_fix": "requiere crear llave GPG (~5 min)",
                "cost_of_ignore": "commits no verificables criptográficamente",
            }
        ]
    return []


_SEVERITY_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}


def run_audit(*, quick: bool = False, as_json: bool = False) -> int:
    if not is_repo():
        error("no es un repositorio git")
        return 1

    cwd = repo_root()
    if cwd is None:
        error("no se pudo determinar la raíz del repositorio")
        return 1

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
                "message": f"{len(stale)} rama(s) con upstream eliminado ([gone])",
                "fix": "gitwise clean --branches --dry-run",
                "cost_of_fix": "trivial",
                "cost_of_ignore": "clutter en `git branch`; confunde agentes Claude",
            }
        )

    has_commit_graph = _check_commit_graph(cwd)
    if not has_commit_graph:
        findings.append(
            {
                "type": "missing_commit_graph",
                "severity": "medium",
                "message": "commit-graph ausente — git log puede ser 2-10x más lento",
                "fix": "gitwise optimize --yes",
                "cost_of_fix": "trivial (segundos)",
                "cost_of_ignore": "latencia acumulada en cada sesión de Claude",
            }
        )

    if platform.system() == "Darwin":
        if not _check_fsmonitor(cwd):
            findings.append(
                {
                    "type": "fsmonitor_disabled",
                    "severity": "low",
                    "message": "core.fsmonitor desactivado — git status más lento en repos grandes",
                    "fix": "gitwise setup --yes",
                    "cost_of_fix": "trivial",
                    "cost_of_ignore": "~50ms extra por git status en repos medianos",
                }
            )

    old_stashes = _find_old_stashes(cwd)
    if old_stashes:
        findings.append(
            {
                "type": "old_stashes",
                "severity": "low",
                "count": len(old_stashes),
                "stashes": old_stashes,
                "message": f"{len(old_stashes)} stash(es) con más de {_STALE_DAYS} días",
                "fix": "git stash drop stash@{N}  o  git stash clear",
                "cost_of_fix": "irreversible — revisar antes",
                "cost_of_ignore": "acumulación de WIP probablemente irrelevante",
            }
        )

    large_blobs: list[dict] = []
    if not quick:
        large_blobs = _find_large_blobs(cwd)
        if large_blobs:
            findings.append(
                {
                    "type": "large_blobs",
                    "severity": "low",
                    "count": len(large_blobs),
                    "blobs": large_blobs,
                    "message": f"{len(large_blobs)} archivo(s) grandes (≥1MB) en HEAD",
                    "fix": "considerar git-lfs o eliminación de la historia",
                    "cost_of_fix": "depende del archivo",
                    "cost_of_ignore": "lentitud en clone y fetch",
                }
            )

    if _check_mixed_staging(cwd):
        findings.append(
            {
                "type": "mixed_staging",
                "severity": "info",
                "message": "hay archivos staged y unstaged — el commit no sería atómico",
                "fix": "revisar con git diff --staged antes de commitear",
                "cost_of_fix": "n/a",
                "cost_of_ignore": "commits no atómicos dificultan el historial",
            }
        )

    sizer = _run_git_sizer(cwd) if not quick else None
    has_issues = any(f["severity"] in ("critical", "high", "medium") for f in findings)

    result: dict[str, Any] = {
        "v": 1,
        "ok": not has_issues,
        "quick": quick,
        "findings": findings,
        "summary": {
            "stale_branches": len(stale),
            "commit_graph": has_commit_graph,
            "old_stashes": len(old_stashes),
            "large_blobs": len(large_blobs),
            "gpg_ready": gpg["ready"],
        },
        "git_sizer": sizer,
    }

    if as_json:
        print_json(result)
        return 0 if not has_issues else 1

    if not findings:
        ok(f"repositorio en buen estado{'  (quick)' if quick else ''}")
        return 0

    lines = [
        f"{'Diagnóstico rápido' if quick else 'Diagnóstico'} — {len(findings)} observación(es):",
        "",
    ]
    for f in findings:
        icon = _SEVERITY_ICON.get(f["severity"], "•")
        lines.append(f"  {icon} [{f['severity'].upper()}] {f['message']}")
        lines.append(f"     fix:    `{f['fix']}`")
        lines.append(f"     ignora: {f['cost_of_ignore']}")
        lines.append("")

    bat_pipe("\n".join(lines), language="Markdown")

    return 0 if not has_issues else 1
