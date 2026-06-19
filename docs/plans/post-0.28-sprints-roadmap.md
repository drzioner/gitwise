# Roadmap: post-0.28 sprints — safety, capabilities, contracts, polish

Status: living · Last updated: 2026-06-19 · Origin: `feat/loading-feedback-integration` review session

This document is the forward plan that emerged from a full-depth multi-review
of the `feat/loading-feedback-integration` merge (the branch that became
v0.28.0). The sibling plan
[`agent-output-status-diff-roadmap.md`](./agent-output-status-diff-roadmap.md)
captures what that PR shipped and what it explicitly deferred. This document
captures the four sprints that pick up those deferrals plus gaps the review
surfaced outside the original plan scope.

gitwise guiding purpose (unchanged): **simplify commands, improve DX, improve
security, and improve the workflow with AI agents.** Every sprint below is
justified against those pillars.

---

## How this plan is organized

Each sprint is a PR-sized unit with: goal, files touched (with current
`file:line` anchors), pillars, breaking-change status, exit criteria, and
dependencies on prior sprints. Sprints are sequenced for safety first
(anti-corruption), then capability gaps, then contract redesign, then polish.

All file references are pre-0.28 baselines verified by
`verify-before-implement` against the merged tree on 2026-06-19.

---

## Sprint 1 — In-progress safety and i18n hardening

**Goal:** prevent an agent from committing mid-merge/rebase/cherry-pick, and
make i18n parity enforceable per-locale.

**Why first:** a commit mid-rebase corrupts repository state silently. This
is the only sprint whose absence is an active data-loss risk, not just a
capability gap.

### Work items

| ID | Item | Anchors | Pillar | Effort |
|----|------|---------|--------|--------|
| S1 | Detect in-progress operations and expose them | new `gitwise/utils/in_progress.py` (helper); wire into `gitwise/status.py` (new JSON field `in_progress`) | Security + Workflow | small |
| G2 | Guard `suggest` and `commit` against in-progress state | `gitwise/suggest.py:112` (`run_suggest`), `gitwise/commit.py:97` (`run_commit`) | Security | trivial (reuses S1 helper) |
| G1 | `merge --abort` and `merge --continue` subcommands | `gitwise/merge.py:146` (`run_merge`); add `abort`/`continue` flags | Simplify | small |
| G6 | i18n parity test (already shipped in 0.28.0) | `tests/test_i18n.py::test_all_keys_have_es_and_en_translations` | Quality | done |

### S1 detection contract

`detect_in_progress(root: Path) -> InProgressState` where `InProgressState` is
a TypedDict `{"state": Literal["none","merge","rebase","cherry-pick","revert","bisect"], "ref": str | None}`.

Detection reads `.git/` artifacts (no porcelain cost):
- `MERGE_HEAD` → `merge`
- `.git/rebase-merge/` or `.git/rebase-apply/` → `rebase`
- `CHERRY_PICK_HEAD` → `cherry-pick`
- `REVERT_HEAD` → `revert`
- `.git/BISECT_LOG` → `bisect`

`status --json` gains `in_progress: InProgressState` (additive, no `v` bump).
`suggest` and `commit` refuse with a clear error + actionable hint when
`state != "none"`.

### Exit criteria

- New tests: `test_in_progress_*` per state; `test_suggest_refuses_during_merge`;
  `test_commit_refuses_during_rebase`; `test_merge_abort` / `test_merge_continue`.
- All four `scripts/docs/check_*` pass (baseline bumped in ROADMAP).
- No new BREAKING CHANGE marker in any commit footer (all changes additive or
  guarded by detection).

### Dependencies

None. This sprint can land immediately after 0.28.0.

### Release impact

`fix:`-typed commits → patch bump `0.28.x → 0.28.(x+1)` unless a `feat:`
commit (e.g. `--abort`/`--continue` as new flags) rotates minor.

---

## Sprint 2 — Diff capability parity and secret scanning

**Goal:** close the two biggest capability gaps vs native git (`diff <ref>`,
`diff -- path`) and ship a differentiating security feature (secret scanning
before commit).

### Work items

| ID | Item | Anchors | Pillar | Effort |
|----|------|---------|--------|--------|
| D1 | `gitwise diff <ref>`, `diff a..b`, `diff a...b` | `gitwise/diff.py:146` (`_diff_cmd` only supports `staged/name_only/full` today) | Simplify + DX | medium |
| D2 | `gitwise diff -- <path>` (path scope) | `gitwise/diff.py:146` | DX | small |
| D3 | Secret scanning in diff and as a commit pre-check | new `gitwise/utils/secret_scan.py`; wire into `diff.py`, `suggest.py:112`, `commit.py:97` | **Security** (differentiator) | medium-large |
| D4 | Large/binary file warning (LFS candidates) | `gitwise/diff.py:127` (already detects binaries; extend to size) | Workflow | small |
| D5 | `gitwise diff --summary` (compact AI summary, ± per hunk, no full patch) | `gitwise/diff.py` (new render path) | AI (tokens) | small |

### D3 secret scanning contract

New `secret_scan(diff_text: str) -> list[Finding]` where `Finding` is
`{"rule": str, "path": str, "line": int, "preview": str, "severity": "high"|"medium"}`.

Initial ruleset (verified patterns, no false-positive on test fixtures):
- AWS access key: `AKIA[0-9A-Z]{16}` (Verified: AWS docs §IAM identifiers)
- AWS secret: 40-char base64 after `aws_secret_access_key`
- GitHub token (any prefix): `gh[pousr]_[A-Za-z0-9]{36,}` and
  `github_pat_[A-Za-z0-9_]{82,}` — note GitHub recommends treating tokens as
  opaque and warns formats may evolve (Verified: GitHub blog 2021-04-12 +
  GitHub docs §Keeping API credentials secure). The implementation should
  prefer prefix detection over rigid length validation so future format
  changes don't silently regress detection.
- GitLab PAT: `glpat-[A-Za-z0-9_-]{20,300}` — modern tokens range 27–300
  chars depending on kind (personal/CI/deploy/feed). (Verified: GitLab docs
  §Personal access tokens + GitLab §Token prefixes)
- Private key block — both formats, since OpenSSH 7.8+ (2018) defaults to
  the new binary format:
  - PEM: `-----BEGIN (RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----`
  - OpenSSH new: `openssh-key-v1` magic bytes, or the base64-encoded form
    `b3BlbnNzaC1rZXktdjE` when captured as text in a diff
    (Verified: PROTOCOL.key §OpenSSH key format)
- `.env` assignment: `^[A-Z_]+=(https?://|\S+@)` after a `.env` filename header

Output: `gitwise diff --scan-secrets --json` returns findings; non-zero exit
on `severity=high`. `gitwise commit` runs scan by default and refuses on
high-severity hits unless `--allow-secret` (with confirmation).

### Exit criteria

- `test_diff_ref_*`, `test_diff_path_scope`, `test_secret_scan_*` (per rule +
  per clean fixture).
- Documented false-positive rate target: 0 on the project's own test corpus.
- ROADMAP baseline bumped; check scripts green.

### Dependencies

None hard. D3 wires naturally into the guards from Sprint 1's G2 (refuses
commit on in-progress + refuses on secret leak — same guard layer).

### Release impact

`feat:`-typed → minor bump `0.28.x → 0.29.0`.

---

## Sprint 3 — Envelope v3 (contract redesign)

**Goal:** unify the `--json` envelope so consumers can parse every command
with one schema, and publish output schemas so agents can self-discover them.

**Why third, not first:** this is the largest sprint (~1500 lines, every
command touched) and ships a real breaking change. Doing it before S1/S2
would force rework (S1 adds `in_progress` to status JSON; doing that on v2
then migrating to v3 is wasted churn).

### Work items

| ID | Item | Anchors | Pillar | Effort |
|----|------|---------|--------|--------|
| J2 | Canonical envelope `{"v":3,"ok","command","data","hints","errors"}` | `gitwise/utils/json_envelope.py` (rewrite); all 27 commands | AI workflow | large |
| J3 | Single `FileEntry` shared by status/diff/summarize | `gitwise/status.py:58`, `gitwise/diff.py`, `gitwise/summarize.py` | AI workflow | medium |
| J7 | Collections as arrays: `log.parents`, `log.stats` | `gitwise/log.py:101` (`parents: lines[6]` string), `:133` (`stats: ""` string) | AI workflow | small |
| J9 | `truncated`, `total`, `next_actions` metadata | all envelopes | DX agents | medium |
| S2 | `conflicted` as a first-class status category | `gitwise/status.py:30-32` (mixes UU/AA/DD into staged/unstaged) | Security + AI | small |
| S3 | Per-file JSON with status code/stage/binary in status | `gitwise/status.py:58` (`files: [paths]` lossy) | AI workflow | small |
| M1 + G5 | Output schema catalog `share/schemas/v1/output/` + `gitwise schema <cmd> --output` | `share/schemas/v1/output/` (does not exist); `gitwise/_cli_dispatch.py:422` | AI workflow | medium |

### v3 envelope contract

```json
{
  "v": 3,
  "ok": true,
  "command": "status",
  "data": { "..." },
  "hints": ["gitwise commit"],
  "errors": []
}
```

- `errors` always present (empty if ok); shape `[{code, message, hint}]`.
  Already exists as `error_envelope` in `utils/json_envelope.py`; made
  universal across commands.
- `FileEntry`: `{"path","old_path"?,"code","status","staged":bool,
  "insertions"?,"deletions"?,"binary":bool}` — same shape in status/diff/
  summarize.
- ISO-8601 strict dates everywhere (already shipped for log/tag in 0.28.0).

### Breaking change

Real, intentional, documented. The PR commit footer carries the BREAKING
CHANGE marker listing every field rename/shape change per command. With
`major_version_zero=true` this rotates the minor `0.29.x → 0.30.0`. The
CHANGELOG section `### Breaking Changes` lists each command's delta.

### Exit criteria

- `share/schemas/v1/output/<command>.json` for every command (~27 files).
- `gitwise schema <cmd> --output` prints the output schema.
- Every command's `--json` test updated to the new envelope; new tests assert
  envelope shape invariants in one place (`tests/test_envelope_contract.py`).
- Migration note in CHANGELOG with before/after JSON examples.

### Dependencies

Hard: must come after Sprint 1 (in-progress field stabilizes in v2 first).
Soft: better after Sprint 2 (D1 adds new diff args that v3 absorbs cleanly).

### Release impact

`feat!:` with BREAKING footer → minor bump `0.29.x → 0.30.0`.

---

## Sprint 4 — DX polish

**Goal:** fill remaining UX gaps and Windows-parity items. Lowest priority;
ship after contracts stabilize so polish is not reworked.

### Work items

| ID | Item | Anchors | Pillar | Effort |
|----|------|---------|--------|--------|
| G3 | `gitwise worktree list` subcommand | `gitwise/worktree.py:21` (`_list_worktrees` is internal helper only) | DX | small |
| G4 | `conflicts --union` and semantic-conflict detection | `gitwise/conflicts.py:31` (`_resolve_all_conflicts` only ours/theirs) | Simplify | medium-large |
| G7 | PowerShell completion | `gitwise/_cli_completions.py:1` (bash/zsh/fish today; Windows installer shipped in 0.27.0) | Windows parity | medium |
| P10 (D4+D5 fold) | Binary warning + `diff --summary` | carries over from Sprint 2 if not picked up | DX + AI | small |
| NDJSON | `log --json-lines` and `diff --full --json-lines` for incremental processing | `gitwise/log.py`, `gitwise/diff.py` | AI (tokens) | medium |

### Exit criteria

- `test_worktree_list`; `test_conflicts_union`; `test_completion_powershell`
  (script generation smoke test); `test_log_ndjson`.
- PowerShell completion documented in README + Windows install section.

### Dependencies

None hard. G3/G4 independent. G7 independent. NDJSON absorbs the v3 envelope
from Sprint 3.

### Release impact

Mixed `feat:` / `chore:` → minor or patch depending on the dominant commit
type in the sprint.

---

## Cross-cutting: verification and ordering

### Recommended order

1. **Sprint 1** — anti-corruption first (only sprint with data-loss risk).
2. **Sprint 2** — capability parity + security differentiator.
3. **Sprint 3** — contract redesign (absorbs S1/S2 additions cleanly).
4. **Sprint 4** — polish (ride the stable v3 contract).

### Out-of-order risks

- **Sprint 3 before Sprint 1:** S1's `in_progress` field would be added to v2,
  then immediately migrated to v3 — wasted churn and a redundant breaking
  change.
- **Sprint 2 before Sprint 1:** D3 secret-scan wiring collides with G2's guard
  wiring in `commit.py`; doing G2 first gives a single guard layer to extend.

### Release train (target)

| PR | Branch | Base | Generates release |
|----|--------|------|-------------------|
| #1 | `feat/loading-feedback-integration` | main | 0.28.0 (BREAKING branches + log + tag) |
| #2 | `feat/in-progress-safety` | main (post 0.28.0) | 0.28.x or 0.29.0 |
| #3 | `feat/diff-refs-secret-scan` | main | 0.29.0 |
| #4 | `feat/envelope-v3` | main | 0.30.0 (BREAKING envelope) |
| #5 | `chore/dx-polish` | main | 0.30.x |

### Verification discipline (applies to every sprint)

Each sprint PR must:
1. Run the four `scripts/docs/check_*` scripts locally before push (they are
   the pre-push gate via `lefthook.yml`).
2. Bump the ROADMAP baseline (test count + i18n key count) in the same PR.
3. Cite a `Verified:` reference in the PR body for any claim that depends on
   external behavior (git flag availability, library version, CVE status).
4. Carry a BREAKING CHANGE footer only if the sprint introduces a real
   contract break — and list every break, not a representative one (the
   v0.23.0 lesson in `CHANGELOG.md:82-92`).
5. Open as a separate PR per sprint; no monolith merges.

### Items explicitly out of scope

- Migrating from argparse to Typer/Click (no concrete pain; argparse + shtab
  works).
- Rewriting the loading feedback layer in async (subprocess-bound; async
  gives no win).
- Adding a `gitwise` TUI mode (rich already covers human-mode rendering).
