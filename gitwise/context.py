"""gitwise context — enriched snapshot for LLMs (tree, contributors, topology, file types, TODO/FIXME)."""

import sys
from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import print_json


def _directory_tree(root: Path, max_depth: int = 3) -> list[str]:
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
    r = git_run(["grep", "-c", "-E", r"TODO|FIXME", "HEAD", "--", "."], cwd=root, check=False)
    if r.returncode != 0:
        return {"todo": 0, "fixme": 0}
    todo = fixme = 0
    for line in r.stdout.splitlines():
        if ":TODO:" in line.upper() or line.upper().endswith(":TODO"):
            todo += 1
        if ":FIXME:" in line.upper() or line.upper().endswith(":FIXME"):
            fixme += 1
    return {"todo": todo, "fixme": fixme}


def _branch_topology(root: Path) -> dict[str, list[str]]:
    r = git_run(["branch", "-a", "--format=%(refname:short)"], cwd=root, check=False)
    if r.returncode != 0:
        return {"local": [], "remote": []}
    local: list[str] = []
    remote: list[str] = []
    for line in r.stdout.splitlines():
        name = line.strip()
        if "/" in name and not name.startswith("("):
            remote.append(name)
        elif name and not name.startswith("("):
            local.append(name)
    return {"local": local, "remote": remote}


def run_context(*, as_json: bool = False) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    tree = _directory_tree(root)
    contributors = _top_contributors(root)
    file_types = _file_type_breakdown(root)
    todo_fixme = _todo_fixme_counts(root)
    topology = _branch_topology(root)

    if as_json:
        print_json(
            {
                "v": 1,
                "tree": tree,
                "contributors": contributors,
                "file_types": file_types,
                "todo_fixme": todo_fixme,
                "branches": topology,
            }
        )
    else:
        print("## Directory Tree")
        for ln in tree[:50]:
            print(f"  {ln}")
        if len(tree) > 50:
            print(f"  ... ({len(tree) - 50} more entries)")
        print()
        if contributors:
            print("## Top Contributors")
            for c in contributors:
                print(f"  {c['commits']:>5}  {c['author']}")
            print()
        if file_types:
            print("## File Types")
            for ext, count in list(file_types.items())[:10]:
                print(f"  .{ext}: {count}")
            print()
        if todo_fixme["todo"] or todo_fixme["fixme"]:
            print(f"## TODO/FIXME: {todo_fixme['todo']} TODO, {todo_fixme['fixme']} FIXME")
            print()
        print(f"## Branches: {len(topology['local'])} local, {len(topology['remote'])} remote")

    return 0
