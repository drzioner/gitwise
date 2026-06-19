"""Shared parsing helpers for CLI text/number normalization."""


def non_empty_lines(text: str) -> list[str]:
    """Split ``text`` into lines, dropping blanks. Preserves leading/trailing whitespace."""
    return [line for line in text.splitlines() if line.strip()]


def stripped_non_empty_lines(text: str) -> list[str]:
    """Split ``text`` into lines, dropping blanks and stripping each survivor."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def to_int(value: object, *, default: int = 0) -> int:
    """Coerce ``value`` to int, returning ``default`` on parse failure (no exception)."""
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def parse_two_ints(text: str) -> tuple[int, int] | None:
    """Parse two whitespace-separated ints (e.g. git ahead/behind counts). None on failure."""
    parts = text.strip().split()
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, TypeError):
        return None


def dict_list(value: object) -> list[dict[str, object]]:
    """Return ``value`` if it is a list of dicts, else ``[]``. Tolerates non-list input."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
