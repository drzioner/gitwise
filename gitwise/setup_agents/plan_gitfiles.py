"""Managed gitignore/gitattributes blocks for setup-agents."""

from pathlib import Path

from gitwise.i18n import t

_MANAGED_MARKER_START = "# >>> gitwise managed (do not edit between markers) >>>"
_MANAGED_MARKER_END = "# <<< gitwise managed <<<"


def _snapshot_path_for_block(*, has_agents_dir: bool) -> str:
    """Return the snapshot file path used inside managed blocks."""
    if has_agents_dir:
        return ".agents/git-snapshot.md"
    return ".claude/git-snapshot.md"


def gitignore_block_basic() -> str:
    """Return the .gitignore managed block for claude-only repos."""
    lines = [
        _MANAGED_MARKER_START,
        "# Claude Code local/personal files (do not commit)",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
        "# Snapshot regenerated each gitwise run (timestamps change)",
        _snapshot_path_for_block(has_agents_dir=False),
        "# Backups from gitwise setup-agents",
        "*.bak",
        "CLAUDE.md.bak*",
        _MANAGED_MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def gitignore_block_extended(has_agents_md: bool, has_agents_dir: bool = False) -> str:
    """Return the .gitignore managed block for repos with AGENTS.md and/or .agents/."""
    lines = [
        _MANAGED_MARKER_START,
        "# Claude Code local/personal files (do not commit)",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
        "# Snapshot regenerated each gitwise run (timestamps change)",
        _snapshot_path_for_block(has_agents_dir=has_agents_dir),
        "# Backups from gitwise setup-agents",
        "*.bak",
        "CLAUDE.md.bak*",
    ]
    if has_agents_md:
        lines.append("AGENTS.md.bak*")
    lines.append(_MANAGED_MARKER_END)
    return "\n".join(lines) + "\n"


def gitattributes_block_basic() -> str:
    """Return the .gitattributes managed block for claude-only repos."""
    lines = [
        _MANAGED_MARKER_START,
        "# Generated snapshot: use local version on merge",
        f"{_snapshot_path_for_block(has_agents_dir=False)} merge=ours linguist-generated=true",
        "# Convention files: force LF for cross-platform consistency",
        "CLAUDE.md text=auto eol=lf",
        ".claude/skills/**/SKILL.md text=auto eol=lf",
        _MANAGED_MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def gitattributes_block_extended(has_agents_md: bool, has_agents_dir: bool) -> str:
    """Return the .gitattributes managed block for repos with AGENTS.md and/or .agents/."""
    lines = [
        _MANAGED_MARKER_START,
        "# Generated snapshot: use local version on merge",
        f"{_snapshot_path_for_block(has_agents_dir=has_agents_dir)} merge=ours linguist-generated=true",
        "# Convention files: force LF for cross-platform consistency",
        "CLAUDE.md text=auto eol=lf",
    ]
    if has_agents_md:
        lines.append("AGENTS.md text=auto eol=lf")
    lines.append(".claude/skills/**/SKILL.md text=auto eol=lf")
    if has_agents_dir:
        lines.append(".agents/skills/**/SKILL.md text=auto eol=lf")
    lines.append(_MANAGED_MARKER_END)
    return "\n".join(lines) + "\n"


def _gitattributes_conflicts(existing_text: str, desired_block: str) -> list[str]:
    """Detect patterns in the existing .gitattributes outside the managed block that conflict with the desired block."""
    block_start = existing_text.find(_MANAGED_MARKER_START)
    outside_text = existing_text[:block_start] if block_start != -1 else existing_text

    def _parse(text: str) -> dict[str, str]:
        """Parse non-comment, non-blank lines into a pattern-to-full-line mapping."""
        result: dict[str, str] = {}
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split(None, 1)
            if len(parts) > 1:
                result[parts[0]] = s
        return result

    outside = _parse(outside_text)
    block = _parse(desired_block)
    warnings: list[str] = []
    for pattern, block_line in block.items():
        if pattern in outside and outside[pattern] != block_line:
            warnings.append(
                t(
                    "gitattributes_conflict",
                    pattern=pattern,
                    existing=outside[pattern],
                    desired=block_line,
                )
            )
    return warnings


def plan_managed_block(
    path: Path, desired_block: str, file_key: str
) -> tuple[list[dict], list[str]]:
    """Plan actions for a managed block: create, append, replace, or skip.

    Returns (actions, conflict_warnings).
    """
    if not path.exists():
        return [
            {
                "file": file_key,
                "action": "managed-block-create",
                "content": desired_block,
                "_path": str(path),
            }
        ], []

    try:
        current = path.read_text(encoding="utf-8")
    except OSError:
        return [], []

    conflict_warnings = (
        _gitattributes_conflicts(current, desired_block) if file_key == ".gitattributes" else []
    )

    if _MANAGED_MARKER_START not in current:
        return [
            {
                "file": file_key,
                "action": "managed-block-create",
                "content": desired_block,
                "_path": str(path),
                "_append": True,
            }
        ], conflict_warnings

    start_idx = current.index(_MANAGED_MARKER_START)
    end_marker_idx = current.find(_MANAGED_MARKER_END, start_idx)
    if end_marker_idx == -1:
        return [], [t("managed_block_unclosed", file=file_key)] + conflict_warnings

    end_idx = end_marker_idx + len(_MANAGED_MARKER_END)
    existing_block = current[start_idx:end_idx]

    if existing_block.rstrip() == desired_block.rstrip():
        return [
            {"file": file_key, "action": "managed-block-skip", "_path": str(path)}
        ], conflict_warnings

    return [
        {
            "file": file_key,
            "action": "managed-block-replace",
            "content": desired_block,
            "_path": str(path),
            "_start_idx": start_idx,
            "_end_idx": end_idx,
        }
    ], conflict_warnings
