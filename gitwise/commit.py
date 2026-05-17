"""gitwise commit — conventional format validation, GPG enforcement, --amend protection."""

import re
import sys
from pathlib import Path

from .git import current_branch, gpg_status, require_root
from .git import run as git_run
from .i18n import t
from .output import print_json

_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|docs|chore|test|style|perf|ci|build|revert)(\(.+\))?!?: .{1,72}"
)

_PROTECTED_BRANCHES = {"main", "master", "release"}


def _is_pushed(branch: str, cwd: Path) -> bool:
    r = git_run(["rev-parse", "--verify", branch + "@{u}"], cwd=cwd, check=False)
    return r.returncode == 0


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
    assert root is not None

    if amend:
        branch = current_branch(cwd=root) or ""
        if branch in _PROTECTED_BRANCHES:
            print(t("commit_amend_protected", branch=branch), file=sys.stderr)
            return 1
        if _is_pushed(branch, root):
            print(t("commit_amend_pushed", branch=branch), file=sys.stderr)
            return 1

    if message is None:
        print(t("commit_no_message"), file=sys.stderr)
        return 1

    if _CONVENTIONAL_RE.match(message.split("\n")[0]) and not type:
        full_msg = message
    elif type:
        prefix = type
        if scope:
            prefix += f"({scope})"
        if breaking:
            prefix += "!"
        full_msg = f"{prefix}: {message}"
    else:
        full_msg = message

    if not _CONVENTIONAL_RE.match(full_msg.split("\n")[0]):
        print(t("commit_invalid_format"), file=sys.stderr)
        return 1

    gpg = gpg_status(cwd=root)
    if gpg["gpgsign_enabled"] and not gpg["ready"]:
        print(t("gpg_signing_active_no_key"), file=sys.stderr)
        return 1

    if dry_run:
        if as_json:
            print_json({"v": 2, "ok": True, "message": full_msg, "amend": amend, "dry_run": True})
        else:
            print(t("dry_run_no_exec"))
            print(f"  git commit -m {full_msg!r}")
            if amend:
                print("  --amend")
        return 0

    args = ["commit", "-m", full_msg]
    if amend:
        args.append("--amend")

    r = git_run(args, cwd=root, check=False)
    if r.returncode != 0:
        err = t("git_command_failed", cmd="commit", error=r.stderr.strip())
        if as_json:
            print_json({"v": 2, "ok": False, "error": err})
        else:
            print(err, file=sys.stderr)
        return 1

    if as_json:
        print_json({"v": 2, "ok": True, "message": full_msg, "amend": amend})
    return 0
