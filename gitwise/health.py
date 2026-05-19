"""gitwise health — repo health score (0-100) with grade and breakdown."""

from pathlib import Path

from .git import (
    gpg_status,
    has_commit_graph,
    has_remote,
    has_upstream,
    require_root,
)
from .git import run as git_run
from .i18n import t
from .output import print_header, print_json, print_status_line


def _untracked_count(cwd: Path) -> int:
    r = git_run(["ls-files", "--others", "--exclude-standard"], cwd=cwd, check=False)
    return len(r.stdout.splitlines()) if r.returncode == 0 else 0


def _stash_count(cwd: Path) -> int:
    r = git_run(["stash", "list"], cwd=cwd, check=False)
    return len(r.stdout.splitlines()) if r.returncode == 0 and r.stdout.strip() else 0


def _commit_count(cwd: Path) -> int:
    r = git_run(["rev-list", "--count", "HEAD"], cwd=cwd, check=False)
    return int(r.stdout.strip()) if r.returncode == 0 else 0


def _branch_info(cwd: Path) -> tuple[int, list[str]]:
    r = git_run(
        ["for-each-ref", "--format=%(refname:short) %(upstream:track)", "refs/heads/"],
        cwd=cwd,
        check=False,
    )
    if r.returncode != 0:
        return 0, []
    branches: list[str] = []
    stale: list[str] = []
    for line in r.stdout.splitlines():
        parts = line.strip().split(" ", 1)
        name = parts[0] if parts else ""
        if name:
            branches.append(name)
        if len(parts) >= 2 and "[gone]" in parts[1]:
            stale.append(name)
    return len(branches), stale


def _breakdown_labels() -> dict[str, str]:
    return {
        "remote": t("health_remote"),
        "upstream": t("health_upstream"),
        "gpg_signing": t("health_gpg_signing"),
        "stale_branches": t("health_stale_branches"),
        "commit_graph": t("health_commit_graph"),
        "old_stashes": t("health_old_stashes"),
        "untracked_clutter": t("health_untracked_clutter"),
        "no_commits": t("health_no_commits"),
        "too_many_branches": t("health_too_many_branches"),
    }


_GRADE_MAP = [(90, "A"), (75, "B"), (60, "C"), (40, "D"), (0, "F")]


def _grade(score: int) -> str:
    for threshold, letter in _GRADE_MAP:
        if score >= threshold:
            return letter
    return "F"


def compute_health(
    root: Path,
    *,
    _has_remote_gpg: dict | None = None,
    _has_commit_graph: bool | None = None,
    _has_remote: bool | None = None,
    _has_upstream: bool | None = None,
    _stale_branches: list | None = None,
) -> dict:
    score = 100
    breakdown: dict[str, int] = {}

    has_rem = _has_remote if _has_remote is not None else has_remote(root)
    if not has_rem:
        score -= 20
        breakdown["remote"] = -20

    has_up = (
        _has_upstream if _has_upstream is not None else (has_upstream(root) if has_rem else False)
    )
    if has_rem and not has_up:
        score -= 10
        breakdown["upstream"] = -10

    gpg = _has_remote_gpg if _has_remote_gpg is not None else gpg_status(root)
    if not gpg["gpgsign_enabled"]:
        score -= 10
        breakdown["gpg_signing"] = -10

    branch_count, stale = _branch_info(root) if _stale_branches is None else (0, _stale_branches)
    if stale:
        penalty = min(len(stale) * 5, 15)
        score -= penalty
        breakdown["stale_branches"] = -penalty

    has_cg = _has_commit_graph if _has_commit_graph is not None else has_commit_graph(root)
    if not has_cg:
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

    branches = branch_count
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
            "has_remote": has_rem,
            "has_upstream": has_up,
            "gpg_ready": gpg["ready"],
            "stale_branches": len(stale),
            "stashes": stashes,
            "untracked": untracked,
            "commits": commits,
            "branches": branches,
            "commit_graph": has_cg,
        },
    }


def run_health(*, as_json: bool = False) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    h = compute_health(root)

    if as_json:
        print_json({"v": 2, "ok": True, **h})
    else:
        print_header(t("health_label", score=str(h["score"]), grade=h["grade"]))
        if h["breakdown"]:
            for key, delta in h["breakdown"].items():
                label = _breakdown_labels().get(key) or key
                is_ok = delta == 0
                print_status_line("✓" if is_ok else "✗", label, str(delta), ok_flag=is_ok)

    return 0
