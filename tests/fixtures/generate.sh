#!/usr/bin/env bash
# Generates 4 synthetic git repos used as test fixtures
# Run from project root: bash tests/fixtures/generate.sh
# Requires: git >= 2.29
set -euo pipefail

FIXTURES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$FIXTURES_DIR/repos"

rm -rf "$OUT"
mkdir -p "$OUT"

GIT_ENV=(
    GIT_AUTHOR_NAME="Fixture User"
    GIT_AUTHOR_EMAIL="fixture@example.com"
    GIT_COMMITTER_NAME="Fixture User"
    GIT_COMMITTER_EMAIL="fixture@example.com"
)

_commit() {
    local repo="$1" msg="$2"
    local file
    file="$repo/file-$(date +%s%N).txt"
    echo "content" > "$file"
    git -C "$repo" add .
    env "${GIT_ENV[@]}" git -C "$repo" commit --no-gpg-sign -m "$msg"
}

# Fixture 1: clean — 50 commits, sin ramas stale
echo "generating fixture-1-clean..."
git init -b main "$OUT/fixture-1-clean"
git -C "$OUT/fixture-1-clean" config user.email "fixture@example.com"
git -C "$OUT/fixture-1-clean" config user.name "Fixture User"
for i in $(seq 1 50); do
    _commit "$OUT/fixture-1-clean" "chore: commit $i"
done
git -C "$OUT/fixture-1-clean" commit-graph write --reachable
echo "  ✓ fixture-1-clean (50 commits, commit-graph present)"

# Fixture 2: dirty-with-stale — problemas reales
echo "generating fixture-2-dirty..."
git init -b main "$OUT/fixture-2-dirty"
git -C "$OUT/fixture-2-dirty" config user.email "fixture@example.com"
git -C "$OUT/fixture-2-dirty" config user.name "Fixture User"
_commit "$OUT/fixture-2-dirty" "chore: initial"
# Create stale branches (simulate [gone] by creating without push)
for branch in stale-1 stale-2 stale-3; do
    git -C "$OUT/fixture-2-dirty" checkout -b "$branch"
    _commit "$OUT/fixture-2-dirty" "feat: work on $branch"
    git -C "$OUT/fixture-2-dirty" checkout main
    # Mark as [gone] by setting upstream to nonexistent remote
    git -C "$OUT/fixture-2-dirty" branch --set-upstream-to=origin/nonexistent "$branch" 2>/dev/null || true
done
# Old stash
git -C "$OUT/fixture-2-dirty" stash push -m "old work" || true
echo "  ✓ fixture-2-dirty (stale branches, no commit-graph)"

# Fixture 3: gpg-configured
echo "generating fixture-3-gpg..."
git init -b main "$OUT/fixture-3-gpg"
git -C "$OUT/fixture-3-gpg" config user.email "fixture@example.com"
git -C "$OUT/fixture-3-gpg" config user.name "Fixture User"
git -C "$OUT/fixture-3-gpg" config commit.gpgsign true
git -C "$OUT/fixture-3-gpg" config user.signingkey "FAKEKEYID123"
_commit "$OUT/fixture-3-gpg" "chore: initial" 2>/dev/null || true
echo "  ✓ fixture-3-gpg (commit.gpgsign=true, user.signingkey=FAKEKEYID123)"

echo ""
echo "fixtures generated in: $OUT"
