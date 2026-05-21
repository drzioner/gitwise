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
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        code = status[:1].upper() if status else ""
        if code in {"R", "C"} and len(parts) >= 3:
            old_path = parts[1].strip()
            path = parts[2].strip()
            if not path:
                continue
            rename_entry: DiffFileEntry = {"status": status, "path": path}
            if code and code != status:
                rename_entry["code"] = code
            if old_path:
                rename_entry["old_path"] = old_path
            if len(status) > 1 and status[1:].isdigit():
                rename_entry["score"] = status[1:]
            entries[path] = rename_entry
            continue

        path = parts[-1].strip()
        if not path:
            continue
        file_entry: DiffFileEntry = {"status": status, "path": path}
        if code and code != status:
            file_entry["code"] = code
        entries[path] = file_entry
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
            print_json({"v": 2, "ok": True, "files": [], "count": 0, "note": t("no_commits_yet")})
            return 0
        info(t("no_commits_yet"))
        return 0

    if full:
        r = git_run(["--no-pager", "diff", "HEAD"], cwd=cwd, check=False)
        if r.returncode != 0:
            error(t("git_diff_failed", error=r.stderr.strip()))
            return 1
        if as_json:
            print_json({"v": 2, "ok": True, "diff": r.stdout})
        else:
            if HAS_DELTA:
                print_dim(t("using_delta"))
            bat_pipe(r.stdout, language="diff")
        return 0

    use_stat = stat or (not staged and not name_only and not full)
    if use_stat:
        r = git_run(["--no-pager", "diff", "--stat", "HEAD"], cwd=cwd, check=False)
    elif staged:
        r = git_run(["--no-pager", "diff", "--name-status", "--staged"], cwd=cwd, check=False)
    elif name_only:
        r = git_run(["--no-pager", "diff", "--name-only", "HEAD"], cwd=cwd, check=False)
    else:
        r = git_run(["--no-pager", "diff", "--name-status", "HEAD"], cwd=cwd, check=False)

    if r.returncode != 0:
        error(t("git_diff_failed", error=r.stderr.strip()))
        return 1

    lines = [line for line in r.stdout.splitlines() if line.strip()]

    if use_stat:
        files = _parse_diffstat_entries(lines)
        if not files:
            if as_json:
                print_json({"v": 2, "ok": True, "files": [], "count": 0})
                return 0
            info(t("no_uncommitted_changes"))
            return 0
        status_details = _name_status_details(cwd, staged=staged)
        numstat_details = _numstat_details(cwd, staged=staged)
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

        if as_json:
            print_json(
                {
                    "v": 2,
                    "ok": True,
                    "files": merged_files,
                    "count": len(merged_files),
                    "totals": _diff_totals(merged_files),
                }
            )
            return 0

        styled_files = [
            {
                "path": str(f.get("path", "")),
                "changes": str(f.get("changes", "")),
                "status": str(f.get("code", f.get("status", "M"))),
            }
            for f in merged_files
            if str(f.get("path", ""))
        ]
        print_diffstat(t("changed_files", count=str(len(styled_files))), styled_files)
        return 0

    if not lines:
        if as_json:
            print_json({"v": 2, "ok": True, "files": [], "count": 0})
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
        print_json({"v": 2, "ok": True, "files": files, "count": len(files)})
        return 0

    print_header(t("changed_files", count=str(len(files))))
    for f in files:
        print_file_status(f["status"], f["path"])
    return 0
