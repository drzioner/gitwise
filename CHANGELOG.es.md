# Historial de cambios

Source: CHANGELOG.md
Last sync: 2026-06-19

[English](CHANGELOG.md) | [Español](CHANGELOG.es.md)

El changelog oficial de gitwise se mantiene en ingles para evitar divergencia en
versiones y notas de release.

Consulta la version canonica aqui:

- [CHANGELOG.md](CHANGELOG.md)

## Ultimo release (resumen canonico)

## v0.28.0 (2026-06-19)

### BREAKING CHANGE

- three JSON contract changes for agents. (1) branches --json: current/in_worktree are now bool (were strings); ahead/behind are now int|null (were strings); upstream/tracking are now string|null. (2) log --json: date field changes from --date=iso to --date=iso-strict (e.g. "2026-06-18T14:30:00+00:00"). (3) tag list --json: date field changes from %(creatordate:iso) to %(creatordate:iso-strict), same shift as log. Agents and scripts parsing these fields must update their deserializers. With major_version_zero=true this rotates the minor (0.27.x -> 0.28.0); the auto-release workflow will bump pyproject.toml and regenerate CHANGELOG.md on push to main, surfacing all three breaks under the Breaking Changes section.
- `branches --json` changes types in 5 fields. `current`
and `in_worktree` are now bool (were "true"/"false" strings); `ahead` and
`behind` are now int|null (were strings); `upstream` and `tracking` are
now string|null (were always strings). Agents and scripts parsing these
fields must update their deserializers. With major_version_zero=true this
rotates the minor (0.27.x -> 0.28.0); the auto-release workflow will bump
pyproject.toml and regenerate CHANGELOG.md on push to main.

### Feat

- unified loading feedback + structured JSON (BREAKING branches/log/tag) (#64)
- unified loading feedback + structured JSON for status/branches

### Fix

- address CI failures and CodeRabbit review findings
