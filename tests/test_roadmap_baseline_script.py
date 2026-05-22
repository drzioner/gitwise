from pathlib import Path

from scripts.docs.check_roadmap_baseline import (
    EN_BASELINE_RE,
    ES_BASELINE_RE,
    _extract_baseline_counts,
    _parse_collected_tests,
)


def test_parse_collected_tests_extracts_count() -> None:
    output = "...\n501 tests collected\n..."

    count = _parse_collected_tests(output)

    assert count == 501


def test_parse_collected_tests_returns_none_when_missing() -> None:
    output = "no collection summary here"

    count = _parse_collected_tests(output)

    assert count is None


def test_extract_baseline_counts_english(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text(
        "Current baseline: 501 tests collected, 447 i18n keys (es/en), one dependency.",
        encoding="utf-8",
    )

    counts = _extract_baseline_counts(roadmap, EN_BASELINE_RE)

    assert counts == (501, 447)


def test_extract_baseline_counts_spanish(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.es.md"
    roadmap.write_text(
        "Baseline actual: 501 tests recolectados, 447 keys i18n (es/en), una dependencia.",
        encoding="utf-8",
    )

    counts = _extract_baseline_counts(roadmap, ES_BASELINE_RE)

    assert counts == (501, 447)


def test_extract_baseline_counts_returns_none_for_invalid_line(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text("Current baseline: N/A", encoding="utf-8")

    counts = _extract_baseline_counts(roadmap, EN_BASELINE_RE)

    assert counts is None
