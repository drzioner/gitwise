---
alwaysApply: true
---

# GitHub Actions — Security Conventions

> **Loading:** This rule has `alwaysApply: true` frontmatter and no path scope, so it loads **Always** and applies unconditionally across all supported agents (Claude Code, opencode, etc.). Every workflow change must satisfy these conventions regardless of which files it touches.

This project is **public**. Every workflow change must assume untrusted inputs
can reach `run:` blocks via interpolation.

## Rule: never use `${{ }}` inside `run:` blocks

`run:` blocks are interpolated by the workflow runner into a shell script.
If an attacker can control the interpolated value, they get arbitrary shell
execution. Attackers control more than you think:

- `inputs.*` from `workflow_dispatch` (anyone with repo write access)
- `github.event.issue.title`, `github.event.pull_request.body`, etc.
- `github.event.workflow_run.head_branch` from upstream workflows
- Step outputs that chain from any of the above

### Required pattern

Always pass interpolated values via the `env:` block, then reference the env
var inside the script. The runner treats `env:` values as opaque strings, so
shell metacharacters in them are inert.

```yaml
# WRONG — template injection vector
- name: Bad
  run: |
    git push origin "refs/tags/${{ steps.bump.outputs.tag }}"

# RIGHT — env: is treated as a literal string
- name: Good
  env:
    TAG: ${{ steps.bump.outputs.tag }}
  run: |
    git push origin "refs/tags/${TAG}"
```

### Edge case: `if:` conditions

`if:` conditions **can** contain `${{ }}` because the runner evaluates them as
YAML expressions, not shell. They are safe.

```yaml
# OK — if: is a YAML expression context, not shell
- name: OK
  if: steps.bump.outputs.no_bump == 'false'
```

## Enforcement

A repo-level audit script lives at `scripts/audit-template-injection.py`. Run
it locally before pushing workflow changes:

```bash
python3 scripts/audit-template-injection.py
```

CI also runs it on every PR (see `.github/workflows/ci.yml` — "Workflow
audit" job). The check fails the PR if any `${{ }}` appears inside a `run:`
block.

## Other GitHub Actions security rules

- **Pin all `uses:` by SHA**, not by tag. Tags can be moved by maintainers of
  the action; SHAs are immutable. Comment the version next to the SHA so
  Dependabot can bump it (`uses: actions/checkout@9c091bb2... # v7.0.0`).
  The CI job "Workflow Audit" runs `scripts/audit-template-injection.py`
  on every PR, which fails the build if any `uses:` is pinned to a tag
  (`@v4`) or branch (`@main`) instead of a SHA. Local actions (`./...`)
  and Docker actions (`docker://...`) are exempt.
- **Use `permissions:` at the workflow level** with the minimum scope. Use
  `contents: read` as the default and elevate only in jobs that need write.
- **Use GitHub App tokens for cross-repo automation**, not PATs. App tokens
  are scoped, short-lived, and auditable.
- **Set `persist-credentials: false` on `actions/checkout`** unless the next
  step genuinely needs to push back to the same repo (in which case document
  why you cannot set it to false).
- **Prefer `workflow_run` over `repository_dispatch`** when chaining workflows
  inside the same repo — `workflow_run` does not require sharing secrets.
- **Never log secrets.** GitHub masks known secrets, but `echo "$VAR"` where
  `$VAR` came from an untrusted source can still leak via error messages or
  stack traces. Validate before echoing.

## Required: Node 24 runtime for every JavaScript `uses:`

GitHub deprecates Node 16/20 runtimes on Actions runners. As of 2025-09-19,
Node 20 is deprecated and emits a warning on every run (`Node.js 20 is
deprecated. The following actions target Node.js 20 but are being forced to
run on Node.js 24: ...`). The next runtime removal will break the workflow
outright.

**Before merging any workflow change that adds or bumps a JavaScript `uses:`
action, verify the action's `action.yml` declares `runs.using: node24`.**

If a temporary `node20` exception is unavoidable, the PR must include a
waiver note with: (a) the reason `node24` is not available, (b) the owner
responsible for tracking the upstream action's `node24` release, and (c) a
removal date.

How to verify without leaving the chat:

```bash
# For an action at SHA, fetch action.yml and check `runs.using`
curl -fsSL https://raw.githubusercontent.com/actions/upload-artifact/<SHA>/action.yml | grep -A 1 "^runs:"
```

Concrete example of a wrong bump (caught in PR #62):

| Action | Old (Node 20) | New (Node 24) |
|--------|---------------|---------------|
| `actions/upload-artifact` | v4.6.2 | v7.0.1 |
| `actions/download-artifact` | v4.3.0 | v8.0.1 |
| `actions/checkout` | v6 (Node 24 already) | v7.0.0 (no Node change) |

`actions/checkout` v6 already runs on Node 24 — bumping to v7 is opportunistic,
not deprecation-driven. The Node check above distinguishes the two cases.

## Why this rule exists

PRs #59, #60, #61 added and hardened several workflows. Despite the existing
SHA-pinning rule, the team missed that `actions/upload-artifact@v4` and
`actions/download-artifact@v4` were still on Node 20 until the deprecation
warning appeared in publish-pypi.yml logs. The fix forward is to check the
Node runtime of every new `uses:` *before* it lands, not after CI complains.

## TDD with installers that download from PyPI

When a workflow tests an installer (e.g. `install.ps1`, `install.sh`) that
downloads the published package from PyPI, the test is exercising the
**published** artifact, not the branch code. If a fix lives on the branch
but has not been published yet (PR not merged, or merge pending publish),
the workflow will fail repeatedly even after the source-level fix is in.

**Required pattern** for any CI workflow that tests an installer against
PyPI on a PR (not on `main`):

```yaml
- name: Run installer (validates installer flow + published artifact)
  shell: pwsh
  run: .\install.ps1

- name: Reinstall from branch source (validates branch code)
  shell: pwsh
  run: |
    # install.ps1 pulled the published version from PyPI. Reinstall from
    # the checked-out source so the rest of the workflow exercises the
    # code in this branch, not the previously-published artifact.
    uv tool install --reinstall --from . gitwise-cli
```

Without this, the workflow gets stuck in a "test the previous release"
loop until the PR merges and a new version publishes — at which point the
test stops catching regressions on the branch.

## `if: always()` for diagnostic steps (and not for production steps)

GitHub Actions' default behavior is to skip subsequent steps when a prior
step fails. This is desirable for production steps (no point uploading
coverage if tests failed). It is **not** desirable for diagnostic steps
added to investigate a failure — those need to run regardless.

**Required pattern** for diagnostic steps:

```yaml
- name: Diagnose <something>
  if: always()  # runs even if prior steps failed
  shell: pwsh
  run: |
    # capture full output for diagnosis, then exit 0 so the step itself
    # does not mask the original failure
    & some-diagnostic-command 2>&1
    exit 0
```

The `if: always()` is also appropriate for required cleanup steps
(`actions/upload-artifact@v4` of logs, `docker system prune` on
self-hosted runners, etc.). It is **not** appropriate as a way to silence
a real failure — the failure still needs to be fixed.

## `workflow_run.head_branch` for tag-triggered workflows

When chaining workflows via `workflow_run`, the upstream workflow's branch
or tag name is exposed in `github.event.workflow_run.head_branch`. For
a tag push, this is typically just the tag name (`v0.26.1`), but it can
include the `refs/tags/` prefix in some events. Always strip both forms:

```bash
TAG="${{ github.event.workflow_run.head_branch }}"
TAG="${TAG##*/}"          # strip any refs/.../ prefix
VERSION="${TAG#v}"        # strip leading v
```

`Verified: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_run`

## PyPI propagation delay

After `publish-pypi.yml` succeeds, the new version is not immediately
visible in `https://pypi.org/pypi/<pkg>/json`. Typical propagation lag
is 30–60 seconds, occasionally longer. Workflows that consume PyPI
metadata immediately after publish (e.g. `update-homebrew-tap.yml`)
**must** include retry logic:

```bash
RESPONSE=""
for attempt in 1 2 3 4 5 6 7 8; do
  RESPONSE=$(curl -fsSL "$URL" 2>/dev/null) && [ -n "$RESPONSE" ] && break
  echo "::notice::PyPI not ready (attempt ${attempt}/8). Retrying in 20s..."
  sleep 20
done
if [ -z "$RESPONSE" ]; then
  echo "::error::PyPI never returned metadata after 8 attempts."
  exit 1
fi
```

## Commitizen counts reverted commits for bumping

`cz bump` reads `git log <last_tag>..HEAD` and applies the highest-severity
subject it finds. A `git revert` adds a new commit that inverts the diff
but does NOT remove the original commit from the log. So if `aaab519 fix:`
gets reverted by `9155ddb revert:`, `cz bump` still sees `fix:` and bumps
the version, producing a release whose CHANGELOG promises changes the
shipped code does not contain.

`auto-release.yml` includes a pre-bump "revert guard" that aborts the
workflow when the range contains revert commit(s) AND the net diff is
zero. Do not remove that guard. If you need to revert a commit that
already bumped a release, the fix is to publish a corrective release
(e.g. `0.24.5` after a broken `0.24.4`), not to remove the guard.

## See also

- [verify-before-implement](../../../.agents/skills/verify-before-implement) —
  the methodology for verifying any workflow change before merge.
- [shell-scripts.md](shell-scripts.md) — rules for `install.sh`, `bin/gitwise`,
  and any other standalone shell script (different threat model: no template
  interpolation, but still subject to `set -e`, quoting, etc.).
