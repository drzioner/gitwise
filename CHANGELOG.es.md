# Historial de cambios

Source: CHANGELOG.md
Last sync: 2026-06-20

[English](CHANGELOG.md) | [Español](CHANGELOG.es.md)

El changelog oficial de gitwise se mantiene en ingles para evitar divergencia en
versiones y notas de release.

Consulta la version canonica aqui:

- [CHANGELOG.md](CHANGELOG.md)

## Ultimo release (resumen canonico)

## v0.32.0 (2026-06-20)

### BREAKING CHANGE

- all --json command outputs now nest fields under data with the v3 envelope {v,ok,command,data,hints,errors}; status.files are FileEntry objects with a new data.conflicted bucket (UU/AA/DD no longer counted in staged/unstaged); log.parents and log.stats are arrays (was space-joined string and raw --stat blob); doctor/audit override top-level ok to reflect computed health. Consumers parsing the old flat v2 shape must read command-specific fields from data.

### Feat

- v3 JSON envelope -- nested data, FileEntry, output schemas (Sprint 3) (#70)
