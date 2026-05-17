"""gitwise branches — intelligence dashboard with ahead/behind, merged, stale, worktree info."""

import sys

from .git import is_repo, repo_root, stale_branches, worktree_branches
from .git import run as git_run
from .i18n import t
from .output import print_json


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


def _format_branch(b: dict[str, str], show_remote: bool = False) -> str:
    name = b["name"]
    current = " * " if b["current"] == "true" else "   "
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
    flag_str = " ".join(flags)
    flag_display = f" [{flag_str}]" if flag_str else ""

    age_display = f" ({age})" if age else ""

    return f"{current}{name:25s} {sha} {subject:40s}{age_display}{flag_display}"


def run_branches(
    *,
    stale: bool = False,
    remote: bool = False,
    sort: str = "refname",
    as_json: bool = False,
) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    if stale:
        names = stale_branches(cwd=root)
        if not names:
            print(t("no_stale_branches"))
            return 0
        if as_json:
            print_json({"v": 2, "ok": True, "stale_branches": names, "count": len(names)})
        else:
            print(t("branches_to_delete", count=str(len(names))))
            for n in names:
                print(f"  {n}")
            print(t("clean_to_delete"))
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
        print(t("git_diff_failed", error=r.stderr.strip()), file=sys.stderr)
        return 1

    if not r.stdout.strip():
        print(t("no_commits_yet"))
        return 0

    branches = _parse_branches(r.stdout, wt_branches)

    if as_json:
        print_json({"v": 2, "ok": True, "branches": branches, "count": len(branches)})
    else:
        for b in branches:
            print(_format_branch(b, show_remote=remote))

    return 0
