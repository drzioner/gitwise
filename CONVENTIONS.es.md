# Convenciones Git

Source: CONVENTIONS.md
Last sync: 2026-05-22

- Diff: `gitwise diff` (`git diff --name-status HEAD`). Evita `git diff` crudo.
- Log: `git --no-pager log --oneline -n 20`. Evita log sin limite.
- Commits: formato convencional `feat/fix/refactor/docs/chore: descripcion`.
- Commits: siempre firmados con GPG. Nunca `--no-gpg-sign`.
- Cambio de rama: `gitwise worktree new <branch>`. Evita `git stash + checkout`.
- Antes de commits grandes: `gitwise audit --quick`.
