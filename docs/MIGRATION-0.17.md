Source: docs/MIGRATION-0.17.md
Last sync: 2026-05-23

# setup-agents migration guide (0.17)

This guide explains how to migrate from legacy Claude-only layout to canonical agents-first layout.

## Target layout

- Canonical document: `AGENTS.md`
- Canonical skills: `.agents/skills/<skill>/SKILL.md`
- Compatibility layer: `CLAUDE.md` may remain as symlink to `AGENTS.md`

## Automatic migration (recommended)

Run in repository root:

```bash
gitwise setup-agents --local --yes --migrate-legacy-claude
```

Dry-run first:

```bash
gitwise setup-agents --local --dry-run --migrate-legacy-claude
```

## What migrates

- If only `CLAUDE.md` exists, `AGENTS.md` is created from current content and `CLAUDE.md` becomes a symlink.
- Skills move to `.agents/skills/` and `.claude/skills/<name>` becomes symlink where applicable.
- Snapshot target switches to `.agents/git-snapshot.md` for canonical layout.

## Idempotency

You can run migration command multiple times safely; no duplicate content should be produced.

## Deprecated alias

- `--providers claude-only` is deprecated and treated as `--providers claude`.
- `--adapters` remains as hidden legacy alias for compatibility.
