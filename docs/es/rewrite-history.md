# Reescribir historial Git

Source: docs/rewrite-history.md
Last sync: 2026-05-22

[English](../rewrite-history.md) | [Espanol](rewrite-history.md)

gitwise no incluye un subcomando para reescritura de historial. Es una operacion
de alto riesgo y `git-filter-repo` ya cubre este caso mejor.

## Cuando usarlo

- Remover un secreto comprometido
- Corregir email/nombre de autor historico
- Eliminar un binario grande de todo el historial

## Pasos con git-filter-repo

```bash
# Instalar
pip install git-filter-repo

# Remover un archivo del historial completo
git filter-repo --path secrets/api-key.txt --invert-paths

# Cambiar email en commits
git filter-repo --email-callback 'return email.replace(b"old@old.com", b"new@new.com")'

# Remover contenido sensible (manteniendo el archivo)
git filter-repo --replace-text expressions.txt
```

## Advertencias

- Reescribe todo el historial: colaboradores tendran que reclonar
- GitHub/GitLab requeriran `--force` al hacer push
- Verifica con `git log --all -- <file>` que el archivo ya no exista en historial
- Coordina con el equipo antes de ejecutarlo en repos compartidos

## Referencias

- [git-filter-repo docs](https://github.com/newren/git-filter-repo)
- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
