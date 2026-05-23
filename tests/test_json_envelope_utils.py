"""Tests for reusable JSON envelope helpers."""

from gitwise.utils.json_envelope import error_envelope, ok_envelope


def test_ok_envelope_sets_reserved_keys_last() -> None:
    payload = {"v": 99, "ok": False, "value": 1}
    data = ok_envelope(payload=payload)
    assert data["v"] == 2
    assert data["ok"] is True
    assert data["value"] == 1


def test_error_envelope_sets_error_and_reserved_keys() -> None:
    data = error_envelope(error="boom", detail="x")
    assert data["v"] == 2
    assert data["ok"] is False
    assert data["error"] == "boom"
    assert data["detail"] == "x"
    errors = data["errors"]
    assert isinstance(errors, list)
    first = errors[0]
    assert isinstance(first, dict)
    assert first["code"] == "error"
    assert first["message"] == "boom"


def test_error_envelope_supports_code_and_hint() -> None:
    data = error_envelope(error="boom", code="boom_code", hint="try x")
    errors = data["errors"]
    assert isinstance(errors, list)
    first = errors[0]
    assert isinstance(first, dict)
    assert first["code"] == "boom_code"
    assert first["message"] == "boom"
    assert first["hint"] == "try x"
