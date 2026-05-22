from __future__ import annotations

import sys
from pathlib import Path

ROOT_EXCLUSIONS = {"AGENTS.md", "CLAUDE.md"}


def _required_pairs(repo_root: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []

    for md_path in sorted(repo_root.glob("*.md")):
        if md_path.name in ROOT_EXCLUSIONS or md_path.name.endswith(".es.md"):
            continue
        en_rel = md_path.relative_to(repo_root)
        es_rel = en_rel.with_suffix(".es.md")
        pairs.append((en_rel, es_rel))

    docs_root = repo_root / "docs"
    for md_path in sorted(docs_root.rglob("*.md")):
        rel = md_path.relative_to(repo_root)
        rel_posix = rel.as_posix()
        if rel_posix.startswith("docs/es/"):
            continue
        es_rel = Path("docs/es") / rel.relative_to("docs")
        pairs.append((rel, es_rel))

    return pairs


def _check_translation_metadata(es_path: Path, source_rel: Path) -> list[str]:
    errors: list[str] = []
    content = es_path.read_text(encoding="utf-8")
    expected_source = f"Source: {source_rel.as_posix()}"
    if expected_source not in content:
        errors.append(f"missing source metadata '{expected_source}' in {es_path.as_posix()}")
    if "Last sync: " not in content:
        errors.append(f"missing 'Last sync' metadata in {es_path.as_posix()}")
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    pairs = _required_pairs(repo_root)
    errors: list[str] = []

    for en_rel, es_rel in pairs:
        en_path = repo_root / en_rel
        es_path = repo_root / es_rel

        if not en_path.exists():
            errors.append(f"missing English source file: {en_rel.as_posix()}")
        if not es_path.exists():
            errors.append(f"missing Spanish mirror file: {es_rel.as_posix()}")
            continue

        errors.extend(_check_translation_metadata(es_path, en_rel))

    if errors:
        for err in errors:
            print(f"i18n-check: {err}", file=sys.stderr)
        return 1

    print("i18n-check: all required EN/ES pairs are present and annotated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
