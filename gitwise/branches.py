"""gitwise branches — intelligence dashboard with ahead/behind, merged, stale, worktree info."""

from .git import require_root, stale_branches, worktree_branches
from .git import run as git_run
from .i18n import t
from .output import error, info, print_accent, print_header, print_json, print_table


def _parse_branches(raw: str, wt_branches: set[str]) -> list[dict[str, str]]:
    branches: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        name = parts[0].removeprefix("* ").strip()
        is_current = parts[0].startswith("*")
        sha = parts[1]
        subject = parts[2]
        age = parts[3]
        tracking = parts[4] if len(parts) > 4 else ""
        upstream = parts[5] if len(parts) > 5 else ""

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
    assert root is not None

    if stale:
        names = stale_branches(cwd=root)
        if not names:
            info(t("no_stale_branches"))
            return 0
        if as_json:
            print_json({"v": 2, "ok": True, "stale_branches": names, "count": len(names)})
        else:
            print_header(t("branches_to_delete", count=str(len(names))))
            for n in names:
                print_accent(f"  {n}")
            info(t("clean_to_delete"))
        return 0

    wt_branches = worktree_branches(cwd=root)

    ref_pattern = "refs/remotes/" if remote else "refs/heads/"
    fmt = "%(refname:short)\t%(objectname:short)\t%(subject)\t%(committerdate:relative)\t%(upstream:track)\t%(upstream:short)"

    r = git_run(
        ["for-each-ref", f"--sort={sort}", f"--format={fmt}", ref_pattern],
        cwd=root,
        check=False,
    )
    if r.returncode != 0:
        error(t("git_ref_failed", error=r.stderr.strip()))
        return 1

    if not r.stdout.strip():
        info(t("no_commits_yet"))
        return 0

    branches = _parse_branches(r.stdout, wt_branches)

    if as_json:
        print_json({"v": 2, "ok": True, "branches": branches, "count": len(branches)})
        return 0

    current_idx: int | None = None
    columns = [
        ("Branch", "name"),
        ("SHA", "sha"),
        ("Subject", "subject"),
        ("Age", "age"),
        ("Status", "status"),
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
        title=t("branch_list_title")
        if current_idx is None
        else f"Branches (current: {branches[current_idx]['name']})",
        columns=columns,
        rows=rows,
        highlight_rows=highlight_rows,
    )

    return 0
