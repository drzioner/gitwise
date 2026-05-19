---
alwaysApply: false
paths: bin/*, install.sh
---

# Shell Script Conventions

- ShellCheck clean: `shellcheck install.sh bin/gitwise` passes with zero warnings
- `set -Eeuo pipefail` at top of all shell scripts
- Quote all variable expansions; never leave `$var` unquoted
- Check exit codes directly with `if command; then` — never `if [ $? -eq 0 ]`
