"""Generates .claude/git-snapshot.md — static repo context for Claude."""

from datetime import datetime, timezone
from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import debug, error, ok, print_json


def generate_snapshot(root: Path, *, frozen_time: bool = False) -> Path:
    """Write .claude/git-snapshot.md in repo root. Updates generated_at on every call."""
    snapshot_path = root / ".claude" / "git-snapshot.md"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    if frozen_time:
        generated_at = "1970-01-01T00:00:00Z"
    else:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = ["# Git Snapshot", "", f"generated_at: {generated_at}", ""]

    branch = git_run(["branch", "--show-current"], cwd=root, check=False)
    if branch.returncode == 0:
        lines += [
            t("seccion_rama_actual"),
            "```",
            branch.stdout.strip() or "(detached HEAD)",
            "```",
            "",
        ]

    status = git_run(["status", "--short"], cwd=root, check=False)
    if status.returncode == 0:
        lines += [
            t("seccion_estado"),
            "```",
            status.stdout.strip() or t("estado_limpio"),
            "```",
            "",
        ]

    log = git_run(["--no-pager", "log", "--oneline", "-n", "10"], cwd=root, check=False)
    if log.returncode == 0 and log.stdout.strip():
        lines += [t("seccion_ultimos_commits"), "```", log.stdout.strip(), "```", ""]

    stash = git_run(["stash", "list"], cwd=root, check=False)
    if stash.returncode == 0 and stash.stdout.strip():
        stash_count = len(stash.stdout.strip().splitlines())
        lines += [f"## Stashes: {stash_count}", ""]

    worktrees = git_run(["worktree", "list", "--porcelain"], cwd=root, check=False)
    if worktrees.returncode == 0:
        wt_count = worktrees.stdout.count("worktree ")
        if wt_count > 1:
            lines += [f"## Worktrees activos: {wt_count}", ""]

    tmp = snapshot_path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(snapshot_path)
    debug(f"snapshot escrito en {snapshot_path}")
    return snapshot_path


def run_snapshot(*, as_json: bool = False) -> int:
    if not is_repo():
        error(t("no_repo"))
        return 1

    root = repo_root()
    if root is None:
        error(t("no_root"))
        return 1

    path = generate_snapshot(root)

    if as_json:
        print_json({"v": 1, "path": str(path), "ok": True})
        return 0

    ok(t("snapshot_generado", path=str(path.relative_to(root))))
    return 0
