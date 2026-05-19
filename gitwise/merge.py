"""gitwise merge — merge/rebase with pre-flight checks."""

from pathlib import Path

from .git import current_branch, require_root
from .git import run as git_run
from .i18n import t
from .output import (
    confirm,
    error,
    ok,
    print_bracket,
    print_header,
    print_json,
    warn,
)


def _has_uncommitted(root: Path) -> bool:
    r = git_run(["status", "--porcelain"], cwd=root, check=False)
    return r.returncode == 0 and bool(r.stdout.strip())


def _branch_exists(root: Path, name: str) -> bool:
    r = git_run(["rev-parse", "--verify", name], cwd=root, check=False)
    return r.returncode == 0


def run_merge(
    branch: str,
    *,
    rebase: bool = False,
    no_ff: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    cur = current_branch(root)
    if cur is None:
        error(t("merge_detached_head"))
        return 1

    if not _branch_exists(root, branch):
        error(t("merge_branch_not_found", branch=branch))
        return 1

    if branch == cur:
        error(t("merge_same_branch"))
        return 1

    warnings: list[str] = []
    if _has_uncommitted(root):
        warnings.append(t("merge_uncommitted"))

    ahead = git_run(["rev-list", "--count", f"{branch}..HEAD"], cwd=root, check=False)
    behind = git_run(["rev-list", "--count", f"HEAD..{branch}"], cwd=root, check=False)
    try:
        ahead_count = int(ahead.stdout.strip()) if ahead.returncode == 0 else 0
        behind_count = int(behind.stdout.strip()) if behind.returncode == 0 else 0
    except ValueError:
        from .output import debug

        debug(
            f"merge ahead/behind parse failed: {ahead.stdout.strip()!r} / {behind.stdout.strip()!r}"
        )
        ahead_count = behind_count = 0

    if ahead_count > 0 and behind_count > 0:
        warnings.append(t("merge_diverged", ahead=str(ahead_count), behind=str(behind_count)))

    if dry_run:
        if as_json:
            print_json(
                {
                    "v": 2,
                    "dry_run": True,
                    "action": "rebase" if rebase else "merge",
                    "branch": branch,
                    "current": cur,
                    "ahead": ahead_count,
                    "behind": behind_count,
                    "warnings": warnings,
                    "ok": True,
                }
            )
            return 0
        action = t("merge_rebase_label") if rebase else t("merge_merge_label")
        print_header(f"{action}: {branch} → {cur}")
        if ahead_count or behind_count:
            print_bracket(t("status_ahead_label"), str(ahead_count))
            print_bracket(t("status_behind_label"), str(behind_count))
        for w in warnings:
            warn(w)
        return 0

    if warnings:
        for w in warnings:
            warn(w)
        if not yes and not confirm(t("merge_proceed")):
            warn(t("aborted"))
            return 1

    if rebase:
        args = ["rebase", branch]
    else:
        args = ["merge"]
        if no_ff:
            args.append("--no-ff")
        args.append(branch)

    r = git_run(args, cwd=root, check=False)
    if r.returncode != 0:
        err = (
            t("merge_conflicts")
            if ("CONFLICT" in r.stdout or "CONFLICT" in r.stderr)
            else t("git_command_failed", cmd="merge/rebase", error=r.stderr.strip())
        )
        if as_json:
            print_json({"v": 2, "ok": False, "error": err})
        else:
            error(err)
        return 1

    if as_json:
        print_json({"v": 2, "merged": branch, "into": cur, "ok": True})
        return 0
    label = (
        t("merge_rebased", branch=branch, into=cur)
        if rebase
        else t("merge_ok", branch=branch, into=cur)
    )
    ok(label)
    return 0
