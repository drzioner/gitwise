"""Injects AGENTS.md awareness, CLAUDE.md, settings.json, slash-commands, and initial snapshot."""

import json
import os
import platform
import re
import time
from pathlib import Path
from typing import Any, Literal

from .git import config as git_config
from .git import is_repo, repo_root
from .output import debug, error, info, ok, print_json, warn

_SHARE_DIR = Path(__file__).parent.parent / "share" / "claude"
_SKILLS: tuple[str, ...] = ("git-audit", "git-clean", "git-optimize")

_AGENTS_MD = "AGENTS.md"
_CLAUDE_MD = "CLAUDE.md"
_MARKER_RE = re.compile(
    r"^##\s+(Convenciones git para este proyecto|Git conventions for this project)\b",
    re.MULTILINE,
)
_POINTER_TEMPLATE = "## Convenciones git para este proyecto\n\n@AGENTS.md\n"
_GITIGNORE_MARKER_START = "# >>> gitwise managed (do not edit between markers) >>>"
_GITIGNORE_MARKER_END = "# <<< gitwise managed <<<"

_supports_symlinks_cache: dict[Path, bool] = {}


class SymlinkConflict(Exception):
    pass


class PlanExecutionError(Exception):
    pass


def _read_template(name: str) -> str:
    path = _SHARE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"template no encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _gpg_ready(root: Path) -> bool:
    import shutil

    if not (shutil.which("gpg") or shutil.which("gpg2")):
        return False
    return git_config("commit.gpgsign", cwd=root) == "true" and bool(
        git_config("user.signingkey", cwd=root)
    )


def _classify_path(p: Path) -> Literal["absent", "regular", "symlink_valid", "symlink_broken"]:
    if p.is_symlink():
        return "symlink_valid" if p.exists() else "symlink_broken"
    if p.exists():
        return "regular"
    return "absent"


def _supports_symlinks(root: Path) -> bool:
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
    try:
        text = p.read_text(encoding="utf-8")
        return bool(_MARKER_RE.search(text))
    except OSError:
        return False


def _files_equal(a: Path, b: Path) -> bool:
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
            warnings.append(f".claude/rules/{f.name}: symlink fuera del repo — ignorado")
            continue
        try:
            if f.stat().st_size > 64_000:
                warnings.append(f".claude/rules/{f.name}: archivo demasiado grande — no validado")
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
            warnings.append(
                f".claude/rules/{f.name}: falta 'globs:' en frontmatter — la regla no se activará"
            )
    return warnings


def _detect_state(root: Path) -> dict[str, Any]:
    agents_md = root / _AGENTS_MD
    claude_md = root / _CLAUDE_MD
    agents_dir = root / ".agents"
    skills_dir = root / ".claude" / "skills"

    a_state = _classify_path(agents_md)
    c_state = _classify_path(claude_md)
    errors: list[str] = []

    if a_state == "symlink_broken":
        errors.append(f"{_AGENTS_MD} es un symlink roto — arréglalo manualmente")
    if c_state == "symlink_broken":
        errors.append(f"{_CLAUDE_MD} es un symlink roto — arréglalo manualmente")

    skills_state = _classify_path(skills_dir)
    skills_target: str | None = None
    if skills_state == "symlink_valid":
        try:
            skills_target = os.readlink(skills_dir)
        except OSError:
            pass
    elif skills_state == "symlink_broken":
        errors.append(".claude/skills es un symlink roto — arréglalo manualmente")

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


def _safe_create_symlink(link: Path, target_relative: str, root: Path) -> None:
    """Creates a relative symlink safely: idempotency + sandbox + TOCTOU re-check."""
    if link.is_symlink():
        existing = os.readlink(link)
        if existing == target_relative:
            return  # already correct, no-op
        raise SymlinkConflict(
            f"{link.name} ya es symlink a '{existing}', se esperaba '{target_relative}'"
        )
    if link.exists():
        raise SymlinkConflict(
            f"{link.name} es un archivo regular — no se sobreescribirá automáticamente"
        )

    # Sandbox: target must not escape root (use realpath to resolve /var→/private/var etc.)
    root_real = Path(os.path.realpath(str(root)))
    target_real = Path(os.path.realpath(str(link.parent / target_relative)))
    if not target_real.is_relative_to(root_real):
        raise SymlinkConflict(f"Symlink target escapa del root del repositorio: {target_relative}")

    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target_relative, link)


def _undo_partial(actions_done: list[dict], root: Path) -> None:
    """Minimal rollback: revert symlinks created and restore .bak files."""
    for action in reversed(actions_done):
        act = action.get("action", "")
        file_key = action.get("file", "")
        path = root / file_key
        try:
            if act == "symlink-create" and path.is_symlink():
                path.unlink()
                debug(f"rollback: eliminado symlink {file_key}")
            elif act == "claude-md-replace-with-symlink":
                if path.is_symlink():
                    path.unlink()
                bak = action.get("backup_path")
                if bak and Path(bak).exists():
                    Path(bak).rename(path)
                    debug(f"rollback: restaurado {file_key} desde {Path(bak).name}")
            elif act == "skill-migrate-to-agents":
                moved_from = action.get("_moved_from")
                agents_skill_str = action.get("agents_skill")
                if path.is_symlink():
                    path.unlink()
                if moved_from and agents_skill_str and Path(agents_skill_str).exists():
                    import shutil

                    shutil.move(str(agents_skill_str), moved_from)
                    debug(f"rollback: restaurado {file_key} desde {agents_skill_str}")
            elif act in ("create",) and action.get("_created") and path.exists():
                path.unlink()
                debug(f"rollback: eliminado {file_key}")
        except OSError as e:
            debug(f"rollback falló para {file_key}: {e}")


# --- Managed block helpers ---


def _gitignore_block_basic() -> str:
    lines = [
        _GITIGNORE_MARKER_START,
        "# Claude Code local/personal files (do not commit)",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
        "# Snapshot regenerated each gitwise run (timestamps change)",
        ".claude/git-snapshot.md",
        "# Backups from gitwise setup-agents",
        "*.bak",
        "CLAUDE.md.bak*",
        _GITIGNORE_MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def _gitignore_block_extended(has_agents_md: bool) -> str:
    lines = [
        _GITIGNORE_MARKER_START,
        "# Claude Code local/personal files (do not commit)",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
        "# Snapshot regenerated each gitwise run (timestamps change)",
        ".claude/git-snapshot.md",
        "# Backups from gitwise setup-agents",
        "*.bak",
        "CLAUDE.md.bak*",
    ]
    if has_agents_md:
        lines.append("AGENTS.md.bak*")
    lines.append(_GITIGNORE_MARKER_END)
    return "\n".join(lines) + "\n"


def _gitattributes_block_basic() -> str:
    lines = [
        _GITIGNORE_MARKER_START,
        "# Generated snapshot: use local version on merge",
        ".claude/git-snapshot.md merge=ours linguist-generated=true",
        "# Convention files: force LF for cross-platform consistency",
        "CLAUDE.md text=auto eol=lf",
        ".claude/skills/**/SKILL.md text=auto eol=lf",
        _GITIGNORE_MARKER_END,
    ]
    return "\n".join(lines) + "\n"


def _gitattributes_block_extended(has_agents_md: bool, has_agents_dir: bool) -> str:
    lines = [
        _GITIGNORE_MARKER_START,
        "# Generated snapshot: use local version on merge",
        ".claude/git-snapshot.md merge=ours linguist-generated=true",
        "# Convention files: force LF for cross-platform consistency",
        "CLAUDE.md text=auto eol=lf",
    ]
    if has_agents_md:
        lines.append("AGENTS.md text=auto eol=lf")
    lines.append(".claude/skills/**/SKILL.md text=auto eol=lf")
    if has_agents_dir:
        lines.append(".agents/skills/**/SKILL.md text=auto eol=lf")
    lines.append(_GITIGNORE_MARKER_END)
    return "\n".join(lines) + "\n"


def _gitattributes_conflicts(existing_text: str, desired_block: str) -> list[str]:
    """Warns on .gitattributes entries outside the managed block that conflict
    (same path pattern, different attributes). Exact path-key match only —
    glob overlaps are not detected. Only scans content before the managed block."""
    block_start = existing_text.find(_GITIGNORE_MARKER_START)
    outside_text = existing_text[:block_start] if block_start != -1 else existing_text

    def _parse(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split(None, 1)
            if len(parts) > 1:  # skip bare paths with no attributes to compare
                result[parts[0]] = s
        return result

    outside = _parse(outside_text)
    block = _parse(desired_block)
    warnings: list[str] = []
    for pattern, block_line in block.items():
        if pattern in outside and outside[pattern] != block_line:
            warnings.append(
                f".gitattributes: '{pattern}' tiene regla existente '{outside[pattern]}' "
                f"que puede entrar en conflicto con la de gitwise '{block_line}'. "
                f"Elimina la línea fuera del bloque managed para evitar duplicados."
            )
    return warnings


def _plan_managed_block(
    path: Path, desired_block: str, file_key: str
) -> tuple[list[dict], list[str]]:
    """Returns (actions, warnings) for idempotent managed block in path."""
    if not path.exists():
        return [
            {
                "file": file_key,
                "action": "managed-block-create",
                "content": desired_block,
                "_path": str(path),
            }
        ], []

    current = path.read_text(encoding="utf-8")

    # .gitattributes: warn on semantic conflicts outside the block (fires on all paths)
    # .gitignore: duplicates are harmless — no warning needed
    conflict_warnings = (
        _gitattributes_conflicts(current, desired_block) if file_key == ".gitattributes" else []
    )

    if _GITIGNORE_MARKER_START not in current:
        return [
            {
                "file": file_key,
                "action": "managed-block-create",
                "content": desired_block,
                "_path": str(path),
                "_append": True,
            }
        ], conflict_warnings

    start_idx = current.index(_GITIGNORE_MARKER_START)
    end_marker_idx = current.find(_GITIGNORE_MARKER_END, start_idx)
    if end_marker_idx == -1:
        return [], [
            f"{file_key}: bloque managed sin marcador de cierre — se dejará intacto"
        ] + conflict_warnings

    end_idx = end_marker_idx + len(_GITIGNORE_MARKER_END)
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


# --- Sub-planners ---


def _plan_settings_json(root: Path) -> tuple[list[dict], list[str]]:
    settings_path = root / ".claude" / "settings.json"
    settings_template: dict = json.loads(_read_template("settings.json.template"))
    if settings_path.exists():
        try:
            existing_settings: dict = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [
                {"file": ".claude/settings.json", "action": "create", "data": settings_template}
            ], [".claude/settings.json existente tiene JSON inválido — se sobreescribirá"]
        existing_deny: list = existing_settings.get("permissions", {}).get("deny", [])
        new_deny: list = settings_template.get("permissions", {}).get("deny", [])
        merged_deny = list(dict.fromkeys(existing_deny + new_deny))
        existing_settings.setdefault("permissions", {})["deny"] = merged_deny
        gpg_rules = [r for r in merged_deny if "gpgsign" in r or "no-gpg-sign" in r]
        warnings: list[str] = []
        if not gpg_rules:
            warnings.append(
                "settings.json no tiene reglas deny para GPG bypass — revisar manualmente"
            )
        return [
            {"file": ".claude/settings.json", "action": "merge", "data": existing_settings}
        ], warnings
    return [{"file": ".claude/settings.json", "action": "create", "data": settings_template}], []


def _plan_skills(
    root: Path,
    state: dict,
    global_skills: frozenset[str] = frozenset(),
) -> tuple[list[dict], list[str]]:
    """Plans per-skill symlinks when .agents/ exists, or regular dirs otherwise.

    global_skills: set of skill names already installed in ~/.claude/skills/.
    Skills in this set are skipped with a warning (user > project priority).
    """
    actions: list[dict] = []
    warnings: list[str] = []

    agents_skills_dir = root / ".agents" / "skills"
    claude_skills = root / ".claude" / "skills"
    skills_state = state["skills_state"]
    has_agents_dir = state["agents_dir"]

    if skills_state == "symlink_valid":
        # .claude/skills is a whole-dir symlink — only manage SKILL.md files, no further symlinks
        for skill in _SKILLS:
            skill_file = f".claude/skills/{skill}/SKILL.md"
            if skill in global_skills:
                actions.append(
                    {"file": skill_file, "action": "skip", "reason": "instalado globalmente"}
                )
            elif (claude_skills / skill / "SKILL.md").exists():
                actions.append({"file": skill_file, "action": "skip", "reason": "ya existe"})
            else:
                actions.append(
                    {
                        "file": skill_file,
                        "action": "create",
                        "content": _read_template(f"skills/{skill}/SKILL.md"),
                    }
                )
    else:
        for skill in _SKILLS:
            claude_skill = claude_skills / skill
            skill_file = f".claude/skills/{skill}/SKILL.md"
            c_skill_state = _classify_path(claude_skill)

            if has_agents_dir:
                agents_skill = agents_skills_dir / skill
                # Relative path from .claude/skills/ to .agents/skills/<skill>
                target_rel = os.path.relpath(str(agents_skill), str(claude_skill.parent))

                if c_skill_state == "absent":
                    if skill in global_skills:
                        warnings.append(
                            f".claude/skills/{skill}: skill ya disponible globalmente "
                            f"(~/.claude/skills/) — se omite creación local (prioridad user > project)"
                        )
                    else:
                        if not agents_skill.exists():
                            actions.append({"file": f".agents/skills/{skill}", "action": "mkdir"})
                        actions.append(
                            {
                                "file": f".claude/skills/{skill}",
                                "action": "symlink-create",
                                "target_relative": target_rel,
                            }
                        )
                        actions.append(
                            {
                                "file": skill_file,
                                "action": "create",
                                "content": _read_template(f"skills/{skill}/SKILL.md"),
                            }
                        )
                elif c_skill_state == "symlink_valid":
                    try:
                        existing_target = os.readlink(str(claude_skill))
                    except OSError:
                        existing_target = ""
                    if existing_target == target_rel:
                        if (claude_skill / "SKILL.md").exists():
                            actions.append(
                                {"file": skill_file, "action": "skip", "reason": "ya existe"}
                            )
                        else:
                            actions.append(
                                {
                                    "file": skill_file,
                                    "action": "create",
                                    "content": _read_template(f"skills/{skill}/SKILL.md"),
                                }
                            )
                    else:
                        warnings.append(
                            f".claude/skills/{skill} es symlink a '{existing_target}', "
                            f"no a '{target_rel}' — se mantiene como está"
                        )
                elif c_skill_state == "symlink_broken":
                    warnings.append(
                        f".claude/skills/{skill} es un symlink roto — arréglalo manualmente"
                    )
                else:  # regular
                    warnings.append(
                        f".claude/skills/{skill} es un directorio regular aunque .agents/ existe — "
                        "gitwise escribe SKILL.md directamente"
                    )
                    if (claude_skill / "SKILL.md").exists():
                        actions.append(
                            {"file": skill_file, "action": "skip", "reason": "ya existe"}
                        )
                    else:
                        actions.append(
                            {
                                "file": skill_file,
                                "action": "create",
                                "content": _read_template(f"skills/{skill}/SKILL.md"),
                            }
                        )
            else:
                if skill in global_skills and not (claude_skill / "SKILL.md").exists():
                    warnings.append(
                        f".claude/skills/{skill}: skill ya disponible globalmente "
                        f"(~/.claude/skills/) — se omite creación local (prioridad user > project)"
                    )
                    actions.append(
                        {"file": skill_file, "action": "skip", "reason": "instalado globalmente"}
                    )
                elif (claude_skill / "SKILL.md").exists():
                    actions.append({"file": skill_file, "action": "skip", "reason": "ya existe"})
                else:
                    actions.append(
                        {
                            "file": skill_file,
                            "action": "create",
                            "content": _read_template(f"skills/{skill}/SKILL.md"),
                        }
                    )

    legacy_dir = root / ".claude" / "commands"
    for skill in _SKILLS:
        if (legacy_dir / f"{skill}.md").exists():
            warnings.append(
                f".claude/commands/{skill}.md es formato legacy — "
                f"ahora se usa .claude/skills/{skill}/SKILL.md. "
                f"Eliminá el .md viejo manualmente."
            )

    return actions, warnings


def _plan_rules(root: Path) -> tuple[list[dict], list[str]]:
    """Plans gitwise rule file in .claude/rules/."""
    rule_path = root / ".claude" / "rules" / "gitwise.md"
    if rule_path.exists():
        return [{"file": ".claude/rules/gitwise.md", "action": "skip", "reason": "ya existe"}], []
    return [
        {
            "file": ".claude/rules/gitwise.md",
            "action": "create",
            "content": _read_template("rules/gitwise.md"),
        }
    ], []


def _plan_global_skills(home: Path) -> tuple[list[dict], list[str]]:
    """Plans skills for ~/.claude/skills/. Mirrors local per-skill symlink logic when ~/.agents/ exists."""
    actions: list[dict] = []
    warnings: list[str] = []

    agents_dir = home / ".agents"
    has_agents_dir = agents_dir.is_dir() and not agents_dir.is_symlink()
    agents_skills_dir = home / ".agents" / "skills"
    claude_skills = home / ".claude" / "skills"
    claude_skills_state = _classify_path(claude_skills)

    if claude_skills_state == "symlink_valid":
        # Whole-dir symlink — only manage SKILL.md files
        for skill in _SKILLS:
            skill_file = f".claude/skills/{skill}/SKILL.md"
            if (claude_skills / skill / "SKILL.md").exists():
                actions.append({"file": skill_file, "action": "skip", "reason": "ya existe"})
            else:
                actions.append(
                    {
                        "file": skill_file,
                        "action": "create",
                        "content": _read_template(f"skills/{skill}/SKILL.md"),
                    }
                )
    else:
        for skill in _SKILLS:
            claude_skill = claude_skills / skill
            skill_file = f".claude/skills/{skill}/SKILL.md"
            c_skill_state = _classify_path(claude_skill)

            if has_agents_dir:
                agents_skill = agents_skills_dir / skill
                target_rel = os.path.relpath(str(agents_skill), str(claude_skill.parent))

                if c_skill_state == "absent":
                    if not agents_skill.exists():
                        actions.append({"file": f".agents/skills/{skill}", "action": "mkdir"})
                    actions.append(
                        {
                            "file": f".claude/skills/{skill}",
                            "action": "symlink-create",
                            "target_relative": target_rel,
                        }
                    )
                    actions.append(
                        {
                            "file": skill_file,
                            "action": "create",
                            "content": _read_template(f"skills/{skill}/SKILL.md"),
                        }
                    )
                elif c_skill_state == "symlink_valid":
                    try:
                        existing_target = os.readlink(str(claude_skill))
                    except OSError:
                        existing_target = ""
                    if existing_target == target_rel:
                        if (claude_skill / "SKILL.md").exists():
                            actions.append(
                                {"file": skill_file, "action": "skip", "reason": "ya existe"}
                            )
                        else:
                            actions.append(
                                {
                                    "file": skill_file,
                                    "action": "create",
                                    "content": _read_template(f"skills/{skill}/SKILL.md"),
                                }
                            )
                    else:
                        warnings.append(
                            f"~/.claude/skills/{skill} es symlink a '{existing_target}', "
                            f"no a '{target_rel}' — se mantiene como está"
                        )
                elif c_skill_state == "symlink_broken":
                    warnings.append(
                        f"~/.claude/skills/{skill} es un symlink roto — arréglalo manualmente"
                    )
                else:  # regular dir — auto-migrate to .agents/ since ~/.agents/ is present
                    if agents_skill.exists():
                        # Target already exists; skip with warning
                        warnings.append(
                            f"~/.claude/skills/{skill} es dir regular y ~/.agents/skills/{skill} "
                            f"también existe — sin cambios. Consolida manualmente."
                        )
                        actions.append(
                            {
                                "file": skill_file,
                                "action": "skip",
                                "reason": "conflicto dir/agents",
                            }
                        )
                    else:
                        # Move existing dir to .agents/skills/ and create symlink
                        actions.append(
                            {
                                "file": f".claude/skills/{skill}",
                                "action": "skill-migrate-to-agents",
                                "target_relative": target_rel,
                                "agents_skill": str(agents_skill),
                            }
                        )
            else:
                if (claude_skill / "SKILL.md").exists():
                    actions.append({"file": skill_file, "action": "skip", "reason": "ya existe"})
                else:
                    actions.append(
                        {
                            "file": skill_file,
                            "action": "create",
                            "content": _read_template(f"skills/{skill}/SKILL.md"),
                        }
                    )

    return actions, warnings


def _plan_actions_global(
    home: Path,
    no_skills: bool = False,
) -> tuple[list[dict], list[str], list[dict]]:
    """Plans ~/.claude/ global artifacts. home = Path.home(). No git repo required."""
    actions: list[dict] = []
    warnings: list[str] = []

    s_actions, s_warnings = _plan_settings_json(home)
    actions += s_actions
    warnings += s_warnings

    r_actions, r_warnings = _plan_rules(home)
    actions += r_actions
    warnings += r_warnings

    if not no_skills:
        sk_actions, sk_warnings = _plan_global_skills(home)
        actions += sk_actions
        warnings += sk_warnings

    return actions, warnings, []


def _run_setup_global(
    home: Path,
    *,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    no_skills: bool = False,
) -> int:
    """Installs global Claude Code artifacts to ~/.claude/. No git repo required."""
    try:
        actions, warnings, _ = _plan_actions_global(home, no_skills=no_skills)
    except FileNotFoundError as e:
        error(str(e))
        return 1

    if as_json:
        summary: dict[str, int] = {
            "created": 0,
            "appended": 0,
            "symlinked": 0,
            "skipped": 0,
            "errored": 0,
        }
        for a in actions:
            match a["action"]:
                case "create" | "managed-block-create":
                    summary["created"] += 1
                case "append":
                    summary["appended"] += 1
                case "symlink-create":
                    summary["symlinked"] += 1
                case "skip" | "symlink-skip" | "managed-block-skip":
                    summary["skipped"] += 1
        print_json(
            {
                "v": 2,
                "v_compat": [1, 2],
                "dry_run": dry_run,
                "root": str(home / ".claude"),
                "mode": "global",
                "actions": [{"file": a["file"], "action": a["action"]} for a in actions],
                "warnings": warnings,
                "errors": [],
                "summary": summary,
                "ok": True,
            }
        )
        return 0

    info(f"configurando agentes globalmente en: {home / '.claude'}")
    info("")

    for w in warnings:
        warn(w)
    if warnings:
        info("")

    if dry_run:
        info("modo dry-run — no se escribirá nada:")
        info("")
        for a in actions:
            verb = a["action"].upper()
            reason = f" ({a['reason']})" if "reason" in a else ""
            info(f"  [{verb}] {a['file']}{reason}")
        return 0

    if not yes:
        info("acciones a realizar:")
        for a in actions:
            if a["action"] not in ("skip", "symlink-skip", "managed-block-skip"):
                info(f"  [{a['action'].upper()}] {a['file']}")
        info("")
        try:
            resp = input("¿continuar? [s/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = ""
        if resp not in ("s", "si", "sí", "y", "yes"):
            info("cancelado.")
            return 0
        info("")

    try:
        _execute_actions(home, actions)
    except PlanExecutionError as e:
        error(f"setup-agents (global) falló: {e}")
        return 1

    info("")
    ok("setup-agents global completado")
    return 0


def _compute_backup_path(path: Path) -> Path:
    backup = path.with_suffix(".md.bak")
    if backup.exists():
        backup = path.parent / f"{path.stem}.md.bak.{int(time.time())}"
    return backup


def _resolve_canonical_doc(
    root: Path,
    state: dict,
    no_symlinks: bool = False,
    replace_claude_with_symlink: bool = False,
) -> tuple[int, list[dict], list[str]]:
    """Returns (bucket, actions, warnings) per the 5-bucket model."""
    a_state = state["a_state"]
    c_state = state["c_state"]
    agents_md = root / _AGENTS_MD
    claude_md = root / _CLAUDE_MD
    supports_symlinks = state["supports_symlinks"] and not no_symlinks

    gpg = _gpg_ready(root)

    def _template() -> str:
        raw = _read_template("CLAUDE.md.template")
        if gpg:
            return raw
        return (
            "\n".join(
                line
                for line in raw.splitlines()
                if "GPG" not in line and "gpg-sign" not in line.lower()
            )
            + "\n"
        )

    # Bucket 1: no AGENTS.md → current behavior
    if a_state == "absent":
        content = _template()
        if c_state == "absent":
            return 1, [{"file": _CLAUDE_MD, "action": "create", "content": content}], []
        if c_state in ("symlink_valid", "regular"):
            if _has_marker(claude_md):
                return (
                    1,
                    [
                        {
                            "file": _CLAUDE_MD,
                            "action": "skip",
                            "reason": "ya contiene convenciones git",
                        }
                    ],
                    [],
                )
            return 1, [{"file": _CLAUDE_MD, "action": "append", "content": content}], []
        return 1, [], []  # symlink_broken caught by _detect_state → bucket 5

    # AGENTS.md exists — ensure it has the marker first
    agents_actions: list[dict] = []
    if not _has_marker(agents_md):
        agents_actions.append({"file": _AGENTS_MD, "action": "append", "content": _template()})

    if c_state == "absent":
        # Bucket 2: AGENTS.md present, CLAUDE.md absent → create pointer
        if supports_symlinks:
            claude_actions: list[dict] = [
                {"file": _CLAUDE_MD, "action": "symlink-create", "target_relative": _AGENTS_MD}
            ]
        else:
            claude_actions = [
                {"file": _CLAUDE_MD, "action": "create", "content": _POINTER_TEMPLATE}
            ]
        return 2, agents_actions + claude_actions, []

    if c_state == "symlink_valid":
        try:
            link_target = os.readlink(claude_md)
        except OSError:
            link_target = ""
        # Check if it already points to AGENTS.md (by string or resolved path)
        points_to_agents = (
            link_target == _AGENTS_MD
            or (claude_md.parent / link_target).resolve() == agents_md.resolve()
        )
        if points_to_agents:
            # Bucket 3: idempotent
            return (
                3,
                agents_actions
                + [
                    {
                        "file": _CLAUDE_MD,
                        "action": "symlink-skip",
                        "reason": "ya apunta a AGENTS.md",
                    }
                ],
                [],
            )
        # Points somewhere else — treat as bucket 4 conflict
        return (
            4,
            agents_actions,
            [
                f"{_CLAUDE_MD} es symlink a '{link_target}', no a '{_AGENTS_MD}'. "
                f"Revisa manualmente. Para reemplazar: "
                f"`gitwise setup-agents --replace-claude-with-symlink`"
            ],
        )

    if c_state == "regular":
        if replace_claude_with_symlink:
            backup_path = _compute_backup_path(claude_md)
            return (
                4,
                agents_actions
                + [
                    {
                        "file": _CLAUDE_MD,
                        "action": "claude-md-replace-with-symlink",
                        "target_relative": _AGENTS_MD,
                        "backup_path": str(backup_path),
                    }
                ],
                [
                    f"{_CLAUDE_MD} reemplazado por symlink a {_AGENTS_MD} (backup: {backup_path.name})"
                ],
            )

        if _files_equal(claude_md, agents_md):
            return (
                3,
                agents_actions
                + [
                    {
                        "file": _CLAUDE_MD,
                        "action": "skip",
                        "reason": "contenido idéntico a AGENTS.md",
                    }
                ],
                [],
            )

        # Bucket 4: distinct regular files → warning, no overwrite
        return (
            4,
            agents_actions,
            [
                f"{_CLAUDE_MD} y {_AGENTS_MD} son archivos separados con contenido distinto. "
                f"Para unificar: revisa `diff {_CLAUDE_MD} {_AGENTS_MD}`, mueve contenido relevante "
                f"manualmente, luego ejecuta `gitwise setup-agents --replace-claude-with-symlink`."
            ],
        )

    # symlink_broken already caught by _detect_state → bucket 5
    return 5, [], []


def _plan_actions(
    root: Path,
    no_symlinks: bool = False,
    replace_claude_with_symlink: bool = False,
    no_git_files: bool = False,
    frozen_time: bool = False,
) -> tuple[list[dict], list[str], list[dict], int, dict]:
    """Returns (actions, warnings, errors, bucket, state). Non-empty errors blocks execution."""
    state = _detect_state(root)
    if state["errors"]:
        err_actions = [{"file": "", "action": "error", "reason": r} for r in state["errors"]]
        return [], [], err_actions, 5, state

    bucket, doc_actions, doc_warnings = _resolve_canonical_doc(
        root,
        state,
        no_symlinks=no_symlinks,
        replace_claude_with_symlink=replace_claude_with_symlink,
    )
    settings_actions, settings_warnings = _plan_settings_json(root)
    home = Path.home()
    global_skills = frozenset(
        s for s in _SKILLS if (home / ".claude" / "skills" / s / "SKILL.md").exists()
    )
    skills_actions, skills_warnings = _plan_skills(root, state, global_skills=global_skills)
    rules_actions, rules_warnings = _plan_rules(root)

    has_agents_md = state["a_state"] != "absent"
    has_agents_dir = state["agents_dir"]

    git_file_actions: list[dict] = []
    git_file_warnings: list[str] = []
    if not no_git_files and bucket != 5:
        if has_agents_md or has_agents_dir:
            gi_block = _gitignore_block_extended(has_agents_md)
            ga_block = _gitattributes_block_extended(has_agents_md, has_agents_dir)
        else:
            gi_block = _gitignore_block_basic()
            ga_block = _gitattributes_block_basic()

        gi_actions, gi_warnings = _plan_managed_block(root / ".gitignore", gi_block, ".gitignore")
        ga_actions, ga_warnings = _plan_managed_block(
            root / ".gitattributes", ga_block, ".gitattributes"
        )
        git_file_actions = gi_actions + ga_actions
        git_file_warnings = gi_warnings + ga_warnings

    actions = (
        doc_actions
        + settings_actions
        + skills_actions
        + rules_actions
        + git_file_actions
        + [{"file": ".claude/git-snapshot.md", "action": "generate", "frozen_time": frozen_time}]
    )
    warnings = (
        doc_warnings
        + settings_warnings
        + skills_warnings
        + rules_warnings
        + git_file_warnings
        + state["rules_warnings"]
    )
    return actions, warnings, [], bucket, state


def _apply_managed_block(action: dict) -> None:
    path = Path(action["_path"])
    desired = action["content"]
    act = action["action"]

    if act == "managed-block-create":
        if not path.exists() or not action.get("_append"):
            path.write_text(desired, encoding="utf-8")
        else:
            current = path.read_text(encoding="utf-8")
            sep = "\n" if current.endswith("\n") else "\n\n"
            path.write_text(current + sep + desired, encoding="utf-8")
    elif act == "managed-block-replace":
        current = path.read_text(encoding="utf-8")
        start_idx = action["_start_idx"]
        end_idx = action["_end_idx"]
        new_content = current[:start_idx] + desired.rstrip("\n") + current[end_idx:]
        path.write_text(new_content, encoding="utf-8")


def _execute_actions(root: Path, actions: list[dict[str, Any]]) -> None:
    (root / ".claude").mkdir(parents=True, exist_ok=True)

    actions_done: list[dict] = []
    try:
        for action in actions:
            file_key: str = action["file"]
            act: str = action["action"]

            if act in ("skip", "symlink-skip", "managed-block-skip"):
                debug(f"skip: {file_key}")
                actions_done.append(action)
                continue

            if file_key == _CLAUDE_MD:
                path = root / _CLAUDE_MD
                if act == "create":
                    path.write_text(action["content"], encoding="utf-8")
                    action["_created"] = True
                    ok(f"creado: {_CLAUDE_MD}")
                elif act == "append":
                    existing = path.read_text(encoding="utf-8")
                    sep = "\n" if existing.endswith("\n") else "\n\n"
                    path.write_text(existing + sep + action["content"], encoding="utf-8")
                    ok(f"actualizado: {_CLAUDE_MD} (convenciones git agregadas)")
                elif act == "symlink-create":
                    _safe_create_symlink(path, action["target_relative"], root)
                    ok(f"symlink: {_CLAUDE_MD} → {action['target_relative']}")
                elif act == "claude-md-replace-with-symlink":
                    backup = Path(action["backup_path"])
                    path.rename(backup)
                    _safe_create_symlink(path, action["target_relative"], root)
                    ok(f"reemplazado: {_CLAUDE_MD} (backup: {backup.name})")

            elif file_key == _AGENTS_MD:
                path = root / _AGENTS_MD
                if act == "append":
                    existing = path.read_text(encoding="utf-8")
                    sep = "\n" if existing.endswith("\n") else "\n\n"
                    path.write_text(existing + sep + action["content"], encoding="utf-8")
                    ok(f"actualizado: {_AGENTS_MD} (convenciones git agregadas)")

            elif file_key == ".claude/settings.json":
                path = root / ".claude" / "settings.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(action["data"], ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                verb = "creado" if act == "create" else "actualizado (deny rules merged)"
                ok(f"{verb}: .claude/settings.json")

            elif file_key == ".claude/skills":
                if act == "symlink-create":
                    # Whole-dir symlink (legacy path — kept for backward compat)
                    target_dir = Path(
                        os.path.normpath(root / ".claude" / action["target_relative"])
                    )
                    target_dir.mkdir(parents=True, exist_ok=True)
                    _safe_create_symlink(
                        root / ".claude" / "skills", action["target_relative"], root
                    )
                    ok(f"symlink: .claude/skills → {action['target_relative']}")

            elif file_key.startswith(".agents/skills/") and file_key.count("/") == 2:
                if act == "mkdir":
                    (root / file_key).mkdir(parents=True, exist_ok=True)
                    debug(f"mkdir: {file_key}")

            elif file_key.startswith(".claude/skills/") and file_key.count("/") == 2:
                if act == "symlink-create":
                    skill_link = root / file_key
                    skill_link.parent.mkdir(parents=True, exist_ok=True)
                    _safe_create_symlink(skill_link, action["target_relative"], root)
                    ok(f"symlink: {file_key} → {action['target_relative']}")
                elif act == "skill-migrate-to-agents":
                    import shutil

                    skill_link = root / file_key
                    agents_skill = Path(action["agents_skill"])
                    agents_skill.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(skill_link), str(agents_skill))
                    action["_moved_from"] = str(skill_link)
                    _safe_create_symlink(skill_link, action["target_relative"], root)
                    ok(f"migrado: {file_key} → {action['target_relative']} (symlink)")

            elif file_key.startswith(".claude/skills/") and file_key.endswith("/SKILL.md"):
                rel = Path(file_key).relative_to(".claude")
                target = root / ".claude" / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                # write_text follows symlinks (handles cortex-api pattern)
                target.write_text(action["content"], encoding="utf-8")
                ok(f"creado: {file_key}")

            elif file_key.startswith(".claude/rules/") and file_key.endswith(".md"):
                path = root / file_key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(action["content"], encoding="utf-8")
                action["_created"] = True
                ok(f"creado: {file_key}")

            elif file_key == ".claude/git-snapshot.md":
                from .snapshot import generate_snapshot as _gen_snapshot

                _gen_snapshot(root, frozen_time=action.get("frozen_time", False))
                ok("generado: .claude/git-snapshot.md")

            elif act in ("managed-block-create", "managed-block-replace"):
                _apply_managed_block(action)
                verb = "creado" if act == "managed-block-create" else "actualizado"
                ok(f"{verb} bloque managed: {file_key}")

            else:
                warn(f"acción desconocida: {act} en {file_key}")

            actions_done.append(action)

    except (SymlinkConflict, OSError) as exc:
        warn(f"acción falló: {exc} — revirtiendo {len(actions_done)} acciones previas")
        _undo_partial(actions_done, root)
        raise PlanExecutionError(str(exc))


def _run_setup_local(
    target: Path | None = None,
    *,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    no_symlinks: bool = False,
    strict: bool = False,
    replace_claude_with_symlink: bool = False,
    frozen_time: bool = False,
    no_git_files: bool = False,
) -> int:
    cwd = target or Path.cwd()

    if not is_repo(cwd):
        error("no es un repositorio git")
        return 1

    root = repo_root(cwd)
    if root is None:
        error("no se pudo determinar la raíz del repositorio")
        return 1

    gpgsign = git_config("commit.gpgsign", cwd=root)
    gpg_warnings: list[str] = []
    if gpgsign == "true":
        signing_key = git_config("user.signingkey", cwd=root)
        if not signing_key:
            gpg_warnings.append(
                "GPG signing activo pero sin user.signingkey — ejecuta: git config user.signingkey <id>"
            )

    try:
        actions, warnings, plan_errors, bucket, state = _plan_actions(
            root,
            no_symlinks=no_symlinks,
            replace_claude_with_symlink=replace_claude_with_symlink,
            no_git_files=no_git_files,
            frozen_time=frozen_time,
        )
    except FileNotFoundError as e:
        error(str(e))
        return 1

    has_errors = bool(plan_errors)
    all_warnings = gpg_warnings + warnings

    has_agents_md = state.get("a_state", "absent") != "absent"
    has_agents_dir = state.get("agents_dir", False)
    supports_symlinks = state.get("supports_symlinks", False)

    if as_json:
        if has_errors:
            print_json(
                {
                    "v": 2,
                    "v_compat": [1, 2],
                    "dry_run": dry_run,
                    "root": str(root),
                    "bucket": 5,
                    "agents_md_detected": False,
                    "agents_dir_detected": False,
                    "supports_symlinks": False,
                    "actions": [],
                    "warnings": all_warnings,
                    "rules_warnings": [],
                    "errors": [e["reason"] for e in plan_errors],
                    "summary": {
                        "created": 0,
                        "appended": 0,
                        "symlinked": 0,
                        "skipped": 0,
                        "errored": len(plan_errors),
                    },
                    "ok": False,
                }
            )
            return 1

        summary: dict[str, int] = {
            "created": 0,
            "appended": 0,
            "symlinked": 0,
            "skipped": 0,
            "errored": 0,
        }
        for a in actions:
            match a["action"]:
                case "create" | "managed-block-create":
                    summary["created"] += 1
                case "append":
                    summary["appended"] += 1
                case "symlink-create":
                    summary["symlinked"] += 1
                case "skip" | "symlink-skip" | "managed-block-skip":
                    summary["skipped"] += 1

        print_json(
            {
                "v": 2,
                "v_compat": [1, 2],
                "dry_run": dry_run,
                "root": str(root),
                "bucket": bucket,
                "agents_md_detected": has_agents_md,
                "agents_dir_detected": has_agents_dir,
                "supports_symlinks": supports_symlinks,
                "actions": [{"file": a["file"], "action": a["action"]} for a in actions],
                "warnings": all_warnings,
                "rules_warnings": state.get("rules_warnings", []),
                "errors": [],
                "summary": summary,
                "ok": True,
            }
        )
        return 0

    if has_errors:
        for e in plan_errors:
            error(e["reason"])
        return 1

    info(f"configurando agentes en: {root}")
    info("")

    for w in all_warnings:
        warn(w)

    if all_warnings and strict:
        error("--strict: warnings tratados como errores")
        return 2

    if all_warnings:
        info("")

    if dry_run:
        info("modo dry-run — no se escribirá nada:")
        info("")
        for a in actions:
            verb = a["action"].upper()
            reason = f" ({a['reason']})" if "reason" in a else ""
            info(f"  [{verb}] {a['file']}{reason}")
        return 0

    if not yes:
        info("acciones a realizar:")
        for a in actions:
            if a["action"] not in ("skip", "symlink-skip", "managed-block-skip"):
                info(f"  [{a['action'].upper()}] {a['file']}")
        info("")
        try:
            resp = input("¿continuar? [s/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = ""
        if resp not in ("s", "si", "sí", "y", "yes"):
            info("cancelado.")
            return 0
        info("")

    try:
        _execute_actions(root, actions)
    except PlanExecutionError as e:
        error(f"setup-agents falló: {e}")
        return 1

    skills_skipped = sum(
        1
        for a in actions
        if a.get("action") == "skip"
        and a.get("file", "").startswith(".claude/skills/")
        and a.get("file", "").endswith("/SKILL.md")
    )
    if skills_skipped == len(_SKILLS):
        ok(f"skills ({len(_SKILLS)}): ya configurados")

    info("")
    ok("setup-agents completado")

    if strict and all_warnings:
        return 2

    return 0


def run_setup_agents(
    target: Path | None = None,
    *,
    local: bool = False,
    no_skills: bool = False,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
    no_symlinks: bool = False,
    strict: bool = False,
    replace_claude_with_symlink: bool = False,
    frozen_time: bool = False,
    no_git_files: bool = False,
) -> int:
    """Dispatcher: global mode (default) or per-repo mode (--local)."""
    if local:
        return _run_setup_local(
            target,
            dry_run=dry_run,
            yes=yes,
            as_json=as_json,
            no_symlinks=no_symlinks,
            strict=strict,
            replace_claude_with_symlink=replace_claude_with_symlink,
            frozen_time=frozen_time,
            no_git_files=no_git_files,
        )
    return _run_setup_global(
        Path.home(),
        dry_run=dry_run,
        yes=yes,
        as_json=as_json,
        no_skills=no_skills,
    )
