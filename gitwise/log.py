"""gitwise log — pretty git log with filters and JSON output."""

import sys

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import HAS_DELTA, bat_pipe, info, print_json


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
        args.append(
            "--format=%C(yellow)%h%C(reset) %C(dim)%ad%C(reset) %C(bold)%an%C(reset)%C(dim)%d%C(reset)%n  %s"
        )
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


def _enrich_with_stats(commits: list[dict[str, str]], cwd: object) -> None:
    from pathlib import Path

    assert isinstance(cwd, Path)
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
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    if as_json:
        args = _build_log_json_args(
            author=author, grep=grep, since=since, until=until, file=file, max_count=max_count
        )
        r = git_run(args, cwd=root, check=False)
        if r.returncode != 0:
            if "does not have any commits yet" in r.stderr:
                print_json({"v": 2, "ok": True, "commits": [], "count": 0})
                return 0
            print(t("git_log_failed", error=r.stderr.strip()), file=sys.stderr)
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
                print(t("no_commits_yet"))
                return 0
            print(t("git_log_failed", error=r.stderr.strip()), file=sys.stderr)
            return 1
        if not r.stdout.strip():
            print(t("no_commits_yet"))
            return 0
        if HAS_DELTA:
            info(t("using_delta"))
        bat_pipe(r.stdout, language="gitlog")

    return 0
