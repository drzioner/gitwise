from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

EN_BASELINE_RE = re.compile(r"Current baseline:\s*(\d+)\s*tests collected,\s*(\d+)\s*i18n keys")
ES_BASELINE_RE = re.compile(r"Baseline actual:\s*(\d+)\s*tests recolectados,\s*(\d+)\s*keys i18n")
COLLECTED_TESTS_RE = re.compile(r"(\d+)\s+tests collected")


def _count_i18n_keys(repo_root: Path) -> int:
    i18n_file = repo_root / "gitwise" / "_i18n_data.json"
    data = json.loads(i18n_file.read_text(encoding="utf-8"))
    return len(data)


def _parse_collected_tests(output: str) -> int | None:
    match = COLLECTED_TESTS_RE.search(output)
    if match is None:
        return None
    return int(match.group(1))


def _collect_tests_count(repo_root: Path) -> int | None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = f"{result.stdout}\n{result.stderr}"
    return _parse_collected_tests(combined)


def _extract_baseline_counts(path: Path, pattern: re.Pattern[str]) -> tuple[int, int] | None:
    content = path.read_text(encoding="utf-8")
    match = pattern.search(content)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    errors: list[str] = []

    tests_count = _collect_tests_count(repo_root)
    if tests_count is None:
        errors.append(
            "unable to determine collected tests count from pytest --collect-only output"
        )

    i18n_keys = _count_i18n_keys(repo_root)

    en_counts = _extract_baseline_counts(repo_root / "ROADMAP.md", EN_BASELINE_RE)
    if en_counts is None:
        errors.append("missing or invalid baseline line in ROADMAP.md")
    elif tests_count is not None and en_counts != (tests_count, i18n_keys):
        errors.append(
            "ROADMAP.md baseline mismatch: "
            f"found tests={en_counts[0]}, i18n={en_counts[1]} "
            f"expected tests={tests_count}, i18n={i18n_keys}"
        )

    es_counts = _extract_baseline_counts(repo_root / "ROADMAP.es.md", ES_BASELINE_RE)
    if es_counts is None:
        errors.append("missing or invalid baseline line in ROADMAP.es.md")
    elif tests_count is not None and es_counts != (tests_count, i18n_keys):
        errors.append(
            "ROADMAP.es.md baseline mismatch: "
            f"found tests={es_counts[0]}, i18n={es_counts[1]} "
            f"expected tests={tests_count}, i18n={i18n_keys}"
        )

    if errors:
        for error in errors:
            print(f"roadmap-baseline-check: {error}", file=sys.stderr)
        return 1

    print(f"roadmap-baseline-check: baseline aligned (tests={tests_count}, i18n_keys={i18n_keys})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
