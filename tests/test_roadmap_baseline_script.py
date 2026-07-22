from dataclasses import replace
from pathlib import Path

import pytest
from scripts.docs import check_roadmap_baseline as baseline


def test_parse_collected_tests_extracts_count() -> None:
    output = "...\n501 tests collected\n..."

    count = baseline._parse_collected_tests(output)

    assert count == 501


def test_parse_collected_tests_returns_none_when_missing() -> None:
    output = "no collection summary here"

    count = baseline._parse_collected_tests(output)

    assert count is None


def test_parse_project_version_extracts_project_version() -> None:
    content = '[project]\nname = "gitwise-cli"\nversion = "1.2.3"\n'

    assert baseline._parse_project_version(content) == "1.2.3"


def test_parse_package_version_extracts_source_version() -> None:
    content = '__version__ = "1.2.3"\n'

    assert baseline._parse_package_version(content) == "1.2.3"


def test_parse_runtime_dependencies_extracts_project_dependency_names() -> None:
    content = """[project]
dependencies = [
    "rich>=13.0,<16",
    "rich-argparse>=1.8.0,<2",
    "shtab>=1.8.0,<2",
]

[dependency-groups]
dev = ["pytest>=8.0"]
"""

    assert baseline._parse_runtime_dependencies(content) == (
        "rich",
        "rich-argparse",
        "shtab",
    )


def test_count_commands_reads_cli_introspection() -> None:
    assert baseline._count_commands() == 30


def test_extract_baseline_english(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text(
        "Current baseline: 30 commands, 501 tests collected, "
        "447 i18n keys (es/en), 3 runtime dependencies (rich, rich-argparse, shtab).",
        encoding="utf-8",
    )

    result = baseline._extract_baseline(roadmap, baseline.EN_BASELINE_RE)

    assert result == baseline.RoadmapBaseline(
        commands=30,
        tests=501,
        i18n_keys=447,
        dependencies=("rich", "rich-argparse", "shtab"),
    )


def test_extract_baseline_spanish(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.es.md"
    roadmap.write_text(
        "Baseline actual: 30 comandos, 501 tests recolectados, "
        "447 keys i18n (es/en), 3 dependencias runtime (rich, rich-argparse, shtab).",
        encoding="utf-8",
    )

    result = baseline._extract_baseline(roadmap, baseline.ES_BASELINE_RE)

    assert result == baseline.RoadmapBaseline(
        commands=30,
        tests=501,
        i18n_keys=447,
        dependencies=("rich", "rich-argparse", "shtab"),
    )


def test_extract_baseline_returns_none_for_invalid_line(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text("Current baseline: N/A", encoding="utf-8")

    result = baseline._extract_baseline(roadmap, baseline.EN_BASELINE_RE)

    assert result is None


@pytest.mark.parametrize(
    "changes",
    [
        {"commands": 29},
        {"dependencies": ("rich",)},
    ],
)
def test_baseline_mismatch_rejects_wrong_project_facts(changes: dict[str, object]) -> None:
    expected = baseline.RoadmapBaseline(
        commands=30,
        tests=501,
        i18n_keys=447,
        dependencies=("rich", "rich-argparse", "shtab"),
    )
    found = replace(expected, **changes)

    assert baseline._baseline_mismatch("ROADMAP.md", found, expected) is not None


def test_version_mismatch_rejects_wrong_source_version() -> None:
    assert baseline._version_mismatch("1.2.3", "9.9.9") is not None


def test_readmes_share_five_workflows() -> None:
    root = Path(__file__).parent.parent
    english = (root / "README.md").read_text(encoding="utf-8")
    spanish = (root / "README.es.md").read_text(encoding="utf-8")

    for index in range(1, 6):
        assert f"### {index}." in english
        assert f"### {index}." in spanish
