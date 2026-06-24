"""gitwise context — enriched snapshot for LLMs (tree, contributors, topology, file types, TODO/FIXME)."""

from pathlib import Path

from gitwise.git import require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import (
    info,
    print_blank,
    print_bracket,
    print_dim,
    print_header,
    print_json,
    status,
)
from gitwise.utils.json_envelope import ok_envelope


def _directory_tree(root: Path, max_depth: int = 3) -> list[str]:
    """Return Unicode box-drawing lines for the directory tree, skipping common noise dirs."""
    lines: list[str] = []
    skip = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }

    def _walk(path: Path, prefix: str, depth: int) -> None:
        """Recursively append tree lines for *path* at *depth*."""
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        dirs = [e for e in entries if e.is_dir() and e.name not in skip]
        files = [e for e in entries if e.is_file() and e.name not in skip]
        children = dirs + files
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{child.name}")
            if child.is_dir():
                extension = "    " if is_last else "│   "
                _walk(child, prefix + extension, depth + 1)

    _walk(root, "", 0)
    return lines


def _top_contributors(root: Path, count: int = 5) -> list[dict[str, str | int]]:
    """Return top-N contributors by commit count."""
    r = git_run(["shortlog", "-sne", "HEAD"], cwd=root, check=False)
    if r.returncode != 0:
        return []
    contributors: list[dict[str, str | int]] = []
    for line in r.stdout.strip().splitlines()[:count]:
        parts = line.strip().split("\t", 1)
        if len(parts) == 2:
            contributors.append({"commits": int(parts[0].strip()), "author": parts[1].strip()})
    return contributors


def _file_type_breakdown(root: Path) -> dict[str, int]:
    """Return a ``{ext: count}`` dict for the top 15 file extensions in HEAD."""
    r = git_run(["ls-tree", "-r", "--name-only", "HEAD"], cwd=root, check=False)
    if r.returncode != 0:
        return {}
    counts: dict[str, int] = {}
    for line in r.stdout.splitlines():
        name = line.strip()
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else "(no ext)"
        counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1])[:15])


def _todo_fixme_counts(root: Path) -> dict[str, int]:
    """Count TODO and FIXME occurrences in HEAD."""

    def _count_pattern(pattern: str) -> int:
        """Count occurrences of *pattern* across files in HEAD."""
        r = git_run(
            ["grep", "-c", "-e", pattern, "HEAD", "--", "."],
            cwd=root,
            check=False,
        )
        if r.returncode != 0:
            return 0
        total = 0
        for line in r.stdout.splitlines():
            try:
                total += int(line.rsplit(":", 1)[-1])
            except (ValueError, IndexError):
                continue
        return total

    return {"todo": _count_pattern("TODO"), "fixme": _count_pattern("FIXME")}


def _branch_topology(root: Path) -> dict[str, list[str]]:
    """Return ``{local: [...], remote: [...]}`` branch name lists."""
    r = git_run(["branch", "-a", "--format=%(refname)"], cwd=root, check=False)
    if r.returncode != 0:
        return {"local": [], "remote": []}
    local: list[str] = []
    remote: list[str] = []
    for line in r.stdout.splitlines():
        ref = line.strip()
        if ref.startswith("refs/heads/"):
            local.append(ref.removeprefix("refs/heads/"))
        elif ref.startswith("refs/remotes/"):
            remote.append(ref.removeprefix("refs/remotes/"))
    return {"local": local, "remote": remote}


def run_context(*, as_json: bool = False) -> int:
    """Entry point for the ``gitwise context`` command."""
    root = require_root()
    if root is None:
        return 1

    with status(t("status_context_scan")):
        tree = _directory_tree(root)
        contributors = _top_contributors(root)
        file_types = _file_type_breakdown(root)
        todo_fixme = _todo_fixme_counts(root)
        topology = _branch_topology(root)

    if as_json:
        from gitwise.health import compute_health

        h = compute_health(root)
        print_json(
            ok_envelope(
                "context",
                data={
                    "tree": tree,
                    "contributors": contributors,
                    "file_types": file_types,
                    "todo_fixme": todo_fixme,
                    "branches": topology,
                    "health": {"score": h["score"], "grade": h["grade"]},
                },
            )
        )
    else:
        print_header(t("ctx_directory_tree"))
        for ln in tree[:50]:
            info(f"  {ln}")
        if len(tree) > 50:
            print_dim(t("ctx_more_entries", count=str(len(tree) - 50)))
        print_blank()
        if contributors:
            print_bracket(t("ctx_top_contributors"))
            for c in contributors:
                print_dim(f"  {c['commits']:>5}  {c['author']}")
            print_blank()
        if file_types:
            print_bracket(t("ctx_file_types"))
            for ext, count in list(file_types.items())[:10]:
                print_dim(f"  .{ext}: {count}")
            print_blank()
        if todo_fixme["todo"] or todo_fixme["fixme"]:
            print_bracket(
                t("ctx_todo_fixme", todo=str(todo_fixme["todo"]), fixme=str(todo_fixme["fixme"]))
            )
            print_blank()
        print_bracket(
            t(
                "ctx_branches",
                local=str(len(topology["local"])),
                remote=str(len(topology["remote"])),
            )
        )

    return 0
