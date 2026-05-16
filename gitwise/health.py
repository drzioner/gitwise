"""gitwise health — repo health score (0-100) with grade and breakdown."""

import sys
from pathlib import Path

from .git import (
    gpg_status,
    has_commit_graph,
    has_remote,
    has_upstream,
    is_repo,
    repo_root,
    stale_branches,
)
from .git import run as git_run
from .i18n import t
from .output import print_json


def _untracked_count(cwd: Path) -> int:
    r = git_run(["ls-files", "--others", "--exclude-standard"], cwd=cwd, check=False)
    return len(r.stdout.splitlines()) if r.returncode == 0 else 0


def _stash_count(cwd: Path) -> int:
    r = git_run(["stash", "list"], cwd=cwd, check=False)
    return len(r.stdout.splitlines()) if r.returncode == 0 and r.stdout.strip() else 0


def _commit_count(cwd: Path) -> int:
    r = git_run(["rev-list", "--count", "HEAD"], cwd=cwd, check=False)
    return int(r.stdout.strip()) if r.returncode == 0 else 0


def _branch_count(cwd: Path) -> int:
    r = git_run(["branch"], cwd=cwd, check=False)
    return len(r.stdout.splitlines()) if r.returncode == 0 else 0


_GRADE_MAP = [(90, "A"), (75, "B"), (60, "C"), (40, "D"), (0, "F")]


def _grade(score: int) -> str:
    for threshold, letter in _GRADE_MAP:
        if score >= threshold:
            return letter
    return "F"


def compute_health(root: Path) -> dict:
    score = 100
    breakdown: dict[str, int] = {}

    _has_remote = has_remote(root)
    if not _has_remote:
        score -= 20
        breakdown["remote"] = -20

    _has_upstream = has_upstream(root) if _has_remote else False
    if _has_remote and not _has_upstream:
        score -= 10
        breakdown["upstream"] = -10

    gpg = gpg_status(root)
    if not gpg["gpgsign_enabled"]:
        score -= 10
        breakdown["gpg_signing"] = -10

    stale = stale_branches(root)
    if stale:
        penalty = min(len(stale) * 5, 15)
        score -= penalty
        breakdown["stale_branches"] = -penalty

    if not has_commit_graph(root):
        score -= 5
        breakdown["commit_graph"] = -5

    stashes = _stash_count(root)
    if stashes > 3:
        penalty = min((stashes - 3) * 2, 10)
        score -= penalty
        breakdown["old_stashes"] = -penalty

    untracked = _untracked_count(root)
    if untracked > 20:
        penalty = min((untracked - 20), 10)
        score -= penalty
        breakdown["untracked_clutter"] = -penalty

    commits = _commit_count(root)
    if commits == 0:
        score -= 20
        breakdown["no_commits"] = -20

    branches = _branch_count(root)
    if branches > 15:
        penalty = min((branches - 15) * 2, 10)
        score -= penalty
        breakdown["too_many_branches"] = -penalty

    score = max(0, min(100, score))
    return {
        "score": score,
        "grade": _grade(score),
        "breakdown": breakdown,
        "details": {
            "has_remote": _has_remote,
            "has_upstream": _has_upstream,
            "gpg_ready": gpg["ready"],
            "stale_branches": len(stale),
            "stashes": stashes,
            "untracked": untracked,
            "commits": commits,
            "branches": branches,
            "commit_graph": has_commit_graph(root),
        },
    }


def run_health(*, as_json: bool = False) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    h = compute_health(root)

    if as_json:
        print_json({"v": 2, "ok": True, **h})
    else:
        print(t("health_label", score=str(h["score"]), grade=h["grade"]))
        if h["breakdown"]:
            for key, delta in h["breakdown"].items():
                print(f"  {key}: {delta}")

    return 0
