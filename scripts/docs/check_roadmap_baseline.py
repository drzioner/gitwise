from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from gitwise._cli_introspection import commands_metadata
from gitwise._cli_parser import build_parser

EN_BASELINE_RE = re.compile(
    r"Current baseline:\s*(\d+) commands,\s*(\d+) tests collected,\s*"
    r"(\d+) i18n keys \(es/en\),\s*(\d+) runtime dependencies\s+\(([^)]+)\)"
)
ES_BASELINE_RE = re.compile(
    r"Baseline actual:\s*(\d+) comandos,\s*(\d+) tests recolectados,\s*"
    r"(\d+) keys i18n \(es/en\),\s*(\d+) dependencias runtime\s+\(([^)]+)\)"
)
COLLECTED_TESTS_RE = re.compile(r"(\d+)\s+tests collected")
PROJECT_SECTION_RE = re.compile(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)")
VERSION_RE = re.compile(r'(?m)^version\s*=\s*"([^"]+)"')
PACKAGE_VERSION_RE = re.compile(r'(?m)^__version__\s*=\s*"([^"]+)"')
DEPENDENCIES_RE = re.compile(r"(?ms)^dependencies\s*=\s*\[(.*?)^\]")
DEPENDENCY_RE = re.compile(r'"([A-Za-z0-9][A-Za-z0-9._-]*)[^\"]*"')


@dataclass(frozen=True)
class RoadmapBaseline:
    """Project facts recorded in both roadmap baseline lines."""

    commands: int
    tests: int
    i18n_keys: int
    dependencies: tuple[str, ...]


def _count_i18n_keys(repo_root: Path) -> int:
    i18n_file = repo_root / "gitwise" / "_i18n_data.json"
    data = json.loads(i18n_file.read_text(encoding="utf-8"))
    return len(data)


def _project_section(content: str) -> str:
    match = PROJECT_SECTION_RE.search(content)
    return match.group(1) if match else ""


def _parse_project_version(content: str) -> str | None:
    """Extract the PEP 621 project version from pyproject content."""
    match = VERSION_RE.search(_project_section(content))
    return match.group(1) if match else None


def _parse_package_version(content: str) -> str | None:
    """Extract the source package version from gitwise/__init__.py content."""
    match = PACKAGE_VERSION_RE.search(content)
    return match.group(1) if match else None


def _parse_runtime_dependencies(content: str) -> tuple[str, ...]:
    """Extract normalized runtime dependency names from the project section."""
    match = DEPENDENCIES_RE.search(_project_section(content))
    if match is None:
        return ()
    return tuple(DEPENDENCY_RE.findall(match.group(1)))


def _count_commands() -> int:
    """Count canonical CLI commands through the introspection registry."""
    return len(commands_metadata(build_parser()))


def _parse_collected_tests(output: str) -> int | None:
    match = COLLECTED_TESTS_RE.search(output)
    if match is None:
        return None
    return int(match.group(1))


def _collect_tests_count(repo_root: Path) -> int | None:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None
    combined = f"{result.stdout}\n{result.stderr}"
    return _parse_collected_tests(combined)


def _extract_baseline(path: Path, pattern: re.Pattern[str]) -> RoadmapBaseline | None:
    content = path.read_text(encoding="utf-8")
    match = pattern.search(content)
    if match is None:
        return None
    dependencies = tuple(item.strip() for item in match.group(5).split(",") if item.strip())
    if int(match.group(4)) != len(dependencies):
        return None
    return RoadmapBaseline(
        commands=int(match.group(1)),
        tests=int(match.group(2)),
        i18n_keys=int(match.group(3)),
        dependencies=dependencies,
    )


def _format_baseline(value: RoadmapBaseline) -> str:
    dependencies = ",".join(value.dependencies)
    return (
        f"commands={value.commands}, tests={value.tests}, "
        f"i18n={value.i18n_keys}, dependencies={dependencies}"
    )


def _version_mismatch(project_version: str | None, package_version: str | None) -> str | None:
    if project_version is None or package_version is None:
        return "unable to determine project/package version"
    if project_version == package_version:
        return None
    return (
        f"version mismatch: pyproject.toml={project_version}, "
        f"gitwise/__init__.py={package_version}"
    )


def _baseline_mismatch(
    path_name: str, found: RoadmapBaseline | None, expected: RoadmapBaseline
) -> str | None:
    if found is None:
        return f"missing or invalid baseline line in {path_name}"
    if found == expected:
        return None
    return (
        f"{path_name} baseline mismatch: found {_format_baseline(found)} "
        f"expected {_format_baseline(expected)}"
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    errors: list[str] = []

    tests_count = _collect_tests_count(repo_root)
    if tests_count is None:
        errors.append(
            "unable to determine collected tests count from pytest --collect-only output"
        )

    pyproject_content = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    version = _parse_project_version(pyproject_content)
    package_content = (repo_root / "gitwise" / "__init__.py").read_text(encoding="utf-8")
    version_error = _version_mismatch(version, _parse_package_version(package_content))
    if version_error:
        errors.append(version_error)

    expected = None
    if tests_count is not None and version is not None:
        expected = RoadmapBaseline(
            commands=_count_commands(),
            tests=tests_count,
            i18n_keys=_count_i18n_keys(repo_root),
            dependencies=_parse_runtime_dependencies(pyproject_content),
        )

    if expected is not None:
        for path_name, pattern in (
            ("ROADMAP.md", EN_BASELINE_RE),
            ("ROADMAP.es.md", ES_BASELINE_RE),
        ):
            mismatch = _baseline_mismatch(
                path_name,
                _extract_baseline(repo_root / path_name, pattern),
                expected,
            )
            if mismatch:
                errors.append(mismatch)

    if errors:
        for error in errors:
            print(f"roadmap-baseline-check: {error}", file=sys.stderr)
        return 1

    assert expected is not None
    print(
        "roadmap-baseline-check: baseline aligned "
        f"(version={version}, {_format_baseline(expected)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
