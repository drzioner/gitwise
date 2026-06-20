"""Tests for the v3 JSON envelope helpers."""

from typing import cast

from gitwise.utils.json_envelope import (
    ENVELOPE_VERSION,
    error_envelope,
    ok_envelope,
)


def test_ok_envelope_nests_data_and_requires_command() -> None:
    env = ok_envelope("log", commits=[], count=0)
    assert env["v"] == ENVELOPE_VERSION == 3
    assert env["ok"] is True
    assert env["command"] == "log"
    assert env["data"] == {"commits": [], "count": 0}
    assert env["hints"] == []
    assert env["errors"] == []


def test_ok_envelope_data_mapping_merges_with_extras() -> None:
    env = ok_envelope("clean", data={"dry_run": True}, applied=True)
    assert env["data"] == {"dry_run": True, "applied": True}


def test_ok_envelope_reserved_keys_are_not_overridable() -> None:
    env = ok_envelope("status", data={"v": 99, "ok": False})
    assert env["v"] == 3
    assert env["ok"] is True
    data = cast(dict[str, object], env["data"])
    assert data["v"] == 99


def test_ok_envelope_hints_default_empty_list() -> None:
    env = ok_envelope("diff")
    assert env["data"] == {}
    assert env["hints"] == []


def test_error_envelope_structured_errors_and_hint() -> None:
    env = error_envelope("commit", error="boom", code="boom_code", hint="try x")
    assert env["v"] == 3
    assert env["ok"] is False
    assert env["command"] == "commit"
    assert env["data"] == {}
    errors = env["errors"]
    assert isinstance(errors, list)
    first = errors[0]
    assert isinstance(first, dict)
    assert first["code"] == "boom_code"
    assert first["message"] == "boom"
    assert first["hint"] == "try x"
    hints = env["hints"]
    assert isinstance(hints, list)
    assert "try x" in hints


def test_error_envelope_extras_merge_into_data() -> None:
    env = error_envelope("commit", error="leak", code="secret_leak_high", findings=[1, 2])
    assert env["data"] == {"findings": [1, 2]}
    errors = env["errors"]
    assert isinstance(errors, list)
    first = errors[0]
    assert isinstance(first, dict)
    assert first["code"] == "secret_leak_high"


def test_error_envelope_default_code_is_error() -> None:
    env = error_envelope("merge", error="nope")
    errors = env["errors"]
    assert isinstance(errors, list)
    first = errors[0]
    assert isinstance(first, dict)
    assert first["code"] == "error"
    assert env["hints"] == []
