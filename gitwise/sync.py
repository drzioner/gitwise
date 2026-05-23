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
    status,
)
from .utils.json_envelope import error_envelope, ok_envelope
from .utils.parsing import parse_two_ints, stripped_non_empty_lines


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
    parsed = parse_two_ints(r.stdout)
    if parsed is not None:
        behind, ahead = parsed
        return {"behind": behind, "ahead": ahead}
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
    return stripped_non_empty_lines(r.stdout)


def _sync_dry_run_payload(
    *,
    branch: str,
    pull: bool,
    push: bool,
    remote: str | None,
    root: Path,
) -> dict[str, object]:
    ab = _ahead_behind(root)
    unpushed = _unpushed_commits(root)
    return {
        "branch": branch,
        "ahead": ab["ahead"],
        "behind": ab["behind"],
        "unpushed": unpushed,
        "actions": _planned_actions(pull, push, ab, unpushed, remote),
        "dry_run": True,
    }


def _print_sync_dry_run_human(*, pull: bool, push: bool, root: Path, remote: str | None) -> None:
    ab = _ahead_behind(root)
    unpushed = _unpushed_commits(root)
    print_header(t("sync_dry_run_title"))
    for action in _planned_actions(pull, push, ab, unpushed, remote):
        print_bracket(action)
    print_dim(t("dry_run_no_exec"))


def _sync_fetch(*, root: Path, remote: str | None, as_json: bool) -> int:
    with status(t("status_sync_fetch")):
        result = git_run(
            ["fetch", "--prune"] + ([remote] if remote else ["--all"]), cwd=root, check=False
        )
    if result.returncode == 0:
        return 0
    if as_json:
        print_json(
            error_envelope(
                error=t("sync_fetch_failed", error=result.stderr.strip()),
                code="sync_fetch_failed",
                hint=t("sync_hint"),
            )
        )
    else:
        error(t("sync_fetch_failed", error=result.stderr.strip()))
    return 1


def _sync_pull(*, root: Path, as_json: bool) -> int:
    with status(t("status_sync_pull")):
        result = git_run(["pull", "--ff-only"], cwd=root, check=False)
    if result.returncode == 0:
        return 0
    if as_json:
        print_json(
            error_envelope(
                error=t("sync_pull_diverged"),
                code="sync_pull_diverged",
                hint=t("sync_hint"),
            )
        )
    else:
        error(t("sync_pull_diverged"))
    return 1


def _sync_push(*, root: Path, branch: str, as_json: bool) -> int:
    if branch in PROTECTED_BRANCHES:
        if as_json:
            print_json(
                error_envelope(
                    error=t("sync_push_protected", branch=branch),
                    code="sync_push_protected",
                    hint=t("sync_push_protected_hint"),
                )
            )
        else:
            error(t("sync_push_protected", branch=branch))
        return 1
    with status(t("status_sync_push")):
        result = git_run(["push"], cwd=root, check=False)
    if result.returncode == 0:
        return 0
    if as_json:
        print_json(
            error_envelope(
                error=t("sync_push_failed", error=result.stderr.strip()),
                code="sync_push_failed",
                hint=t("sync_hint"),
            )
        )
    else:
        error(t("sync_push_failed", error=result.stderr.strip()))
    return 1


def _print_sync_complete_human(*, branch: str, ahead: int, behind: int) -> None:
    print_header(t("sync_complete_title"))
    print_bracket(branch, t("sync_status", ahead=str(ahead), behind=str(behind)))


def _sync_final_payload(*, branch: str, root: Path) -> dict[str, object]:
    ab = _ahead_behind(root)
    return {
        "branch": branch,
        "ahead": ab["ahead"],
        "behind": ab["behind"],
        "unpushed": _unpushed_commits(root),
    }


def _report_sync_final(*, as_json: bool, branch: str, root: Path) -> int:
    payload = _sync_final_payload(branch=branch, root=root)
    if as_json:
        print_json(ok_envelope(payload=payload))
        return 0
    ahead = payload["ahead"]
    behind = payload["behind"]
    _print_sync_complete_human(
        branch=branch,
        ahead=ahead if isinstance(ahead, int) else 0,
        behind=behind if isinstance(behind, int) else 0,
    )
    return 0


def _run_sync_dry_run(
    *, as_json: bool, branch: str, pull: bool, push: bool, remote: str | None, root: Path
) -> int:
    if as_json:
        print_json(
            ok_envelope(
                payload=_sync_dry_run_payload(
                    branch=branch, pull=pull, push=push, remote=remote, root=root
                )
            )
        )
        return 0
    _print_sync_dry_run_human(pull=pull, push=push, root=root, remote=remote)
    return 0


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
        return _run_sync_dry_run(
            as_json=as_json,
            branch=branch,
            pull=pull,
            push=push,
            remote=remote,
            root=root,
        )

    fetch_rc = _sync_fetch(root=root, remote=remote, as_json=as_json)
    if fetch_rc != 0:
        return fetch_rc

    if pull:
        pull_rc = _sync_pull(root=root, as_json=as_json)
        if pull_rc != 0:
            return pull_rc

    if push:
        push_rc = _sync_push(root=root, branch=branch, as_json=as_json)
        if push_rc != 0:
            return push_rc

    return _report_sync_final(as_json=as_json, branch=branch, root=root)


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
