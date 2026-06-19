"""State detection for setup-agents: path classification, symlink support, GPG readiness."""

import os
import platform
import re
from pathlib import Path

from gitwise.git import config as git_config
from gitwise.i18n import t
from gitwise.setup_agents.types import PathState, StateDict

_AGENTS_MD = "AGENTS.md"
_CLAUDE_MD = "CLAUDE.md"
_MARKER_RE = re.compile(
    r"^##\s+(Convenciones git para este proyecto|Git conventions for this project)\b",
    re.MULTILINE,
)

_supports_symlinks_cache: dict[Path, bool] = {}


def _gpg_ready(root: Path) -> bool:
    """Return True when gpg is available, commit.gpgsign is on, and a signing key is configured."""
    import shutil

    if not (shutil.which("gpg") or shutil.which("gpg2")):
        return False
    return git_config("commit.gpgsign", cwd=root) == "true" and bool(
        git_config("user.signingkey", cwd=root)
    )


def _classify_path(p: Path) -> PathState:
    """Classify a path as absent, regular, symlink_valid, or symlink_broken."""
    if p.is_symlink():
        return "symlink_valid" if p.exists() else "symlink_broken"
    if p.exists():
        return "regular"
    return "absent"


def _supports_symlinks(root: Path) -> bool:
    """Probe whether the filesystem supports symlinks under root (cached per root)."""
    if platform.system() == "Windows":
        return False
    if root in _supports_symlinks_cache:
        return _supports_symlinks_cache[root]
    try:
        import tempfile

        with tempfile.TemporaryDirectory(dir=root) as td:
            link = Path(td) / "_test_link"
            link.symlink_to("_nonexistent")
            link.unlink()
        _supports_symlinks_cache[root] = True
    except (OSError, NotImplementedError):
        _supports_symlinks_cache[root] = False
    return _supports_symlinks_cache[root]


def _has_marker(p: Path) -> bool:
    """Return True if file contains the git-conventions heading marker."""
    try:
        text = p.read_text(encoding="utf-8")
        return bool(_MARKER_RE.search(text))
    except OSError:
        return False


def _files_equal(a: Path, b: Path) -> bool:
    """Return True if two files have identical text content."""
    try:
        return a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")
    except OSError:
        return False


def _detect_rules(root: Path) -> list[str]:
    """Validates .claude/rules/*.md for required globs: frontmatter field."""
    rules_dir = root / ".claude" / "rules"
    warnings: list[str] = []
    if not rules_dir.is_dir():
        return warnings
    root_real = Path(os.path.realpath(str(root)))
    for f in sorted(rules_dir.glob("*.md")):
        f_real = Path(os.path.realpath(str(f)))
        if not f_real.is_relative_to(root_real):
            warnings.append(t("symlink_outside_repo", name=f.name))
            continue
        try:
            if f.stat().st_size > 64_000:
                warnings.append(t("file_too_large", name=f.name))
                continue
        except OSError:
            continue
        try:
            text = f.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        has_frontmatter = text.startswith("---\n")
        fm_end = text.find("\n---\n", 4) if has_frontmatter else -1
        has_globs = "globs:" in text[4:fm_end] if fm_end > 0 else False
        if not (has_frontmatter and has_globs):
            warnings.append(t("missing_globs_frontmatter", name=f.name))
    return warnings


def reset_caches() -> None:
    """Clear the symlink-support cache so the next call re-probes the filesystem."""
    _supports_symlinks_cache.clear()


def _detect_state(root: Path) -> StateDict:
    """Detect the current state of convention docs, skills dir, symlink support, and rule files in the repo."""
    agents_md = root / _AGENTS_MD
    claude_md = root / _CLAUDE_MD
    agents_dir = root / ".agents"
    skills_dir = root / ".claude" / "skills"

    a_state = _classify_path(agents_md)
    c_state = _classify_path(claude_md)
    errors: list[str] = []

    if a_state == "symlink_broken":
        errors.append(t("symlink_conflict_broken", file=_AGENTS_MD))
    if c_state == "symlink_broken":
        errors.append(t("symlink_conflict_broken", file=_CLAUDE_MD))

    skills_state = _classify_path(skills_dir)
    skills_target: str | None = None
    if skills_state == "symlink_valid":
        try:
            skills_target = os.readlink(skills_dir)
        except OSError as e:
            errors.append(t("symlink_read_failed", file=".claude/skills", error=str(e)))
    elif skills_state == "symlink_broken":
        errors.append(t("symlink_conflict_broken", file=".claude/skills"))

    return {
        "a_state": a_state,
        "c_state": c_state,
        "agents_dir": agents_dir.is_dir() and not agents_dir.is_symlink(),
        "skills_state": skills_state,
        "skills_target": skills_target,
        "supports_symlinks": _supports_symlinks(root),
        "errors": errors,
        "rules_warnings": _detect_rules(root),
    }
