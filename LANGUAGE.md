# Language Conventions — gitwise

> Last updated: 2026-05-15

This document defines the language rules for all artifacts in the gitwise project. Humans and AI agents must follow these conventions.

---

## Summary Table

| Artifact | Language | Examples |
|----------|----------|----------|
| Source code comments | **English** | `# Why: Path.resolve() fails on broken symlinks` |
| Docstrings | **English** | `"""Thin wrappers over subprocess for git operations."""` |
| Function/variable names | **English** | `run_clean`, `_classify_path`, `stale_branches` |
| Commit messages | **English** | `feat: add worktree clean command` |
| Pull request titles/bodies | **English** | `Fix symlink conflict detection on macOS` |
| Code review comments | **English** | `This breaks the GPG safety invariant.` |
| `AGENTS.md` | **English** | Already in English |
| `CONTRIBUTING.md` | **English** | Already in English |
| `SECURITY.md` | **English** | Already in English |
| `docs/` (all `.md` files) | **English** | Including guidelines, design docs, etc. |
| `share/` templates | **English** | `CLAUDE.md.template`, `SKILL.md` |
| GitHub Issues / PRs | **English** | Standard for open source |
| CLI user-facing output | **es/en** (i18n) | Managed via `i18n.py` |
| `LANGUAGE.md` | **English** | This file |

---

## Rules

### 1. Source code: English only

All comments, docstrings, variable names, function names, error messages (in code), and commit messages must be in English.

```python
# CORRECT
def _classify_path(p: Path) -> Literal["absent", "regular", "symlink_valid", "symlink_broken"]:
    """Classify a path's filesystem state."""
    ...

# WRONG — Spanish in code
def _clasificar_ruta(p: Path) -> Literal["ausente", "regular", ...]:
    """Clasifica el estado del path en el filesystem."""
    ...
```

### 2. Documentation: English only

All markdown files in the repo (`docs/`, `*.md` at root, guidelines) are written in English. This ensures the project is accessible to the global open-source community.

### 3. CLI output: i18n (es/en) via `i18n.py`

CLI output visible to end users supports Spanish and English through the `i18n.py` module. **Never** hardcode user-facing strings.

```python
# CORRECT — i18n function
from .i18n import t
ok(t("setup_agents.created", path=str(target)))

# WRONG — hardcoded Spanish or English string
ok(f"Creado {target}")
ok(f"Created {target}")
```

When adding new user-facing strings:
1. Add the key to both `es` and `en` dictionaries in `i18n.py`
2. Use `t("key", placeholder=value)` to call it
3. Never mix languages in the same key

### 4. Commit messages: English, conventional format

```
feat: add worktree clean command
fix: handle broken symlinks in setup_agents
refactor: extract _classify_path helper
docs: add testing guidelines
chore: bump version to 0.2.3
```

### 5. AI agent instructions: English

Files like `AGENTS.md`, `CLAUDE.md`, skill definitions (`SKILL.md`), and any instructions meant for AI agents must be in English. AI agents process English instructions more reliably and consistently.

### 6. Informal communication (chat, comments in PR reviews)

When the context is a conversation between team members who share Spanish as a primary language, Spanish is acceptable. However, all permanent artifacts (code, docs, commits) remain in English.

---

## Why English as default

- **Open source**: The project is public on GitHub. English maximizes accessibility.
- **AI agent reliability**: AI coding agents follow English instructions with higher fidelity.
- **Consistency**: Mixed-language codebases create confusion for contributors.
- **Industry standard**: The vast majority of Python open-source projects use English.
- **i18n separation**: User-facing localization is handled systematically through `i18n.py`, not ad-hoc.

---

## Quick checklist for contributors

- [ ] Comments in code: English?
- [ ] Docstrings: English?
- [ ] Commit message: English, conventional format?
- [ ] New documentation: English?
- [ ] New user-facing strings: Added to `i18n.py` (both es and en)?
- [ ] Variable/function names: English?
