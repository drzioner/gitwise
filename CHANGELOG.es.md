# Historial de cambios

Source: CHANGELOG.md
Last sync: 2026-06-25

[English](CHANGELOG.md) | [Español](CHANGELOG.es.md)

El changelog oficial de gitwise se mantiene en ingles para evitar divergencia en
versiones y notas de release.

Consulta la version canonica aqui:

- [CHANGELOG.md](CHANGELOG.md)

## Ultimo release (resumen canonico)

## v0.34.0 (2026-06-25)

### BREAKING CHANGE

- the --help --json and bare --json output shape changed
from flat top-level fields (kind/scope/commands/options) to the standard
v3 envelope with those fields nested under data. Pin to gitwise <0.34 or
read from payload.data if you consumed the old flat layout.

### Feat

- **schema**: add output schemas for all JSON-emitting commands
- **pr**: add list filters and create action
- **stash,worktree**: add stash push/apply and worktree remove
- **diff,log,show,branches**: add --git-arg passthrough with safety deny-list
- **conflicts**: add --dry-run and --files for safe, scoped resolution
- expose json-lines capability, scrub git config env, surface sync upstream

### Fix

- close last 3 review comments (limit min, health details, test pin)
- close remaining CodeRabbit comments (JSON contract, schemas, nits)
- windows installer temp file + complete remaining review comments
- address PR review comments (security, JSON contract, tests, schemas)
- resolve multi-review gate findings on the branch
- **install**: optional SHA-256 verification for the uv installer
- **schema**: regenerate conflicts input schema to canonical form
- **diff**: validate refspec before forwarding to git (defense-in-depth)
- add explicit machine error codes to all error envelopes
- **cli**: unify help JSON to the v3 envelope shape
- **diff,commit**: redact secret previews from JSON output
- **git**: handle subprocess timeout and reject zero GITWISE_GIT_TIMEOUT
- **show,commit**: emit JSON error envelopes on failure paths
- **commit**: block --allow-secret bypass in agent (JSON) mode

### Refactor

- **health**: centralize score thresholds as named constants
- **output**: central report_error helper, migrate sync/show/commit
- **git**: simplify require_root to return Path | None
- remove dead emoji constant, inline trivial wrapper, type _gh cwd
- **setup-agents**: use shared schema constants in provider-list JSON

### Perf

- **diff,status**: run independent git calls concurrently
