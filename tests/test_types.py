"""Tests for the shared FileEntry type and status-code mapping."""

from gitwise.utils.types import CONFLICT_CODES, build_file_entry, status_from_code


def test_build_file_entry_basic_modified_staged() -> None:
    entry = build_file_entry("src/a.py", "M ", staged=True)
    assert entry["path"] == "src/a.py"
    assert entry["code"] == "M "
    assert entry["status"] == "modified"
    assert entry["staged"] is True
    assert entry["binary"] is False
    assert "insertions" not in entry
    assert "old_path" not in entry


def test_build_file_entry_conflict_code_maps_to_conflict() -> None:
    entry = build_file_entry("src/b.py", "UU", staged=False)
    assert entry["status"] == "conflict"
    assert entry["staged"] is False


def test_build_file_entry_untracked() -> None:
    entry = build_file_entry("new.txt", "??", staged=False)
    assert entry["status"] == "untracked"


def test_build_file_entry_with_diff_fields() -> None:
    entry = build_file_entry(
        "c.py",
        "M ",
        staged=True,
        insertions=10,
        deletions=3,
        old_path="c_old.py",
    )
    extra = dict(entry)
    assert extra["insertions"] == 10
    assert extra["deletions"] == 3
    assert extra["old_path"] == "c_old.py"


def test_status_from_code_covers_all_categories() -> None:
    assert status_from_code("A ") == "added"
    assert status_from_code(" D") == "deleted"
    assert status_from_code("R ") == "renamed"
    assert status_from_code("C ") == "copied"
    assert status_from_code("!!") == "ignored"
    for cc in CONFLICT_CODES:
        assert status_from_code(cc) == "conflict"


def test_status_from_code_raises_on_short_code() -> None:
    import pytest

    with pytest.raises(ValueError):
        status_from_code("M")
    with pytest.raises(ValueError):
        status_from_code("")
