# Git conventions

- Diff: `gitwise diff` (= `git diff --name-status HEAD`). Never raw `git diff`.
- Log: `git --no-pager log --oneline -n 20`. Never without a limit.
- Commits: conventional format `feat/fix/refactor/docs/chore: <description>`.
- Commits: always GPG-signed. Never `--no-gpg-sign`.
- Branch switch: `gitwise worktree new <branch>`. Never `git stash + checkout`.
- Before large commits: `gitwise audit --quick`.
