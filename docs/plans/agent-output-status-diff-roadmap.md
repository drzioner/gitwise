# Roadmap: AI-agent output + `status` and `diff` improvements

Status: living · Last updated: 2026-05-28 · Origin branch: `feat/unified-loading-feedback`

This document captures the full analysis of three related reviews so the information is not lost:

1. Unified loading/feedback system (implemented).
2. Capability improvements for `gitwise status` and `gitwise diff` vs native git.
3. Better `--json` output formats so AI agents understand them more easily.

gitwise guiding purpose: **simplify commands, improve DX, improve security, and improve
the workflow with AI agents.** Every improvement here is justified against those pillars.

---

## 1. Unified loading/feedback — IMPLEMENTED

Pattern: the `status(message)` context manager in `gitwise/output.py`.

- Global JSON-mode gate: `set_json_mode(bool)` in `output.py`, wired in `__main__.py:main()`
  after resolving `args.json`. `status()` is a no-op when JSON mode is active. **Rule:** the
  spinner always shows in human mode and is suppressed ONLY with `--json` / `--json-pretty`
  (not by mere TTY detection).
- Spinner added to: `status`, `summarize`, `diff`, `log`, `show`, `branches`, `suggest`,
  `context`, `health`, `snapshot`, `worktree`, `conflicts`, `pr` (helper `_gh`), `stash`
  (list/show), `tag` (list), `doctor`, `clean` (scan). Already had it: `sync`, `optimize`,
  `audit`.
- New i18n keys: `status_reading_status`, `status_summarizing`, `status_reading_diff`,
  `status_reading_log`, `status_loading_commit`, `status_analyzing_branches`,
  `status_analyzing_staged`, `status_detecting_conflicts`, `status_reading_stashes`,
  `status_reading_tags`, `status_querying_github`, `status_checking_env`,
  `status_scanning_stale`, `status_worktree_add`, `status_health_scan`,
  `status_context_scan`, `status_snapshot_gen`, `status_updating`.

Mutating commands (`commit`, `merge`, `undo`, `pick`, `setup`, `setup-agents`) do NOT get a
wrapping spinner: they already print their plan/confirmation/result live and a spinner would
collide with the prompts.

---

## 2. `gitwise status` vs `git status` — gaps and proposals

### Parity gaps (even vs native git)

| # | Gap | Pillar | Status |
|---|-----|--------|--------|
| S1 | **In-progress operation** (merge/rebase/cherry-pick/revert/bisect) is not detected. An agent may commit mid-rebase. Detect `MERGE_HEAD`, `rebase-merge/`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `BISECT_LOG` → expose `in_progress: "rebase"`. | Security+Workflow+AI | pending |
| S2 | **Conflicts/unmerged** are not their own category. `status.py` classifies with `ln[0]/ln[1]` and mixes `UU/AA/DD` into staged/unstaged. Needs an explicit `conflicted` category. | Security+AI | pending |
| S3 | **Lossy JSON:** `files: [paths]` with no status code. The agent gets `unstaged: 21` and a flat list, cannot tell which is staged/untracked/conflicted. Should be `files: [{path, code, status, staged}]`. | AI workflow | pending (part of §4 FileEntry) |

### DX/orientation improvements (lower priority)

- Upstream name (not just ahead/behind, but `origin/main`).
- Last commit (hash + subject) to orient the agent.
- Stash count.
- Actionable hints in human mode: "you have staged changes → `gitwise commit`".
- Structured renames (`old → new`) instead of the raw porcelain line.

---

## 3. `gitwise diff` vs `git diff` — gaps and proposals

| # | Improvement | Pillar | Status |
|---|-------------|--------|--------|
| D1 | **Compare arbitrary refs/branches/ranges.** Today `diff.py:_diff_cmd` always compares vs `HEAD` or `--staged`. No `gitwise diff <ref>`, `diff main..HEAD`, `diff <a> <b>`. Forces falling back to native git. | Simplify+DX | pending |
| D2 | **Scope to paths:** `gitwise diff -- <path>`. | DX | pending |
| D3 | **Secret scanning in the diff** (API keys, tokens, `.env`, private keys) before commit. Not in git; fits security + preventing an agent from leaking credentials. Differentiating feature. | **Security** | pending |
| D4 | **Large/binary file warning** (LFS candidates). Already detects binaries (`diff.py:127`); extend to size. | Security/Workflow | pending |
| D5 | **Compact AI summary** (`--summary`): files + ± per hunk, without dumping the full patch → saves tokens. | AI (tokens) | pending |

---

## 4. `--json` format for AI agents

**Format decision:** keep JSON as the canonical format (LLMs parse it more reliably than
YAML/TOML/tables). Do NOT switch formats. The only addition worth it: optional
**NDJSON (JSON Lines)** for large lists (`log`, `diff --full`) → incremental processing and
token truncation.

### Detected problems (with real evidence, pre-fix)

| # | Problem | Real example | Severity | Status |
|---|---------|--------------|----------|--------|
| J1 | **Types as strings** | `branches`: `"current":"false"` (truthy!), `"ahead":""` | critical | **DONE** |
| J2 | **Inconsistent envelope** | `status` puts `v/ok` first; `diff`/`health` last; `summarize` uses `v:3` | high | pending |
| J3 | **3 shapes for "changed files"** | status `["path"]`, diff `[{...}]`, summarize `{"path":"M"}` | high | pending (single FileEntry) |
| J4 | **Empty string instead of null** | `branches`: `"upstream":""` | medium | **DONE** (now `null`) |
| J5 | **Raw codes without normalization** | `M`, `??`, `UU` with no readable label | medium | **DONE in diff** (`status_label`); pending in status/summarize |
| J6 | **Local, inconsistent date format** | `tag`: `-0500` and `+0000` mixed | medium | **DONE** (ISO-8601 strict) |
| J7 | **Collections as string** | `log`: `"parents":"hash1 hash2"` (should be array), `"stats":""` | medium | pending |
| J8 | **Redundancy that wastes tokens** | `diff` repeats `changes`, `graph` (ASCII), `lines_changed`, `insertions`, `deletions` | low | pending |
| J9 | **Missing truncation metadata + next-actions** | no `truncated`/`total`; no machine-readable `next_actions` | DX agents | pending |

### Proposed canonical schema (target, requires `v3`)

```json
{
  "v": 3,
  "ok": true,
  "command": "status",
  "data": { "...command-specific payload..." },
  "hints": ["gitwise commit"],
  "errors": []
}
```

- `errors` always present (empty if ok), shape `[{code, message, hint}]` — already exists in
  `error_envelope` (`utils/json_envelope.py`), needs to be made universal.
- Correct types, explicit `null`, ISO-8601 dates.
- **Single `FileEntry`** reused by status/diff/summarize:
  `{"path", "old_path"?, "code", "status", "staged": bool, "insertions"?, "deletions"?, "binary": bool}`.

**Compatibility note:** J2/J3 break the current envelope shape → bump to `v3`, update the
`gitwise schema` catalog and the tests. That is why they are left for a larger versioned PR.

---

## 5. Implemented in this batch (low-risk block, backward-compatible)

- **J1 — correct types** in `branches.py`: new `TypedDict BranchEntry`.
  `current`/`in_worktree` → `bool`; `ahead`/`behind` → `int | None`;
  `upstream`/`tracking` → `str | None`. Helper `_parse_track_count`.
- **J4 — explicit null** in `branches` (`upstream`/`tracking`/`ahead`/`behind`).
- **J5 — normalized label** `status_label(code)` in `utils/git_output.py`
  (M→modified, ??→untracked, UU→conflicted, ...). Applied to `diff --json`
  (`status_label` next to the raw `status`).
- **J6 — ISO-8601 strict dates**: `log` (`--date=iso-strict`) and `tag`
  (`creatordate:iso-strict`). Result: `2026-05-15T09:59:35-05:00`.

**Breaking change (be explicit):** the `branches` type change (string `"false"`/`""` →
`bool`/`int`/`null`) is NOT backward-compatible for a consumer that pinned `v:2` and compared
strings (e.g. `entry["current"] == "false"`, previously truthy, now a falsy bool). The `v`
field is still `2`. Since the project is pre-1.0 and has no per-command output-schema
contract yet, this batch flags the break here and in the PR/CHANGELOG rather than bumping
`branches` alone (which would worsen the cross-command `v` divergence, J2). The full envelope
versioning (`v3` across all commands) is the documented future PR.

`status.ahead_commits`/`behind_commits` are emitted as structured objects
`[{hash, short_hash, subject}]` (consistent with `log --json`), not raw "hash subject" strings.

`status_label` stable enum: `modified | added | deleted | renamed | copied | type_changed |
conflicted | untracked | ignored | unknown` (`utils/git_output.py`). Not yet in a discoverable
output-schema catalog — see pending item below.

Also in this batch (not a JSON change): `update` now guards a missing upstream with an
actionable error (`code: no_upstream` + hint) instead of git's raw error, and uses the loading
spinner.

### Pending hardening surfaced by review

- **Output schema catalog (M1):** `share/schemas/v1/` is INPUT-only; there is no `output/`
  catalog, so agents cannot discover enums like `status_label`. Add `share/schemas/v1/output/`
  + a `gitwise schema <cmd> --output` flag (folds into the J2/J3 `v3` PR).
- **Terminal-escape hygiene (global):** branch names / refs are echoed verbatim into human
  output in several commands (`status`, `branches`, `update`); a branch name with ANSI control
  chars is a (low) terminal-injection vector (CWE-150). Fix centrally in the output layer, not
  per-command.
- **`log.parents`/`log.stats` as strings (J7):** still string-typed; fold into `v3`.

---

## 6b. Multi-review verdict (33+ profile panel, official-doc backed)

A full-depth multi-perspective review (security, architecture/Python, QA/test-arch,
DX/AI-consumer/docs) validated this batch. Real findings, fixes applied in this branch:

- **HIGH — `git.run` timeout bug (fixed):** `_get_timeout` keyed on `args[0]`; with a leading
  `--no-pager` it fell back to the 120s default instead of the per-command timeout. Fixed in
  `gitwise/git.py` to pick the first non-flag arg as the command — repairs the new status.py
  calls AND pre-existing `--no-pager` sites (diff/summarize/snapshot).
- **HIGH — structured ahead/behind commits (fixed):** now `[{hash, short_hash, subject}]`.
- **MEDIUM — suggest.py double spinner (fixed):** consolidated into one spinner span.
- **CRITICAL — `branches` breaking type change:** acknowledged and documented (see §5); the
  types are correct, the break is flagged for the PR/CHANGELOG, full `v3` deferred.
- **LOW — spinner flicker** on sub-100ms commands and **terminal-escape hygiene**: documented
  as pending (no min-duration guard in Rich `status`; global output sanitization).

**pytest-xdist proposal — verdict: SAFE-WITH-CONDITIONS.** Official `pytest-cov` docs confirm
xdist `--dist load` combines per-worker coverage and "each worker will have its subprocesses
measured", so `--cov` + `patch=["subprocess"]` works under `-n`. Test isolation holds
(per-test `tmp_path`, `GIT_CONFIG_GLOBAL/SYSTEM=/dev/null`, no shared state). Conditions before
adoption:
1. Pre-push: `-n auto --maxprocesses=4` (or `-n 4`) to avoid pinning a dev laptop; CI: `-n 2`
   (GitHub runners have 2-4 vCPUs).
2. Add `parallel=true` to `[tool.coverage.run]`.
3. Fix two timing tests that turn flaky under parallelism: `test_audit_quick_under_5s`
   (wall-clock budget) and the `test_snapshot` mtime test.
4. Complementary higher-ROI lever: convert pure-logic tests to in-process calls (the dominant
   cost is ~440 subprocess spawns × full Python+rich import, not parallelism-deficit).

## 6. Suggested order of attack for what's pending

1. **status S1 + S2 + S3** (single module, very high agent value): in-progress operation,
   conflicts, per-file JSON with FileEntry.
2. **diff D1 + D2** (refs/ranges + paths): closes the core capability gap.
3. **diff D3** (secret scanning): differentiating security feature.
4. **Envelope v3** (J2 + J3 + J7 + J9): versioned redesign with single FileEntry,
   `next_actions`, truncation metadata, collections as arrays. Update `gitwise schema` + tests.
5. **NDJSON** optional for `log` / `diff --full`.
