Source: docs/MIGRATION-0.17.md
Last sync: 2026-05-23

# Guia de migracion setup-agents (0.17)

Esta guia explica como migrar desde layout legacy Claude-only al layout canonico agents-first.

## Layout objetivo

- Documento canonico: `AGENTS.md`
- Skills canonicos: `.agents/skills/<skill>/SKILL.md`
- Capa de compatibilidad: `CLAUDE.md` puede quedar como symlink a `AGENTS.md`

## Migracion automatica (recomendada)

Ejecuta en la raiz del repo:

```bash
gitwise setup-agents --local --yes --migrate-legacy-claude
```

Primero en dry-run:

```bash
gitwise setup-agents --local --dry-run --migrate-legacy-claude
```

## Que migra

- Si solo existe `CLAUDE.md`, se crea `AGENTS.md` con el contenido actual y `CLAUDE.md` pasa a symlink.
- Los skills se mueven a `.agents/skills/` y `.claude/skills/<name>` queda como symlink cuando aplica.
- El snapshot pasa a `.agents/git-snapshot.md` cuando el layout es canonico.

## Idempotencia

Puedes ejecutar el comando varias veces de forma segura; no debe duplicar contenido.

## Alias deprecado

- `--providers claude-only` esta deprecado y se interpreta como `--providers claude`.
- `--adapters` se mantiene como alias legacy oculto por compatibilidad.
