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


_active_locale: Locale = _detect_locale()
_active_mode: OutputMode = _detect_output_mode()


def get_locale() -> Locale:
    return _active_locale


def get_mode() -> OutputMode:
    return _active_mode


def set_locale(locale: Locale) -> None:
    global _active_locale
    _active_locale = locale


def set_mode(mode: OutputMode) -> None:
    global _active_mode
    _active_mode = mode


def t(key: str, **kwargs: str) -> str:
    cached_key = f"{_active_locale}:{key}:{sorted(kwargs.items())}"
    if cached_key in _CACHE and "GITWISE_DEBUG" not in os.environ:
        return _CACHE[cached_key]
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    template = entry.get(_active_locale, entry.get("en", key))
    result = template.format(**kwargs) if kwargs else template
    _CACHE[cached_key] = result
    return result


def confirm_responses() -> set[str]:
    if _active_locale == "es":
        return {"s", "si", "sí", "y", "yes"}
    return {"y", "yes", "s", "si"}


def reset_cache() -> None:
    _CACHE.clear()
