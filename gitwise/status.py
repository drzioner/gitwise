"""gitwise status — enhanced git status for humans and AI agents."""

import sys

from .git import current_branch, has_upstream, is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import ok, print_json


def _count_by_prefix(lines: list[str], prefix: str) -> int:
    return sum(1 for line in lines if line and line[0] == prefix)


def run_status(*, as_json: bool = False) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    branch = current_branch(root) or "(detached HEAD)"

    status_r = git_run(["status", "--porcelain"], cwd=root, check=False)
    status_lines = status_r.stdout.splitlines() if status_r.returncode == 0 else []

    staged = [ln for ln in status_lines if ln and ln[0] not in (" ", "?")]
    unstaged = [ln for ln in status_lines if ln and ln[1] not in (" ", "?")]
    untracked = [ln for ln in status_lines if ln and ln.startswith("??")]

    ahead_r = git_run(["rev-list", "--count", "@{u}..HEAD"], cwd=root, check=False)
    behind_r = git_run(["rev-list", "--count", "HEAD..@{u}"], cwd=root, check=False)
    ahead = int(ahead_r.stdout.strip()) if ahead_r.returncode == 0 else 0
    behind = int(behind_r.stdout.strip()) if behind_r.returncode == 0 else 0

    if as_json:
        print_json(
            {
                "v": 2,
                "ok": True,
                "branch": branch,
                "has_upstream": has_upstream(root),
                "ahead": ahead,
                "behind": behind,
                "staged": len(staged),
                "unstaged": len(unstaged),
                "untracked": len(untracked),
                "files": [ln[3:] for ln in status_lines],
            }
        )
        return 0

    print(f"  {t('branch_label', branch=branch)}")
    if ahead or behind:
        print(
            f"  {t('branches_ahead', count=str(ahead))}  {t('branches_behind', count=str(behind))}"
        )
    print()

    if not status_lines:
        ok(t("working_tree_clean"))
        return 0

    if staged:
        print(f"  {t('status_staged', count=str(len(staged)))}")
        for line in staged:
            print(f"    {line}")
        print()

    if unstaged:
        print(f"  {t('status_unstaged', count=str(len(unstaged)))}")
        for line in unstaged:
            print(f"    {line}")
        print()

    if untracked:
        print(f"  {t('status_untracked', count=str(len(untracked)))}")
        for line in untracked[:10]:
            print(f"    {line[3:]}")
        if len(untracked) > 10:
            print(f"    ... +{len(untracked) - 10} more")
        print()

    return 0
