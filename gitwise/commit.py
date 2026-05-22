"""gitwise commit — conventional format validation, GPG enforcement, --amend protection."""

import re
from pathlib import Path

from .git import PROTECTED_BRANCHES, current_branch, gpg_status, require_root
from .git import run as git_run
from .i18n import t
from .output import error, print_bracket, print_header, print_json
from .utils.json_envelope import error_envelope, ok_envelope

_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|docs|chore|test|style|perf|ci|build|revert)(\(.+\))?!?: .{1,72}"
)


def _is_pushed(branch: str, cwd: Path) -> bool:
    r = git_run(["rev-parse", "--verify", branch + "@{u}"], cwd=cwd, check=False)
    return r.returncode == 0


def _compose_message(
    *,
    message: str,
    type: str | None,
    scope: str | None,
    breaking: bool,
) -> str:
    if _CONVENTIONAL_RE.match(message.split("\n")[0]) and not type:
        return message
    if not type:
        return message
    prefix = type
    if scope:
        prefix += f"({scope})"
    if breaking:
        prefix += "!"
    return f"{prefix}: {message}"


def _validate_amend_policy(*, amend: bool, root: Path) -> int:
    if not amend:
        return 0
    branch = current_branch(cwd=root) or ""
    if branch in PROTECTED_BRANCHES:
        error(t("commit_amend_protected", branch=branch))
        return 1
    if _is_pushed(branch, root):
        error(t("commit_amend_pushed", branch=branch))
        return 1
    return 0


def _print_dry_run(*, message: str, amend: bool, root: Path) -> None:
    print_header(t("dry_run_no_exec"))
    print_bracket(t("commit_msg_label"), message)
    if amend:
        print_bracket(t("commit_amend_label"))
    branch = current_branch(cwd=root) or ""
    if branch:
        print_bracket(t("commit_branch_label"), branch)


def _validate_commit_message(message: str) -> bool:
    if _CONVENTIONAL_RE.match(message.split("\n")[0]):
        return True
    error(t("commit_invalid_format"))
    return False


def _execute_commit(*, root: Path, message: str, amend: bool) -> tuple[bool, str]:
    args = ["commit", "-m", message]
    if amend:
        args.append("--amend")
    result = git_run(args, cwd=root, check=False)
    if result.returncode == 0:
        return True, ""
    return False, t("git_command_failed", cmd="commit", error=result.stderr.strip())


def _validate_gpg_ready(root: Path) -> bool:
    gpg = gpg_status(cwd=root)
    if gpg["gpgsign_enabled"] and not gpg["ready"]:
        error(t("gpg_signing_active_no_key"))
        return False
    return True


def _report_commit_error(*, as_json: bool, err: str) -> int:
    if as_json:
        print_json(error_envelope(error=err))
    else:
        error(err)
    return 1


def run_commit(
    *,
    message: str | None = None,
    type: str | None = None,
    scope: str | None = None,
    breaking: bool = False,
    amend: bool = False,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    amend_policy_rc = _validate_amend_policy(amend=amend, root=root)
    if amend_policy_rc != 0:
        return amend_policy_rc

    if message is None:
        error(t("commit_no_message"))
        return 1

    full_msg = _compose_message(message=message, type=type, scope=scope, breaking=breaking)

    if not _validate_commit_message(full_msg):
        return 1

    if not _validate_gpg_ready(root):
        return 1

    if dry_run:
        if as_json:
            print_json(ok_envelope(message=full_msg, amend=amend, dry_run=True))
        else:
            _print_dry_run(message=full_msg, amend=amend, root=root)
        return 0

    success, err = _execute_commit(root=root, message=full_msg, amend=amend)
    if not success:
        return _report_commit_error(as_json=as_json, err=err)

    if as_json:
        print_json(ok_envelope(message=full_msg, amend=amend))
    return 0
