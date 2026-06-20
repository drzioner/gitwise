"""Shared value types used across command JSON output.

The :data:`FileEntry` shape unifies ``status`` / ``diff`` / ``summarize`` so a
single consumer can parse per-file data from any of them (roadmap J3).
"""

from typing import TypedDict

CONFLICT_CODES = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})


def status_from_code(code: str) -> str:
    """Map a porcelain v1 ``XY`` status code to a human-readable category."""
    if code in CONFLICT_CODES:
        return "conflict"
    if code.startswith("??"):
        return "untracked"
    if code.startswith("!!"):
        return "ignored"
    if code[0] == "R" or code[1] == "R":
        return "renamed"
    if code[0] == "C" or code[1] == "C":
        return "copied"
    if code[0] == "A" or code[1] == "A":
        return "added"
    if code[0] == "D" or code[1] == "D":
        return "deleted"
    return "modified"


class _FileEntryRequired(TypedDict):
    """Always-present FileEntry fields (inherited as required keys)."""

    path: str
    code: str
    status: str
    staged: bool
    binary: bool


class FileEntry(_FileEntryRequired, total=False):
    """A per-file record shared by status/diff/summarize JSON output.

    The five core keys are required (inherited); diff-only fields are optional.
    Uses TypedDict inheritance instead of ``typing.Required`` so it works on
    Python 3.10 without the ``typing_extensions`` dependency.
    """

    insertions: int
    deletions: int
    old_path: str


def build_file_entry(
    path: str,
    code: str,
    *,
    staged: bool,
    binary: bool = False,
    insertions: int | None = None,
    deletions: int | None = None,
    old_path: str | None = None,
) -> FileEntry:
    """Construct a :data:`FileEntry` with optional diff-only fields."""
    entry: FileEntry = {
        "path": path,
        "code": code,
        "status": status_from_code(code),
        "staged": staged,
        "binary": binary,
    }
    if old_path is not None:
        entry["old_path"] = old_path
    if insertions is not None:
        entry["insertions"] = insertions
    if deletions is not None:
        entry["deletions"] = deletions
    return entry
