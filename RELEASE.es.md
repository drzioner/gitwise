# Proceso de release

Source: RELEASE.md
Last sync: 2026-05-22

gitwise usa releases automatizados con commitizen. Cada merge a `main` dispara
el workflow `auto-release`, que incrementa version, crea tag y publica release.

## Flujo automatico

```
merge to main -> CI -> cz bump -> git push --atomic (commit + tag) -> gh release create
```

Commits prefijados con `bump:` se omiten para evitar loops.

### Dry run

Usa **Actions -> Auto Release -> Run workflow** con `dry-run: true` para probar
sin publicar.

## Rollback manual

Si se publica un release incorrecto:

```bash
# 1. Borrar release en GitHub
gh release delete v0.X.0 --repo drzioner/gitwise --yes

# 2. Borrar tag remoto
git push --delete origin v0.X.0

# 3. Revertir commit de bump en main
git revert <bump-commit-sha>

# 4. El siguiente merge a main publicara el fix
```

## Saltar release

Para mergear sin disparar release, asegure que los commits desde el ultimo
release sean `chore:` o `docs:`. Commitizen solo incrementa con `feat:`,
`fix:`, `refactor:` y `perf:`.

## Mapeo conventional commit -> version

| Prefijo | Tipo de bump | Ejemplo |
|---|---|---|
| `feat:` | Minor (0.X.0) | `feat: add worktree list command` |
| `fix:` | Patch (0.0.X) | `fix: correct symlink resolution` |
| `feat!:` o `BREAKING CHANGE` | Major (X.0.0) | `feat!: redesign CLI interface` |
