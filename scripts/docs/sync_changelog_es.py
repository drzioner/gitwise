from __future__ import annotations

import datetime as dt
from pathlib import Path


def _extract_summary(changelog_content: str) -> str:
    lines = changelog_content.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("## "):
            block: list[str] = [line]
            cursor = index + 1
            while cursor < len(lines) and not lines[cursor].startswith("## "):
                block.append(lines[cursor])
                cursor += 1
            return "\n".join(block).strip()
    return ""


def sync_changelog_es(repo_root: Path) -> None:
    changelog_en = repo_root / "CHANGELOG.md"
    changelog_es = repo_root / "CHANGELOG.es.md"

    en_content = changelog_en.read_text(encoding="utf-8")
    latest_block = _extract_summary(en_content)
    today = dt.date.today().isoformat()

    es_content = "\n".join(
        [
            "# Historial de cambios",
            "",
            "Source: CHANGELOG.md",
            f"Last sync: {today}",
            "",
            "[English](CHANGELOG.md) | [Español](CHANGELOG.es.md)",
            "",
            "El changelog oficial de gitwise se mantiene en ingles para evitar divergencia en",
            "versiones y notas de release.",
            "",
            "Consulta la version canonica aqui:",
            "",
            "- [CHANGELOG.md](CHANGELOG.md)",
            "",
            "## Ultimo release (resumen canonico)",
            "",
            latest_block,
            "",
        ]
    )
    changelog_es.write_text(es_content, encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    sync_changelog_es(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
