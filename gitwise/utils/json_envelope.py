"""Helpers for standardized JSON envelopes in CLI commands."""

from collections.abc import Mapping


def ok_envelope(
    *,
    payload: Mapping[str, object] | None = None,
    version: int = 2,
    **extra: object,
) -> dict[str, object]:
    """Build a success envelope: ``{v, ok: true, ...payload, ...extra}``.

    ``payload`` and ``extra`` are flattened into the top-level dict so callers
    can pass command-specific fields (e.g. ``message=``, ``merged=``) directly.
    """
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
    """Build an error envelope: ``{v, ok: false, error, errors: [{code, message, hint?}]}``.

    ``code`` defaults to ``"error"``; pass a stable machine-readable code
    (e.g. ``"in_progress_merge"``) so agents can branch on it. ``hint`` is
    surfaced both in ``errors[0].hint`` and (by callers) in human output.
    """
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
    """Build a versioned envelope without an ``ok`` field.

    Used by commands whose payload already carries the success/failure signal
    (e.g. ``health`` returns its own status), so forcing ``ok: true/false``
    would duplicate or contradict it.
    """
    data: dict[str, object] = {}
    if payload is not None:
        data.update(payload)
    data.update(extra)
    data["v"] = version
    return data
