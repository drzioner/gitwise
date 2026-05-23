from pathlib import Path

from scripts.docs.check_md_links import _resolve_link


def test_changelog_es_summary_heading_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    es = (root / "CHANGELOG.es.md").read_text(encoding="utf-8")
    assert "## Ultimo release (resumen canonico)" in es


def test_resolve_link_with_title(tmp_path: Path) -> None:
    root = tmp_path
    docs_dir = root / "docs"
    source_file = docs_dir / "guide.md"
    target_file = docs_dir / "target.md"
    docs_dir.mkdir()
    source_file.write_text("", encoding="utf-8")
    target_file.write_text("", encoding="utf-8")

    resolved = _resolve_link(root, source_file, 'target.md "Some title"')

    assert resolved is not None
    assert resolved == target_file.resolve()


def test_resolve_link_ignores_whitespace_only(tmp_path: Path) -> None:
    root = tmp_path
    source_file = root / "README.md"
    source_file.write_text("", encoding="utf-8")

    resolved = _resolve_link(root, source_file, "   ")

    assert resolved is None


def test_resolve_link_ignores_anchor_only(tmp_path: Path) -> None:
    root = tmp_path
    source_file = root / "README.md"
    source_file.write_text("", encoding="utf-8")

    resolved = _resolve_link(root, source_file, "#section")

    assert resolved is None
