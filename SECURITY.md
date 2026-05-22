# Security Policy

[English](SECURITY.md) | [Espanol](SECURITY.es.md)

## Supported versions

| Version | Supported |
|---|---|
| >= 0.1.0 | Yes |
| < 0.1.0 | No |

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

- **Minimal runtime dependencies** — one runtime dependency (`rich>=13.0`) and otherwise stdlib + git subprocess
- **GPG signing enforcement** — pre-commit hook validates key availability
- **Sandboxed symlinks** — `_safe_create_symlink` with TOCTOU protection and path traversal prevention
- **No secrets in code** — credentials, tokens, and keys are never logged or stored
- **Pinned CI actions** — core third-party GitHub Actions are pinned by SHA, not mutable tags
- **pip-audit in CI** — continuous dependency vulnerability scanning
- **shellcheck** — static analysis on all shell scripts
- **Branch protection** — main branch requires passing CI and review for external contributions
