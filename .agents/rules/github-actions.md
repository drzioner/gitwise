---
alwaysApply: true
---

# GitHub Actions — Security Conventions

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
  Dependabot can bump it (`uses: actions/checkout@df4cb1c0... # v6.0.3`).
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

## See also

- [verify-before-implement](../../../.agents/skills/verify-before-implement) —
  the methodology for verifying any workflow change before merge.
- [shell-scripts.md](shell-scripts.md) — rules for `install.sh`, `bin/gitwise`,
  and any other standalone shell script (different threat model: no template
  interpolation, but still subject to `set -e`, quoting, etc.).
