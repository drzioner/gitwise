from pathlib import Path

from scripts.docs.sync_changelog_es import _extract_summary, sync_changelog_es


def test_extract_summary_reads_latest_release_block() -> None:
    changelog = "\n".join(
        [
            "# Changelog",
            "",
            "## v0.17.0 (2026-05-23)",
            "",
            "### Feat",
            "- item",
            "",
            "## v0.16.0 (2026-05-23)",
            "",
            "### Fix",
            "- old",
        ]
    )
    summary = _extract_summary(changelog)
    assert "## v0.17.0 (2026-05-23)" in summary
    assert "## v0.16.0 (2026-05-23)" not in summary


def test_sync_changelog_es_updates_metadata_and_summary(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## v0.17.0 (2026-05-23)",
                "",
                "### Feat",
                "- **setup-agents**: new change",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.es.md").write_text("old", encoding="utf-8")

    sync_changelog_es(tmp_path)

    es = (tmp_path / "CHANGELOG.es.md").read_text(encoding="utf-8")
    assert "Source: CHANGELOG.md" in es
    assert "Last sync: " in es
    assert "## Ultimo release (resumen canonico)" in es
    assert "## v0.17.0 (2026-05-23)" in es
    assert "new change" in es
