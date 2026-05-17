"""gitwise sync — remote fetch, safe pull/push, ahead/behind reporting."""

import sys

from .git import current_branch, is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import print_json


def _ahead_behind(cwd) -> dict[str, int]:
    branch = current_branch(cwd=cwd)
    if not branch:
        return {"ahead": 0, "behind": 0}
    r = git_run(
        ["rev-list", "--left-right", "--count", branch + "@{u}...HEAD"], cwd=cwd, check=False
    )
    if r.returncode != 0:
        return {"ahead": 0, "behind": 0}
    parts = r.stdout.strip().split()
    if len(parts) == 2:
        return {"behind": int(parts[0]), "ahead": int(parts[1])}
    return {"ahead": 0, "behind": 0}


def _unpushed_commits(cwd) -> list[str]:
    branch = current_branch(cwd=cwd)
    if not branch:
        return []
    r = git_run(["log", "--oneline", branch + "@{u}..HEAD"], cwd=cwd, check=False)
    if r.returncode != 0:
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
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
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
            print(t("dry_run_no_exec"))
            for action in _planned_actions(pull, push, ab, unpushed, remote):
                print(f"  {action}")
        return 0

    r = git_run(["fetch", "--prune"] + ([remote] if remote else ["--all"]), cwd=root, check=False)
    if r.returncode != 0:
        print(t("sync_fetch_failed", error=r.stderr.strip()), file=sys.stderr)
        return 1

    if pull:
        r = git_run(["pull", "--ff-only"], cwd=root, check=False)
        if r.returncode != 0:
            print(t("sync_pull_diverged"), file=sys.stderr)
            return 1

    if push:
        if branch in ("main", "master", "release"):
            print(t("sync_push_protected", branch=branch), file=sys.stderr)
            return 1
        r = git_run(["push"], cwd=root, check=False)
        if r.returncode != 0:
            print(t("sync_push_failed", error=r.stderr.strip()), file=sys.stderr)
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
        print(t("sync_complete", branch=branch, ahead=str(ab["ahead"]), behind=str(ab["behind"])))
    return 0


def _planned_actions(
    pull: bool, push: bool, ab: dict, unpushed: list, remote: str | None = None
) -> list[str]:
    fetch_cmd = f"fetch {remote}" if remote else "fetch --all --prune"
    actions = [fetch_cmd]
    if pull and ab["behind"] > 0:
        actions.append("pull --ff-only")
    if push and unpushed:
        actions.append(f"push ({len(unpushed)} commits)")
    return actions
