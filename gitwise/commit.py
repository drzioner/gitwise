"""gitwise commit — conventional format validation, GPG enforcement, --amend protection."""

import os
import re
from pathlib import Path

from gitwise.git import PROTECTED_BRANCHES, current_branch, gpg_status, require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import confirm, error, print_bracket, print_header, print_json, warn
from gitwise.utils.in_progress import detect_in_progress, in_progress_hint
from gitwise.utils.json_envelope import error_envelope, ok_envelope
from gitwise.utils.secret_scan import SecretScanUnavailable, scan_staged_diff

_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|docs|chore|test|style|perf|ci|build|revert)(\(.+\))?!?: .{1,72}"
)

# Out-of-band override for --allow-secret in agent (--json) mode. An AI agent
# cannot set environment variables via a prompt, so requiring this closes the
# prompt-injection vector where a tricked agent silently commits leaked secrets.
_ALLOW_SECRET_JSON_ENV = "GITWISE_ALLOW_SECRETS"


def _is_pushed(branch: str, cwd: Path) -> bool:
    """Return True if the branch has an upstream tracking reference."""
    r = git_run(["rev-parse", "--verify", branch + "@{u}"], cwd=cwd, check=False)
    return r.returncode == 0


def _compose_message(
    *,
    message: str,
    type: str | None,
    scope: str | None,
    breaking: bool,
) -> str:
    """Build a conventional-commit prefix or return the message unchanged.

    If the first line already matches the conventional pattern and no explicit
    type is given, the message is returned as-is.
    """
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


def _validate_amend_policy(*, amend: bool, root: Path, as_json: bool = False) -> int:
    """Refuse amending on protected branches or branches with a pushed upstream.

    Returns 0 when amend is allowed, 1 when blocked.
    """
    if not amend:
        return 0
    branch = current_branch(cwd=root) or ""
    if branch in PROTECTED_BRANCHES:
        return _report_error(
            as_json=as_json,
            err=t("commit_amend_protected", branch=branch),
            code="commit_amend_protected",
        )
    if _is_pushed(branch, root):
        return _report_error(
            as_json=as_json,
            err=t("commit_amend_pushed", branch=branch),
            code="commit_amend_pushed",
        )
    return 0


def _print_dry_run(*, message: str, amend: bool, root: Path) -> None:
    """Print what would be committed without touching the working tree."""
    print_header(t("dry_run_no_exec"))
    print_bracket(t("commit_msg_label"), message)
    if amend:
        print_bracket(t("commit_amend_label"))
    branch = current_branch(cwd=root) or ""
    if branch:
        print_bracket(t("commit_branch_label"), branch)


def _validate_commit_message(message: str, as_json: bool = False) -> bool:
    """Return True if the first line matches the conventional-commit pattern."""
    if _CONVENTIONAL_RE.match(message.split("\n")[0]):
        return True
    _report_error(as_json=as_json, err=t("commit_invalid_format"), code="commit_invalid_format")
    return False


def _execute_commit(*, root: Path, message: str, amend: bool) -> tuple[bool, str]:
    """Run ``git commit`` and return (success, error_message)."""
    args = ["commit", "-m", message]
    if amend:
        args.append("--amend")
    result = git_run(args, cwd=root, check=False)
    if result.returncode == 0:
        return True, ""
    return False, t("git_command_failed", cmd="commit", error=result.stderr.strip())


def _validate_gpg_ready(root: Path, as_json: bool = False) -> bool:
    """Return False and print an error if GPG signing is enabled but no key is available."""
    gpg = gpg_status(cwd=root)
    if gpg["gpgsign_enabled"] and not gpg["ready"]:
        _report_error(
            as_json=as_json,
            err=t("gpg_signing_active_no_key"),
            code="gpg_not_ready",
        )
        return False
    return True


def _report_error(*, as_json: bool, err: str, code: str = "commit_failed") -> int:
    """Emit a commit error in JSON or human form and return 1."""
    if as_json:
        print_json(error_envelope("commit", error=err, code=code))
    else:
        error(err)
    return 1


# Back-compat alias for the previous helper name.
_report_commit_error = _report_error


def _enforce_secret_guard(*, root: Path, allow_secret: bool, as_json: bool) -> int | None:
    """Scan staged content for leaked credentials; return 1 to block, None to proceed.

    Runs by default on every commit. High-severity findings block unless
    ``allow_secret`` is set (human mode still asks for confirmation); medium
    findings only warn. The full secret is never printed -- previews are redacted.
    Fails closed: if the staged diff cannot be read, the commit is blocked
    rather than allowed through unscanned.
    """
    try:
        findings = scan_staged_diff(root)
    except SecretScanUnavailable as exc:
        unavailable = t("secret_scan_unavailable", error=str(exc))
        if as_json:
            print_json(error_envelope("commit", error=unavailable, code="secret_scan_unavailable"))
        else:
            error(unavailable)
        return 1
    if not findings:
        return None
    high = [f for f in findings if f["severity"] == "high"]
    medium = [f for f in findings if f["severity"] == "medium"]
    for f in medium:
        warn(
            t(
                "secret_scan_medium_warning",
                rule=f["rule"],
                path=f["path"],
                line=str(f["line"]),
                preview=f["preview"],
            )
        )
    if not high:
        return None
    if not allow_secret:
        if as_json:
            print_json(
                error_envelope(
                    "commit",
                    error=t("secret_scan_blocked_high", count=str(len(high))),
                    code="secret_leak_high",
                    hint=t("secret_scan_blocked_hint"),
                    findings=high,
                )
            )
        else:
            for f in high:
                error(
                    t(
                        "secret_scan_found",
                        rule=f["rule"],
                        path=f["path"],
                        line=str(f["line"]),
                        preview=f["preview"],
                    )
                )
            error(t("secret_scan_blocked_hint"))
        return 1
    if as_json:
        # An agent must not silence the secret confirmation via a prompt-set
        # flag. Require an operator-controlled env var so prompt injection
        # cannot smuggle `--allow-secret` into a forced commit.
        if os.environ.get(_ALLOW_SECRET_JSON_ENV, "") != "1":
            print_json(
                error_envelope(
                    "commit",
                    error=t("secret_allow_requires_env"),
                    code="secret_allow_requires_env",
                    hint=t("secret_allow_requires_env_hint"),
                    findings=high,
                )
            )
            return 1
        return None
    if not confirm(t("secret_scan_allow_confirm", count=str(len(high)))):
        return 1
    return None


def run_commit(
    *,
    message: str | None = None,
    type: str | None = None,
    scope: str | None = None,
    breaking: bool = False,
    amend: bool = False,
    dry_run: bool = False,
    allow_secret: bool = False,
    as_json: bool = False,
) -> int:
    """Validate a conventional-commit message and create a GPG-signed commit.

    Refuses with ``in_progress_<state>`` if an operation is paused. Enforces
    the project's amend policy (no amending pushed or protected branches)
    and GPG readiness before delegating to ``git commit``.
    """
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    in_progress = detect_in_progress(root)
    if in_progress["state"] != "none":
        hint = in_progress_hint(in_progress["state"])
        blocked_msg = t("commit_blocked_in_progress", state=in_progress["state"])
        if as_json:
            print_json(
                error_envelope(
                    "commit",
                    error=blocked_msg,
                    code=f"in_progress_{in_progress['state']}",
                    hint=hint,
                )
            )
            return 1
        error(blocked_msg, hint=hint)
        return 1

    amend_policy_rc = _validate_amend_policy(amend=amend, root=root, as_json=as_json)
    if amend_policy_rc != 0:
        return amend_policy_rc

    if message is None:
        return _report_error(as_json=as_json, err=t("commit_no_message"), code="commit_no_message")

    full_msg = _compose_message(message=message, type=type, scope=scope, breaking=breaking)

    if not _validate_commit_message(full_msg, as_json=as_json):
        return 1

    if not _validate_gpg_ready(root, as_json=as_json):
        return 1

    secret_rc = _enforce_secret_guard(root=root, allow_secret=allow_secret, as_json=as_json)
    if secret_rc is not None:
        return secret_rc

    if dry_run:
        if as_json:
            print_json(ok_envelope("commit", message=full_msg, amend=amend, dry_run=True))
        else:
            _print_dry_run(message=full_msg, amend=amend, root=root)
        return 0

    success, err = _execute_commit(root=root, message=full_msg, amend=amend)
    if not success:
        return _report_commit_error(as_json=as_json, err=err)

    if as_json:
        print_json(ok_envelope("commit", message=full_msg, amend=amend))
    return 0
