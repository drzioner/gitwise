"""Zero-dependency i18n: es/en string catalog with auto locale detection."""

import os
from typing import Literal

Locale = Literal["es", "en"]
OutputMode = Literal["human", "agent"]

_CACHE: dict[str, str] = {}


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


_STRINGS: dict[str, dict[Locale, str]] = {
    "advertencia": {"es": "advertencia", "en": "warning"},
    "error": {"es": "error", "en": "error"},
    "ok_prefix": {"es": "✓", "en": "✓"},
    "cancelado": {"es": "cancelado.", "en": "cancelled."},
    "no_repo": {"es": "no es un repositorio git", "en": "not a git repository"},
    "no_root": {
        "es": "no se pudo determinar la raíz del repositorio",
        "en": "could not determine repository root",
    },
    "dry_run_nothing": {
        "es": "modo dry-run — no se escribirá nada:",
        "en": "dry-run mode — nothing will be written:",
    },
    "dry_run_no_exec": {
        "es": "modo dry-run — no se ejecutará nada",
        "en": "dry-run mode — nothing will be executed",
    },
    "dry_run_no_delete": {
        "es": "modo dry-run — no se eliminará nada",
        "en": "dry-run mode — nothing will be deleted",
    },
    "dry_run_no_clean": {
        "es": "modo dry-run — no se limpiará nada",
        "en": "dry-run mode — nothing will be cleaned",
    },
    "acciones_realizar": {"es": "acciones a realizar:", "en": "actions to perform:"},
    "continuar": {"es": "¿continuar? [s/N] ", "en": "continue? [y/N] "},
    "completado_en": {"es": "completado en {elapsed}s", "en": "completed in {elapsed}s"},
    "setup_completado": {"es": "setup completado", "en": "setup complete"},
    "config_actualizada": {
        "es": "configuración de git ya está actualizada",
        "en": "git config is already up to date",
    },
    "cambios_planificados": {
        "es": "cambios planificados ({count}):",
        "en": "planned changes ({count}):",
    },
    "no_configurado": {"es": " (no configurado)", "en": " (not configured)"},
    "actual": {"es": " (actual: {current})", "en": " (current: {current})"},
    "confirm_setup": {"es": "¿aplicar estos cambios? [s/N] ", "en": "apply these changes? [y/N] "},
    "config_fallo": {
        "es": "config {name}: falló (continuando)",
        "en": "config {name}: failed (continuing)",
    },
    "setup_agents_completado": {
        "es": "setup-agents completado",
        "en": "setup-agents complete",
    },
    "setup_agents_global_completado": {
        "es": "setup-agents global completado",
        "en": "setup-agents global complete",
    },
    "config_agentes_en": {
        "es": "configurando agentes en: {root}",
        "en": "configuring agents in: {root}",
    },
    "config_agentes_global": {
        "es": "configurando agentes globalmente en: {path}",
        "en": "configuring agents globally in: {path}",
    },
    "config_agentes_actualizado": {
        "es": "actualizado: {file} (convenciones git agregadas)",
        "en": "updated: {file} (git conventions added)",
    },
    "creado": {"es": "creado: {file}", "en": "created: {file}"},
    "symlink": {"es": "symlink: {file} → {target}", "en": "symlink: {file} → {target}"},
    "reemplazado": {
        "es": "reemplazado: {file} (backup: {backup})",
        "en": "replaced: {file} (backup: {backup})",
    },
    "ya_contiene": {
        "es": "ya contiene convenciones git",
        "en": "already contains git conventions",
    },
    "ya_existe": {"es": "ya existe", "en": "already exists"},
    "instalado_globalmente": {"es": "instalado globalmente", "en": "installed globally"},
    "setup_agents_fallo": {
        "es": "setup-agents falló: {error}",
        "en": "setup-agents failed: {error}",
    },
    "setup_agents_global_fallo": {
        "es": "setup-agents (global) falló: {error}",
        "en": "setup-agents (global) failed: {error}",
    },
    "strict_warnings": {
        "es": "--strict: warnings tratados como errores",
        "en": "--strict: warnings treated as errors",
    },
    "actualizando_desde": {
        "es": "actualizando desde {dir}...",
        "en": "updating from {dir}...",
    },
    "error_actualizar": {"es": "error al actualizar", "en": "error updating"},
    "repo_buen_estado": {
        "es": "repositorio en buen estado{suffix}",
        "en": "repository in good shape{suffix}",
    },
    "diagnostico": {
        "es": "Diagnóstico{suffix} — {count} observación(es):",
        "en": "Diagnostic{suffix} — {count} finding(s):",
    },
    "fix_label": {"es": "fix", "en": "fix"},
    "ignora_label": {"es": "ignora", "en": "ignore"},
    "herramientas_opcionales": {
        "es": "herramientas opcionales:",
        "en": "optional tools:",
    },
    "gpg_titulo": {"es": "GPG (firma de commits):", "en": "GPG (commit signing):"},
    "gpg_listo": {
        "es": "  GPG listo — commit.gpgsign=true, llave y binario configurados",
        "en": "  GPG ready — commit.gpgsign=true, key and binary configured",
    },
    "gpg_no_instalado": {
        "es": "  gpg no instalado — commits no se firmarán",
        "en": "  gpg not installed — commits won't be signed",
    },
    "gpg_no_activado": {
        "es": "  gpg instalado pero commit.gpgsign no activado",
        "en": "  gpg installed but commit.gpgsign not enabled",
    },
    "gpg_no_key": {
        "es": "  commit.gpgsign=true pero user.signingkey no configurado",
        "en": "  commit.gpgsign=true but user.signingkey not configured",
    },
    "git_demasiado_antiguo": {
        "es": "git {ver} demasiado antiguo — se requiere ≥ {min}",
        "en": "git {ver} too old — ≥ {min} required",
    },
    "python_demasiado_antiguo": {
        "es": "Python {ver} demasiado antiguo — se requiere ≥ 3.9",
        "en": "Python {ver} too old — ≥ 3.9 required",
    },
    "fsmonitor_no_soportado": {
        "es": "fsmonitor integrado no está soportado en Linux (solo macOS y Windows)",
        "en": "built-in fsmonitor not supported on Linux (macOS and Windows only)",
    },
    "clean_refs_no_impl": {
        "es": "'clean --refs' no está implementado",
        "en": "'clean --refs' is not implemented",
    },
    "clean_especifica": {
        "es": "especifica --branches  (o --refs)",
        "en": "specify --branches  (or --refs)",
    },
    "no_ramas_stale": {
        "es": "no hay ramas stale ([gone])",
        "en": "no stale branches ([gone])",
    },
    "ramas_protegidas": {
        "es": "ramas stale protegidas ({count}) — no se tocarán:",
        "en": "protected stale branches ({count}) — won't be touched:",
    },
    "ramas_a_eliminar": {
        "es": "ramas stale a eliminar ({count}):",
        "en": "stale branches to delete ({count}):",
    },
    "clean_para_eliminar": {
        "es": "para eliminar: gitwise clean --branches --yes",
        "en": "to delete: gitwise clean --branches --yes",
    },
    "confirm_eliminar": {
        "es": "¿eliminar {count} rama(s)? [s/N] ",
        "en": "delete {count} branch(es)? [y/N] ",
    },
    "eliminada": {"es": "eliminada: {branch}", "en": "deleted: {branch}"},
    "no_se_pudo_eliminar": {
        "es": "no se pudo eliminar: {branch}  ({error})",
        "en": "could not delete: {branch}  ({error})",
    },
    "eliminadas_count": {
        "es": "eliminadas {count} rama(s) stale",
        "en": "deleted {count} stale branch(es)",
    },
    "no_ramas_eliminables": {
        "es": "no hay ramas eliminables",
        "en": "no branches to delete",
    },
    "protegida": {"es": "protegida (lista por defecto)", "en": "protected (default list)"},
    "rama_actual": {"es": "rama actual (checked out)", "en": "current branch (checked out)"},
    "activa_worktree": {"es": "activa en un worktree", "en": "active in a worktree"},
    "gc_en_ejecucion": {
        "es": "git gc/maintenance ya está en ejecución — esperá a que termine",
        "en": "git gc/maintenance already running — wait for it to finish",
    },
    "optimizando": {"es": "optimizando: {root}", "en": "optimizing: {root}"},
    "commit_graph_actualizado": {
        "es": "commit-graph actualizado",
        "en": "commit-graph updated",
    },
    "commit_graph_fallo": {
        "es": "commit-graph: falló (repo puede estar vacío)",
        "en": "commit-graph: failed (repo may be empty)",
    },
    "repack_completado": {"es": "repack completado", "en": "repack complete"},
    "repack_fallo": {"es": "repack: falló", "en": "repack: failed"},
    "prune_completado": {"es": "prune completado", "en": "prune complete"},
    "prune_no_critico": {
        "es": "prune: no crítico, continuando",
        "en": "prune: not critical, continuing",
    },
    "espacio_liberado": {
        "es": "espacio liberado: {saved}KB  ({before}KB → {after}KB)",
        "en": "space freed: {saved}KB  ({before}KB → {after}KB)",
    },
    "tamano_repo": {"es": "tamaño del repo: {size}KB", "en": "repo size: {size}KB"},
    "confirm_optimizar": {
        "es": "¿ejecutar optimizaciones? [s/N] ",
        "en": "run optimizations? [y/N] ",
    },
    "rama": {"es": "rama: {branch}", "en": "branch: {branch}"},
    "estado_archivos": {
        "es": "estado ({count} archivos modificados):",
        "en": "status ({count} modified files):",
    },
    "working_tree_limpio": {"es": "working tree limpio", "en": "working tree clean"},
    "ultimos_commits": {"es": "últimos {count} commits:", "en": "last {count} commits:"},
    "sin_commits": {"es": "sin commits aún", "en": "no commits yet"},
    "diff_prefix": {"es": "diff: {stat}", "en": "diff: {stat}"},
    "output_superior_8kb": {
        "es": "output {size} bytes supera 8KB — usa --max-commits menor",
        "en": "output {size} bytes exceeds 8KB — use smaller --max-commits",
    },
    "no_uncommitted_changes": {
        "es": "no uncommitted changes",
        "en": "no uncommitted changes",
    },
    "changed_files": {"es": "changed files: ({count})", "en": "changed files: ({count})"},
    "nothing_staged": {"es": "nothing staged", "en": "nothing staged"},
    "tip_staged": {
        "es": "no uncommitted changes  (tip: --staged for staged files)",
        "en": "no uncommitted changes  (tip: --staged for staged files)",
    },
    "snapshot_generado": {
        "es": "snapshot generado: {path}",
        "en": "snapshot generated: {path}",
    },
    "seccion_rama_actual": {"es": "## Rama actual", "en": "## Current branch"},
    "seccion_estado": {"es": "## Estado", "en": "## Status"},
    "seccion_ultimos_commits": {
        "es": "## Últimos 10 commits",
        "en": "## Last 10 commits",
    },
    "estado_limpio": {"es": "(limpio)", "en": "(clean)"},
    "worktree_creado": {"es": "worktree creado: {path}", "en": "worktree created: {path}"},
    "worktree_rama": {"es": "  rama: {branch}", "en": "  branch: {branch}"},
    "worktree_usar": {"es": "  para usarlo: cd {path}", "en": "  to use: cd {path}"},
    "directorio_existe": {
        "es": "el directorio ya existe: {path}",
        "en": "directory already exists: {path}",
    },
    "worktree_fallo": {
        "es": "no se pudo crear worktree: {error}",
        "en": "could not create worktree: {error}",
    },
    "no_worktrees_huerfanos": {
        "es": "no hay worktrees huérfanos{suffix}",
        "en": "no orphaned worktrees{suffix}",
    },
    "worktrees_huerfanos": {
        "es": "worktrees huérfanos detectados ({count}) — directorio inexistente:",
        "en": "orphaned worktrees detected ({count}) — missing directory:",
    },
    "rama_desconocida": {"es": "desconocida", "en": "unknown"},
    "worktrees_limpiados": {
        "es": "limpiados {count} worktree(s) huérfano(s)",
        "en": "cleaned {count} orphaned worktree(s)",
    },
    "worktree_uso": {
        "es": "uso: gitwise worktree new <branch>",
        "en": "usage: gitwise worktree new <branch>",
    },
    "worktree_uso_completo": {
        "es": "uso: gitwise worktree new <branch>  |  gitwise worktree clean [--dry-run]",
        "en": "usage: gitwise worktree new <branch>  |  gitwise worktree clean [--dry-run]",
    },
    "git_diff_failed": {"es": "git diff failed: {error}", "en": "git diff failed: {error}"},
    "gpg_signing_activo_sin_key": {
        "es": "GPG signing activo pero sin user.signingkey — "
        "ejecuta: git config user.signingkey <id>",
        "en": "GPG signing active but no user.signingkey — run: git config user.signingkey <id>",
    },
    "gpg_signing_no_config": {
        "es": "GPG signing no configurado — si lo deseas: git config commit.gpgsign true",
        "en": "GPG signing not configured — if desired: git config commit.gpgsign true",
    },
    "gpg_activo_sin_key_repo": {
        "es": "GPG signing activo pero sin user.signingkey — "
        "ejecuta: git config user.signingkey <id>",
        "en": "GPG signing active but no user.signingkey — run: git config user.signingkey <id>",
    },
    "gitwise": {"es": "gitwise", "en": "gitwise"},
    "yes_response": {"es": "s", "en": "y"},
    "no_commits_yet_note": {"es": "no commits yet", "en": "no commits yet"},
    "skills_ya_configurados": {
        "es": "skills ({count}): ya configurados",
        "en": "skills ({count}): already configured",
    },
    "bloque_managed_sin_cierre": {
        "es": "{file}: bloque managed sin marcador de cierre — se dejará intacto",
        "en": "{file}: managed block missing closing marker — will be left intact",
    },
    "symlink_fuera_repo": {
        "es": ".claude/rules/{name}: symlink fuera del repo — ignorado",
        "en": ".claude/rules/{name}: symlink outside repo — ignored",
    },
    "archivo_demasiado_grande": {
        "es": ".claude/rules/{name}: archivo demasiado grande — no validado",
        "en": ".claude/rules/{name}: file too large — not validated",
    },
    "falta_globs_frontmatter": {
        "es": ".claude/rules/{name}: falta 'globs:' en frontmatter — la regla no se activará",
        "en": ".claude/rules/{name}: missing 'globs:' in frontmatter — rule won't activate",
    },
    "symlink_conflict_broken": {
        "es": "{file} es un symlink roto — arréglalo manualmente",
        "en": "{file} is a broken symlink — fix it manually",
    },
    "symlink_conflict_regular": {
        "es": "{file} ya es symlink a '{existing}', se esperaba '{expected}'",
        "en": "{file} is already a symlink to '{existing}', expected '{expected}'",
    },
    "symlink_conflict_file": {
        "es": "{file} es un archivo regular — no se sobreescribirá automáticamente",
        "en": "{file} is a regular file — won't be overwritten automatically",
    },
    "symlink_escapa_root": {
        "es": "Symlink target escapa del root del repositorio: {target}",
        "en": "Symlink target escapes repository root: {target}",
    },
    "json_invalido": {
        "es": ".claude/settings.json existente tiene JSON inválido — se sobreescribirá",
        "en": "existing .claude/settings.json has invalid JSON — will be overwritten",
    },
    "settings_sin_gpg_deny": {
        "es": "settings.json no tiene reglas deny para GPG bypass — revisar manualmente",
        "en": "settings.json missing deny rules for GPG bypass — check manually",
    },
    "settings_actualizado_merged": {
        "es": "actualizado (deny rules merged): .claude/settings.json",
        "en": "updated (deny rules merged): .claude/settings.json",
    },
    "skill_global_disponible": {
        "es": ".claude/skills/{skill}: skill ya disponible globalmente "
        "(~/.claude/skills/) — se omite creación local (prioridad user > project)",
        "en": ".claude/skills/{skill}: skill already available globally "
        "(~/.claude/skills/) — skipping local creation (user > project priority)",
    },
    "skill_symlink_diferente": {
        "es": ".claude/skills/{skill} es symlink a '{existing}', "
        "no a '{expected}' — se mantiene como está",
        "en": ".claude/skills/{skill} is symlink to '{existing}', "
        "not '{expected}' — keeping as is",
    },
    "skill_symlink_roto": {
        "es": ".claude/skills/{skill} es un symlink roto — arréglalo manualmente",
        "en": ".claude/skills/{skill} is a broken symlink — fix it manually",
    },
    "skill_dir_regular_con_agents": {
        "es": ".claude/skills/{skill} es un directorio regular aunque .agents/ existe — "
        "gitwise escribe SKILL.md directamente",
        "en": ".claude/skills/{skill} is a regular directory even though .agents/ exists — "
        "gitwise writes SKILL.md directly",
    },
    "skill_conflicto_dir_agents": {
        "es": "~/.claude/skills/{skill} es dir regular y ~/.agents/skills/{skill} "
        "también existe — sin cambios. Consolida manualmente.",
        "en": "~/.claude/skills/{skill} is a regular dir and ~/.agents/skills/{skill} "
        "also exists — no changes. Consolidate manually.",
    },
    "legacy_commands": {
        "es": ".claude/commands/{skill}.md es formato legacy — "
        "ahora se usa .claude/skills/{skill}/SKILL.md. "
        "Eliminá el .md viejo manualmente.",
        "en": ".claude/commands/{skill}.md is legacy format — "
        "now using .claude/skills/{skill}/SKILL.md. "
        "Delete the old .md manually.",
    },
    "claude_md_symlink_otro": {
        "es": "{file} es symlink a '{existing}', no a '{expected}'. "
        "Revisa manualmente. Para reemplazar: "
        "`gitwise setup-agents --replace-claude-with-symlink`",
        "en": "{file} is symlink to '{existing}', not '{expected}'. "
        "Review manually. To replace: "
        "`gitwise setup-agents --replace-claude-with-symlink`",
    },
    "claude_md_reemplazado": {
        "es": "{file} reemplazado por symlink a {target} (backup: {backup})",
        "en": "{file} replaced by symlink to {target} (backup: {backup})",
    },
    "claude_md_contenido_identico": {
        "es": "contenido idéntico a AGENTS.md",
        "en": "identical content to AGENTS.md",
    },
    "claude_md_separados": {
        "es": "{c} y {a} son archivos separados con contenido distinto. "
        "Para unificar: revisa `diff {c} {a}`, mueve contenido relevante "
        "manualmente, luego ejecuta `gitwise setup-agents --replace-claude-with-symlink`.",
        "en": "{c} and {a} are separate files with different content. "
        "To unify: review `diff {c} {a}`, move relevant content "
        "manually, then run `gitwise setup-agents --replace-claude-with-symlink`.",
    },
    "ya_apunta_agents": {
        "es": "ya apunta a AGENTS.md",
        "en": "already points to AGENTS.md",
    },
    "global_skill_symlink_diferente": {
        "es": "~/.claude/skills/{skill} es symlink a '{existing}', "
        "no a '{expected}' — se mantiene como está",
        "en": "~/.claude/skills/{skill} is symlink to '{existing}', "
        "not '{expected}' — keeping as is",
    },
    "global_skill_symlink_roto": {
        "es": "~/.claude/skills/{skill} es un symlink roto — arréglalo manualmente",
        "en": "~/.claude/skills/{skill} is a broken symlink — fix it manually",
    },
    "accion_desconocida": {
        "es": "acción desconocida: {action} en {file}",
        "en": "unknown action: {action} on {file}",
    },
    "accion_fallo": {
        "es": "acción falló: {error} — revirtiendo {count} acciones previas",
        "en": "action failed: {error} — rolling back {count} previous actions",
    },
    "hook_instala": {
        "es": "instala hooks GPG + conventional commits",
        "en": "installs GPG + conventional commit hooks",
    },
    "gitattributes_conflicto": {
        "es": ".gitattributes: '{pattern}' tiene regla existente '{existing}' "
        "que puede entrar en conflicto con la de gitwise '{desired}'. "
        "Elimina la línea fuera del bloque managed para evitar duplicados.",
        "en": ".gitattributes: '{pattern}' has existing rule '{existing}' "
        "that may conflict with gitwise's '{desired}'. "
        "Remove the line outside the managed block to avoid duplicates.",
    },
    "template_no_encontrado": {
        "es": "template no encontrado: {path}",
        "en": "template not found: {path}",
    },
    "protected_key_attempt": {
        "es": "Intento de modificar clave protegida: {key}",
        "en": "Attempt to modify protected key: {key}",
    },
    "git_version_ok": {
        "es": "git {ver} (≥ {min} requerido)",
        "en": "git {ver} (≥ {min} required)",
    },
    "python_version_ok": {"es": "Python {ver}", "en": "Python {ver}"},
    "plataforma": {"es": "plataforma: {name}", "en": "platform: {name}"},
    "commit_graph_ausente": {
        "es": "commit-graph ausente — git log puede ser 2-10x más lento",
        "en": "commit-graph missing — git log can be 2-10x slower",
    },
    "fsmonitor_desactivado": {
        "es": "core.fsmonitor desactivado — git status más lento en repos grandes",
        "en": "core.fsmonitor disabled — slower git status in large repos",
    },
    "stashes_viejos": {
        "es": "{count} stash(es) con más de {days} días",
        "en": "{count} stash(es) older than {days} days",
    },
    "large_blobs": {
        "es": "{count} archivo(s) grandes (≥1MB) en HEAD",
        "en": "{count} large file(s) (≥1MB) in HEAD",
    },
    "mixed_staging": {
        "es": "hay archivos staged y unstaged — el commit no sería atómico",
        "en": "staged and unstaged files present — commit wouldn't be atomic",
    },
    "stale_branches_audit": {
        "es": "{count} rama(s) con upstream eliminado ([gone])",
        "en": "{count} branch(es) with deleted upstream ([gone])",
    },
    "gpg_binary_missing_audit": {
        "es": "commit.gpgsign=true pero gpg no instalado — los commits fallarán",
        "en": "commit.gpgsign=true but gpg not installed — commits will fail",
    },
    "gpg_key_missing_audit": {
        "es": "commit.gpgsign=true pero user.signingkey no configurado",
        "en": "commit.gpgsign=true but user.signingkey not configured",
    },
    "gpg_not_configured_audit": {
        "es": "GPG no configurado — commits sin firma digital",
        "en": "GPG not configured — unsigned commits",
    },
    "repack_fallo_bitmap": {
        "es": "repack --write-bitmap-index falló, reintentando sin bitmap",
        "en": "repack --write-bitmap-index failed, retrying without bitmap",
    },
    "usando_delta": {"es": "usando delta para mostrar diff", "en": "using delta to display diff"},
    "commit_graph_fix": {
        "es": "gitwise optimize --yes",
        "en": "gitwise optimize --yes",
    },
    "fsmonitor_fix": {"es": "gitwise setup --yes", "en": "gitwise setup --yes"},
    "clean_fix": {
        "es": "gitwise clean --branches --dry-run",
        "en": "gitwise clean --branches --dry-run",
    },
    "stash_fix": {
        "es": "git stash drop stash@{N}  o  git stash clear",
        "en": "git stash drop stash@{N}  or  git stash clear",
    },
    "large_blobs_fix": {
        "es": "considerar git-lfs o eliminación de la historia",
        "en": "consider git-lfs or history removal",
    },
    "mixed_staging_fix": {
        "es": "revisar con git diff --staged antes de commitear",
        "en": "review with git diff --staged before committing",
    },
    "gpg_binary_missing_fix": {"es": "brew install gnupg", "en": "brew install gnupg"},
    "gpg_key_missing_fix": {
        "es": "git config user.signingkey <key-id>",
        "en": "git config user.signingkey <key-id>",
    },
    "gpg_not_configured_fix": {
        "es": "brew install gnupg  →  git config --global commit.gpgsign true",
        "en": "brew install gnupg  →  git config --global commit.gpgsign true",
    },
    "gpg_binary_missing_cost": {
        "es": "ningún git commit funcionará hasta instalarlo",
        "en": "no git commit will work until installed",
    },
    "gpg_key_missing_cost": {
        "es": "ningún git commit funcionará",
        "en": "no git commit will work",
    },
    "gpg_not_configured_cost": {
        "es": "commits no verificables criptográficamente",
        "en": "commits not cryptographically verifiable",
    },
    "stale_branches_cost": {
        "es": "clutter en `git branch`; confunde agentes Claude",
        "en": "clutter in `git branch`; confuses Claude agents",
    },
    "commit_graph_cost": {
        "es": "latencia acumulada en cada sesión de Claude",
        "en": "accumulated latency in each Claude session",
    },
    "fsmonitor_cost": {
        "es": "~50ms extra por git status en repos medianos",
        "en": "~50ms extra per git status in medium repos",
    },
    "stash_cost": {
        "es": "acumulación de WIP probablemente irrelevante",
        "en": "accumulation of probably irrelevant WIP",
    },
    "large_blobs_cost": {
        "es": "lentitud en clone y fetch",
        "en": "slow clone and fetch",
    },
    "mixed_staging_cost": {
        "es": "commits no atómicos dificultan el historial",
        "en": "non-atomic commits make history harder to follow",
    },
    "gpg_not_configured_fix_cost": {
        "es": "requiere crear llave GPG (~5 min)",
        "en": "requires creating GPG key (~5 min)",
    },
    "stash_fix_cost": {
        "es": "irreversible — revisar antes",
        "en": "irreversible — review first",
    },
    "large_blobs_fix_cost": {
        "es": "depende del archivo",
        "en": "depends on the file",
    },
    "mixed_staging_fix_cost": {"es": "n/a", "en": "n/a"},
    "commit_graph_fix_cost": {
        "es": "trivial (segundos)",
        "en": "trivial (seconds)",
    },
    "fsmonitor_fix_cost": {"es": "trivial", "en": "trivial"},
    "stale_branches_fix_cost": {"es": "trivial", "en": "trivial"},
    "gpg_binary_fix_cost": {"es": "trivial", "en": "trivial"},
    "gpg_key_fix_cost": {"es": "trivial", "en": "trivial"},
    "clave_protegida": {
        "es": "Intento de modificar clave protegida: {name}",
        "en": "Attempt to modify protected key: {name}",
    },
    "gpg_signing_activo_global": {
        "es": "GPG signing activo pero sin user.signingkey — "
        "ejecuta: git config user.signingkey <id>",
        "en": "GPG signing active but no user.signingkey — run: git config user.signingkey <id>",
    },
    "hook_install_note": {
        "es": "instala hooks GPG + conventional commits",
        "en": "installs GPG + conventional commit hooks",
    },
    "gitattributes_merge_ours": {
        "es": "# Generated snapshot: use local version on merge",
        "en": "# Generated snapshot: use local version on merge",
    },
    "gitattributes_force_lf": {
        "es": "# Convention files: force LF for cross-platform consistency",
        "en": "# Convention files: force LF for cross-platform consistency",
    },
    "gitignore_claude_local": {
        "es": "# Claude Code local/personal files (do not commit)",
        "en": "# Claude Code local/personal files (do not commit)",
    },
    "gitignore_snapshot": {
        "es": "# Snapshot regenerated each gitwise run (timestamps change)",
        "en": "# Snapshot regenerated each gitwise run (timestamps change)",
    },
    "gitignore_backups": {
        "es": "# Backups from gitwise setup-agents",
        "en": "# Backups from gitwise setup-agents",
    },
}


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
