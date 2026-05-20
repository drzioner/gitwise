"""gitwise branches — intelligence dashboard with ahead/behind, merged, stale, worktree info."""

from .git import require_root, stale_branches, worktree_branches
from .git import run as git_run
from .i18n import t
from .output import error, info, print_dim, print_json, print_table


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
        if not names:
            info(t("no_stale_branches"))
            return 0
        if as_json:
            print_json({"v": 2, "ok": True, "stale_branches": names, "count": len(names)})
            return 0
        for n in names:
            print_dim(n)
        return 0

    if sort not in _VALID_SORT_FIELDS:
        error(t("invalid_sort_field", field=sort))
        return 1

    wt_branches = worktree_branches(cwd=root)

    ref_pattern = "refs/remotes/" if remote else "refs/heads/"
    fmt = "%(HEAD)\t%(refname:short)\t%(objectname:short)\t%(subject)\t%(committerdate:relative)\t%(upstream:track)\t%(upstream:short)"

    r = git_run(
        ["for-each-ref", f"--sort={sort}", f"--format={fmt}", ref_pattern],
        cwd=root,
        check=False,
    )
    if r.returncode != 0:
        error(t("git_ref_failed", error=r.stderr.strip()))
        return 1

    if not r.stdout.strip():
        if remote:
            info(t("no_remote_branches"))
        else:
            info(t("no_commits_yet"))
        return 0

    branches = _parse_branches(r.stdout, wt_branches)

    if as_json:
        print_json({"v": 2, "ok": True, "branches": branches, "count": len(branches)})
        return 0

    current_idx: int | None = None
    columns = [
        (t("col_branch"), "name"),
        (t("col_sha"), "sha"),
        (t("col_subject"), "subject"),
        (t("col_age"), "age"),
        (t("col_status"), "status"),
    ]

    rows: list[list[str]] = []
    highlight_rows: set[int] = set()

    for idx, b in enumerate(branches):
        sha = b["sha"][:8]
        subject = b["subject"][:40]
        age = b.get("age", "")

        flags: list[str] = []
        if b.get("ahead"):
            flags.append(f"↑{b['ahead']}")
        if b.get("behind"):
            flags.append(f"↓{b['behind']}")
        if b.get("in_worktree") == "true":
            flags.append("wt")
        if b.get("upstream"):
            flags.append(f"→{b['upstream']}")
        status = " ".join(flags) if flags else ""

        name_display = f"* {b['name']}" if b["current"] == "true" else b["name"]
        rows.append([name_display, sha, subject, age, status])

        if b["current"] == "true":
            current_idx = idx
            highlight_rows.add(idx)

    print_table(
        title=t("branch_list_title_current", branch=branches[current_idx]["name"])
        if current_idx is not None
        else t("branch_list_title"),
        columns=columns,
        rows=rows,
        highlight_rows=highlight_rows,
    )

    return 0
