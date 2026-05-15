"""Detects git version, Python version, platform, and optional deps."""

import platform
import shutil
import sys

from . import __version__
from .git import gpg_status
from .git import version as git_version
from .output import info, ok, print_json, warn

MIN_GIT = (2, 29, 0)

_OPTIONAL_TOOLS = ["bat", "delta", "rg", "eza", "git-sizer", "watchman"]

_TOOL_INFO: dict[str, tuple[str, str]] = {
    "bat": ("visualización de archivos con syntax highlighting", "brew install bat"),
    "delta": ("diffs con syntax highlighting", "brew install git-delta"),
    "rg": ("búsqueda rápida en código (ripgrep)", "brew install ripgrep"),
    "eza": ("listado de directorios moderno", "brew install eza"),
    "git-sizer": ("análisis de tamaño e historia del repo", "brew install git-sizer"),
    "watchman": ("fsmonitor nativo — acelera git status", "brew install watchman"),
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
        ok(f"git {git_str} (≥ {min_str} requerido)")
    else:
        warn(f"git {git_str} demasiado antiguo — se requiere ≥ {min_str}")

    py_str = ".".join(str(n) for n in python_ver)
    if python_ok:
        ok(f"Python {py_str}")
    else:
        warn(f"Python {py_str} demasiado antiguo — se requiere ≥ 3.9")

    ok(f"plataforma: {platform_name}")

    if not fsmonitor_supported:
        warn("fsmonitor integrado no está soportado en Linux (solo macOS y Windows)")

    info("")
    info("herramientas opcionales:")
    for tool, found in optional.items():
        if found:
            info(f"  ✓ {tool}")
        else:
            desc, install = _TOOL_INFO.get(tool, ("", f"brew install {tool}"))
            info(f"  – {tool}  ({desc})")
            info(f"      → {install}")

    info("")
    info("GPG (firma de commits):")
    if gpg["ready"]:
        ok("  GPG listo — commit.gpgsign=true, llave y binario configurados")
    elif not gpg["gpg_binary"]:
        warn("  gpg no instalado — commits no se firmarán")
        info("      → brew install gnupg")
    elif not gpg["gpgsign_enabled"]:
        info("  gpg instalado pero commit.gpgsign no activado")
        info("      → git config --global commit.gpgsign true")
    elif not gpg["signing_key_set"]:
        warn("  commit.gpgsign=true pero user.signingkey no configurado")
        info("      → git config --global user.signingkey <key-id>")

    return 0 if result["ok"] else 1
