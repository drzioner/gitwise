"""Detects git version, Python version, platform, and optional deps."""

import platform
import shutil
import sys

from . import __version__
from .git import gpg_status
from .git import version as git_version
from .i18n import t
from .output import info, ok, print_json, warn

MIN_GIT = (2, 29, 0)

_OPTIONAL_TOOLS = ["bat", "delta", "rg", "eza", "git-sizer", "watchman"]

_TOOL_INFO: dict[str, tuple[str, str]] = {
    "bat": ("tool_bat_desc", "brew install bat"),
    "delta": ("tool_delta_desc", "brew install git-delta"),
    "rg": ("tool_rg_desc", "brew install ripgrep"),
    "eza": ("tool_eza_desc", "brew install eza"),
    "git-sizer": ("tool_git_sizer_desc", "brew install git-sizer"),
    "watchman": ("tool_watchman_desc", "brew install watchman"),
}


def run_doctor(*, as_json: bool = False) -> int:
    git_ver = git_version()
    git_ok = git_ver >= MIN_GIT

    python_ver = sys.version_info[:3]
    python_ok = python_ver >= (3, 9)

    platform_name = platform.system()
    fsmonitor_supported = platform_name in ("Darwin", "Windows")

    optional = {tool: bool(shutil.which(tool)) for tool in _OPTIONAL_TOOLS}
    gpg = gpg_status()

    result = {
        "v": 1,
        "gitwise_version": __version__,
        "git_version": ".".join(str(n) for n in git_ver),
        "git_version_ok": git_ok,
        "git_min_required": ".".join(str(n) for n in MIN_GIT),
        "python_version": ".".join(str(n) for n in python_ver),
        "python_version_ok": python_ok,
        "platform": platform_name,
        "fsmonitor_supported": fsmonitor_supported,
        "optional_tools": optional,
        "gpg": gpg,
        "ok": git_ok and python_ok,
    }

    if as_json:
        print_json(result)
        return 0 if result["ok"] else 1

    info(f"gitwise {__version__}")
    info("")

    git_str = ".".join(str(n) for n in git_ver)
    min_str = ".".join(str(n) for n in MIN_GIT)
    if git_ok:
        ok(t("git_version_ok", ver=git_str, min=min_str))
    else:
        warn(t("git_too_old", ver=git_str, min=min_str))

    py_str = ".".join(str(n) for n in python_ver)
    if python_ok:
        ok(t("python_version_ok", ver=py_str))
    else:
        warn(t("python_too_old", ver=py_str))

    ok(t("platform_label", name=platform_name))

    if not fsmonitor_supported:
        warn(t("fsmonitor_not_supported"))

    info("")
    info(t("optional_tools"))
    for tool, found in optional.items():
        if found:
            info(f"  ✓ {tool}")
        else:
            desc_key, install = _TOOL_INFO.get(tool, ("", f"brew install {tool}"))
            desc = t(desc_key) if desc_key else ""
            info(f"  – {tool}  ({desc})")
            info(f"      → {install}")

    info("")
    info(t("gpg_title"))
    if gpg["ready"]:
        ok(t("gpg_ready_msg"))
    elif not gpg["gpg_binary"]:
        warn(t("gpg_not_installed"))
        info(t("gpg_install_instruction"))
    elif not gpg["gpgsign_enabled"]:
        info(t("gpg_not_enabled"))
        info(t("gpg_enable_instruction"))
    elif not gpg["signing_key_set"]:
        warn(t("gpg_no_signing_key"))
        info(t("gpg_key_instruction"))

    return 0 if result["ok"] else 1
