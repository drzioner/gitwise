"""gitwise conflicts — conflict detection and resolution helper."""

import sys
from pathlib import Path

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import ok, print_json, warn


def _find_conflict_files(root: Path) -> list[str]:
    r = git_run(["diff", "--name-only", "--diff-filter=U"], cwd=root, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def _conflict_markers(root: Path, filepath: str) -> int:
    r = git_run(["grep", "-c", "<<<<<<< ", "--", filepath], cwd=root, check=False)
    if r.returncode != 0:
        return 0
    count = 0
    for line in r.stdout.splitlines():
        try:
            count += int(line.rsplit(":", 1)[-1])
        except (ValueError, IndexError):
            pass
    return count


def run_conflicts(
    *,
    ours: bool = False,
    theirs: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    conflicts = _find_conflict_files(root)

    if not conflicts:
        if as_json:
            print_json({"v": 2, "conflicts": [], "count": 0, "ok": True})
            return 0
        ok(t("conflicts_none"))
        return 0

    if ours:
        r = git_run(["checkout", "--ours", "--"] + conflicts, cwd=root, check=False)
        if r.returncode != 0:
            print(r.stderr.strip(), file=sys.stderr)
            return 1
        git_run(["add"] + conflicts, cwd=root, check=False)
        if as_json:
            print_json({"v": 2, "resolved": len(conflicts), "strategy": "ours", "ok": True})
            return 0
        ok(t("conflicts_resolved_ours", count=str(len(conflicts))))
        return 0

    if theirs:
        r = git_run(["checkout", "--theirs", "--"] + conflicts, cwd=root, check=False)
        if r.returncode != 0:
            print(r.stderr.strip(), file=sys.stderr)
            return 1
        git_run(["add"] + conflicts, cwd=root, check=False)
        if as_json:
            print_json({"v": 2, "resolved": len(conflicts), "strategy": "theirs", "ok": True})
            return 0
        ok(t("conflicts_resolved_theirs", count=str(len(conflicts))))
        return 0

    details: list[dict[str, str | int]] = []
    for f in conflicts:
        markers = _conflict_markers(root, f)
        details.append({"file": f, "markers": markers})

    if as_json:
        print_json({"v": 2, "conflicts": details, "count": len(conflicts), "ok": False})
        return 0

    warn(t("conflicts_found", count=str(len(conflicts))))
    for d in details:
        print(f"  {d['file']}  ({d['markers']} {t('markers_label')})")
    print()
    print(t("conflicts_hint"))
    return 1
