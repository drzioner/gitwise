"""gitwise conflicts — conflict detection and resolution helper."""

import subprocess
import tempfile
from pathlib import Path

from gitwise.git import require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import (
    error,
    ok,
    print_accent,
    print_blank,
    print_dim,
    print_header,
    print_json,
    status,
)
from gitwise.utils.json_envelope import error_envelope, ok_envelope
from gitwise.utils.parsing import stripped_non_empty_lines, to_int


def _git_bytes(args: list[str], *, cwd: Path) -> tuple[int, bytes, bytes]:
    """Run git capturing raw bytes (no text decoding) for binary-safe I/O."""
    r = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        timeout=120,
    )
    return r.returncode, r.stdout, r.stderr


def _find_conflict_files(root: Path) -> list[str]:
    """Return file paths with unmerged (U) status."""
    r = git_run(["diff", "--name-only", "--diff-filter=U"], cwd=root, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    return stripped_non_empty_lines(r.stdout)


def _conflict_markers(root: Path, filepath: str) -> int:
    """Count ``<<<<<<<`` conflict markers in *filepath*."""
    r = git_run(["grep", "-c", "<<<<<<< ", "--", filepath], cwd=root, check=False)
    if r.returncode != 0:
        return 0
    count = 0
    for line in r.stdout.splitlines():
        marker_count = line.rsplit(":", 1)[-1]
        count += max(to_int(marker_count, default=0), 0)
    return count


def _resolve_all_conflicts(*, root: Path, conflicts: list[str], strategy: str) -> int:
    """Resolve conflicts in all files using ``--ours``/``--theirs``, then stage."""
    if strategy == "union":
        return _resolve_union(root=root, conflicts=conflicts)
    checkout_flag = "--ours" if strategy == "ours" else "--theirs"
    result = git_run(["checkout", checkout_flag, "--"] + conflicts, cwd=root, check=False)
    if result.returncode != 0:
        error(result.stderr.strip())
        return 1
    git_run(["add", "--"] + conflicts, cwd=root, check=False)
    return 0


def _stage_blob(root: Path, stage_ref: str) -> bytes:
    """Return the raw bytes of a staged blob (e.g. ``:2:path`` = ours).

    Binary-safe (no UTF-8 round-trip). Returns b"" only for a missing base
    (``:1:``); callers treat base absence as an empty common ancestor.
    """
    rc, out, _ = _git_bytes(["show", stage_ref], cwd=root)
    return out if rc == 0 else b""


def _resolve_union(*, root: Path, conflicts: list[str]) -> int:
    """Resolve conflicts with ``git merge-file --union`` (keeps both sides, no markers).

    For each file, materialize the base (:1:), ours (:2:), theirs (:3:) stage
    blobs as raw bytes, union-merge them, write the result back, and stage it.
    Uses bytes throughout so binary/non-UTF-8 conflict files keep full fidelity.
    """
    for filepath in conflicts:
        ours = _stage_blob(root, f":2:{filepath}")
        base = _stage_blob(root, f":1:{filepath}")
        theirs = _stage_blob(root, f":3:{filepath}")
        if not ours and not theirs:
            error(t("conflicts_union_failed", file=filepath))
            return 1
        with tempfile.TemporaryDirectory() as tmp:
            ours_p = Path(tmp) / "ours"
            base_p = Path(tmp) / "base"
            theirs_p = Path(tmp) / "theirs"
            ours_p.write_bytes(ours)
            base_p.write_bytes(base)
            theirs_p.write_bytes(theirs)
            rc, out, err = _git_bytes(
                ["merge-file", "--union", "-p", str(ours_p), str(base_p), str(theirs_p)],
                cwd=root,
            )
            if rc not in (0, 1):
                error(
                    err.decode("utf-8", errors="replace").strip()
                    or t("conflicts_union_failed", file=filepath)
                )
                return 1
            (root / filepath).write_bytes(out)
        add_rc, _, add_err = _git_bytes(["add", "--", filepath], cwd=root)
        if add_rc != 0:
            error(
                add_err.decode("utf-8", errors="replace").strip()
                or t("conflicts_union_failed", file=filepath)
            )
            return 1
    return 0


def _conflict_details(root: Path, conflicts: list[str]) -> list[dict[str, str | int]]:
    """Return ``[{file, markers}]`` with conflict marker counts per file."""
    details: list[dict[str, str | int]] = []
    for file_path in conflicts:
        markers = _conflict_markers(root, file_path)
        details.append({"file": file_path, "markers": markers})
    return details


def _report_no_conflicts(*, as_json: bool) -> int:
    """Print or envelope a clean conflicts report."""
    if as_json:
        print_json(ok_envelope("conflicts", conflicts=[], count=0))
        return 0
    ok(t("conflicts_none"))
    return 0


def _resolve_by_strategy(
    *,
    root: Path,
    conflicts: list[str],
    strategy: str,
    as_json: bool,
    dry_run: bool = False,
) -> int:
    """Resolve all conflicts with the given strategy and report."""
    if dry_run:
        if as_json:
            print_json(
                ok_envelope(
                    "conflicts",
                    dry_run=True,
                    strategy=strategy,
                    would_resolve=conflicts,
                    count=len(conflicts),
                )
            )
        else:
            print_header(t("conflicts_dry_run", strategy=strategy, count=str(len(conflicts))))
            for file_path in conflicts:
                print_accent(f"  {file_path}")
            print_dim(t("dry_run_no_exec"))
        return 0
    rc = _resolve_all_conflicts(root=root, conflicts=conflicts, strategy=strategy)
    if rc != 0:
        return rc
    if as_json:
        print_json(ok_envelope("conflicts", resolved=len(conflicts), strategy=strategy))
        return 0
    key = {
        "ours": "conflicts_resolved_ours",
        "theirs": "conflicts_resolved_theirs",
        "union": "conflicts_resolved_union",
    }[strategy]
    ok(t(key, count=str(len(conflicts))))
    return 0


def _report_conflicts(*, details: list[dict[str, str | int]], count: int, as_json: bool) -> int:
    """Print or envelope the conflict report."""
    if as_json:
        print_json(
            error_envelope(
                "conflicts",
                error=t("merge_conflicts"),
                code="merge_conflicts",
                conflicts=details,
                count=count,
            )
        )
        return 1
    print_header(t("conflicts_found", count=str(count)))
    for detail in details:
        print_accent(f"  {detail['file']}  ({detail['markers']} {t('markers_label')})")
    print_blank()
    print_dim(t("conflicts_hint"))
    return 1


def run_conflicts(
    *,
    ours: bool = False,
    theirs: bool = False,
    union: bool = False,
    files: list[str] | None = None,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    """Entry point for the ``gitwise conflicts`` command.

    With a strategy flag (``--ours``/``--theirs``/``--union``) it resolves;
    ``--dry-run`` reports what would be resolved without touching the tree, and
    ``--files`` scopes resolution to a subset of the conflicted paths.
    """
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    with status(t("status_detecting_conflicts")):
        conflicts = _find_conflict_files(root)

    if not conflicts:
        return _report_no_conflicts(as_json=as_json)

    if files:
        wanted = set(files)
        conflicts = [c for c in conflicts if c in wanted]

    if not conflicts:
        if as_json:
            print_json(
                ok_envelope(
                    "conflicts",
                    conflicts=[],
                    count=0,
                    note="none of the requested --files are conflicted",
                )
            )
            return 0
        ok(t("conflicts_none"))
        return 0

    strategy = "union" if union else ("ours" if ours else ("theirs" if theirs else ""))
    if strategy:
        return _resolve_by_strategy(
            root=root,
            conflicts=conflicts,
            strategy=strategy,
            as_json=as_json,
            dry_run=dry_run,
        )

    details = _conflict_details(root, conflicts)
    return _report_conflicts(details=details, count=len(conflicts), as_json=as_json)
