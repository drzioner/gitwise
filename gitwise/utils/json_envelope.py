"""Helpers for standardized JSON envelopes in CLI commands."""

from collections.abc import Mapping


def ok_envelope(
    *,
    payload: Mapping[str, object] | None = None,
    version: int = 2,
    **extra: object,
) -> dict[str, object]:
    data: dict[str, object] = {}
    if payload is not None:
        data.update(payload)
    data.update(extra)
    data["v"] = version
    data["ok"] = True
    return data


def error_envelope(
    *,
    error: str,
    code: str | None = None,
    hint: str | None = None,
    payload: Mapping[str, object] | None = None,
    version: int = 2,
    **extra: object,
) -> dict[str, object]:
    data: dict[str, object] = {}
    if payload is not None:
        data.update(payload)
    data.update(extra)
    data["v"] = version
    data["ok"] = False
    data["error"] = error
    err_item: dict[str, object] = {
        "code": code or "error",
        "message": error,
    }
    if hint:
        err_item["hint"] = hint
    data["errors"] = [err_item]
    return data


def passthrough_envelope(
    *,
    payload: Mapping[str, object] | None = None,
    version: int = 2,
    **extra: object,
) -> dict[str, object]:
    data: dict[str, object] = {}
    if payload is not None:
        data.update(payload)
    data.update(extra)
    data["v"] = version
    return data
