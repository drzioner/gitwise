"""gitwise conflicts — conflict detection and resolution helper."""

from pathlib import Path

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import (
    error,
    ok,
    print_accent,
    print_blank,
    print_dim,
    print_header,
    print_json,
    status,
)
from .utils.json_envelope import error_envelope, ok_envelope
from .utils.parsing import stripped_non_empty_lines, to_int


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
    """Resolve conflicts in all files using ``--ours`` or ``--theirs``, then stage."""
    checkout_flag = "--ours" if strategy == "ours" else "--theirs"
    result = git_run(["checkout", checkout_flag, "--"] + conflicts, cwd=root, check=False)
    if result.returncode != 0:
        error(result.stderr.strip())
        return 1
    git_run(["add", "--"] + conflicts, cwd=root, check=False)
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
        print_json(ok_envelope(conflicts=[], count=0))
        return 0
    ok(t("conflicts_none"))
    return 0


def _resolve_by_strategy(*, root: Path, conflicts: list[str], strategy: str, as_json: bool) -> int:
    """Resolve all conflicts with the given strategy and report."""
    rc = _resolve_all_conflicts(root=root, conflicts=conflicts, strategy=strategy)
    if rc != 0:
        return rc
    if as_json:
        print_json(ok_envelope(resolved=len(conflicts), strategy=strategy))
        return 0
    key = "conflicts_resolved_ours" if strategy == "ours" else "conflicts_resolved_theirs"
    ok(t(key, count=str(len(conflicts))))
    return 0


def _report_conflicts(*, details: list[dict[str, str | int]], count: int, as_json: bool) -> int:
    """Print or envelope the conflict report."""
    if as_json:
        print_json(error_envelope(error=t("merge_conflicts"), conflicts=details, count=count))
        return 0
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
