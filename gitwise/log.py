"""gitwise log — pretty git log with filters and JSON output."""

from pathlib import Path

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import bat_pipe, error, info, print_header, print_json, print_table


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
    args = ["log", f"--max-count={max_count}"]
    if graph:
        args.append("--graph")
    if oneline:
        args.append("--oneline")
    else:
        args.append("--format=%h\t%an\t%ad\t%s")
        args.append("--date=short")
    if author:
        args.append(f"--author={author}")
    if grep:
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
    args = [
        "log",
        f"--max-count={max_count}",
        "--format=%H%n%h%n%an%n%ae%n%ad%n%s%n%P%n---END---",
        "--date=iso",
    ]
    if author:
        args.append(f"--author={author}")
    if grep:
        args.append(f"--grep={grep}")
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if file:
        args.append("--")
        args.append(file)
    return args


def _parse_log_json(raw: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    entries = raw.split("---END---")
    for entry in entries:
        lines = [ln for ln in entry.strip().splitlines() if ln.strip()]
        if len(lines) >= 7:
            commits.append(
                {
                    "hash": lines[0],
                    "short_hash": lines[1],
                    "author": lines[2],
                    "email": lines[3],
                    "date": lines[4],
                    "subject": lines[5],
                    "parents": lines[6],
                }
            )
    return commits


def _enrich_with_stats(commits: list[dict[str, str]], cwd: Path) -> None:
    for c in commits:
        r = git_run(
            ["diff-tree", "--no-commit-id", "--stat", "-r", c["hash"]],
            cwd=cwd,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            c["stats"] = r.stdout.strip()
        else:
            c["stats"] = ""


def _parse_log_table(raw: str) -> list[list[str]]:
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


def run_log(
    *,
    as_json: bool = False,
    oneline: bool = False,
    graph: bool = False,
    author: str | None = None,
    grep: str | None = None,
    since: str | None = None,
    until: str | None = None,
    file: str | None = None,
    max_count: int = 20,
) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    if as_json:
        args = _build_log_json_args(
            author=author, grep=grep, since=since, until=until, file=file, max_count=max_count
        )
        r = git_run(args, cwd=root, check=False)
        if r.returncode != 0:
            if "does not have any commits yet" in r.stderr:
                print_json({"v": 2, "ok": True, "commits": [], "count": 0})
                return 0
            error(t("git_log_failed", error=r.stderr.strip()))
            return 1
        commits = _parse_log_json(r.stdout)
        _enrich_with_stats(commits, root)
        print_json({"v": 2, "ok": True, "commits": commits, "count": len(commits)})
    else:
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
        r = git_run(args, cwd=root, check=False)
        if r.returncode != 0:
            if r.stderr and "does not have any commits yet" in r.stderr:
                info(t("no_commits_yet"))
                return 0
            error(t("git_log_failed", error=r.stderr.strip()))
            return 1
        if not r.stdout.strip():
            info(t("no_commits_yet"))
            return 0

        if graph or oneline:
            print_header(t("git_log_title"))
            bat_pipe(r.stdout, language="gitlog")
        else:
            rows = _parse_log_table(r.stdout)
            if not rows:
                info(t("no_commits_yet"))
                return 0

            columns = [
                ("SHA", "sha"),
                ("Author", "author"),
                ("Date", "date"),
                ("Subject", "subject"),
            ]

            print_table(
                title=t("git_log_title"),
                columns=columns,
                rows=rows,
            )

    return 0
