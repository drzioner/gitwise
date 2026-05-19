#!/usr/bin/env bash
set -Eeuo pipefail

echo "=== gitwise v0.12.0 — Adapter Demo ==="
echo ""
echo "1. Listing available adapters:"
gitwise setup-agents --list-adapters
echo ""
echo "2. Dry-run with cursor adapter:"
gitwise setup-agents --local --dry-run --yes --adapters cursor
echo ""
echo "3. Installing cursor + aider adapters:"
gitwise setup-agents --local --yes --adapters cursor --adapters aider
echo ""
echo "4. Verifying created files:"
ls -la .cursor/rules/gitwise.mdc .aider/gitwise.md 2>/dev/null || echo "(files not found — run from a git repo)"
echo ""
echo "5. JSON output:"
gitwise setup-agents --local --dry-run --yes --json --adapters opencode
echo ""
echo "=== Demo complete ==="
