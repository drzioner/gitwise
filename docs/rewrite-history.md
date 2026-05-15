# Rewriting git history

gitwise does NOT provide a subcommand for history rewriting — it's high risk,
low usage, and `git-filter-repo` already does it better.

## When to use it

- Removing a secret (password, API key) committed accidentally
- Changing the author email/name in historical commits
- Removing a large binary file from the entire history

## Steps with git-filter-repo

```bash
# Install
pip install git-filter-repo

# Remove a file from the entire history
git filter-repo --path secrets/api-key.txt --invert-paths

# Change email in commits
git filter-repo --email-callback 'return email.replace(b"old@old.com", b"new@new.com")'

# Remove sensitive content from a file (keeps the file)
git filter-repo --replace-text expressions.txt
# expressions.txt:
# REGEX:(?i)password\s*=\s*\S+   ==>  password=REDACTED
```

## Warnings

- **Rewrites the entire history** — any collaborator must re-clone
- **GitHub/GitLab require `--force`** on push after rewriting
- Verify with `git log --all -- <file>` that the file no longer appears
- On shared repos: coordinate with the team before running

## References

- [git-filter-repo docs](https://github.com/newren/git-filter-repo)
- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
