"""gitwise health — repo health score (0-100) with grade and breakdown."""

from pathlib import Path
from typing import TypedDict

from gitwise.git import (
    gpg_status,
    has_commit_graph,
    has_remote,
    has_upstream,
    require_root,
)
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import print_header, print_json, print_status_line, status
from gitwise.utils.json_envelope import ok_envelope
from gitwise.utils.parsing import non_empty_lines, to_int


class HealthDetails(TypedDict):
    """Detailed booleans and counts that feed into the health score."""

    has_remote: bool
    has_upstream: bool
    gpg_ready: bool
    stale_branches: int
    stashes: int
    untracked: int
    commits: int
    branches: int
    commit_graph: bool


class HealthResult(TypedDict):
    """Aggregated health score, letter grade, and breakdown."""

    score: int
    grade: str
    breakdown: dict[str, int]
    details: HealthDetails


def _untracked_count(cwd: Path) -> int:
    """Count untracked files not matched by .gitignore."""
    r = git_run(["ls-files", "--others", "--exclude-standard"], cwd=cwd, check=False)
    return len(non_empty_lines(r.stdout)) if r.returncode == 0 else 0


def _stash_count(cwd: Path) -> int:
    """Count stash entries."""
    r = git_run(["stash", "list"], cwd=cwd, check=False)
    return len(non_empty_lines(r.stdout)) if r.returncode == 0 else 0


def _commit_count(cwd: Path) -> int:
    """Count reachable commits on HEAD."""
    r = git_run(["rev-list", "--count", "HEAD"], cwd=cwd, check=False)
    return to_int(r.stdout, default=0) if r.returncode == 0 else 0


def _branch_info(cwd: Path) -> tuple[int, list[str]]:
    """Return total local branch count and list of stale branch names."""
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
    """Return localised labels for each breakdown key."""
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

# Health-score thresholds. Centralized as named constants (review F-25) so the
# penalties are tunable in one place rather than scattered magic numbers.
_STALE_BRANCH_PENALTY_PER = 5
_STALE_BRANCH_PENALTY_MAX = 15
_TOO_MANY_BRANCHES_THRESHOLD = 15
_TOO_MANY_BRANCHES_PENALTY_PER = 2
_TOO_MANY_BRANCHES_PENALTY_MAX = 10
_OLD_STASHES_THRESHOLD = 3
_OLD_STASHES_PENALTY_PER = 2
_OLD_STASHES_PENALTY_MAX = 10
_UNTRACKED_CLUTTER_THRESHOLD = 20
_UNTRACKED_CLUTTER_PENALTY_MAX = 10


def _grade(score: int) -> str:
    """Map a 0-100 score to a letter grade (A/B/C/D/F)."""
    for threshold, letter in _GRADE_MAP:
        if score >= threshold:
            return letter
    return "F"


def _apply_remote_penalties(
    *, score: int, breakdown: dict[str, int], root: Path
) -> tuple[int, bool, bool]:
    """Deduct points for missing remote/upstream. Returns (score, has_remote, has_upstream)."""
    has_rem = has_remote(root)
    has_up = has_upstream(root) if has_rem else False
    if not has_rem:
        score -= 20
        breakdown["remote"] = -20
    if has_rem and not has_up:
        score -= 10
        breakdown["upstream"] = -10
    return score, has_rem, has_up


def _apply_gpg_penalty(*, score: int, breakdown: dict[str, int], root: Path) -> tuple[int, dict]:
    """Deduct points if GPG signing is disabled. Returns (score, gpg_info)."""
    gpg = gpg_status(root)
    if not gpg["gpgsign_enabled"]:
        score -= 10
        breakdown["gpg_signing"] = -10
    return score, gpg


def _apply_branch_penalties(
    *,
    score: int,
    breakdown: dict[str, int],
    root: Path,
    stale_override: list[str] | None,
) -> tuple[int, int, list[str]]:
    """Deduct points for stale and excess branches. Returns (score, branch_count, stale_list)."""
    branch_count, stale = _branch_info(root) if stale_override is None else (0, stale_override)
    if stale:
        penalty = min(len(stale) * _STALE_BRANCH_PENALTY_PER, _STALE_BRANCH_PENALTY_MAX)
        score -= penalty
        breakdown["stale_branches"] = -penalty
    if branch_count > _TOO_MANY_BRANCHES_THRESHOLD:
        penalty = min(
            (branch_count - _TOO_MANY_BRANCHES_THRESHOLD) * _TOO_MANY_BRANCHES_PENALTY_PER,
            _TOO_MANY_BRANCHES_PENALTY_MAX,
        )
        score -= penalty
        breakdown["too_many_branches"] = -penalty
    return score, branch_count, stale


def _apply_commit_graph_penalty(
    *,
    score: int,
    breakdown: dict[str, int],
    root: Path,
    commit_graph_override: bool | None,
) -> tuple[int, bool]:
    """Deduct points for missing commit-graph. Returns (score, has_commit_graph)."""
    has_cg = commit_graph_override if commit_graph_override is not None else has_commit_graph(root)
    if not has_cg:
        score -= 5
        breakdown["commit_graph"] = -5
    return score, has_cg


def _apply_repo_size_penalties(
    *, score: int, breakdown: dict[str, int], root: Path
) -> tuple[int, int, int, int]:
    """Deduct points for old stashes, untracked clutter, and zero commits. Returns (score, stashes, untracked, commits)."""
    stashes = _stash_count(root)
    if stashes > _OLD_STASHES_THRESHOLD:
        penalty = min(
            (stashes - _OLD_STASHES_THRESHOLD) * _OLD_STASHES_PENALTY_PER,
            _OLD_STASHES_PENALTY_MAX,
        )
        score -= penalty
        breakdown["old_stashes"] = -penalty

    untracked = _untracked_count(root)
    if untracked > _UNTRACKED_CLUTTER_THRESHOLD:
        penalty = min((untracked - _UNTRACKED_CLUTTER_THRESHOLD), _UNTRACKED_CLUTTER_PENALTY_MAX)
        score -= penalty
        breakdown["untracked_clutter"] = -penalty

    commits = _commit_count(root)
    if commits == 0:
        score -= 20
        breakdown["no_commits"] = -20

    return score, stashes, untracked, commits


def _remote_state(
    *,
    root: Path,
    score: int,
    breakdown: dict[str, int],
    has_remote_override: bool | None,
    has_upstream_override: bool | None,
) -> tuple[int, bool, bool]:
    """Compute remote state, using overrides when provided for testability."""
    if has_remote_override is not None or has_upstream_override is not None:
        has_rem = has_remote_override if has_remote_override is not None else has_remote(root)
        has_up = (
            has_upstream_override
            if has_upstream_override is not None
            else (has_upstream(root) if has_rem else False)
        )
        if not has_rem:
            score -= 20
            breakdown["remote"] = -20
        if has_rem and not has_up:
            score -= 10
            breakdown["upstream"] = -10
        return score, has_rem, has_up
    return _apply_remote_penalties(score=score, breakdown=breakdown, root=root)


def _gpg_state(
    *,
    root: Path,
    score: int,
    breakdown: dict[str, int],
    gpg_override: dict | None,
) -> tuple[int, dict]:
    """Compute GPG state, using override when provided for testability."""
    if gpg_override is not None:
        gpg = gpg_override
        if not gpg["gpgsign_enabled"]:
            score -= 10
            breakdown["gpg_signing"] = -10
        return score, gpg
    return _apply_gpg_penalty(score=score, breakdown=breakdown, root=root)


def _build_health_result(
    *,
    score: int,
    breakdown: dict[str, int],
    has_rem: bool,
    has_up: bool,
    gpg: dict,
    stale: list[str],
    stashes: int,
    untracked: int,
    commits: int,
    branches: int,
    has_cg: bool,
) -> HealthResult:
    """Assemble the final HealthResult, clamping the score to 0-100."""
    bounded_score = max(0, min(100, score))
    return {
        "score": bounded_score,
        "grade": _grade(bounded_score),
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


def _remaining_health_state(
    *,
    root: Path,
    score: int,
    breakdown: dict[str, int],
    stale_override: list[str] | None,
    commit_graph_override: bool | None,
) -> tuple[int, int, list[str], bool, int, int, int]:
    """Apply branch, commit-graph, and repo-size penalties in sequence."""
    score, branches, stale = _apply_branch_penalties(
        score=score,
        breakdown=breakdown,
        root=root,
        stale_override=stale_override,
    )
    score, has_cg = _apply_commit_graph_penalty(
        score=score,
        breakdown=breakdown,
        root=root,
        commit_graph_override=commit_graph_override,
    )
    score, stashes, untracked, commits = _apply_repo_size_penalties(
        score=score,
        breakdown=breakdown,
        root=root,
    )
    return score, branches, stale, has_cg, stashes, untracked, commits


def compute_health(
    root: Path,
    *,
    _gpg_override: dict | None = None,
    _has_commit_graph: bool | None = None,
    _has_remote: bool | None = None,
    _has_upstream: bool | None = None,
    _stale_branches: list[str] | None = None,
) -> HealthResult:
    """Compute the 0-100 health score for *root*.

    Underscore-prefixed overrides allow deterministic testing without
    touching the real git repo.
    """
    score = 100
    breakdown: dict[str, int] = {}
    score, has_rem, has_up = _remote_state(
        root=root,
        score=score,
        breakdown=breakdown,
        has_remote_override=_has_remote,
        has_upstream_override=_has_upstream,
    )
    score, gpg = _gpg_state(
        root=root,
        score=score,
        breakdown=breakdown,
        gpg_override=_gpg_override,
    )

    score, branches, stale, has_cg, stashes, untracked, commits = _remaining_health_state(
        root=root,
        score=score,
        breakdown=breakdown,
        stale_override=_stale_branches,
        commit_graph_override=_has_commit_graph,
    )

    return _build_health_result(
        score=score,
        breakdown=breakdown,
        has_rem=has_rem,
        has_up=has_up,
        gpg=gpg,
        stale=stale,
        stashes=stashes,
        untracked=untracked,
        commits=commits,
        branches=branches,
        has_cg=has_cg,
    )


def run_health(*, as_json: bool = False) -> int:
    """Entry point for the ``gitwise health`` command."""
    root = require_root()
    if root is None:
        return 1

    with status(t("status_health_scan")):
        h = compute_health(root)

    if as_json:
        print_json(ok_envelope("health", data=h))
    else:
        print_header(t("health_label", score=str(h["score"]), grade=h["grade"]))
        if h["breakdown"]:
            for key, delta in h["breakdown"].items():
                label = _breakdown_labels().get(key) or key
                is_ok = delta == 0
                print_status_line("✓" if is_ok else "✗", label, str(delta), ok_flag=is_ok)

    return 0
