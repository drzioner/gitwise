"""Policy evaluation engine: the gate between an agent and the object database.

Two halves, deliberately separated. ``collect_*_context`` reads git and is the
only part that touches the repository; ``evaluate_*`` is pure and decides. That
split is what lets every rule be tested against a real index without a fixture
per rule, and what lets the same verdict serve three callers -- the git hooks,
``gitwise commit``, and an agent asking permission before it acts.

Violations are data, never prose to be parsed: a caller branches on ``rule`` and
``severity``. The credential itself never enters a violation, only the rule that
matched and where.
"""

from __future__ import annotations

import fnmatch
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, TypedDict

from gitwise.git import current_branch, gpg_status, require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import error, ok, print_json, report_error, status, warn
from gitwise.policy import Policy, PolicyError, load_policy, policy_source
from gitwise.utils.in_progress import InProgressInfo, detect_in_progress
from gitwise.utils.json_envelope import ok_envelope
from gitwise.utils.secret_scan import SecretScanUnavailable, scan_staged_diff

ZERO_OBJECT_NAME = "0" * 40

Severity = Literal["block", "warn"]


class Violation(TypedDict):
    """One policy rule that the inspected operation breaks."""

    rule: str
    severity: Severity
    message: str
    path: str | None
    detail: str | None


class CommitContext(TypedDict):
    """Everything the commit rules need, read once from the repository."""

    branch: str | None
    staged_paths: list[str]
    secret_findings: Sequence[Mapping[str, object]]
    secret_scan_error: str | None
    in_progress: InProgressInfo
    gpg: dict[str, bool]
    amend: bool


class PushRef(TypedDict):
    """One ref update proposed by a push, with its fast-forward verdict."""

    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str
    deleting: bool
    non_fast_forward: bool


class PushContext(TypedDict):
    """The ref updates a push would perform."""

    refs: list[PushRef]


def _violation(
    rule: str,
    severity: Severity,
    message: str,
    *,
    path: str | None = None,
    detail: str | None = None,
) -> Violation:
    """Build a Violation with the optional fields defaulted."""
    return {
        "rule": rule,
        "severity": severity,
        "message": message,
        "path": path,
        "detail": detail,
    }


def staged_paths(root: Path) -> list[str]:
    """Return the repository-relative paths currently staged in *root*."""
    result = git_run(["diff", "--cached", "--name-only"], cwd=root, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def path_is_forbidden(path: str, patterns: list[str]) -> bool:
    """Return True if *path* matches any pattern, by full path or by basename.

    Patterns are fnmatch globs. They are tried against the full
    repository-relative path (so ``secrets/**`` catches ``secrets/prod.key``)
    and against the basename (so ``*.pem`` catches a key at any depth), because
    fnmatch does not treat ``/`` as a separator and a pattern without one would
    otherwise only ever match files at the repository root.
    """
    basename = path.rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(basename, pattern)
        for pattern in patterns
    )


def collect_commit_context(root: Path, *, amend: bool = False) -> CommitContext:
    """Read the repository state the commit rules evaluate.

    A secret scan that cannot run is recorded as ``secret_scan_error`` rather
    than as an empty finding list, so the rules can fail closed on it instead of
    mistaking "did not scan" for "scanned clean".
    """
    try:
        findings: Sequence[Mapping[str, object]] = list(scan_staged_diff(root))
        scan_error: str | None = None
    except SecretScanUnavailable as exc:
        findings = []
        scan_error = str(exc)

    return {
        "branch": current_branch(cwd=root),
        "staged_paths": staged_paths(root),
        "secret_findings": findings,
        "secret_scan_error": scan_error,
        "in_progress": detect_in_progress(root),
        "gpg": gpg_status(cwd=root),
        "amend": amend,
    }


def evaluate_commit(policy: Policy, context: CommitContext) -> list[Violation]:
    """Return every policy violation the staged commit would commit."""
    violations: list[Violation] = []

    state = context["in_progress"]["state"]
    if state != "none":
        violations.append(
            _violation(
                "in_progress",
                "block",
                f"a {state} is in progress; finish or abort it before committing",
                detail=state,
            )
        )

    branch = context["branch"]
    if branch and branch in policy["protected_branches"]:
        violations.append(
            _violation(
                "protected_branch",
                "block",
                f"branch {branch!r} is protected by the repository policy",
                detail=branch,
            )
        )

    for path in context["staged_paths"]:
        if path_is_forbidden(path, policy["forbidden_paths"]):
            violations.append(
                _violation(
                    "forbidden_path",
                    "block",
                    f"{path} matches a forbidden path in the repository policy",
                    path=path,
                )
            )

    if context["secret_scan_error"] is not None:
        violations.append(
            _violation(
                "secret_scan_unavailable",
                "block",
                "the staged diff could not be scanned for credentials",
                detail=context["secret_scan_error"],
            )
        )

    for finding in context["secret_findings"]:
        high = finding.get("severity") == "high"
        severity: Severity = "block" if (high and policy["block_secrets"]) else "warn"
        violations.append(
            _violation(
                "secret",
                severity,
                f"possible {finding.get('rule')} credential in staged content",
                path=str(finding.get("path")) if finding.get("path") is not None else None,
                detail=f"line {finding.get('line')}",
            )
        )

    if policy["require_gpg"] and not context["gpg"].get("ready", False):
        violations.append(
            _violation(
                "gpg",
                "block",
                "the repository policy requires GPG signing, which is not ready",
            )
        )

    return violations


def parse_push_stdin(text: str) -> list[tuple[str, str, str, str]]:
    """Parse the pre-push hook's stdin into ref-update tuples.

    Format per githooks(5):
    ``<local-ref> SP <local-object-name> SP <remote-ref> SP <remote-object-name> LF``.
    Lines that do not carry four fields are ignored rather than guessed at.
    """
    updates: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        updates.append((fields[0], fields[1], fields[2], fields[3]))
    return updates


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return True if *ancestor* is reachable from *descendant*."""
    result = git_run(["merge-base", "--is-ancestor", ancestor, descendant], cwd=root, check=False)
    return result.returncode == 0


def collect_push_context(root: Path, stdin_text: str) -> PushContext:
    """Classify each proposed ref update as a delete, a fast-forward, or not.

    git does not tell the hook whether ``--force`` was passed, so a rewrite is
    detected structurally: the remote tip must be an ancestor of the local tip,
    otherwise the push would drop commits the remote already has.
    """
    refs: list[PushRef] = []
    for local_ref, local_sha, remote_ref, remote_sha in parse_push_stdin(stdin_text):
        deleting = local_ref == "(delete)" or local_sha == ZERO_OBJECT_NAME
        creating = remote_sha == ZERO_OBJECT_NAME
        non_fast_forward = False
        if not deleting and not creating:
            non_fast_forward = not _is_ancestor(root, remote_sha, local_sha)
        refs.append(
            {
                "local_ref": local_ref,
                "local_sha": local_sha,
                "remote_ref": remote_ref,
                "remote_sha": remote_sha,
                "deleting": deleting,
                "non_fast_forward": non_fast_forward,
            }
        )
    return {"refs": refs}


def evaluate_push(policy: Policy, context: PushContext) -> list[Violation]:
    """Return every policy violation the proposed push would commit."""
    violations: list[Violation] = []
    for ref in context["refs"]:
        branch = ref["remote_ref"].removeprefix("refs/heads/")
        protected = branch in policy["protected_branches"]
        if not protected:
            continue
        if ref["deleting"]:
            violations.append(
                _violation(
                    "protected_branch_delete",
                    "block",
                    f"refusing to delete protected branch {branch!r} on the remote",
                    detail=branch,
                )
            )
            continue
        if ref["non_fast_forward"] and not policy["allow_force_push"]:
            violations.append(
                _violation(
                    "force_push",
                    "block",
                    f"non-fast-forward push to protected branch {branch!r} would rewrite history",
                    detail=branch,
                )
            )
    return violations


def blocking(violations: list[Violation]) -> list[Violation]:
    """Return only the violations that must stop the operation."""
    return [violation for violation in violations if violation["severity"] == "block"]


def _violations_payload(violations: list[Violation]) -> list[dict[str, object]]:
    """Return violations as plain dicts for the JSON envelope."""
    return [dict(violation) for violation in violations]


def run_guard_check(
    *,
    push: bool = False,
    stdin_text: str | None = None,
    as_json: bool = False,
) -> int:
    """Evaluate the repository policy and report the verdict without side effects.

    Exit codes: 0 when nothing blocks, 2 when the policy blocks the operation,
    1 on an operational failure (not a repository, unreadable policy). The
    distinct 2 lets a caller tell "policy stopped me" from "the tool broke",
    which a hook collapses into a single non-zero but an agent must not.
    """
    root = require_root(as_json=as_json, command="guard")
    if root is None:
        return 1

    try:
        policy = load_policy(root)
    except PolicyError as exc:
        return report_error(
            "guard",
            as_json=as_json,
            msg=t("guard_policy_invalid", error=str(exc)),
            code="policy_invalid",
            hint=t("guard_policy_invalid_hint"),
        )

    with status(t("status_guard_check")):
        if push:
            text = stdin_text if stdin_text is not None else sys.stdin.read()
            violations = evaluate_push(policy, collect_push_context(root, text))
            scope = "push"
        else:
            violations = evaluate_commit(policy, collect_commit_context(root))
            scope = "commit"

    blockers = blocking(violations)
    warnings = [v for v in violations if v["severity"] == "warn"]

    if as_json:
        print_json(
            ok_envelope(
                "guard",
                data={
                    "action": "check",
                    "scope": scope,
                    "allowed": not blockers,
                    "violations": _violations_payload(violations),
                    "blocking_count": len(blockers),
                    "warning_count": len(warnings),
                    "policy_source": policy_source(root),
                },
            )
        )
    else:
        for violation in violations:
            line = t("guard_violation", rule=violation["rule"], message=violation["message"])
            if violation["severity"] == "block":
                error(line)
            else:
                warn(line)
        if blockers:
            error(t("guard_blocked", count=str(len(blockers))))
        elif warnings:
            warn(t("guard_warnings", count=str(len(warnings))))
        else:
            ok(t("guard_allowed"))

    return 2 if blockers else 0


def run_guard(
    action: str | None,
    *,
    push: bool = False,
    as_json: bool = False,
) -> int:
    """Entry point for the ``gitwise guard`` command."""
    if action is None:
        return report_error(
            "guard",
            as_json=as_json,
            msg=t("guard_action_required"),
            code="action_required",
        )
    if action == "check":
        return run_guard_check(push=push, as_json=as_json)
    return report_error(
        "guard",
        as_json=as_json,
        msg=t("guard_unknown_action", action=action),
        code="unknown_action",
    )
