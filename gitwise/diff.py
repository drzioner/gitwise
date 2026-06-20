"""Focused changed-file list for AI agents and humans."""

from pathlib import Path

from gitwise.git import require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import (
    HAS_DELTA,
    bat_pipe,
    error,
    info,
    print_diffstat,
    print_dim,
    print_file_status,
    print_header,
    print_json,
    status,
    warn,
)
from gitwise.utils.git_output import parse_name_status_entries, status_label
from gitwise.utils.json_envelope import ok_envelope
from gitwise.utils.secret_scan import secret_scan

DiffValue = str | int | bool
DiffFileEntry = dict[str, DiffValue]

# GitHub recommends 1 MiB as the maximum single-object size before considering
# Git LFS or external storage; above it is enforced at 100 MiB.
# Verified: docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits (retrieved 2026-06-19)
_BYTES_PER_MIB = 1024 * 1024
LFS_WARN_BYTES = 1 * _BYTES_PER_MIB


def _parse_diffstat_entries(lines: list[str]) -> list[DiffFileEntry]:
    """Parse ``git diff --stat`` lines into structured dicts with path, changes, and graph."""
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
    """Parse ``git diff --name-status`` output into a path-keyed dict."""
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
    """Sum insertions, deletions, lines_changed, and binary_files across entries."""
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


def _name_status_details(
    cwd: Path, *, staged: bool, refspec: str | None, paths: list[str] | None
) -> dict[str, DiffFileEntry]:
    """Return per-file name-status details for staged or working-tree changes."""
    args = ["--no-pager", "diff", "--name-status"]
    if staged:
        args.append("--staged")
    if refspec:
        args.append(refspec)
    elif not staged:
        args.append("HEAD")
    if paths:
        args.append("--")
        args.extend(paths)
    r = git_run(args, cwd=cwd, check=False)
    if r.returncode != 0:
        return {}
    return _parse_name_status_lines(r.stdout.splitlines())


def _numstat_details(
    cwd: Path, *, staged: bool, refspec: str | None, paths: list[str] | None
) -> dict[str, DiffFileEntry]:
    """Return per-file numstat details with insertion/deletion counts and binary flag."""
    args = ["--no-pager", "diff", "--numstat"]
    if staged:
        args.append("--staged")
    if refspec:
        args.append(refspec)
    elif not staged:
        args.append("HEAD")
    if paths:
        args.append("--")
        args.extend(paths)
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
    """Return True if the repository has at least one commit."""
    return git_run(["rev-parse", "HEAD"], cwd=cwd, check=False).returncode == 0


def _diff_cmd(
    *,
    use_stat: bool,
    staged: bool,
    name_only: bool,
    full: bool,
    refspec: str | None,
    paths: list[str] | None,
) -> list[str]:
    """Build the git diff argv for the requested mode.

    When ``refspec`` is given it replaces the default ``HEAD`` endpoint so the
    caller can diff against a commit, branch, or range (``a..b`` / ``a...b``).
    Diff compares endpoints rather than revision ranges, so the refspec is
    forwarded verbatim. ``paths`` is appended after ``--`` to scope the output.
    """
    cmd = ["--no-pager", "diff"]
    if full:
        pass
    elif use_stat:
        cmd.append("--stat")
    elif name_only:
        cmd.append("--name-only")
    else:
        cmd.append("--name-status")

    if staged:
        cmd.append("--staged")

    if refspec:
        cmd.append(refspec)
    elif not staged:
        cmd.append("HEAD")

    if paths:
        cmd.append("--")
        cmd.extend(paths)
    return cmd


def _print_diff_human_full(*, diff_text: str) -> None:
    """Pipe the full diff through bat (or delta when available)."""
    if HAS_DELTA:
        print_dim(t("using_delta"))
    bat_pipe(diff_text, language="diff")


def _merge_stat_files(
    *,
    files: list[DiffFileEntry],
    status_details: dict[str, DiffFileEntry],
    numstat_details: dict[str, DiffFileEntry],
) -> list[DiffFileEntry]:
    """Enrich diffstat entries with name-status and numstat details."""
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
    refspec: str | None,
    paths: list[str] | None,
    as_json: bool,
) -> int:
    """Render the stat-mode diff output (JSON or human diffstat table)."""
    if not files:
        if as_json:
            print_json(ok_envelope("diff", files=[], count=0))
            return 0
        info(t("no_uncommitted_changes"))
        return 0

    status_details = _name_status_details(cwd, staged=staged, refspec=refspec, paths=paths)
    numstat_details = _numstat_details(cwd, staged=staged, refspec=refspec, paths=paths)
    merged_files = _merge_stat_files(
        files=files,
        status_details=status_details,
        numstat_details=numstat_details,
    )
    binary_warnings = _warn_large_binaries(cwd=cwd, files=merged_files, as_json=as_json)
    if as_json:
        for entry in merged_files:
            raw_code = str(entry.get("code", entry.get("status", "")))
            entry["status_label"] = status_label(raw_code)
        stat_data: dict[str, object] = {
            "files": merged_files,
            "count": len(merged_files),
            "totals": _diff_totals(merged_files),
        }
        if binary_warnings:
            stat_data["binary_warnings"] = binary_warnings
        print_json(ok_envelope("diff", data=stat_data))
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
    """Render name-status or name-only diff output (JSON or human file list)."""
    if not lines:
        if as_json:
            print_json(ok_envelope("diff", files=[], count=0))
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
                code = parts[0].strip()
                files.append(
                    {
                        "status": code,
                        "status_label": status_label(code),
                        "path": parts[1].strip(),
                    }
                )

    if as_json:
        print_json(ok_envelope("diff", files=files, count=len(files)))
        return 0

    print_header(t("changed_files", count=str(len(files))))
    for file_item in files:
        print_file_status(file_item["status"], file_item["path"])
    return 0


def _warn_large_binaries(
    *, cwd: Path, files: list[DiffFileEntry], as_json: bool
) -> list[dict[str, str | float]]:
    """Detect binary files at or above the LFS threshold and warn (human mode).

    Size is read from the working tree when the path exists there; committed
    blobs outside the working tree are skipped to avoid an extra round trip,
    since the binary marker itself is already surfaced in the output. Returns
    the offender list (``{"path", "mib"}``) so JSON callers can include it in
    the envelope -- silent drops in JSON mode would hide the signal from agents.
    """
    offenders: list[dict[str, str | float]] = []
    for entry in files:
        if entry.get("is_binary") is not True:
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            continue
        candidate = cwd / path_value
        try:
            size = candidate.stat().st_size
        except OSError:
            continue
        if size >= LFS_WARN_BYTES:
            mib = round(size / _BYTES_PER_MIB, 1)
            offenders.append({"path": path_value, "mib": mib})
            if not as_json:
                warn(t("diff_binary_lfs_hint", path=path_value, mib=str(mib)))
    return offenders


def _render_summary_output(
    *,
    files: list[DiffFileEntry],
    binary_warnings: list[dict[str, str | float]],
    as_json: bool,
) -> int:
    """Print the compact summary (path + insertions/deletions, no patch)."""
    if not files:
        if as_json:
            print_json(
                ok_envelope("diff", files=[], count=0, totals={"insertions": 0, "deletions": 0})
            )
            return 0
        info(t("no_uncommitted_changes"))
        return 0

    summary_files: list[DiffFileEntry] = []
    for entry in files:
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            continue
        summary_files.append(
            {
                "path": path_value,
                "insertions": entry.get("insertions", 0),
                "deletions": entry.get("deletions", 0),
            }
        )
    totals = _diff_totals(files)
    if as_json:
        summary_data: dict[str, object] = {
            "files": summary_files,
            "count": len(summary_files),
            "totals": totals,
        }
        if binary_warnings:
            summary_data["binary_warnings"] = binary_warnings
        print_json(ok_envelope("diff", data=summary_data))
        return 0

    print_header(t("diff_summary_header", count=str(len(summary_files))))
    for entry in summary_files:
        ins = int(entry.get("insertions", 0) or 0)
        dels = int(entry.get("deletions", 0) or 0)
        print_dim(f"{entry['path']}  +{ins}  -{dels}")
    return 0


def _render_secret_scan_output(
    *, root: Path, refspec: str | None, paths: list[str] | None, as_json: bool
) -> int:
    """Scan the diff patch for leaked credentials and report findings (opt-in).

    The diff flags defeat user config that could bypass the scanner
    (``color.ui=always`` ANSI, external/textconv drivers) -- same reasoning as
    the commit-time guard in ``_staged_diff_text``.
    """
    args = ["--no-pager", "diff", "--no-color", "--no-ext-diff", "--no-textconv"]
    if refspec:
        args.append(refspec)
    else:
        args.append("HEAD")
    if paths:
        args.append("--")
        args.extend(paths)
    result = git_run(args, cwd=root, check=False)
    if result.returncode != 0:
        error(t("git_diff_failed", error=result.stderr.strip()))
        return 1
    findings = secret_scan(result.stdout)
    if as_json:
        print_json(ok_envelope("diff", findings=findings, count=len(findings)))
        return 1 if any(f["severity"] == "high" for f in findings) else 0
    if not findings:
        info(t("secret_scan_clean"))
        return 0
    print_header(t("secret_scan_found_header", count=str(len(findings))))
    for f in findings:
        sev = f["severity"]
        line = t(
            "secret_scan_found",
            rule=f["rule"],
            path=f["path"],
            line=str(f["line"]),
            preview=f["preview"],
        )
        if sev == "high":
            error(line)
        else:
            warn(line)
    return 1 if any(f["severity"] == "high" for f in findings) else 0


def run_diff(
    *,
    refspec: str | None = None,
    paths: list[str] | None = None,
    staged: bool = False,
    stat: bool = False,
    name_only: bool = False,
    full: bool = False,
    summary: bool = False,
    scan_secrets: bool = False,
    as_json: bool = False,
) -> int:
    """Render a diff of changed files, a refspec, or a range.

    With no arguments, shows the working-tree diffstat vs HEAD. ``refspec`` can
    be a commit, branch, or range (``a..b`` / ``a...b``); it is forwarded
    verbatim because git diff compares endpoints, not revision ranges. ``paths``
    scopes the output after ``--``. ``--summary`` prints additions/deletions per
    file with no patch (token-efficient for agents).
    """
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1
    cwd = root

    if not refspec and not staged and not _has_commits(cwd):
        if as_json:
            print_json(ok_envelope("diff", files=[], count=0, note=t("no_commits_yet")))
            return 0
        info(t("no_commits_yet"))
        return 0

    if scan_secrets:
        return _render_secret_scan_output(root=cwd, refspec=refspec, paths=paths, as_json=as_json)

    if summary:
        numstat_details = _numstat_details(cwd, staged=staged, refspec=refspec, paths=paths)
        summary_files = list(numstat_details.values())
        binary_warnings = _warn_large_binaries(cwd=cwd, files=summary_files, as_json=as_json)
        return _render_summary_output(
            files=summary_files, binary_warnings=binary_warnings, as_json=as_json
        )

    use_stat = stat or (not staged and not name_only and not full)
    cmd = _diff_cmd(
        use_stat=use_stat,
        staged=staged,
        name_only=name_only,
        full=full,
        refspec=refspec,
        paths=paths,
    )
    with status(t("status_reading_diff")):
        result = git_run(cmd, cwd=cwd, check=False)
    if result.returncode != 0:
        error(t("git_diff_failed", error=result.stderr.strip()))
        return 1

    if full:
        if as_json:
            print_json(ok_envelope("diff", diff=result.stdout))
        else:
            _print_diff_human_full(diff_text=result.stdout)
        return 0

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if use_stat:
        files = _parse_diffstat_entries(lines)
        return _render_stat_output(
            files=files,
            cwd=cwd,
            staged=staged,
            refspec=refspec,
            paths=paths,
            as_json=as_json,
        )

    return _render_non_stat_output(
        lines=lines, staged=staged, name_only=name_only, as_json=as_json
    )
