"""gitwise merge — merge/rebase with pre-flight checks."""

from pathlib import Path

from .git import current_branch, require_root, validate_ref
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
from .utils.in_progress import detect_in_progress
from .utils.json_envelope import error_envelope, ok_envelope
from .utils.parsing import to_int


def _has_uncommitted(root: Path) -> bool:
    r = git_run(["status", "--porcelain"], cwd=root, check=False)
    return r.returncode == 0 and bool(r.stdout.strip())


def _branch_exists(root: Path, name: str) -> bool:
    r = git_run(["rev-parse", "--verify", "refs/heads/" + name], cwd=root, check=False)
    return r.returncode == 0


def _validate_merge_target(*, root: Path, branch: str, cur: str | None) -> str | None:
    if cur is None:
        return t("merge_detached_head")
    if not validate_ref(branch):
        return t("invalid_ref", ref=branch)
    if not _branch_exists(root, branch):
        return t("merge_branch_not_found", branch=branch)
    if branch == cur:
        return t("merge_same_branch")
    return None


def _ahead_behind_counts(*, root: Path, branch: str) -> tuple[int, int]:
    ahead = git_run(["rev-list", "--count", f"{branch}..HEAD"], cwd=root, check=False)
    behind = git_run(["rev-list", "--count", f"HEAD..{branch}"], cwd=root, check=False)
    ahead_count = to_int(ahead.stdout, default=0) if ahead.returncode == 0 else 0
    behind_count = to_int(behind.stdout, default=0) if behind.returncode == 0 else 0
    return ahead_count, behind_count


def _merge_warnings(*, root: Path, branch: str, ahead_count: int, behind_count: int) -> list[str]:
    warnings: list[str] = []
    if _has_uncommitted(root):
        warnings.append(t("merge_uncommitted"))
    if ahead_count > 0 and behind_count > 0:
        warnings.append(t("merge_diverged", ahead=str(ahead_count), behind=str(behind_count)))
    return warnings


def _handle_merge_dry_run(
    *,
    as_json: bool,
    rebase: bool,
    branch: str,
    cur: str,
    ahead_count: int,
    behind_count: int,
    warnings: list[str],
) -> int:
    if as_json:
        print_json(
            ok_envelope(
                dry_run=True,
                action="rebase" if rebase else "merge",
                branch=branch,
                current=cur,
                ahead=ahead_count,
                behind=behind_count,
                warnings=warnings,
            )
        )
        return 0
    action = t("merge_rebase_label") if rebase else t("merge_merge_label")
    print_header(f"{action}: {branch} -> {cur}")
    if ahead_count or behind_count:
        print_bracket(t("status_ahead_label"), str(ahead_count))
        print_bracket(t("status_behind_label"), str(behind_count))
    for warning_msg in warnings:
        warn(warning_msg)
    return 0


def _execute_merge(*, root: Path, branch: str, rebase: bool, no_ff: bool) -> tuple[bool, str]:
    if rebase:
        args = ["rebase", branch]
    else:
        args = ["merge"]
        if no_ff:
            args.append("--no-ff")
        args.append(branch)
    result = git_run(args, cwd=root, check=False)
    if result.returncode == 0:
        return True, ""
    err = (
        t("merge_conflicts")
        if ("CONFLICT" in result.stdout or "CONFLICT" in result.stderr)
        else t("git_command_failed", cmd="merge/rebase", error=result.stderr.strip())
    )
    return False, err


def _confirm_merge_warnings(*, warnings: list[str], yes: bool) -> bool:
    if not warnings:
        return True
    for warning_msg in warnings:
        warn(warning_msg)
    if yes:
        return True
    if confirm(t("merge_proceed")):
        return True
    warn(t("aborted"))
    return False


def _report_merge_success(*, as_json: bool, branch: str, cur: str, rebase: bool) -> int:
    if as_json:
        print_json(ok_envelope(merged=branch, into=cur))
        return 0
    label = (
        t("merge_rebased", branch=branch, into=cur)
        if rebase
        else t("merge_ok", branch=branch, into=cur)
    )
    ok(label)
    return 0


def _report_merge_error(*, as_json: bool, err: str) -> int:
    if as_json:
        print_json(error_envelope(error=err, code="merge_error", hint=t("merge_hint")))
    else:
        error(err, hint=t("merge_hint"))
    return 1


def _execute_abort_or_continue(*, root: Path, abort: bool) -> tuple[bool, str]:
    """Run `git merge --abort` or `git merge --continue`. Returns (success, error_msg)."""
    args = ["merge", "--abort" if abort else "--continue"]
    result = git_run(args, cwd=root, check=False)
    if result.returncode == 0:
        return True, ""
    return False, result.stderr.strip() or result.stdout.strip()


def _handle_abort_or_continue(*, root: Path, abort: bool, as_json: bool) -> int:
    """Resolve a paused merge or rebase via `git merge --abort` / `--continue`."""
    in_progress = detect_in_progress(root)
    if in_progress["state"] not in ("merge", "rebase"):
        available = "git merge --abort / --continue" if abort else "git merge --continue"
        msg = t("merge_no_in_progress", action=available, state=in_progress["state"])
        if as_json:
            print_json(error_envelope(error=msg, code="merge_no_in_progress"))
        else:
            error(msg)
        return 1
    success, err_msg = _execute_abort_or_continue(root=root, abort=abort)
    if not success:
        return _report_merge_error(as_json=as_json, err=err_msg)
    label_key = "merge_aborted" if abort else "merge_continued"
    if as_json:
        print_json(ok_envelope(action="abort" if abort else "continue"))
    else:
        ok(t(label_key))
    return 0


def run_merge(
    branch: str | None = None,
    *,
    rebase: bool = False,
    no_ff: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    abort: bool = False,
    continue_merge: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    if abort and continue_merge:
        msg = t("merge_abort_continue_mutually_exclusive")
        if as_json:
            print_json(error_envelope(error=msg, code="merge_invalid_args"))
        else:
            error(msg)
        return 1

    if abort or continue_merge:
        return _handle_abort_or_continue(root=root, abort=abort, as_json=as_json)

    if branch is None:
        msg = t("merge_branch_required")
        if as_json:
            print_json(error_envelope(error=msg, code="merge_branch_required"))
        else:
            error(msg)
        return 1

    cur = current_branch(root)
    target_err = _validate_merge_target(root=root, branch=branch, cur=cur)
    if target_err is not None:
        return _report_merge_error(as_json=as_json, err=target_err)
    assert cur is not None

    ahead_count, behind_count = _ahead_behind_counts(root=root, branch=branch)
    warnings = _merge_warnings(
        root=root,
        branch=branch,
        ahead_count=ahead_count,
        behind_count=behind_count,
    )

    if dry_run:
        return _handle_merge_dry_run(
            as_json=as_json,
            rebase=rebase,
            branch=branch,
            cur=cur,
            ahead_count=ahead_count,
            behind_count=behind_count,
            warnings=warnings,
        )

    if not _confirm_merge_warnings(warnings=warnings, yes=yes):
        return 1

    success, err = _execute_merge(root=root, branch=branch, rebase=rebase, no_ff=no_ff)
    if not success:
        return _report_merge_error(as_json=as_json, err=err)

    return _report_merge_success(as_json=as_json, branch=branch, cur=cur, rebase=rebase)
