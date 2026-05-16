"""CLI entry point — argparse router for all gitwise subcommands."""

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .i18n import t


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitwise",
        description="CLI for optimizing git + Claude Code workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"gitwise {__version__}")
    parser.add_argument(
        "--lang",
        choices=["es", "en"],
        default=None,
        help="output language (default: auto-detect from locale)",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("doctor", help="check requirements and environment")
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser(
        "setup-agents",
        help="install skills/rules/settings into ~/.claude/ (default) or current repo (--local)",
    )
    p.add_argument(
        "--local",
        action="store_true",
        help="install into .claude/ of current repo instead of global ~/.claude/",
    )
    p.add_argument(
        "--no-skills",
        action="store_true",
        dest="no_skills",
        help="skip skills installation (global mode only)",
    )
    p.add_argument("--dry-run", action="store_true", help="show actions without executing")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    p.add_argument("--json", action="store_true", help="output JSON")
    p.add_argument(
        "--no-symlinks",
        action="store_true",
        help="force @AGENTS.md import fallback (no symlinks) — --local only",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as errors (CI) — --local only",
    )
    p.add_argument(
        "--replace-claude-with-symlink",
        action="store_true",
        dest="replace_claude_with_symlink",
        help="bucket 4: replace CLAUDE.md with symlink to AGENTS.md — --local only",
    )
    p.add_argument(
        "--frozen-time",
        action="store_true",
        dest="frozen_time",
        help="freeze snapshot timestamp — --local only",
    )
    p.add_argument(
        "--no-git-files",
        action="store_true",
        dest="no_git_files",
        help="don't touch .gitignore or .gitattributes — --local only",
    )

    p = sub.add_parser("setup", help="apply modern git defaults")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("audit", help="repository diagnostics")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("summarize", help="compact status + log")
    p.add_argument("--json", action="store_true")
    p.add_argument("--diff", action="store_true")
    p.add_argument("--max-commits", type=int, default=10, dest="max_commits")

    p = sub.add_parser("snapshot", help="generate .claude/git-snapshot.md")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("clean", help="clean up stale branches and refs")
    p.add_argument("--branches", action="store_true")
    p.add_argument("--refs", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("optimize", help="optimize the repository")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("worktree", help="worktree helpers for Claude agents")
    p.add_argument("action", choices=["new", "clean"], nargs="?", metavar="new|clean")
    p.add_argument("branch", nargs="?")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("diff", help="changed file list (git diff --name-status HEAD)")
    diff_group = p.add_mutually_exclusive_group()
    diff_group.add_argument("--staged", action="store_true", help="show staged changes only")
    diff_group.add_argument(
        "--stat", action="store_true", help="show insertions/deletions per file"
    )
    diff_group.add_argument(
        "--full", action="store_true", help="show full diff with delta integration"
    )
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("log", help="pretty git log with filters")
    p.add_argument("--json", action="store_true", help="output JSON")
    p.add_argument("--oneline", action="store_true", help="one line per commit")
    p.add_argument("--author", type=str, default=None, help="filter by author")
    p.add_argument("--grep", type=str, default=None, help="filter by message pattern")
    p.add_argument("--since", type=str, default=None, help="show commits since date")
    p.add_argument("--until", type=str, default=None, help="show commits until date")
    p.add_argument("--file", type=str, default=None, help="show commits for file")
    p.add_argument("--max-count", type=int, default=20, dest="max_count", help="max commits")

    p = sub.add_parser("show", help="commit inspector")
    p.add_argument("ref", nargs="?", default="HEAD", help="commit ref (default: HEAD)")
    p.add_argument("--stat", action="store_true", help="show diffstat")
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("commit", help="smart conventional commit")
    p.add_argument("-m", "--message", type=str, default=None, help="commit message")
    p.add_argument("--type", type=str, default=None, help="commit type (feat/fix/etc)")
    p.add_argument("--scope", type=str, default=None, help="commit scope")
    p.add_argument("--breaking", action="store_true", help="breaking change (!)")
    p.add_argument("--amend", action="store_true", help="amend last commit")
    p.add_argument("--dry-run", action="store_true", help="show without committing")
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("branches", help="branch intelligence dashboard")
    p.add_argument("--stale", action="store_true", help="show stale [gone] branches only")
    p.add_argument("--remote", action="store_true", help="show remote branches")
    p.add_argument("--sort", type=str, default="refname", help="sort field")
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("sync", help="remote fetch, safe pull/push")
    p.add_argument("--pull", action="store_true", help="pull --ff-only after fetch")
    p.add_argument("--push", action="store_true", help="push unpushed commits")
    p.add_argument("--dry-run", action="store_true", help="show planned actions")
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("pr", help="GitHub PR wrapper (requires gh)")
    p.add_argument(
        "action", nargs="?", default="list", choices=["list", "checks"], help="pr action"
    )
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("undo", help="reflog-based undo")
    p.add_argument("ref", nargs="?", default=None, help="target ref (default: HEAD~1)")
    p.add_argument("--soft", action="store_true", help="soft reset (keep working tree)")
    p.add_argument("--steps", type=int, default=1, help="number of steps back")
    p.add_argument("--dry-run", action="store_true", help="show without resetting")
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("update", help="update gitwise (git pull in install directory)")
    p.add_argument("--dry-run", action="store_true")

    return parser


def _run_update(args: argparse.Namespace) -> int:
    from .git import run as git_run

    install_dir = Path(__file__).parent.parent
    if args.dry_run:
        print(t("update_dry_run", dir=str(install_dir)))
        return 0
    print(t("updating_from", dir=str(install_dir)))
    r = git_run(["pull", "--ff-only"], cwd=install_dir, check=False)
    if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != "Already up to date.":
        print(r.stdout.strip())
    elif r.returncode != 0:
        print(r.stderr.strip() or t("error_updating"), file=sys.stderr)
    return r.returncode


def main() -> int:
    from .i18n import set_locale

    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_usage(sys.stderr)
        return 1

    if args.lang:
        set_locale(args.lang)

    start = time.monotonic()

    if args.command == "doctor":
        from .doctor import run_doctor

        ret = run_doctor(as_json=args.json)

    elif args.command == "setup-agents":
        from .setup_agents import run_setup_agents

        ret = run_setup_agents(
            local=args.local,
            no_skills=args.no_skills,
            dry_run=args.dry_run,
            yes=args.yes,
            as_json=args.json,
            no_symlinks=args.no_symlinks,
            strict=args.strict,
            replace_claude_with_symlink=args.replace_claude_with_symlink,
            frozen_time=args.frozen_time,
            no_git_files=args.no_git_files,
        )

    elif args.command == "setup":
        from .setup import run_setup

        ret = run_setup(dry_run=args.dry_run, yes=args.yes, as_json=args.json)

    elif args.command == "audit":
        from .audit import run_audit

        ret = run_audit(quick=args.quick, as_json=args.json)

    elif args.command == "summarize":
        from .summarize import run_summarize

        ret = run_summarize(as_json=args.json, diff=args.diff, max_commits=args.max_commits)

    elif args.command == "snapshot":
        from .snapshot import run_snapshot

        ret = run_snapshot(as_json=args.json)

    elif args.command == "clean":
        from .clean import run_clean

        ret = run_clean(
            branches=args.branches,
            refs=args.refs,
            dry_run=args.dry_run,
            yes=args.yes,
            as_json=args.json,
        )

    elif args.command == "optimize":
        from .optimize import run_optimize

        ret = run_optimize(dry_run=args.dry_run, yes=args.yes, as_json=args.json)

    elif args.command == "worktree":
        from .worktree import run_worktree

        ret = run_worktree(
            args.action, getattr(args, "branch", None), dry_run=args.dry_run, as_json=args.json
        )

    elif args.command == "diff":
        from .diff import run_diff

        ret = run_diff(staged=args.staged, stat=args.stat, full=args.full, as_json=args.json)

    elif args.command == "log":
        from .log import run_log

        ret = run_log(
            as_json=args.json,
            oneline=args.oneline,
            author=args.author,
            grep=args.grep,
            since=args.since,
            until=args.until,
            file=args.file,
            max_count=args.max_count,
        )

    elif args.command == "show":
        from .show import run_show

        ret = run_show(ref=args.ref, stat=args.stat, as_json=args.json)

    elif args.command == "commit":
        from .commit import run_commit

        ret = run_commit(
            message=args.message,
            type=args.type,
            scope=args.scope,
            breaking=args.breaking,
            amend=args.amend,
            dry_run=args.dry_run,
            as_json=args.json,
        )

    elif args.command == "branches":
        from .branches import run_branches

        ret = run_branches(stale=args.stale, remote=args.remote, sort=args.sort, as_json=args.json)

    elif args.command == "sync":
        from .sync import run_sync

        ret = run_sync(pull=args.pull, push=args.push, dry_run=args.dry_run, as_json=args.json)

    elif args.command == "pr":
        from .pr import run_pr

        ret = run_pr(action=args.action, as_json=args.json)

    elif args.command == "undo":
        from .undo import run_undo

        ret = run_undo(
            ref=args.ref, soft=args.soft, steps=args.steps, dry_run=args.dry_run, as_json=args.json
        )

    elif args.command == "update":
        ret = _run_update(args)

    else:
        parser.print_help()
        ret = 0

    elapsed = time.monotonic() - start
    as_json = getattr(args, "json", False)
    if not as_json and elapsed > 0.2 and args.command not in ("doctor",):
        print(t("completed_in", elapsed=f"{elapsed:.1f}"))

    return ret


if __name__ == "__main__":
    sys.exit(main())
