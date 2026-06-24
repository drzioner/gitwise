"""gitwise suggest — heuristic commit message from staged diff."""

import re

from gitwise.git import require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import (
    error,
    print_bracket,
    print_file_status,
    print_header,
    print_json,
    status,
)
from gitwise.utils.in_progress import detect_in_progress, in_progress_hint
from gitwise.utils.json_envelope import error_envelope, ok_envelope
from gitwise.utils.parsing import stripped_non_empty_lines

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
    """Pick a conventional-commit type from the first matching filename pattern."""
    for pattern, commit_type in _TYPE_MAP:
        for f in files:
            if re.search(pattern, f):
                return commit_type
    return "feat"


def _infer_scope(files: list[str]) -> str | None:
    """Return the common top-level directory when all files share one."""
    dirs: set[str] = set()
    for f in files:
        parts = f.split("/")
        if len(parts) > 1:
            dirs.add(parts[0])
    if len(dirs) == 1:
        return dirs.pop()
    return None


def _build_message(staged_files: list[str], additions: int, deletions: int) -> str:
    """Compose a conventional-commit message from the staged file list."""
    commit_type = _infer_type(staged_files)
    scope = _infer_scope(staged_files)
    scope_str = f"({scope})" if scope else ""
    if len(staged_files) == 1:
        filename = staged_files[0].rsplit("/", 1)[-1]
        return f"{commit_type}{scope_str}: {t('suggest_update_file', filename=filename)}"
    return f"{commit_type}{scope_str}: {t('suggest_update_files', count=str(len(staged_files)))}"


def _staged_with_status(root) -> list[tuple[str, str]]:
    """Return (status_letter, path) pairs from the staged diff."""
    r = git_run(["diff", "--cached", "--name-status"], cwd=root, check=False)
    if r.returncode != 0:
        return []
    pairs: list[tuple[str, str]] = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0][:1].upper()
        path = parts[-1].strip()
        if path:
            pairs.append((status, path))
    return pairs


def _collect_staged_files(root) -> tuple[list[str], dict[str, str]]:
    """Return (file_paths, path_to_status_map) for all staged files.

    Raises RuntimeError if the staged diff cannot be read.
    """
    r = git_run(["diff", "--cached", "--name-only"], cwd=root, check=False)
    if r.returncode != 0:
        raise RuntimeError("staged_diff_failed")
    staged_files = stripped_non_empty_lines(r.stdout)
    staged_pairs = _staged_with_status(root)
    staged_map = {path: status for status, path in staged_pairs}
    return staged_files, staged_map


def _numstat_totals(root) -> tuple[int, int]:
    """Return (total_additions, total_deletions) across all staged files."""
    stat = git_run(["diff", "--cached", "--numstat"], cwd=root, check=False)
    additions = deletions = 0
    if stat.returncode != 0:
        return additions, deletions
    for line in stat.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        added = parts[0]
        removed = parts[1]
        if added != "-" and added.isdigit():
            additions += int(added)
        if removed != "-" and removed.isdigit():
            deletions += int(removed)
    return additions, deletions


def _print_suggest_human(
    message: str, staged_files: list[str], staged_map: dict[str, str]
) -> None:
    """Render the suggestion, inferred type, and staged file list to the terminal."""
    print_header(t("suggest_message", message=message))
    print_bracket(t("suggest_type", type=_infer_type(staged_files)))
    for file_path in staged_files:
        print_file_status(staged_map.get(file_path, "M"), file_path)


def run_suggest(*, as_json: bool = False) -> int:
    """Inspect staged files and propose a conventional-commit message.

    Refuses with ``in_progress_<state>`` if a merge/rebase/cherry-pick/revert/
    bisect is paused (so an agent never commits mid-operation).
    """
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    in_progress = detect_in_progress(root)
    if in_progress["state"] != "none":
        hint = in_progress_hint(in_progress["state"])
        blocked_msg = t("suggest_blocked_in_progress", state=in_progress["state"])
        if as_json:
            print_json(
                error_envelope(
                    "suggest",
                    error=blocked_msg,
                    code=f"in_progress_{in_progress['state']}",
                    hint=hint,
                )
            )
            return 1
        error(blocked_msg, hint=hint)
        return 1

    try:
        with status(t("status_analyzing_staged")):
            staged_files, staged_map = _collect_staged_files(root)
            additions, deletions = _numstat_totals(root) if staged_files else (0, 0)
    except RuntimeError:
        error(t("suggest_diff_failed"))
        return 1

    if not staged_files:
        if as_json:
            print_json(
                error_envelope("suggest", error=t("suggest_no_staged"), code="suggest_no_staged")
            )
            return 1
        error(t("suggest_no_staged"))
        return 1

    message = _build_message(staged_files, additions, deletions)

    if as_json:
        print_json(
            ok_envelope(
                "suggest",
                message=message,
                files=staged_files,
                additions=additions,
                deletions=deletions,
            )
        )
        return 0

    _print_suggest_human(message, staged_files, staged_map)
    return 0
