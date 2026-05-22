"""gitwise branches — intelligence dashboard with ahead/behind, merged, stale, worktree info."""

from .git import require_root, stale_branches, worktree_branches
from .git import run as git_run
from .i18n import t
from .output import error, info, print_dim, print_json, print_table
from .utils.json_envelope import ok_envelope


def _parse_branches(raw: str, wt_branches: set[str]) -> list[dict[str, str]]:
    branches: list[dict[str, str]] = []
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

        ahead = behind = ""
        if "[ahead" in tracking:
            ahead = tracking.split("ahead")[1].split(",")[0].strip().rstrip("]")
        if "behind" in tracking:
            behind = tracking.split("behind")[1].strip().rstrip("]")

        branches.append(
            {
                "name": name,
                "current": str(is_current).lower(),
                "sha": sha,
                "subject": subject,
                "age": age,
                "upstream": upstream,
                "ahead": ahead,
                "behind": behind,
                "tracking": tracking,
                "in_worktree": str(name in wt_branches).lower(),
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
    if not names:
        info(t("no_stale_branches"))
        return 0
    if as_json:
        print_json(ok_envelope(stale_branches=names, count=len(names)))
        return 0
    for branch_name in names:
        print_dim(branch_name)
    return 0


def _fetch_branch_rows(*, root, remote: bool, sort: str) -> list[dict[str, str]] | None:
    wt_branches = worktree_branches(cwd=root)
    ref_pattern = "refs/remotes/" if remote else "refs/heads/"
    fmt = "%(HEAD)\t%(refname:short)\t%(objectname:short)\t%(subject)\t%(committerdate:relative)\t%(upstream:track)\t%(upstream:short)"
    result = git_run(
        ["for-each-ref", f"--sort={sort}", f"--format={fmt}", ref_pattern],
        cwd=root,
        check=False,
    )
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
    branches: list[dict[str, str]],
) -> tuple[list[list[str]], set[int], int | None]:
    rows: list[list[str]] = []
    highlight_rows: set[int] = set()
    current_idx: int | None = None
    for idx, branch_item in enumerate(branches):
        sha = branch_item["sha"][:8]
        subject = branch_item["subject"][:40]
        age = branch_item.get("age", "")
        flags: list[str] = []
        if branch_item.get("ahead"):
            flags.append(f"↑{branch_item['ahead']}")
        if branch_item.get("behind"):
            flags.append(f"↓{branch_item['behind']}")
        if branch_item.get("in_worktree") == "true":
            flags.append("wt")
        if branch_item.get("upstream"):
            flags.append(f"→{branch_item['upstream']}")
        status = " ".join(flags) if flags else ""
        name_display = (
            f"* {branch_item['name']}" if branch_item["current"] == "true" else branch_item["name"]
        )
        rows.append([name_display, sha, subject, age, status])
        if branch_item["current"] == "true":
            current_idx = idx
            highlight_rows.add(idx)
    return rows, highlight_rows, current_idx


def _print_branch_table(branches: list[dict[str, str]]) -> None:
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
) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    if stale:
        names = stale_branches(cwd=root)
        return _print_stale_branches(names=names, as_json=as_json)

    if not _validate_sort_field(sort):
        return 1

    branches = _fetch_branch_rows(root=root, remote=remote, sort=sort)
    if branches is None:
        return 1
    if not branches:
        return 0

    if as_json:
        print_json(ok_envelope(branches=branches, count=len(branches)))
        return 0
    _print_branch_table(branches)

    return 0
