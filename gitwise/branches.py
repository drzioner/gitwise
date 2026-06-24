"""gitwise branches — intelligence dashboard with ahead/behind, merged, stale, worktree info."""

from pathlib import Path
from typing import TypedDict

from gitwise.git import require_root, stale_branches, validate_passthrough_args, worktree_branches
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import error, info, print_dim, print_json, print_table, status
from gitwise.utils.json_envelope import error_envelope, ok_envelope


class BranchEntry(TypedDict):
    """Typed dict for a single branch row in the branches dashboard."""

    name: str
    current: bool
    sha: str
    subject: str
    age: str
    upstream: str | None
    ahead: int | None
    behind: int | None
    tracking: str | None
    in_worktree: bool


def _parse_track_count(tracking: str, marker: str) -> int | None:
    """Extract the integer count for *marker* (``ahead``/``behind``) from a tracking string."""
    if marker not in tracking:
        return None
    raw = tracking.split(marker)[1].split(",")[0].strip().rstrip("]")
    return int(raw) if raw.isdigit() else None


def _parse_branches(raw: str, wt_branches: set[str]) -> list[BranchEntry]:
    """Parse tab-delimited ``for-each-ref`` output into BranchEntry dicts."""
    branches: list[BranchEntry] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        is_current = parts[0].strip() == "*"
        name = parts[1].strip()
        sha = parts[2]
        subject = parts[3]
        age = parts[4]
        tracking = parts[5] if len(parts) > 5 else ""
        upstream = parts[6] if len(parts) > 6 else ""

        branches.append(
            {
                "name": name,
                "current": is_current,
                "sha": sha,
                "subject": subject,
                "age": age,
                "upstream": upstream or None,
                "ahead": _parse_track_count(tracking, "ahead"),
                "behind": _parse_track_count(tracking, "behind"),
                "tracking": tracking or None,
                "in_worktree": name in wt_branches,
            }
        )
    return branches


_VALID_SORT_FIELDS = frozenset(
    {
        "refname",
        "-refname",
        "committerdate",
        "-committerdate",
        "creatordate",
        "-creatordate",
        "authordate",
        "-authordate",
    }
)


def _print_stale_branches(*, names: list[str], as_json: bool) -> int:
    """Print or envelope the list of stale branch names."""
    if not names:
        info(t("no_stale_branches"))
        return 0
    if as_json:
        print_json(ok_envelope("branches", stale_branches=names, count=len(names)))
        return 0
    for branch_name in names:
        print_dim(branch_name)
    return 0


def _fetch_branch_rows(
    *,
    root: Path,
    remote: bool,
    sort: str,
    git_args: list[str] | None = None,
) -> list[BranchEntry] | None:
    """Run ``for-each-ref`` and return parsed branches, or None on git error."""
    wt_branches = worktree_branches(cwd=root)
    ref_pattern = "refs/remotes/" if remote else "refs/heads/"
    fmt = "%(HEAD)\t%(refname:short)\t%(objectname:short)\t%(subject)\t%(committerdate:relative)\t%(upstream:track)\t%(upstream:short)"
    cmd = ["for-each-ref", f"--sort={sort}", f"--format={fmt}"]
    if git_args:
        cmd.extend(git_args)
    cmd.append(ref_pattern)
    result = git_run(cmd, cwd=root, check=False)
    if result.returncode != 0:
        error(t("git_ref_failed", error=result.stderr.strip()))
        return None
    if not result.stdout.strip():
        if remote:
            info(t("no_remote_branches"))
        else:
            info(t("no_commits_yet"))
        return []
    return _parse_branches(result.stdout, wt_branches)


def _build_branch_rows(
    branches: list[BranchEntry],
) -> tuple[list[list[str]], set[int], int | None]:
    """Convert BranchEntry list into display rows, highlight set, and current-row index."""
    rows: list[list[str]] = []
    highlight_rows: set[int] = set()
    current_idx: int | None = None
    for idx, branch_item in enumerate(branches):
        sha = branch_item["sha"][:8]
        subject = branch_item["subject"][:40]
        age = branch_item["age"]
        flags: list[str] = []
        if branch_item["ahead"]:
            flags.append(f"↑{branch_item['ahead']}")
        if branch_item["behind"]:
            flags.append(f"↓{branch_item['behind']}")
        if branch_item["in_worktree"]:
            flags.append("wt")
        if branch_item["upstream"]:
            flags.append(f"→{branch_item['upstream']}")
        status = " ".join(flags) if flags else ""
        name_display = (
            f"* {branch_item['name']}" if branch_item["current"] else branch_item["name"]
        )
        rows.append([name_display, sha, subject, age, status])
        if branch_item["current"]:
            current_idx = idx
            highlight_rows.add(idx)
    return rows, highlight_rows, current_idx


def _print_branch_table(branches: list[BranchEntry]) -> None:
    """Render the branch dashboard table."""
    columns = [
        (t("col_branch"), "name"),
        (t("col_sha"), "sha"),
        (t("col_subject"), "subject"),
        (t("col_age"), "age"),
        (t("col_status"), "status"),
    ]
    rows, highlight_rows, current_idx = _build_branch_rows(branches)
    print_table(
        title=t("branch_list_title_current", branch=branches[current_idx]["name"])
        if current_idx is not None
        else t("branch_list_title"),
        columns=columns,
        rows=rows,
        highlight_rows=highlight_rows,
    )


def _validate_sort_field(sort: str) -> bool:
    """Return False and print an error if *sort* is not in the allowed set."""
    if sort in _VALID_SORT_FIELDS:
        return True
    error(t("invalid_sort_field", field=sort))
    return False


def run_branches(
    *,
    stale: bool = False,
    remote: bool = False,
    sort: str = "refname",
    as_json: bool = False,
    git_args: list[str] | None = None,
) -> int:
    """Entry point for the ``gitwise branches`` command."""
    root = require_root(as_json=as_json, command="branches")
    if root is None:
        return 1

    # for-each-ref parses a fixed tabulated --format; format-changing / count
    # flags from --git-arg would silently corrupt _fetch_branch_rows parsing.
    _BRANCHES_FORMAT_BREAKERS = ("--format", "--shell", "--python", "--perl", "--tcl", "--count")
    denied = validate_passthrough_args(git_args)
    if denied is None and git_args:
        for arg in git_args:
            token = arg.split("=", 1)[0]
            if token in _BRANCHES_FORMAT_BREAKERS:
                denied = (
                    f"--git-arg refuses '{token}' on branches (would break the parsed --format)"
                )
                break
    if denied is not None:
        if as_json:
            print_json(error_envelope("branches", error=denied, code="git_arg_denied"))
        else:
            error(denied)
        return 1

    if stale:
        with status(t("status_analyzing_branches")):
            names = stale_branches(cwd=root)
        return _print_stale_branches(names=names, as_json=as_json)

    if not _validate_sort_field(sort):
        return 1

    with status(t("status_analyzing_branches")):
        branches = _fetch_branch_rows(root=root, remote=remote, sort=sort, git_args=git_args)
    if branches is None:
        return 1
    if not branches:
        return 0

    if as_json:
        print_json(ok_envelope("branches", branches=branches, count=len(branches)))
        return 0
    _print_branch_table(branches)

    return 0
