from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _is_external_link(link: str) -> bool:
    return link.startswith(("http://", "https://", "mailto:", "#"))


def _is_ignored_path(path: Path) -> bool:
    parts = path.parts
    ignored_roots = {".venv", ".opencode", ".agents", "review"}
    return bool(parts and parts[0] in ignored_roots)


def _doc_files(root: Path) -> list[Path]:
    files = [*root.glob("*.md"), *root.joinpath("docs").rglob("*.md")]
    return sorted(p for p in files if not _is_ignored_path(p.relative_to(root)))


def _resolve_link(root: Path, source_file: Path, link: str) -> Path | None:
    clean = link.strip().strip("<>")
    if not clean or _is_external_link(clean):
        return None

    target = clean.split("#", 1)[0].strip()
    if not target:
        return None

    if target.startswith("/"):
        return root / target.lstrip("/")
    return (source_file.parent / target).resolve()


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    errors: list[str] = []

    for md_file in _doc_files(root):
        text = md_file.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            link = match.group(1).strip()
            target_path = _resolve_link(root, md_file, link)
            if target_path is None:
                continue
            if not target_path.exists():
                errors.append(f"broken link in {md_file.relative_to(root).as_posix()}: {link}")

    if errors:
        for err in errors:
            print(f"md-link-check: {err}", file=sys.stderr)
        return 1

    print("md-link-check: no broken internal markdown links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
