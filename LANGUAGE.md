# Language Conventions - gitwise

Last updated: 2026-05-22

This document defines language rules for source code, documentation, and translations.

## Canonical language model

- Source code and code-adjacent artifacts use English only.
- Documentation is bilingual: English canonical + Spanish mirror.
- CLI output remains bilingual (`es`/`en`) through `gitwise/_i18n_data.json` and `gitwise/i18n.py`.

## Summary table

| Artifact | Rule |
|---|---|
| Source code comments/docstrings/names | English only |
| Commit messages, PR titles/bodies | English only |
| AI instructions (`AGENTS.md`, `CLAUDE.md`, skills) | English only |
| Root docs (`README*`, `CONTRIBUTING*`, `SECURITY*`, etc.) | English canonical + Spanish `.es.md` |
| `docs/` | English canonical under `docs/` + Spanish mirror under `docs/es/` |
| CLI user-visible strings | Must use i18n keys (`es` + `en`) |

## Documentation translation rules

1. English source first.
2. Spanish translation follows in the paired file.
3. Pair naming:
   - Root: `FILE.md` <-> `FILE.es.md`
   - Docs tree: `docs/path/file.md` <-> `docs/es/path/file.md`
4. Every Spanish file must include:
   - `Source: <english file path>`
   - `Last sync: YYYY-MM-DD`
5. Keep structure, headings, links, and command examples aligned across EN/ES.

## Translation-friendly writing rules (English source)

- Prefer short, active sentences.
- Avoid ambiguous pronouns.
- Avoid slang and region-specific references.
- Keep inline links focused; prefer short "Further reading" sections for many links.
- Keep code blocks, paths, flags, and identifiers literal.

## CLI i18n rules

- Never hardcode user-facing strings in command modules.
- Add new keys with both `es` and `en` values in `gitwise/_i18n_data.json`.
- Call strings with `t("key", ...)`.

## Contributor checklist

- [ ] Code comments and docstrings are in English.
- [ ] Docs changes updated English canonical files.
- [ ] Matching Spanish files are added/updated.
- [ ] Spanish files include `Source` and `Last sync` metadata.
- [ ] New user-facing strings include `es` and `en` i18n entries.
