"""gitwise suggest — heuristic commit message from staged diff."""

import re
import sys

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import ok, print_json

_TYPE_MAP: list[tuple[str, str]] = [
    (r"/test", "test"),
    (r"test_", "test"),
    (r"_test\.", "test"),
    (r"README", "docs"),
    (r"CHANGELOG", "docs"),
    (r"\.md$", "docs"),
    (r"\.txt$", "docs"),
    (r"Dockerfile", "build"),
    (r"docker-compose", "build"),
    (r"\.ya?ml$", "ci"),
    (r"\.toml$", "build"),
    (r"\.cfg$", "build"),
    (r"\.json$", "chore"),
    (r"\.lock$", "chore"),
]


def _infer_type(files: list[str]) -> str:
    for pattern, commit_type in _TYPE_MAP:
        for f in files:
            if re.search(pattern, f):
                return commit_type
    return "feat"


def _infer_scope(files: list[str]) -> str | None:
    dirs: set[str] = set()
    for f in files:
        parts = f.split("/")
        if len(parts) > 1:
            dirs.add(parts[0])
    if len(dirs) == 1:
        return dirs.pop()
    return None


def _build_message(staged_files: list[str], additions: int, deletions: int) -> str:
    commit_type = _infer_type(staged_files)
    scope = _infer_scope(staged_files)
    scope_str = f"({scope})" if scope else ""
    if len(staged_files) == 1:
        filename = staged_files[0].rsplit("/", 1)[-1]
        return f"{commit_type}{scope_str}: update {filename}"
    dir_name = staged_files[0].split("/")[0] if "/" in staged_files[0] else "files"
    return f"{commit_type}{scope_str}: update {dir_name} ({len(staged_files)} files)"


def run_suggest(*, as_json: bool = False) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    r = git_run(["diff", "--cached", "--name-only"], cwd=root, check=False)
    if r.returncode != 0:
        print(t("suggest_diff_failed"), file=sys.stderr)
        return 1
    staged_files = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    if not staged_files:
        print(t("suggest_no_staged"), file=sys.stderr)
        return 1

    stat = git_run(["diff", "--cached", "--numstat"], cwd=root, check=False)
    additions = deletions = 0
    if stat.returncode == 0:
        for line in stat.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    additions += int(parts[0]) if parts[0] != "-" else 0
                    deletions += int(parts[1]) if parts[1] != "-" else 0
                except ValueError:
                    pass

    message = _build_message(staged_files, additions, deletions)

    if as_json:
        print_json(
            {
                "v": 1,
                "message": message,
                "files": staged_files,
                "additions": additions,
                "deletions": deletions,
            }
        )
        return 0

    ok(t("suggest_message", message=message))
    return 0
