# Policy guard

[English](guard.md) | [Español](../es/reference/guard.md)

`gitwise guard` is the gate between whoever is writing to the repository and
the object database. It reads a declarative policy, reports a machine-readable
verdict, and installs the git hooks that make that verdict unavoidable.

The distinction matters when an agent is doing the writing. A guard that only
runs inside `gitwise commit` protects nothing: the agent can call `git commit`
directly and skip it. The hooks close that gap.

## The policy file

The policy lives at `.gitwise/policy.json`, inside the repository. That is
deliberate: it is reviewable in a pull request, and a developer's global git
config cannot weaken it.

```json
{
  "version": 1,
  "protected_branches": ["main", "master"],
  "forbidden_paths": [".env", "*.pem", "secrets/**"],
  "commit_types": ["feat", "fix", "refactor", "docs", "chore", "test"],
  "require_gpg": true,
  "block_secrets": true,
  "allow_force_push": false,
  "block_direct_commits": false
}
```

Every key is optional; anything omitted falls back to the built-in default, so
a repository with no policy file behaves exactly as it did before. The schema
is published at `share/schemas/v1/policy.json`.

| Key | Default | Effect |
|---|---|---|
| `protected_branches` | `["main", "master"]` | Branches protected against history rewrites: force pushes and deletions |
| `forbidden_paths` | `[]` | fnmatch globs; a staged path matching one blocks the commit |
| `commit_types` | the conventional set | Allowed commit types, checked by the `commit-msg` hook |
| `require_gpg` | `false` | Block when GPG signing is not configured and ready |
| `block_secrets` | `true` | Block on high-severity secret findings; `false` downgrades them to warnings |
| `allow_force_push` | `false` | Permit non-fast-forward pushes to protected branches |
| `block_direct_commits` | `false` | Also refuse commits made directly on a protected branch |

Protecting a branch means no rewrites, not no commits. Refusing direct commits
is a separate team decision, so it has its own opt-in key.

Loading fails closed. A malformed file, an unknown key, or a value of the wrong
type is an error, never a silent downgrade to "everything allowed".

## `gitwise guard check`

Evaluates the policy and reports, without changing anything.

```bash
gitwise guard check                       # staged changes
gitwise guard check --json                # machine-readable verdict
gitwise guard check --push                # ref updates read from stdin
gitwise guard check --commit-msg .git/COMMIT_EDITMSG
gitwise guard check --quiet                # silent unless something is wrong
```

Exit codes separate policy from failure:

| Code | Meaning |
|---|---|
| `0` | Nothing blocks |
| `2` | The policy blocks the operation |
| `1` | Operational error: not a repository, unreadable policy |

A hook collapses both non-zero cases into "refused", but an agent deciding what
to do next must be able to tell them apart.

```json
{
  "v": 3,
  "ok": true,
  "command": "guard",
  "data": {
    "action": "check",
    "scope": "commit",
    "allowed": false,
    "violations": [
      {
        "rule": "forbidden_path",
        "severity": "block",
        "message": "deploy/key.pem matches a forbidden path in the repository policy",
        "path": "deploy/key.pem",
        "detail": null
      }
    ],
    "blocking_count": 1,
    "warning_count": 0,
    "policy_source": ".gitwise/policy.json"
  },
  "hints": [],
  "errors": []
}
```

Rules: `protected_branch`, `forbidden_path`, `secret`,
`secret_scan_unavailable`, `gpg`, `commit_type`, `force_push`,
`protected_branch_delete`. A violation never carries the credential itself,
only the rule that matched and where.

A paused merge, rebase or cherry-pick is deliberately not a violation. The
commit that closes a conflicted merge is the one git runs the hook for, so
refusing it would leave you unable to finish or abort without `--no-verify`.
`gitwise commit` still refuses on its own, where the check belongs.

## `gitwise guard install`

Registers three hooks that call `guard check`:

| Hook | What it refuses |
|---|---|
| `pre-commit` | Forbidden paths, leaked credentials, missing GPG |
| `commit-msg` | A subject whose type the policy does not allow |
| `pre-push` | Force pushes and deletions of protected branches |

```bash
gitwise guard install --dry-run           # show the plan
gitwise guard install --yes
gitwise guard install --uninstall --yes
```

Backends follow `gitwise setup`: `--hooks-mode native` uses git's
`hook.<name>.command` configuration (git 2.54 or newer), `legacy` points
`core.hooksPath` at the shipped scripts, and the default `preserve` picks
whichever is available. If husky, lefthook or pre-commit already owns the
repository's hooks, installation is skipped with a warning rather than taking
them over.

Install also verifies that the hook scripts carry the executable bit. Wheels do
not reliably preserve mode bits, and a hook git cannot execute is protection
that silently does not run.

## Using it from an agent

```bash
gitwise guard check --json || handle_violations
```

The same verdict backs `gitwise commit`, so the two paths cannot drift apart.
`gitwise commit` keeps its own interactive secret confirmation, which is
stricter: allowing a high-severity finding through in `--json` mode requires
the `GITWISE_ALLOW_SECRETS` environment variable, which a prompt cannot set.
