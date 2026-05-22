"""Tests for reusable git output parsers."""

from gitwise.utils.git_output import parse_diffstat_entries, parse_name_status_entries


def test_parse_diffstat_entries_basic() -> None:
    raw = "README.md | 2 ++\nscript.py | 10 +++++-----\n"
    data = parse_diffstat_entries(raw)
    assert data[0]["path"] == "README.md"
    assert data[0]["changes"] == "2 ++"
    assert data[1]["path"] == "script.py"


def test_parse_diffstat_entries_with_default_status() -> None:
    raw = "README.md | 1 +\n"
    data = parse_diffstat_entries(raw, default_status="M")
    assert data == [{"path": "README.md", "changes": "1 +", "status": "M"}]


def test_parse_name_status_entries_handles_rename_and_regular() -> None:
    raw = "M\tREADME.md\nR100\told.py\tnew.py\n"
    data = parse_name_status_entries(raw)
    assert {item["path"] for item in data} == {"README.md", "new.py"}
    renamed = next(item for item in data if item["path"] == "new.py")
    assert renamed["old_path"] == "old.py"
    assert renamed["score"] == "100"
