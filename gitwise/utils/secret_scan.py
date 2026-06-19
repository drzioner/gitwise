"""Detect leaked credentials in diffs before they reach the object database.

Scans added lines (`+`, excluding the `+++` header) of a diff for high-signal
credential patterns. Designed for the commit-time guard (block on high
severity) and `diff --scan-secrets` (advisory). False-positive avoidance is a
hard requirement: the ruleset favours prefixed, vendor-documented formats over
generic "looks like a key" heuristics, so the project's own test corpus scans
clean.

Verified sources (token formats change over time; the GitHub `ghs_` rule in
particular was rewritten in 2026 to match the new stateless long-form):
- GitHub credential prefixes and the 2026 stateless `ghs_APPID_JWT` rollout:
  github.blog/changelog/2026-04-24-notice-about-upcoming-new-format-for-github-app-installation-tokens
  and github/docs content/organizations/.../github-credential-types.md
- Dual `ghs_` regex (legacy 36-char + long-form dotted) ported from
  github/gh-aw PR #34737 (2026-05-25)
- GitLab PAT length 27-300: docs.gitlab.com/security/tokens/ via GitLab MR 169322
- AWS access key id format `AKIA[0-9A-Z]{16}`: docs.aws.amazon.com/IAM/latest/.../reference_identifiers.html
- OpenSSH new-format magic `b3BlbnNzaC1rZXktdjE` (base64 of "openssh-key-v1"):
  protSPEC openssh/PROTOCOL.key
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, TypedDict

from ..git import run as git_run

SecretSeverity = Literal["high", "medium"]

_DIFF_ADDED_LINE_RE = re.compile(r"^\+(?!\+\+)")
_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class SecretScanUnavailable(RuntimeError):
    """Raised when the staged diff cannot be read, so a scan cannot run."""


class SecretFinding(TypedDict):
    """One credential match located in a scanned diff."""

    rule: str
    path: str
    line: int
    preview: str
    severity: SecretSeverity


# Each rule: (compiled pattern, human rule name, severity). Patterns target the
# credential itself; surrounding assignment context is handled where it raises
# precision (e.g. AWS secret key).
_GITHUB_TOKEN_RE = re.compile(
    r"(?:"
    r"gh[pou]_[A-Za-z0-9]{36,}"
    r"|ghr_[A-Za-z0-9]{36,}"
    r"|ghs_(?:[0-9A-Za-z]{36}(?![0-9A-Za-z._-])|[0-9A-Za-z_-]{10,}(?:\.[0-9A-Za-z_-]{10,}){2,})"
    r"|github_pat_[A-Za-z0-9_]{80,}"
    r")"
)

_RULES: list[tuple[re.Pattern[str], str, SecretSeverity]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key_id", "high"),
    (
        re.compile(r"(?i)aws_secret_access_key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})"),
        "aws_secret_access_key",
        "high",
    ),
    (_GITHUB_TOKEN_RE, "github_token", "high"),
    (re.compile(r"glpat-[A-Za-z0-9_-]{20,300}"), "gitlab_pat", "high"),
    (
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED |)PRIVATE KEY-----"),
        "private_key_pem",
        "high",
    ),
    (re.compile(r"b3BlbnNzaC1rZXktdjE[A-Za-z0-9+/=]*"), "openssh_private_key", "high"),
    (
        re.compile(
            r"(?i)(?:api[_-]?key|secret|token|password)['\"]?\s*[:=]\s*['\"]([A-Za-z0-9_\-]{24,})['\"]"
        ),
        "generic_secret_assignment",
        "medium",
    ),
]

_PREVIEW_KEEP_PREFIX = 8
_PREVIEW_KEEP_SUFFIX = 4


def _redact(match: str) -> str:
    """Truncate a credential for display so the full secret is never printed."""
    if len(match) <= _PREVIEW_KEEP_PREFIX + _PREVIEW_KEEP_SUFFIX:
        return "***"
    return f"{match[:_PREVIEW_KEEP_PREFIX]}...{match[-_PREVIEW_KEEP_SUFFIX:]}"


def _staged_diff_text(root: Path) -> str:
    """Return the full cached diff text.

    Raises ``SecretScanUnavailable`` when git itself reports a failure, so the
    commit guard fails closed (block) instead of silently treating an
    unscannable index as clean.
    """
    result = git_run(["--no-pager", "diff", "--cached"], cwd=root, check=False)
    if result.returncode != 0:
        raise SecretScanUnavailable(result.stderr.strip() or "git diff --cached failed")
    return result.stdout


def _parse_diff_hunk_for_path(line: str) -> str | None:
    """Return the path from a `+++ <path>` diff header, or None.

    Handles both the default `+++ b/<path>` prefix and the prefixless form a
    user gets with `diff.noprefix=true`, plus `/dev/null` (file absent on the
    new side of a delete).
    """
    if not line.startswith("+++ "):
        return None
    rest = line[4:]
    if rest == "/dev/null":
        return None
    if rest.startswith("b/"):
        return rest[2:]
    return rest


def secret_scan(diff_text: str) -> list[SecretFinding]:
    """Scan added lines of a unified diff for credential patterns.

    Only lines introduced by the diff (leading `+`, excluding the `+++` header)
    are inspected, so pre-existing content is never flagged. Reported line
    numbers are the true new-file line numbers parsed from each
    ``@@ -old,+new @@`` hunk header (so a finding points at the exact line to
    remediate even across multi-hunk or delete-heavy diffs). Each match becomes
    a ``SecretFinding`` with a redacted preview.
    """
    findings: list[SecretFinding] = []
    current_path = ""
    line_no = 0
    for raw in diff_text.splitlines():
        path_from_header = _parse_diff_hunk_for_path(raw)
        if path_from_header is not None:
            current_path = path_from_header
            line_no = 0
            continue
        hunk = _HUNK_HEADER_RE.match(raw)
        if hunk:
            # Next context/added line in the new file is +new_start; decrement
            # so the increment below lands on the right number.
            line_no = int(hunk.group(1)) - 1
            continue
        if raw.startswith("-"):
            # Removed lines belong to the old file only and do not advance the
            # new-file line counter.
            continue
        if not _DIFF_ADDED_LINE_RE.match(raw):
            if raw.startswith(" "):
                line_no += 1
            continue
        line_no += 1
        payload = raw[1:]
        for pattern, rule, severity in _RULES:
            for match in pattern.finditer(payload):
                findings.append(
                    SecretFinding(
                        rule=rule,
                        path=current_path,
                        line=line_no,
                        preview=_redact(match.group(0)),
                        severity=severity,
                    )
                )
    # Suppress the generic rule when a vendor-specific rule already flagged the
    # same line: "ghp_..." should report github_token (high), not also a noisy
    # medium generic_secret_assignment on top of it.
    specific_keys = {
        (f["path"], f["line"]) for f in findings if f["rule"] != "generic_secret_assignment"
    }
    return [
        f
        for f in findings
        if f["rule"] != "generic_secret_assignment" or (f["path"], f["line"]) not in specific_keys
    ]


def scan_staged_diff(root: Path) -> list[SecretFinding]:
    """Convenience wrapper: scan the index (staged) diff of `root`."""
    return secret_scan(_staged_diff_text(root))


def has_high_severity(findings: list[SecretFinding]) -> bool:
    """Return True if any finding is high severity (commit-blocking)."""
    return any(finding["severity"] == "high" for finding in findings)
