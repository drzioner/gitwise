# Label Taxonomy — gitwise

> Last updated: 2026-05-15
> Convention: `prefix/value` — scannable, filterable, consistent.

This document defines the GitHub label taxonomy for the gitwise repository. Labels follow the `prefix/value` convention used by projects like Apache Burr, Kubernetes, and recommended by GitHub's own triage best practices.

---

## Labeling rules

| Rule | Details |
|------|---------|
| **Every issue gets at least one `kind/`** | Required — describes what the issue is |
| **Every issue gets at least one `area/`** | Required — describes where in the codebase |
| **`priority/` is set after triage** | Applied by maintainers during review |
| **`status/` tracks workflow** | Updated as the issue progresses |
| **Special labels are GitHub-native** | `good first issue` and `help wanted` are recognized by GitHub's UI |
| **At most 1 priority, 1 status** | Avoid conflicting labels |

### Triage workflow

```
New issue → status/needs-triage
          → kind/* + area/* applied
          → priority/* assigned
          → status/accepted (ready to work)
          → status/in-progress (assigned)
          → closed (fixed/wontfix)
```

---

## `kind/` — What it is

**Required on every issue and PR.** Describes the nature of the work.

| Label | Color | When to use |
|-------|-------|-------------|
| `kind/bug` | `#d73a4a` | Something is broken, crashes, or produces incorrect output |
| `kind/feature` | `#a2eeef` | Net-new functionality: new subcommand, new flag, new integration |
| `kind/improvement` | `#7fd4f2` | Enhancing existing functionality: better output, faster performance |
| `kind/documentation` | `#0075ca` | Docs, examples, guidelines, README, AGENTS.md, CONTRIBUTING.md |
| `kind/cleanup` | `#e6e6e6` | Refactor, typos, tech debt, code smell, dependency updates |
| `kind/question` | `#d876e3` | Usage question, how-to, clarification request |
| `kind/security` | `#b60205` | Security vulnerability, GPG issue, credential exposure |

---

## `area/` — Where in the codebase

**At least 1 per issue/PR.** Maps to project structure.

| Label | Color | Covers |
|-------|-------|--------|
| `area/core` | `#1a5276` | `__main__.py`, `git.py`, `output.py`, shared helpers |
| `area/setup-agents` | `#6f42c1` | `setup_agents/` package, 5-bucket model, AGENTS.md/CLAUDE.md coexistence |
| `area/cli` | `#0052cc` | Argparse routing, subcommand pattern, output formatting, i18n |
| `area/git-ops` | `#29C8CA` | `audit.py`, `clean.py`, `optimize.py`, `worktree.py`, `diff.py`, `summarize.py` |
| `area/templates` | `#c5def5` | `share/` directory: CLAUDE.md.template, settings.json, skills, hooks |
| `area/testing` | `#bfd4f2` | `tests/`, `conftest.py`, fixtures, coverage configuration |
| `area/ci` | `#f9d0c4` | `.github/workflows/`, `lefthook.yml`, `dependabot.yml` |
| `area/i18n` | `#fbca04` | `i18n.py`, translations, locale detection, string catalog |
| `area/docs` | `#d4c5f9` | `docs/`, `LANGUAGE.md`, guidelines, design documents |

---

## `priority/` — How urgent

**Applied after triage.** Combines severity and user impact.

| Label | Color | Criteria |
|-------|-------|----------|
| `priority/critical` | `#b60205` | Blocks release, breaks core functionality, data loss risk |
| `priority/high` | `#d93f0b` | Affects many users, regression, needs action within days |
| `priority/medium` | `#fbca04` | Important but not urgent, standard feature request |
| `priority/low` | `#0e8a16` | Nice-to-have, polish, backlog item |

---

## `status/` — Where in the workflow

**Tracks the issue lifecycle.** Updated as work progresses.

| Label | Color | When to apply |
|-------|-------|---------------|
| `status/needs-triage` | `#BBEC04` | New issue, awaiting initial review |
| `status/needs-info` | `#f9d0c4` | Waiting on author for reproduction steps, version, etc. |
| `status/accepted` | `#0e8a16` | Triaged, validated, ready for someone to pick up |
| `status/blocked` | `#b60205` | Depends on another issue, PR, or external decision |
| `status/in-progress` | `#0075ca` | Someone is actively working on it |
| `status/wontfix` | `#ffffff` | Decided not to address (with closing comment explaining why) |

---

## `lifecycle/` — Long-term management

| Label | Color | When to apply |
|-------|-------|---------------|
| `lifecycle/stale` | `#e6e6e6` | No activity for 90+ days. Auto-applied by stale bot if configured. |
| `lifecycle/frozen` | `#d4c5f9` | Protected from auto-close. Use for roadmap items and umbrella issues. |

---

## Special labels

These are recognized by GitHub's native UI features.

| Label | Color | Purpose |
|-------|-------|---------|
| `good first issue` | `#7057ff` | Well-scoped, documented, no deep domain knowledge needed. Populates GitHub's contribute page. |
| `help wanted` | `#008672` | Maintainer wants external help. Signals openness to community contributions. |
| `dependencies` | `#0366d6` | Used by Dependabot for automated dependency updates. |
| `breaking-change` | `#b60205` | PR or issue that introduces backward-incompatible changes. Must include migration guide. |

---

## Label/commit type mapping

The `kind/` labels map to conventional commit types used by commitizen:

| Label | Commit type |
|-------|-------------|
| `kind/bug` | `fix:` |
| `kind/feature` | `feat:` |
| `kind/improvement` | `refactor:` or `feat:` depending on scope |
| `kind/documentation` | `docs:` |
| `kind/cleanup` | `chore:` or `refactor:` |
| `kind/security` | `fix:` with `BREAKING CHANGE` footer if needed |
| `kind/question` | N/A (no commit) |

---

## Managing labels

### Create a new label

```bash
gh label create "area/new-module" -c "HEXCOLOR" -d "Description" -f
```

### Apply labels to an issue

```bash
gh issue edit 42 --add-label "kind/bug,area/git-ops,priority/high"
```

### List all labels

```bash
gh label list
```

### Bulk-apply labels to the current PR

```bash
gh pr edit --add-label "kind/documentation,area/docs,priority/medium"
```
