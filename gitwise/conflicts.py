"""gitwise conflicts — conflict detection and resolution helper."""

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
    """Return the bytes of a staged blob (e.g. ``:2:path`` = ours), empty if missing."""
    r = git_run(["show", stage_ref], cwd=root, check=False)
    return r.stdout.encode("utf-8") if r.returncode == 0 else b""


def _resolve_union(*, root: Path, conflicts: list[str]) -> int:
    """Resolve conflicts with ``git merge-file --union`` (keeps both sides, no markers).

    For each file, materialize the base (:1:), ours (:2:), theirs (:3:) stage
    blobs, union-merge them, write the result back, and stage it.
    """
    for filepath in conflicts:
        ours = _stage_blob(root, f":2:{filepath}")
        base = _stage_blob(root, f":1:{filepath}")
        theirs = _stage_blob(root, f":3:{filepath}")
        with tempfile.TemporaryDirectory() as tmp:
            ours_p = Path(tmp) / "ours"
            base_p = Path(tmp) / "base"
            theirs_p = Path(tmp) / "theirs"
            ours_p.write_bytes(ours)
            base_p.write_bytes(base)
            theirs_p.write_bytes(theirs)
            merged = git_run(
                ["merge-file", "--union", "-p", str(ours_p), str(base_p), str(theirs_p)],
                cwd=root,
                check=False,
            )
            if merged.returncode not in (0, 1):
                error(merged.stderr.strip() or t("conflicts_union_failed", file=filepath))
                return 1
            (root / filepath).write_bytes(merged.stdout.encode("utf-8"))
        git_run(["add", "--", filepath], cwd=root, check=False)
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


def _resolve_by_strategy(*, root: Path, conflicts: list[str], strategy: str, as_json: bool) -> int:
    """Resolve all conflicts with the given strategy and report."""
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
            error_envelope("conflicts", error=t("merge_conflicts"), conflicts=details, count=count)
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
    as_json: bool = False,
) -> int:
    """Entry point for the ``gitwise conflicts`` command."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    with status(t("status_detecting_conflicts")):
        conflicts = _find_conflict_files(root)

    if not conflicts:
        return _report_no_conflicts(as_json=as_json)

    if union:
        return _resolve_by_strategy(
            root=root, conflicts=conflicts, strategy="union", as_json=as_json
        )

    if ours:
        return _resolve_by_strategy(
            root=root, conflicts=conflicts, strategy="ours", as_json=as_json
        )

    if theirs:
        return _resolve_by_strategy(
            root=root,
            conflicts=conflicts,
            strategy="theirs",
            as_json=as_json,
        )

    details = _conflict_details(root, conflicts)
    return _report_conflicts(details=details, count=len(conflicts), as_json=as_json)
