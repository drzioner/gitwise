"""Centralized path resolution for share/ data directory.

Resolves the share/ directory location for both installed (pip) and
development (repo root) environments.
"""

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent


def share_dir() -> Path:
    """Resolve the share/ directory.

    When installed via pip (hatchling force-include), share/ lives inside
    the package at gitwise/share/. When running from a repo checkout,
    share/ is a sibling of the package directory at project root.
    """
    installed = _PACKAGE_DIR / "share"
    if installed.is_dir():
        return installed
    return _PACKAGE_DIR.parent / "share"
