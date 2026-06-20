"""Detects git version, Python version, platform, and optional deps."""

import platform
import shutil
import sys

from . import __version__
from .git import gpg_status
from .git import version as git_version
from .i18n import t
from .output import (
    print_blank,
    print_dim,
    print_header,
    print_json,
    print_kv,
    print_status_line,
    status,
    warn,
)
from .utils.json_envelope import ok_envelope

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
    """Entry point for the ``gitwise doctor`` command.

    Checks git version, Python version, platform, optional tools, and GPG status.
    Returns 0 when critical checks pass (git + Python), 1 otherwise.
    """
    with status(t("status_checking_env")):
        git_ver = git_version()
        git_ok = git_ver >= MIN_GIT

        python_ver = sys.version_info[:3]
        python_ok = python_ver >= (3, 9)

        platform_name = platform.system()
        fsmonitor_supported = platform_name in ("Darwin", "Windows")

        optional = {tool: bool(shutil.which(tool)) for tool in _OPTIONAL_TOOLS}
        gpg = gpg_status()

    result = {
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
    }
    doctor_ok = git_ok and python_ok

    if as_json:
        env = ok_envelope("doctor", data=result)
        env["ok"] = doctor_ok
        print_json(env)
        return 0 if doctor_ok else 1

    print_header(f"gitwise {__version__}")
    print_blank()

    git_str = ".".join(str(n) for n in git_ver)
    min_str = ".".join(str(n) for n in MIN_GIT)
    if git_ok:
        print_status_line("✓", t("doctor_git_label"), git_str, ok_flag=True)
    else:
        print_status_line("✗", t("doctor_git_label"), git_str, ok_flag=False)
        warn(t("git_too_old", ver=git_str, min=min_str))

    py_str = ".".join(str(n) for n in python_ver)
    if python_ok:
        print_status_line("✓", t("doctor_python_label"), py_str, ok_flag=True)
    else:
        print_status_line("✗", t("doctor_python_label"), py_str, ok_flag=False)
        warn(t("python_too_old", ver=py_str))

    print_status_line("✓", t("platform_label", name=platform_name), "", ok_flag=True)

    if not fsmonitor_supported:
        warn(t("fsmonitor_not_supported"))

    print_blank()
    print_header(t("optional_tools"))
    for tool, found in optional.items():
        if found:
            print_status_line("✓", tool, "", ok_flag=True)
        else:
            desc_key, install = _TOOL_INFO.get(tool, ("", f"brew install {tool}"))
            desc = t(desc_key) if desc_key else ""
            print_status_line("–", tool, "", ok_flag=False)
            print_kv(t("doctor_purpose_label"), desc)
            print_kv(t("doctor_install_label"), install)

    print_blank()
    print_header(t("gpg_title"))
    if gpg["ready"]:
        print_status_line("✓", t("gpg_ready_msg"), "", ok_flag=True)
    elif not gpg["gpg_binary"]:
        print_status_line("✗", t("gpg_not_installed"), "", ok_flag=False)
        print_dim(t("gpg_install_instruction"))
    elif not gpg["gpgsign_enabled"]:
        print_status_line("–", t("gpg_not_enabled"), "", ok_flag=False)
        print_dim(t("gpg_enable_instruction"))
    elif not gpg["signing_key_set"]:
        print_status_line("✗", t("gpg_no_signing_key"), "", ok_flag=False)
        print_dim(t("gpg_key_instruction"))

    return 0 if doctor_ok else 1
