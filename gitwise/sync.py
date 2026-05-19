"""gitwise sync — remote fetch, safe pull/push, ahead/behind reporting."""

from pathlib import Path

from .git import PROTECTED_BRANCHES, current_branch, require_root
from .git import run as git_run
from .i18n import t
from .output import (
    debug,
    error,
    print_bracket,
    print_dim,
    print_header,
    print_json,
)


def _ahead_behind(cwd: Path) -> dict[str, int]:
    branch = current_branch(cwd=cwd)
    if not branch:
        return {"ahead": 0, "behind": 0}
    r = git_run(
        ["rev-list", "--left-right", "--count", branch + "@{u}...HEAD"], cwd=cwd, check=False
    )
    if r.returncode != 0:
        debug(f"ahead_behind failed: {r.stderr.strip()}")
        return {"ahead": 0, "behind": 0}
    parts = r.stdout.strip().split()
    if len(parts) == 2:
        try:
            return {"behind": int(parts[0]), "ahead": int(parts[1])}
        except ValueError:
            debug(f"ahead_behind parse failed: {r.stdout.strip()!r}")
    return {"ahead": 0, "behind": 0}


def _unpushed_commits(cwd) -> list[str]:
    branch = current_branch(cwd=cwd)
    if not branch:
        return []
    r = git_run(["log", "--oneline", branch + "@{u}..HEAD"], cwd=cwd, check=False)
    if r.returncode != 0:
        debug(f"unpushed_commits failed: {r.stderr.strip()}")
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def run_sync(
    *,
    pull: bool = False,
    push: bool = False,
    remote: str | None = None,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    branch = current_branch(cwd=root) or ""

    if dry_run:
        ab = _ahead_behind(root)
        unpushed = _unpushed_commits(root)
        if as_json:
            print_json(
                {
                    "v": 2,
                    "ok": True,
                    "branch": branch,
                    "ahead": ab["ahead"],
                    "behind": ab["behind"],
                    "unpushed": unpushed,
                    "actions": _planned_actions(pull, push, ab, unpushed, remote),
                    "dry_run": True,
                }
            )
        else:
            print_header(t("sync_dry_run_title"))
            for action in _planned_actions(pull, push, ab, unpushed, remote):
                print_bracket(action)
            print_dim(t("dry_run_no_exec"))
        return 0

    r = git_run(["fetch", "--prune"] + ([remote] if remote else ["--all"]), cwd=root, check=False)
    if r.returncode != 0:
        if as_json:
            print_json(
                {"v": 2, "ok": False, "error": t("sync_fetch_failed", error=r.stderr.strip())}
            )
        else:
            error(t("sync_fetch_failed", error=r.stderr.strip()))
        return 1

    if pull:
        r = git_run(["pull", "--ff-only"], cwd=root, check=False)
        if r.returncode != 0:
            if as_json:
                print_json({"v": 2, "ok": False, "error": t("sync_pull_diverged")})
            else:
                error(t("sync_pull_diverged"))
            return 1

    if push:
        if branch in PROTECTED_BRANCHES:
            if as_json:
                print_json({"v": 2, "ok": False, "error": t("sync_push_protected", branch=branch)})
            else:
                error(t("sync_push_protected", branch=branch))
            return 1
        r = git_run(["push"], cwd=root, check=False)
        if r.returncode != 0:
            if as_json:
                print_json(
                    {"v": 2, "ok": False, "error": t("sync_push_failed", error=r.stderr.strip())}
                )
            else:
                error(t("sync_push_failed", error=r.stderr.strip()))
            return 1

    ab = _ahead_behind(root)
    if as_json:
        print_json(
            {
                "v": 2,
                "ok": True,
                "branch": branch,
                "ahead": ab["ahead"],
                "behind": ab["behind"],
                "unpushed": _unpushed_commits(root),
            }
        )
    else:
        print_header(t("sync_complete_title"))
        print_bracket(branch, t("sync_status", ahead=str(ab["ahead"]), behind=str(ab["behind"])))
    return 0


def _planned_actions(
    pull: bool, push: bool, ab: dict, unpushed: list, remote: str | None = None
) -> list[str]:
    fetch_cmd = (
        t("sync_action_fetch_remote", remote=remote) if remote else t("sync_action_fetch_all")
    )
    actions = [fetch_cmd]
    if pull and ab["behind"] > 0:
        actions.append(t("sync_pull_ff"))
    if push and unpushed:
        actions.append(t("sync_push_commits", count=str(len(unpushed))))
    return actions
