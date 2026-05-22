"""Shared parsing helpers for CLI text/number normalization."""


def non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def stripped_non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def to_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return default
        sign = 1
        if raw[0] in {"+", "-"}:
            sign = -1 if raw[0] == "-" else 1
            raw = raw[1:]
        if raw.isdigit():
            return sign * int(raw)
    return default


def parse_two_ints(text: str) -> tuple[int, int] | None:
    parts = text.strip().split()
    if len(parts) != 2:
        return None
    left = to_int(parts[0], default=10**9)
    right = to_int(parts[1], default=10**9)
    if left == 10**9 or right == 10**9:
        return None
    return left, right


def dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
