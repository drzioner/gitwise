"""Zero-dependency i18n: es/en string catalog with auto locale detection."""

import json
import os
from pathlib import Path
from typing import Literal

Locale = Literal["es", "en"]
OutputMode = Literal["human", "agent"]

_CACHE: dict[str, str] = {}


def _load_strings() -> dict[str, dict[str, str]]:
    data_path = Path(__file__).with_name("_i18n_data.json")
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


_STRINGS: dict[str, dict[str, str]] = _load_strings()


def _detect_locale() -> Locale:
    lang = os.environ.get("GITWISE_LANG", "").lower()[:2]
    if lang in ("es", "en"):
        return lang
    for var in ("LC_MESSAGES", "LC_ALL", "LANG"):
        val = os.environ.get(var, "").lower()
        if val.startswith("es"):
            return "es"
        if val.startswith("en"):
            return "en"
    return "en"


def _detect_output_mode() -> OutputMode:
    mode = os.environ.get("GITWISE_OUTPUT", "").lower()
    if mode in ("human", "agent"):
        return mode
    if os.environ.get("GITWISE_AGENT", "").lower() in ("1", "true"):
        return "agent"
    if not os.environ.get("TERM", ""):
        return "agent"
    return "human"


class _I18nState:
    __slots__ = ("locale", "mode")

    def __init__(self) -> None:
        self.locale: Locale = _detect_locale()
        self.mode: OutputMode = _detect_output_mode()


_state = _I18nState()


def get_locale() -> Locale:
    return _state.locale


def get_mode() -> OutputMode:
    return _state.mode


def set_locale(locale: Locale) -> None:
    _state.locale = locale
    _CACHE.clear()


def set_mode(mode: OutputMode) -> None:
    _state.mode = mode
    _CACHE.clear()


def t(key: str, **kwargs: str) -> str:
    cached_key = f"{_state.locale}:{key}:{json.dumps(kwargs, sort_keys=True, default=str)}"
    if cached_key in _CACHE and "GITWISE_DEBUG" not in os.environ:
        return _CACHE[cached_key]
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    template = entry.get(_state.locale, entry.get("en", key))
    try:
        result = template.format(**kwargs) if kwargs else template
    except (KeyError, IndexError, ValueError):
        result = template
    _CACHE[cached_key] = result
    return result


def confirm_responses() -> set[str]:
    if _state.locale == "es":
        return {"s", "si", "sí", "y", "yes"}
    return {"y", "yes", "s", "si"}


def reset_cache() -> None:
    _CACHE.clear()
