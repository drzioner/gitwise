"""gitwise conflicts — conflict detection and resolution helper."""

import sys
from pathlib import Path

from .git import is_repo, repo_root
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
    ours: str | None = None,
    theirs: str | None = None,
    as_json: bool = False,
) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    conflicts = _find_conflict_files(root)

    if not conflicts:
        if as_json:
            print_json({"v": 1, "conflicts": [], "count": 0})
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
            print_json({"v": 1, "resolved": len(conflicts), "strategy": "ours", "ok": True})
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
            print_json({"v": 1, "resolved": len(conflicts), "strategy": "theirs", "ok": True})
            return 0
        ok(t("conflicts_resolved_theirs", count=str(len(conflicts))))
        return 0

    details: list[dict[str, str | int]] = []
    for f in conflicts:
        markers = _conflict_markers(root, f)
        details.append({"file": f, "markers": markers})

    if as_json:
        print_json({"v": 1, "conflicts": details, "count": len(conflicts)})
        return 0

    warn(t("conflicts_found", count=str(len(conflicts))))
    for d in details:
        print(f"  {d['file']}  ({d['markers']} markers)")
    print()
    print(t("conflicts_hint"))
    return 1
