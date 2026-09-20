Source: docs/MIGRATION-0.36.md
Last sync: 2026-09-20

# Migration guide (0.36)

0.36 standardises the machine contract and narrows the product surface. The
project is pre-1.0 and in active development, so the decision was to fix the
inconsistencies now and announce them rather than carry them to 1.0.

Everything here is a deliberate break. Nothing was changed by accident.

## 1. `setup-agents --json` uses the canonical envelope

`setup-agents` was the only command of the 31 that put its fields at the top
level. It also declared a schema version of its own (`v_compat`), so a consumer
written against any other command broke on this one.

**Before:**

```json
{
  "v": 3,
  "v_compat": [1, 2, 3],
  "command": "setup-agents",
  "ok": true,
  "bucket": 2,
  "mode": "local",
  "actions": [...],
  "errors": ["something failed"]
}
```

**Now:**

```json
{
  "v": 3,
  "ok": true,
  "command": "setup-agents",
  "data": {
    "bucket": 2,
    "mode": "local",
    "actions": [...]
  },
  "hints": [],
  "errors": [{ "code": "setup_agents_plan_failed", "message": "something failed" }]
}
```

**What to change:** read domain fields from `data`, and read `errors[].message`
instead of treating `errors` as a list of strings. `v_compat` is gone; the
envelope version is `v`, as everywhere else.

The published schema at `share/schemas/v1/output/setup-agents.json` describes
the new shape, and a test validates the real output against it.

## 2. The legacy `adapters` surface is gone

| Removed | Use instead |
|---|---|
| `--adapters` | `--providers` |
| `--list-adapters` | `--list-providers` |
| the `adapters` key in `--list-providers --json` | the `providers` key |

The flags were hidden aliases kept for compatibility since 0.17. Invoking them
now fails with exit code 2 and an `invalid_arguments` envelope.

## 3. Seventeen wrappers are hidden and deprecated

`log`, `show`, `status`, `stash`, `tag`, `pick`, `undo`, `branches`, `sync`,
`merge`, `pr`, `clean`, `optimize`, `health`, `suggest`, `snapshot` and
`update` no longer appear in `gitwise --help`.

They still run, and they still accept their aliases. Each one prints a
deprecation notice to stderr naming its replacement, and
`gitwise commands --json` reports `deprecated: true` plus a `replacement`
string for each. They will be removed in 1.0.

**What to change:** nothing yet, but move to the replacement named in the
notice. gitwise is a policy layer over four commands (`guard`, `commit`,
`worktree`, `setup-agents`); it does not aim for parity with `git` or `gh`.

## 4. Non-ASCII paths are reported raw

gitwise now runs git with `core.quotePath=false`. Previously any path holding a
non-ASCII byte came back quoted and octal-escaped:

```
"configuraci\303\263n/.env"      # before
configuración/.env               # now
```

This affected the paths reported by `diff`, `log`, `show`, `conflicts`,
`health` and `context`, and in the policy engine it was a bypass: a secret
under an accented directory did not match `forbidden_paths`.

**What to change:** if you were unescaping those strings yourself, stop. If you
were matching against the quoted form, match against the real path.

## 5. Argument errors now answer in JSON

A bad flag used to exit 2 with usage on stderr and **nothing** on stdout, in
every command. With `--json` it now also emits a v3 envelope with
`code: "invalid_arguments"`. The exit code is unchanged, and `--help` still
exits 0 without an envelope.

**What to change:** nothing. Error handling that expected empty stdout on a bad
argument keeps working, but you can now parse the failure like any other.

## 6. The policy engine no longer blocks on a paused operation

If you used `gitwise guard check` from 0.36-rc and relied on the `in_progress`
rule, it is gone from the engine. It made conflicted merges impossible to
finish once the hooks were installed: the commit that closes a merge is the one
git runs the hook for. `gitwise commit` still refuses while an operation is
paused, which is where that check belongs.

## 7. `supports_config_hooks` requires git 2.54

Config-based hooks (`hook.<name>.command`) are only fired by git from 2.54.
gitwise previously gated on 2.36, the version that introduced the `git hook run`
subcommand, so `setup --hooks-mode native` could write configuration that never
executed on git 2.36 through 2.53.

**What to change:** on git older than 2.54, use `--hooks-mode legacy`, which is
selected automatically by the default `preserve` mode.
