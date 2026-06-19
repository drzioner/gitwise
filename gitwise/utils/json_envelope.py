"""Standardized v3 JSON envelopes for CLI commands.

Every ``--json`` output is an envelope::

    {"v": 3, "ok": bool, "command": str, "data": {...}, "hints": [...], "errors": [...]}

``data`` carries command-specific fields (the former v2 flattened payload);
``errors`` is always present (empty on success); ``hints`` surfaces suggested
next commands; ``command`` lets a single consumer parse every command with one
schema. Reserved keys (``v``, ``ok``, ``command``, ``data``, ``hints``,
``errors``) are set by the helpers and never leak from caller-supplied fields.
"""

from collections.abc import Mapping

ENVELOPE_VERSION = 3


def ok_envelope(
    command: str,
    *,
    data: Mapping[str, object] | None = None,
    hints: list[str] | None = None,
    **data_fields: object,
) -> dict[str, object]:
    """Build a success v3 envelope.

    ``data`` and ``data_fields`` are merged into the nested ``data`` object so
    callers can pass command-specific fields either as a mapping or as keyword
    arguments (e.g. ``ok_envelope("log", commits=cs, count=len(cs))``).
    """
    payload: dict[str, object] = dict(data) if data else {}
    payload.update(data_fields)
    return {
        "v": ENVELOPE_VERSION,
        "ok": True,
        "command": command,
        "data": payload,
        "hints": list(hints) if hints else [],
        "errors": [],
    }


def error_envelope(
    command: str,
    *,
    error: str,
    code: str | None = None,
    hint: str | None = None,
    data: Mapping[str, object] | None = None,
    hints: list[str] | None = None,
    **data_fields: object,
) -> dict[str, object]:
    """Build an error v3 envelope with one structured ``errors`` entry.

    ``code`` defaults to ``"error"``; pass a stable machine-readable code so
    agents can branch on it. ``hint`` is surfaced both in ``errors[0].hint`` and
    appended to ``hints``. Extra keyword fields (e.g. ``findings=``) merge into
    ``data`` so structured context travels with the error.
    """
    payload: dict[str, object] = dict(data) if data else {}
    payload.update(data_fields)
    err_item: dict[str, object] = {"code": code or "error", "message": error}
    hints_list = list(hints) if hints else []
    if hint:
        err_item["hint"] = hint
        if hint not in hints_list:
            hints_list.append(hint)
    return {
        "v": ENVELOPE_VERSION,
        "ok": False,
        "command": command,
        "data": payload,
        "hints": hints_list,
        "errors": [err_item],
    }
