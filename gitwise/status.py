"""gitwise status — enhanced git status for humans and AI agents."""

from .git import current_branch, has_upstream, require_root
from .git import run as git_run
from .i18n import t
from .output import info, ok, print_bracket, print_header, print_json


def run_status(*, as_json: bool = False) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    branch = current_branch(root) or t("detached_head")

    status_r = git_run(["status", "--porcelain"], cwd=root, check=False)
    status_lines = status_r.stdout.splitlines() if status_r.returncode == 0 else []

    staged = [ln for ln in status_lines if ln and ln[0] not in (" ", "?")]
    unstaged = [ln for ln in status_lines if ln and ln[1] not in (" ", "?")]
    untracked = [ln for ln in status_lines if ln and ln.startswith("??")]

    ahead = behind = 0
    if has_upstream(root):
        ab_r = git_run(
            ["rev-list", "--left-right", "--count", "HEAD...@{u}"],
            cwd=root,
            check=False,
        )
        if ab_r.returncode == 0:
            parts = ab_r.stdout.strip().split()
            if len(parts) == 2:
                try:
                    ahead, behind = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

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

    print_header(t("branch_label", branch=branch))
    if ahead or behind:
        print_bracket(t("status_ahead_label"), str(ahead))
        print_bracket(t("status_behind_label"), str(behind))
    print()

    if not status_lines:
        ok(t("working_tree_clean"))
        return 0

    if staged:
        print_bracket(t("status_staged_label"), str(len(staged)))
        for line in staged:
            info(f"    {line[:2]}  {line[3:]}")
        print()

    if unstaged:
        print_bracket(t("status_unstaged_label"), str(len(unstaged)))
        for line in unstaged:
            info(f"    {line[:2]}  {line[3:]}")
        print()

    if untracked:
        print_bracket(t("status_untracked_label"), str(len(untracked)))
        for line in untracked[:10]:
            info(f"    ??  {line[3:]}")
        if len(untracked) > 10:
            info(f"    {t('status_more_files', count=str(len(untracked) - 10))}")
        print()

    return 0
