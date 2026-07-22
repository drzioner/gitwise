#!/usr/bin/env bash
set -Eeuo pipefail

version="$(gitwise --version)"
printf '=== %s: agent workflow demo ===\n\n' "$version"

printf '1. Check the environment:\n'
gitwise doctor --json || [[ $? -eq 1 ]]
printf '\n2. Preview the canonical agent layout:\n'
gitwise setup-agents --local --dry-run --yes --json --providers opencode
printf '\n3. Generate bounded repository context:\n'
gitwise context --max-entries 25 --json
printf '\n4. Inspect changed files:\n'
gitwise diff --stat --json
printf '\n5. Run a quick repository audit:\n'
gitwise audit --quick --json || [[ $? -eq 1 ]]
printf '\n=== Demo complete ===\n'
