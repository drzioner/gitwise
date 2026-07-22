# Security Policy

[English](SECURITY.md) | [Español](SECURITY.es.md)

## Supported versions

| Version | Supported |
|---|---|
| Latest release | Yes |
| Older releases | No |

## Reporting a vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, use GitHub's private vulnerability reporting:

1. Go to [github.com/drzioner/gitwise/security/advisories](https://github.com/drzioner/gitwise/security/advisories)
2. Click "Report a vulnerability"
3. Fill in the details

You can also email **drzioner@gmail.com** with the subject `gitwise security: <brief description>`.

### What to include

- Type of vulnerability (e.g., command injection, path traversal, privilege escalation)
- Full steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (if you have one)

### Response timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 7 days
- **Fix and disclosure**: depends on severity, typically within 30 days

## Security features

gitwise includes these security measures:

- **Minimal runtime dependencies**: `rich`, `rich-argparse`, and `shtab`; Git operations use subprocesses.
- **Signing configuration preservation**: `setup` and `setup-agents` do not modify `commit.gpgsign`, `user.signingkey`, or credentials.
- **Agent bypass guards**: generated rules deny known signing and hook bypass flags.
- **Hardened subprocesses**: Git config/command injection variables are scrubbed and external processes use explicit timeouts.
- **Secret scanning**: `diff --scan-secrets` and `commit` detect high-confidence credential patterns and redact previews.
- **Sandboxed symlinks**: `_safe_create_symlink` applies TOCTOU and path traversal protections.
- **Pinned CI actions**: core third-party GitHub Actions use immutable SHAs.
- **Dependency and shell audits**: CI runs pip-audit and shellcheck.
- **Branch protection**: `main` requires passing CI and review for external contributions.
