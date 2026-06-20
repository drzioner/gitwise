"""gitwise log — pretty git log with filters and JSON output."""

from pathlib import Path

from gitwise.git import require_root, validate_author_pattern, validate_grep_pattern
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import bat_pipe, error, info, print_json, print_table, status
from gitwise.utils.json_envelope import error_envelope, ok_envelope


def _build_log_args(
    *,
    author: str | None = None,
    grep: str | None = None,
    since: str | None = None,
    until: str | None = None,
    file: str | None = None,
    oneline: bool = False,
    graph: bool = False,
    max_count: int = 20,
) -> list[str]:
    """Build the ``git log`` argv for human output (table, oneline, or graph).

    Raises ValueError if author or grep patterns fail validation.
    """
    args = ["log", f"--max-count={max_count}"]
    if graph:
        args.append("--graph")
    if oneline:
        args.append("--oneline")
    else:
        args.append("--format=%h\t%an\t%ad\t%s")
        args.append("--date=short")
    if author:
        if not validate_author_pattern(author):
            error(t("invalid_author_pattern", pattern=author[:50]))
            raise ValueError(f"unsafe author pattern: {author[:50]}")
        args.append(f"--author={author}")
    if grep:
        if not validate_grep_pattern(grep):
            error(t("invalid_grep_pattern", pattern=grep[:50]))
            raise ValueError(f"unsafe grep pattern: {grep[:50]}")
        args.append(f"--grep={grep}")
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if file:
        args.append("--")
        args.append(file)
    return args


def _build_log_json_args(
    *,
    author: str | None = None,
    grep: str | None = None,
    since: str | None = None,
    until: str | None = None,
    file: str | None = None,
    max_count: int = 20,
) -> list[str]:
    """Build the ``git log`` argv for structured JSON output.

    Uses a multi-line format with ``---END---`` record separators.
    Raises ValueError if author or grep patterns fail validation.
    """
    args = [
        "log",
        f"--max-count={max_count}",
        "--format=___GW_REC___%H%n%h%n%an%n%ae%n%ad%n%s%n%P",
        "--date=iso-strict",
        "--numstat",
    ]
    if author:
        if not validate_author_pattern(author):
            error(t("invalid_author_pattern", pattern=author[:50]))
            raise ValueError(f"unsafe author pattern: {author[:50]}")
        args.append(f"--author={author}")
    if grep:
        if not validate_grep_pattern(grep):
            error(t("invalid_grep_pattern", pattern=grep[:50]))
            raise ValueError(f"unsafe grep pattern: {grep[:50]}")
        args.append(f"--grep={grep}")
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if file:
        args.append("--")
        args.append(file)
    return args


_REC_MARKER = "___GW_REC___"


def _parse_log_json(raw: str) -> list[dict[str, object]]:
    """Parse the ``___GW_REC___``-marked log (with ``--numstat``) into commit dicts.

    Each commit carries ``parents`` as a list of hashes and ``stats`` as a list
    of ``{path, insertions, deletions, binary}`` records (roadmap J7).
    """
    commits: list[dict[str, object]] = []
    lines = raw.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        if not line.startswith(_REC_MARKER):
            i += 1
            continue
        full_hash = line.removeprefix(_REC_MARKER)
        short_hash = lines[i + 1] if i + 1 < n else ""
        author = lines[i + 2] if i + 2 < n else ""
        email = lines[i + 3] if i + 3 < n else ""
        date = lines[i + 4] if i + 4 < n else ""
        subject = lines[i + 5] if i + 5 < n else ""
        parents_str = lines[i + 6] if i + 6 < n else ""
        i += 7
        stats: list[dict[str, object]] = []
        while i < n and not lines[i].startswith(_REC_MARKER):
            stat_line = lines[i]
            i += 1
            if not stat_line:
                continue
            parts = stat_line.split("\t")
            if len(parts) != 3:
                continue
            ins, dels, path = parts
            is_bin = ins == "-" or dels == "-"
            try:
                insertions = 0 if is_bin else int(ins)
                deletions = 0 if is_bin else int(dels)
            except ValueError:
                continue
            stats.append(
                {
                    "path": path,
                    "insertions": insertions,
                    "deletions": deletions,
                    "binary": is_bin,
                }
            )
        commits.append(
            {
                "hash": full_hash,
                "short_hash": short_hash,
                "author": author,
                "email": email,
                "date": date,
                "subject": subject,
                "parents": parents_str.split() if parents_str else [],
                "stats": stats,
            }
        )
    return commits


def _parse_log_table(raw: str) -> list[list[str]]:
    """Parse tab-separated log lines into rows of [hash, author, date, subject]."""
    rows: list[list[str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 4:
            rows.append(
                [
                    parts[0],
                    parts[1],
                    parts[2],
                    parts[3],
                ]
            )
        elif len(parts) >= 3:
            rows.append(
                [
                    parts[0],
                    parts[1],
                    parts[2],
                    "",
                ]
            )
    return rows


def _run_log_json(
    *,
    root: Path,
    author: str | None,
    grep: str | None,
    since: str | None,
    until: str | None,
    file: str | None,
    max_count: int,
    json_lines: bool = False,
) -> int:
    """Execute git log and emit structured JSON with enriched per-commit stats.

    With ``json_lines``, stream one compact v3 envelope per commit (NDJSON) for
    incremental processing instead of a single blob.
    """
    try:
        args = _build_log_json_args(
            author=author,
            grep=grep,
            since=since,
            until=until,
            file=file,
            max_count=max_count + 1,
        )
    except ValueError as exc:
        print_json(error_envelope("log", error=str(exc), code="invalid_argument"))
        return 1
    result = git_run(args, cwd=root, check=False)
    if result.returncode != 0:
        if "does not have any commits yet" in result.stderr:
            print_json(ok_envelope("log", commits=[], count=0, total=0, truncated=False))
            return 0
        print_json(
            error_envelope(
                "log",
                error=t("git_log_failed", error=result.stderr.strip()),
                code="git_log_failed",
            )
        )
        return 1
    commits = _parse_log_json(result.stdout)
    total = len(commits)
    truncated = total > max_count
    commits = commits[:max_count]
    if json_lines:
        from gitwise.output import print_json_line

        for commit in commits:
            print_json_line(ok_envelope("log", commit=commit))
        return 0
    hints: list[str] = []
    if truncated:
        hints.append(f"gitwise log --max-count {max_count} (more commits exist)")
    print_json(
        ok_envelope(
            "log",
            commits=commits,
            count=len(commits),
            total=total,
            truncated=truncated,
            hints=hints or None,
        )
    )
    return 0


def _run_log_human(
    *,
    root: Path,
    oneline: bool,
    graph: bool,
    author: str | None,
    grep: str | None,
    since: str | None,
    until: str | None,
    file: str | None,
    max_count: int,
) -> int:
    """Execute git log and render as a table, oneline, or graph via bat."""
    try:
        args = _build_log_args(
            oneline=oneline,
            graph=graph,
            author=author,
            grep=grep,
            since=since,
            until=until,
            file=file,
            max_count=max_count,
        )
    except ValueError:
        return 1
    with status(t("status_reading_log")):
        result = git_run(args, cwd=root, check=False)
    if result.returncode != 0:
        if result.stderr and "does not have any commits yet" in result.stderr:
            info(t("no_commits_yet"))
            return 0
        error(t("git_log_failed", error=result.stderr.strip()))
        return 1
    if not result.stdout.strip():
        info(t("no_commits_yet"))
        return 0
    if _run_log_human_plain_or_graph(raw=result.stdout, graph=graph, oneline=oneline):
        return 0

    return _print_log_table(result.stdout)


def _print_log_table(raw: str) -> int:
    """Render the log as a formatted table with SHA, author, date, and subject columns."""
    rows = _parse_log_table(raw)
    if not rows:
        info(t("no_commits_yet"))
        return 0
    columns = [
        (t("col_sha"), "sha"),
        (t("col_author"), "author"),
        (t("col_date"), "date"),
        (t("col_subject"), "subject"),
    ]
    print_table(
        title=t("git_log_title"),
        columns=columns,
        rows=rows,
        no_wrap_columns={0, 2},
        min_widths={0: 7, 2: 10},
        max_widths={0: 10, 1: 20},
        overflow_columns={0: "crop", 1: "ellipsis", 2: "crop", 3: "ellipsis"},
        column_ratios={3: 4},
    )
    return 0


def _run_log_human_plain_or_graph(*, raw: str, graph: bool, oneline: bool) -> bool:
    """Pipe raw output through bat when graph or oneline mode is active.

    Returns True if output was handled, False to fall through to table rendering.
    """
    if graph or oneline:
        bat_pipe(raw, language="gitlog")
        return True
    return False


def run_log(
    *,
    as_json: bool = False,
    json_lines: bool = False,
    oneline: bool = False,
    graph: bool = False,
    author: str | None = None,
    grep: str | None = None,
    since: str | None = None,
    until: str | None = None,
    file: str | None = None,
    max_count: int = 20,
) -> int:
    """Display commit history with optional filters, graph, oneline, or JSON output."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    if as_json or json_lines:
        return _run_log_json(
            root=root,
            author=author,
            grep=grep,
            since=since,
            until=until,
            file=file,
            max_count=max_count,
            json_lines=json_lines,
        )

    return _run_log_human(
        root=root,
        oneline=oneline,
        graph=graph,
        author=author,
        grep=grep,
        since=since,
        until=until,
        file=file,
        max_count=max_count,
    )
