"""Tests for gitwise.utils.secret_scan.

Sample tokens are assembled at runtime from prefix + body fragments so the test
source never contains a complete credential literal -- otherwise the commit-time
guard would flag this very file. Each fragment on its own does not match a rule.
"""

from __future__ import annotations

from gitwise.utils.secret_scan import _redact, has_high_severity, redact_findings, secret_scan


def _tok(prefix: str, body: str) -> str:
    """Assemble a sample token at runtime; the source stays scanner-clean."""
    return prefix + body


_AWS_KEY = _tok("AK", "IAIOSFODNN7EXAMPLE")
_GHP = _tok("ghp_", "aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789")
_GHO = _tok("gho_", "aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789")
_GHS_LEGACY = _tok("ghs_", "16C7e42F292c6912E7710c838347Ae178B4a")
_GHS_LONG = _tok("ghs_", "abcdEFGH1234" + ".ijklMNOP5678" + ".qrstUVWX9012")
_GITHUB_PAT = _tok(
    "github_pat_",
    "11AABCDE0aBcDeFgHiJkLmNoPqRsTuVwXyZ" + "0123456789aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789ABCD",
)
_GITLAB = _tok("glpat-", "x" * 27)
_PEM_HEADER = "-----BEGIN " + "RSA PRIVATE KEY-----"
_OPENSSH_MAGIC = _tok("b3BlbnNzaC1r", "ZXktdjEAAAAA")


def test_scan_aws_access_key():
    """A staged AKIA-style key is flagged high."""
    findings = secret_scan(f"+key = '{_AWS_KEY}'\n")
    assert len(findings) == 1
    assert findings[0]["rule"] == "aws_access_key_id"
    assert findings[0]["severity"] == "high"


def test_scan_aws_secret_assignment():
    """An aws_secret_access_key assignment is flagged high."""
    body = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    diff = f"+aws_secret_access_key = {body}\n"
    findings = secret_scan(diff)
    assert any(f["rule"] == "aws_secret_access_key" and f["severity"] == "high" for f in findings)


def test_scan_github_token_classic_prefixes():
    """ghp_, gho_ classic tokens are flagged high."""
    for token in (_GHP, _GHO):
        findings = secret_scan(f"+token = '{token}'\n")
        assert len(findings) == 1
        assert findings[0]["rule"] == "github_token"
        assert findings[0]["severity"] == "high"


def test_scan_github_installation_legacy_and_longform():
    """Both legacy 36-char ghs_ and 2026 long-form ghs_ are flagged."""
    for token in (_GHS_LEGACY, _GHS_LONG):
        findings = secret_scan(f"+token = '{token}'\n")
        assert any(f["rule"] == "github_token" for f in findings)


def test_scan_github_fine_grained_pat():
    """github_pat_ fine-grained tokens are flagged high."""
    findings = secret_scan(f"+token = '{_GITHUB_PAT}'\n")
    assert any(f["rule"] == "github_token" and f["severity"] == "high" for f in findings)


def test_scan_gitlab_pat():
    """A glpat- token is flagged high."""
    findings = secret_scan(f"+token = '{_GITLAB}'\n")
    assert len(findings) == 1
    assert findings[0]["rule"] == "gitlab_pat"


def test_scan_private_key_pem_variants():
    """RSA, EC, and generic PEM private-key headers are flagged high."""
    for header in (
        "-----BEGIN " + "RSA PRIVATE KEY-----",
        "-----BEGIN " + "EC PRIVATE KEY-----",
        "-----BEGIN " + "PRIVATE KEY-----",
    ):
        findings = secret_scan(f"+{header}\n")
        assert any(f["rule"] == "private_key_pem" for f in findings)


def test_scan_openssh_new_format():
    """The OpenSSH new-format magic base64 is flagged high."""
    findings = secret_scan(f"+key = '{_OPENSSH_MAGIC}restofkey'\n")
    assert any(f["rule"] == "openssh_private_key" for f in findings)


def test_scan_generic_secret_assignment_is_medium():
    """A generic api_key/secret/token assignment is medium severity."""
    diff = '+api_key = "' + "a" * 30 + '"\n'
    findings = secret_scan(diff)
    assert findings
    assert all(f["severity"] == "medium" for f in findings)


def test_scan_clean_text_has_no_findings():
    """Normal source code produces no findings."""
    diff = "+import os\n+print('hello world')\n+MAX_RETRIES = 3\n"
    assert secret_scan(diff) == []


def test_scan_ignores_removed_and_context_lines():
    """Only added lines (leading +, not +++) are inspected."""
    diff = f"-key = '{_AWS_KEY}'\n context line\n+++ b/file.py\n"
    assert secret_scan(diff) == []


def test_scan_tracks_path_from_diff_header():
    """Findings are attributed to the path in the +++ b/<path> header."""
    diff = f"+++ b/config/prod.py\n+key = '{_AWS_KEY}'\n"
    findings = secret_scan(diff)
    assert findings[0]["path"] == "config/prod.py"


def test_scan_tracks_path_without_b_prefix():
    """The path is still captured when diff.noprefix=true strips the b/ prefix."""
    diff = f"+++ config/prod.py\n+key = '{_AWS_KEY}'\n"
    findings = secret_scan(diff)
    assert findings[0]["path"] == "config/prod.py"


def test_scan_line_number_from_hunk_header():
    """Reported line numbers follow the @@ -a,+b @@ hunk header, not a 0-based count."""
    diff = f"+++ b/config.py\n@@ -1,3 +1,3 @@\n context line one\n-old line\n+key = '{_AWS_KEY}'\n"
    findings = secret_scan(diff)
    assert findings[0]["line"] == 2


def test_scan_line_number_across_multiple_hunks():
    """Each hunk resets the counter to its own +new_start, even with deletions."""
    diff = (
        f"+++ b/config.py\n"
        f"@@ -1,1 +1,1 @@\n"
        f"+key = '{_AWS_KEY}'\n"
        f"@@ -50,2 +100,2 @@\n"
        f" context\n"
        f"+token = '{_GHP}'\n"
    )
    findings = secret_scan(diff)
    lines = {f["rule"]: f["line"] for f in findings}
    assert lines["aws_access_key_id"] == 1
    assert lines["github_token"] == 101


def test_scan_preview_redaction():
    """The full secret never appears in the preview."""
    findings = secret_scan(f"+x = '{_GHP}'\n")
    preview = findings[0]["preview"]
    assert _GHP not in preview
    assert preview.startswith("ghp_")


def test_has_high_severity_predicate():
    """has_high_severity returns True only when a high finding exists."""
    high = secret_scan(f"+x = '{_AWS_KEY}'\n")
    medium = secret_scan('+api_key = "' + "a" * 30 + '"\n')
    clean = secret_scan("+print('hi')\n")
    assert has_high_severity(high) is True
    assert has_high_severity(medium) is False
    assert has_high_severity(clean) is False


def test_scan_no_false_positive_on_regex_source():
    """Rule source text (regex patterns as literals) is not self-flagged."""
    diff = "+    (re.compile(r'gh[pou]_[A-Za-z0-9]{36,}'), 'github_token', 'high'),\n"
    assert secret_scan(diff) == []


def test_redaction_for_short_matches():
    """Short matches collapse to '***' rather than leaking partial content."""
    assert _redact("short") == "***"


def test_redact_findings_omits_preview():
    """JSON-safe findings must not include the credential preview."""
    findings = secret_scan(f"+key = '{_AWS_KEY}'\n")
    assert findings and findings[0]["preview"]
    safe = redact_findings(findings)
    assert len(safe) == len(findings)
    assert "preview" not in safe[0]
    assert safe[0]["rule"] == findings[0]["rule"]
    assert safe[0]["line"] == findings[0]["line"]
