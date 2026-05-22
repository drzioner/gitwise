# Release Process

gitwise uses automated releases via commitizen. Every merge to `main` triggers the `auto-release` workflow, which bumps the version, pushes a tag, and creates a GitHub Release.

## Automatic Release Flow

```
merge to main → CI → cz bump → git push --atomic (commit + tag) → gh release create
```

Commits prefixed with `bump:` are skipped to prevent infinite loops.

### Dry Run

Use **Actions → Auto Release → Run workflow** with `dry-run: true` to test the bump without publishing.

## Manual Rollback

If a bad release is published:

```bash
# 1. Delete the GitHub Release
gh release delete v0.X.0 --repo drzioner/gitwise --yes

# 2. Delete the remote tag
git push --delete origin v0.X.0

# 3. Revert the version bump commit on main
git revert <bump-commit-sha>

# 4. The next merge to main will auto-release the fix
```

## Skip a Release

To merge a PR without triggering a release, ensure all commits since the last release are `chore:` or `docs:` — commitizen only bumps on `feat:`, `fix:`, `refactor:`, `perf:`.

## Conventional Commit → Version Mapping

| Prefix | Bump Type | Example |
|--------|-----------|---------|
| `feat:` | Minor (0.X.0) | `feat: add worktree list command` |
| `fix:` | Patch (0.0.X) | `fix: correct symlink resolution` |
| `feat!:` or `BREAKING CHANGE` | Major (X.0.0) | `feat!: redesign CLI interface` |
