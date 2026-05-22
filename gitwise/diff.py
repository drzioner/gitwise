"""Focused changed-file list for AI agents and humans."""

from pathlib import Path

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import (
    HAS_DELTA,
    bat_pipe,
    error,
    info,
    print_diffstat,
    print_dim,
    print_file_status,
    print_header,
    print_json,
)
from .utils.git_output import parse_name_status_entries
from .utils.json_envelope import ok_envelope

DiffValue = str | int | bool
DiffFileEntry = dict[str, DiffValue]


def _parse_diffstat_entries(lines: list[str]) -> list[DiffFileEntry]:
    entries: list[DiffFileEntry] = []
    for line in lines:
        if "|" not in line:
            continue
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        path = parts[0].strip()
        changes = parts[1].strip()
        if not path:
            continue
        changed_count = 0
        graph = ""
        change_parts = changes.split(" ", 1)
        if change_parts and change_parts[0].isdigit():
            changed_count = int(change_parts[0])
        if len(change_parts) == 2:
            graph = change_parts[1].strip()
        entry: DiffFileEntry = {
            "path": path,
            "changes": changes,
            "lines_changed": changed_count,
            "graph": graph,
        }
        entries.append(entry)
    return entries


def _parse_name_status_lines(lines: list[str]) -> dict[str, DiffFileEntry]:
    entries: dict[str, DiffFileEntry] = {}
    parsed = parse_name_status_entries("\n".join(lines))
    for entry in parsed:
        path = entry.get("path")
        if not path:
            continue
        typed_entry: DiffFileEntry = dict(entry)
        entries[path] = typed_entry
    return entries


def _diff_totals(files: list[DiffFileEntry]) -> DiffFileEntry:
    insertions = 0
    deletions = 0
    lines_changed = 0
    binary_files = 0
    for item in files:
        ins = item.get("insertions")
        dels = item.get("deletions")
        changed = item.get("lines_changed")
        is_binary = item.get("is_binary")
        if isinstance(ins, int):
            insertions += ins
        if isinstance(dels, int):
            deletions += dels
        if isinstance(changed, int):
            lines_changed += changed
        if is_binary is True:
            binary_files += 1
    return {
        "insertions": insertions,
        "deletions": deletions,
        "lines_changed": lines_changed,
        "binary_files": binary_files,
    }


def _name_status_details(cwd: Path, *, staged: bool) -> dict[str, DiffFileEntry]:
    args = ["--no-pager", "diff", "--name-status"]
    if staged:
        args.append("--staged")
    else:
        args.append("HEAD")
    r = git_run(args, cwd=cwd, check=False)
    if r.returncode != 0:
        return {}
    return _parse_name_status_lines(r.stdout.splitlines())


def _numstat_details(cwd: Path, *, staged: bool) -> dict[str, DiffFileEntry]:
    args = ["--no-pager", "diff", "--numstat"]
    if staged:
        args.append("--staged")
    else:
        args.append("HEAD")
    r = git_run(args, cwd=cwd, check=False)
    if r.returncode != 0:
        return {}

    details: dict[str, DiffFileEntry] = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add_raw = parts[0].strip()
        del_raw = parts[1].strip()
        path = parts[2].strip()
        if not path:
            continue

        if add_raw == "-" or del_raw == "-":
            details[path] = {"path": path, "is_binary": True}
            continue

        if not (add_raw.isdigit() and del_raw.isdigit()):
            continue

        details[path] = {
            "path": path,
            "insertions": int(add_raw),
            "deletions": int(del_raw),
            "is_binary": False,
        }
    return details


def _has_commits(cwd: Path) -> bool:
    return git_run(["rev-parse", "HEAD"], cwd=cwd, check=False).returncode == 0


def _diff_cmd(*, use_stat: bool, staged: bool, name_only: bool, full: bool) -> list[str]:
    if full:
        return ["--no-pager", "diff", "HEAD"]
    if use_stat:
        return ["--no-pager", "diff", "--stat", "HEAD"]
    if staged:
        return ["--no-pager", "diff", "--name-status", "--staged"]
    if name_only:
        return ["--no-pager", "diff", "--name-only", "HEAD"]
    return ["--no-pager", "diff", "--name-status", "HEAD"]


def _print_diff_human_full(*, diff_text: str) -> None:
    if HAS_DELTA:
        print_dim(t("using_delta"))
    bat_pipe(diff_text, language="diff")


def _merge_stat_files(
    *,
    files: list[DiffFileEntry],
    status_details: dict[str, DiffFileEntry],
    numstat_details: dict[str, DiffFileEntry],
) -> list[DiffFileEntry]:
    merged_files: list[DiffFileEntry] = []
    for item in files:
        path_value = item.get("path")
        if not isinstance(path_value, str) or not path_value:
            continue
        merged: DiffFileEntry = dict(item)
        if path_value in status_details:
            for key, value in status_details[path_value].items():
                merged[key] = value
        if path_value in numstat_details:
            for key, value in numstat_details[path_value].items():
                merged[key] = value
        merged_files.append(merged)
    return merged_files


def _render_stat_output(
    *,
    files: list[DiffFileEntry],
    cwd: Path,
    staged: bool,
    as_json: bool,
) -> int:
    if not files:
        if as_json:
            print_json(ok_envelope(files=[], count=0))
            return 0
        info(t("no_uncommitted_changes"))
        return 0

    status_details = _name_status_details(cwd, staged=staged)
    numstat_details = _numstat_details(cwd, staged=staged)
    merged_files = _merge_stat_files(
        files=files,
        status_details=status_details,
        numstat_details=numstat_details,
    )
    if as_json:
        print_json(
            ok_envelope(
                files=merged_files,
                count=len(merged_files),
                totals=_diff_totals(merged_files),
            )
        )
        return 0

    styled_files = [
        {
            "path": str(file_item.get("path", "")),
            "changes": str(file_item.get("changes", "")),
            "status": str(file_item.get("code", file_item.get("status", "M"))),
        }
        for file_item in merged_files
        if str(file_item.get("path", ""))
    ]
    print_diffstat(t("changed_files", count=str(len(styled_files))), styled_files)
    return 0


def _render_non_stat_output(
    *,
    lines: list[str],
    staged: bool,
    name_only: bool,
    as_json: bool,
) -> int:
    if not lines:
        if as_json:
            print_json(ok_envelope(files=[], count=0))
            return 0
        if staged:
            info(t("nothing_staged"))
        else:
            info(t("tip_staged"))
        return 0

    if name_only:
        files = [{"path": line.strip()} for line in lines if line.strip()]
    else:
        files = []
        for line in lines:
            parts = line.split("\t", 1)
            if len(parts) == 2:
                files.append({"status": parts[0].strip(), "path": parts[1].strip()})

    if as_json:
        print_json(ok_envelope(files=files, count=len(files)))
        return 0

    print_header(t("changed_files", count=str(len(files))))
    for file_item in files:
        print_file_status(file_item["status"], file_item["path"])
    return 0


def run_diff(
    *,
    staged: bool = False,
    stat: bool = False,
    name_only: bool = False,
    full: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1
    cwd = root

    if not staged and not _has_commits(cwd):
        if as_json:
            print_json(ok_envelope(files=[], count=0, note=t("no_commits_yet")))
            return 0
        info(t("no_commits_yet"))
        return 0

    use_stat = stat or (not staged and not name_only and not full)
    cmd = _diff_cmd(use_stat=use_stat, staged=staged, name_only=name_only, full=full)
    result = git_run(cmd, cwd=cwd, check=False)
    if result.returncode != 0:
        error(t("git_diff_failed", error=result.stderr.strip()))
        return 1

    if full:
        if as_json:
            print_json(ok_envelope(diff=result.stdout))
        else:
            _print_diff_human_full(diff_text=result.stdout)
        return 0

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if use_stat:
        files = _parse_diffstat_entries(lines)
        return _render_stat_output(files=files, cwd=cwd, staged=staged, as_json=as_json)

    return _render_non_stat_output(
        lines=lines, staged=staged, name_only=name_only, as_json=as_json
    )
