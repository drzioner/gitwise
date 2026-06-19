# Historial de cambios

Source: CHANGELOG.md
Last sync: 2026-06-19

[English](CHANGELOG.md) | [Español](CHANGELOG.es.md)

El changelog oficial de gitwise se mantiene en ingles para evitar divergencia en
versiones y notas de release.

Consulta la version canonica aqui:

- [CHANGELOG.md](CHANGELOG.md)

## Ultimo release (resumen canonico)

## v0.29.0 (2026-06-19)

### Feat

- in-progress safety + merge --abort/--continue (Sprint 1) (#65)
- detect in-progress operations and guard suggest/commit (Sprint 1)

### Fix

- **in_progress**: use os.path.realpath and explicit subprocess timeout (CodeRabbit)
- **merge**: pick rebase subcommand when state=rebase (gemini PR#65 finding)

### Refactor

- **merge**: extract _handle_abort_or_continue (Sprint 1 multi-review)
