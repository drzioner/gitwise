"""gitwise suggest — heuristic commit message from staged diff."""

import re

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import error, print_accent, print_bracket, print_header, print_json

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
        return f"{commit_type}{scope_str}: {t('suggest_update_file', filename=filename)}"
    return f"{commit_type}{scope_str}: {t('suggest_update_files', count=str(len(staged_files)))}"


def run_suggest(*, as_json: bool = False) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    r = git_run(["diff", "--cached", "--name-only"], cwd=root, check=False)
    if r.returncode != 0:
        error(t("suggest_diff_failed"))
        return 1
    staged_files = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    if not staged_files:
        error(t("suggest_no_staged"))
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
                "v": 2,
                "message": message,
                "files": staged_files,
                "additions": additions,
                "deletions": deletions,
                "ok": True,
            }
        )
        return 0

    print_header(t("suggest_message", message=message))
    print_bracket(t("suggest_type", type=_infer_type(staged_files)))
    for f in staged_files:
        print_accent(f"  {f}")
    return 0
