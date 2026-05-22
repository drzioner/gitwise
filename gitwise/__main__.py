"""CLI entry point — argparse router for all gitwise subcommands."""

import argparse
import sys
import time

from . import __version__
from .design import GitwiseHelpFormatter
from .i18n import t
from .output import print_dim, print_json, set_json_pretty


def _json_safe(value: object) -> object:
    if value is argparse.SUPPRESS:
        return None
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def _subparsers_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _serialize_actions(parser: argparse.ArgumentParser) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for action in parser._actions:
        if action.dest in {"help"}:
            continue
        if isinstance(action, argparse._SubParsersAction):
            continue
        option_strings = list(action.option_strings)
        items.append(
            {
                "kind": "option" if option_strings else "argument",
                "name": action.dest,
                "flags": option_strings,
                "required": bool(getattr(action, "required", False)),
                "nargs": _json_safe(action.nargs),
                "default": _json_safe(action.default),
                "choices": _json_safe(list(action.choices) if action.choices else []),
                "help": "" if action.help is argparse.SUPPRESS else (action.help or ""),
            }
        )
    return items


def _extract_command_token(argv: list[str]) -> str | None:
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token in {"--lang", "--theme"}:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        return token
    return None


def _help_payload(
    parser: argparse.ArgumentParser, command: str | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "v": 2,
        "ok": True,
        "kind": "help",
        "schema": "gitwise/help/v1",
        "version": __version__,
    }

    sub_action = _subparsers_action(parser)
    if command is None or sub_action is None or command not in sub_action.choices:
        commands: list[dict[str, object]] = []
        if sub_action is not None:
            help_by_parser_id: dict[int, str] = {}
            for pseudo in sub_action._choices_actions:
                parser_name = str(pseudo.dest)
                parser_obj = sub_action.choices.get(parser_name)
                if parser_obj is None:
                    continue
                parser_id = id(parser_obj)
                if parser_id not in help_by_parser_id:
                    help_by_parser_id[parser_id] = pseudo.help or ""

            seen_parsers: set[int] = set()
            for name, choice_parser in sorted(sub_action.choices.items()):
                parser_id = id(choice_parser)
                if parser_id in seen_parsers:
                    continue
                seen_parsers.add(parser_id)
                aliases = [
                    alias
                    for alias, alias_parser in sub_action.choices.items()
                    if alias_parser is choice_parser and alias != name
                ]
                commands.append(
                    {
                        "name": name,
                        "help": help_by_parser_id.get(parser_id, choice_parser.description or ""),
                        "aliases": sorted(aliases),
                    }
                )

        payload.update(
            {
                "scope": "root",
                "usage": parser.format_usage().strip(),
                "description": parser.description or "",
                "options": _serialize_actions(parser),
                "commands": sorted(commands, key=lambda item: str(item["name"])),
            }
        )
        return payload

    command_parser = sub_action.choices[command]
    payload.update(
        {
            "scope": "command",
            "command": command,
            "usage": command_parser.format_usage().strip(),
            "description": command_parser.description or "",
            "options": _serialize_actions(command_parser),
        }
    )
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--lang",
        choices=["es", "en"],
        default=None,
        help="output language (default: auto-detect from locale)",
    )
    parent.add_argument(
        "--theme",
        choices=["dark", "light", "auto"],
        default=None,
        help="color theme: dark, light, or auto-detect (default: auto)",
    )
    parent.add_argument("--json", action="store_true", help="output JSON")
    parent.add_argument(
        "--json-pretty",
        "--pretty",
        dest="json_pretty",
        action="store_true",
        help="pretty-print JSON output",
    )

    parser = argparse.ArgumentParser(
        prog="gitwise",
        description="CLI for optimizing git workflows and Claude Code integration",
        formatter_class=GitwiseHelpFormatter,
        parents=[parent],
    )
    parser.add_argument("--version", action="version", version=f"gitwise {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("doctor", help="check requirements and environment", parents=[parent])

    p = sub.add_parser(
        "setup-agents",
        help="install skills/rules/settings into ~/.claude/ (default) or current repo (--local)",
        parents=[parent],
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
    p.add_argument(
        "--adapters",
        nargs="*",
        default=None,
        dest="adapters",
        help="install config for coding agents (comma-separated: cursor,aider or multiple: --adapters cursor aider)",
    )
    p.add_argument(
        "--list-adapters",
        action="store_true",
        dest="list_adapters",
        help="list available adapters and exit",
    )

    p = sub.add_parser("setup", help="apply modern git defaults", parents=[parent])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")

    p = sub.add_parser("audit", help="repository diagnostics", parents=[parent])
    p.add_argument("--quick", action="store_true")

    p = sub.add_parser("summarize", help="compact status + log", parents=[parent])
    p.add_argument("--diff", action="store_true")
    p.add_argument("--max-commits", type=int, default=10, dest="max_commits")

    p = sub.add_parser("snapshot", help="generate .claude/git-snapshot.md", parents=[parent])

    p = sub.add_parser(
        "clean",
        help="clean up stale branches and refs",
        aliases=["branch-clean"],
        parents=[parent],
    )
    p.add_argument("--branches", action="store_true")
    p.add_argument("--refs", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")

    p = sub.add_parser("optimize", help="optimize the repository", parents=[parent])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")

    p = sub.add_parser("worktree", help="worktree helpers for Claude agents", parents=[parent])
    p.add_argument("action", choices=["new", "clean"], nargs="?", metavar="new|clean")
    p.add_argument("branch", nargs="?")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser(
        "diff",
        help="changed files with diffstat (default), or patch view",
        parents=[parent],
    )
    diff_group = p.add_mutually_exclusive_group()
    diff_group.add_argument("--staged", action="store_true", help="show staged changes only")
    diff_group.add_argument("--name-only", action="store_true", help="show only file names")
    diff_group.add_argument(
        "--full", "--patch", action="store_true", help="show full patch with delta integration"
    )
    p.add_argument("--stat", action="store_true", help="show diffstat (default behavior)")

    p = sub.add_parser("log", help="pretty git log with filters", parents=[parent])
    p.add_argument("--oneline", action="store_true", help="one line per commit")
    p.add_argument("--graph", action="store_true", help="show branch topology graph")
    p.add_argument("--author", type=str, default=None, help="filter by author")
    p.add_argument("--grep", type=str, default=None, help="filter by message pattern")
    p.add_argument("--since", type=str, default=None, help="show commits since date")
    p.add_argument("--until", type=str, default=None, help="show commits until date")
    p.add_argument("--file", type=str, default=None, help="show commits for file")
    p.add_argument("--max-count", type=int, default=20, dest="max_count", help="max commits")

    p = sub.add_parser("show", help="commit inspector", parents=[parent])
    p.add_argument("ref", nargs="?", default="HEAD", help="commit ref (default: HEAD)")
    p.add_argument("--stat", action="store_true", help="show diffstat")

    p = sub.add_parser("commit", help="smart conventional commit", parents=[parent])
    p.add_argument("-m", "--message", type=str, default=None, help="commit message")
    p.add_argument("--type", type=str, default=None, help="commit type (feat/fix/etc)")
    p.add_argument("--scope", type=str, default=None, help="commit scope")
    p.add_argument("--breaking", action="store_true", help="breaking change (!)")
    p.add_argument("--amend", action="store_true", help="amend last commit")
    p.add_argument("--dry-run", action="store_true", help="show without committing")

    p = sub.add_parser("branches", help="branch intelligence dashboard", parents=[parent])
    p.add_argument("--stale", action="store_true", help="show stale [gone] branches only")
    p.add_argument("--remote", action="store_true", help="show remote branches")
    p.add_argument(
        "--sort",
        type=str,
        default="refname",
        help="sort field: refname, committerdate, -committerdate",
    )

    p = sub.add_parser("sync", help="remote fetch, safe pull/push", parents=[parent])
    p.add_argument("--pull", action="store_true", help="pull --ff-only after fetch")
    p.add_argument("--push", action="store_true", help="push unpushed commits")
    p.add_argument("--remote", type=str, default=None, help="specific remote (default: all)")
    p.add_argument("--dry-run", action="store_true", help="show planned actions")

    p = sub.add_parser("pr", help="GitHub PR wrapper (requires gh)", parents=[parent])
    p.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=["list", "checks", "view", "comments"],
        help="pr action",
    )
    p.add_argument(
        "selector",
        nargs="?",
        default=None,
        help="PR number/url/branch (default: current branch PR)",
    )

    p = sub.add_parser("undo", help="reflog-based undo", parents=[parent])
    p.add_argument("ref", nargs="?", default=None, help="target ref (default: HEAD~1)")
    p.add_argument("--soft", action="store_true", help="soft reset (keep working tree)")
    p.add_argument("--steps", type=int, default=1, help="number of steps back")
    p.add_argument("--dry-run", action="store_true", help="show without resetting")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation for --hard")

    p = sub.add_parser("context", help="enriched repo snapshot for LLMs", parents=[parent])

    p = sub.add_parser("health", help="repo health score (0-100)", parents=[parent])

    p = sub.add_parser(
        "stash",
        help="manage stashes (list/show/pop/drop/clear)",
        parents=[parent],
    )
    p.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=["list", "show", "pop", "drop", "clear", "clean"],
    )
    p.add_argument("--index", type=int, default=0, help="stash index (default: 0)")
    p.add_argument("--dry-run", action="store_true", help="dry run (clear only)")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    p.add_argument("--patch", action="store_true", help="show full patch (show only)")

    p = sub.add_parser("tag", help="semver-aware tag management", parents=[parent])
    p.add_argument(
        "action", nargs="?", default="list", choices=["list", "latest", "create", "delete"]
    )
    p.add_argument("name", nargs="?", help="tag name (for create/delete)")
    p.add_argument("--bump", choices=["major", "minor", "patch"], help="bump semver part")
    p.add_argument("-m", "--message", type=str, help="annotated tag message")
    p.add_argument("--dry-run", action="store_true", help="show without executing")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")

    p = sub.add_parser("merge", help="merge/rebase with pre-flight checks", parents=[parent])
    p.add_argument("branch", help="branch to merge/rebase from")
    p.add_argument("--rebase", action="store_true", help="rebase instead of merge")
    p.add_argument("--no-ff", action="store_true", help="force no-fast-forward")
    p.add_argument("--dry-run", action="store_true", help="show checks without merging")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")

    p = sub.add_parser(
        "conflicts", help="conflict detection and resolution helper", parents=[parent]
    )
    p.add_argument("--ours", action="store_true", help="resolve all conflicts using ours")
    p.add_argument("--theirs", action="store_true", help="resolve all conflicts using theirs")

    p = sub.add_parser(
        "suggest",
        help="suggest commit message from staged diff",
        aliases=["commit-suggest"],
        parents=[parent],
    )

    p = sub.add_parser(
        "pick", help="cherry-pick or revert commits", aliases=["cherry-pick"], parents=[parent]
    )
    p.add_argument("refs", nargs="*", help="commit refs to pick/revert")
    p.add_argument("--revert", action="store_true", help="revert instead of cherry-pick")
    p.add_argument(
        "--continue", dest="continue_", action="store_true", help="continue after conflict"
    )
    p.add_argument("--abort", action="store_true", help="abort in-progress pick/revert")
    p.add_argument("--dry-run", action="store_true", help="show without executing")

    p = sub.add_parser(
        "update", help="update gitwise (git pull in install directory)", parents=[parent]
    )
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("status", help="enhanced git status for humans and AI", parents=[parent])

    return parser


def _run_update(args: argparse.Namespace) -> int:
    from .update import run_update

    return run_update(dry_run=args.dry_run, as_json=args.json)


def _run_doctor(args: argparse.Namespace) -> int:
    from .doctor import run_doctor

    return run_doctor(as_json=args.json)


def _run_setup_agents(args: argparse.Namespace) -> int:
    if getattr(args, "list_adapters", False):
        from .i18n import t as _t
        from .setup_agents.adapters import list_adapters

        adapter_list = list_adapters()
        if args.json:
            print_json({"adapters": adapter_list})
        else:
            from .output import info

            info(_t("adapters_available", list=", ".join(adapter_list)))
        return 0

    from ._cli_setup_agents import run_setup_agents

    return run_setup_agents(
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
        adapters=args.adapters,
    )


def _run_setup(args: argparse.Namespace) -> int:
    from .setup import run_setup

    return run_setup(dry_run=args.dry_run, yes=args.yes, as_json=args.json)


def _run_audit(args: argparse.Namespace) -> int:
    from .audit import run_audit

    return run_audit(quick=args.quick, as_json=args.json)


def _run_summarize(args: argparse.Namespace) -> int:
    from .summarize import run_summarize

    return run_summarize(as_json=args.json, diff=args.diff, max_commits=args.max_commits)


def _run_snapshot(args: argparse.Namespace) -> int:
    from .snapshot import run_snapshot

    return run_snapshot(as_json=args.json)


def _run_clean(args: argparse.Namespace) -> int:
    from .clean import run_clean

    return run_clean(
        branches=args.branches,
        refs=args.refs,
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
    )


def _run_optimize(args: argparse.Namespace) -> int:
    from .optimize import run_optimize

    return run_optimize(dry_run=args.dry_run, yes=args.yes, as_json=args.json)


def _run_worktree(args: argparse.Namespace) -> int:
    from .worktree import run_worktree

    return run_worktree(
        args.action, getattr(args, "branch", None), dry_run=args.dry_run, as_json=args.json
    )


def _run_diff(args: argparse.Namespace) -> int:
    from .diff import run_diff

    return run_diff(
        staged=args.staged,
        stat=args.stat,
        name_only=args.name_only,
        full=args.full,
        as_json=args.json,
    )


def _run_log(args: argparse.Namespace) -> int:
    from .log import run_log

    return run_log(
        as_json=args.json,
        oneline=args.oneline,
        graph=args.graph,
        author=args.author,
        grep=args.grep,
        since=args.since,
        until=args.until,
        file=args.file,
        max_count=args.max_count,
    )


def _run_show(args: argparse.Namespace) -> int:
    from .show import run_show

    return run_show(ref=args.ref, stat=args.stat, as_json=args.json)


def _run_commit(args: argparse.Namespace) -> int:
    from .commit import run_commit

    return run_commit(
        message=args.message,
        type=args.type,
        scope=args.scope,
        breaking=args.breaking,
        amend=args.amend,
        dry_run=args.dry_run,
        as_json=args.json,
    )


def _run_branches(args: argparse.Namespace) -> int:
    from .branches import run_branches

    return run_branches(stale=args.stale, remote=args.remote, sort=args.sort, as_json=args.json)


def _run_sync(args: argparse.Namespace) -> int:
    from .sync import run_sync

    return run_sync(
        pull=args.pull,
        push=args.push,
        remote=args.remote,
        dry_run=args.dry_run,
        as_json=args.json,
    )


def _run_pr(args: argparse.Namespace) -> int:
    from .pr import run_pr

    return run_pr(action=args.action, selector=args.selector, as_json=args.json)


def _run_undo(args: argparse.Namespace) -> int:
    from .undo import run_undo

    return run_undo(
        ref=args.ref,
        soft=args.soft,
        steps=args.steps,
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
    )


def _run_context(args: argparse.Namespace) -> int:
    from .context import run_context

    return run_context(as_json=args.json)


def _run_health(args: argparse.Namespace) -> int:
    from .health import run_health

    return run_health(as_json=args.json)


def _run_stash(args: argparse.Namespace) -> int:
    from .stash import run_stash

    return run_stash(
        action=args.action,
        index=args.index,
        as_json=args.json,
        yes=args.yes,
        dry_run=args.dry_run,
        patch=args.patch,
    )


def _run_tag(args: argparse.Namespace) -> int:
    from .tag import run_tag

    return run_tag(
        action=args.action,
        name=getattr(args, "name", None),
        bump=args.bump,
        message=args.message,
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
    )


def _run_merge(args: argparse.Namespace) -> int:
    from .merge import run_merge

    return run_merge(
        args.branch,
        rebase=args.rebase,
        no_ff=args.no_ff,
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
    )


def _run_conflicts(args: argparse.Namespace) -> int:
    from .conflicts import run_conflicts

    return run_conflicts(ours=args.ours, theirs=args.theirs, as_json=args.json)


def _run_suggest(args: argparse.Namespace) -> int:
    from .suggest import run_suggest

    return run_suggest(as_json=args.json)


def _run_pick(args: argparse.Namespace) -> int:
    from .pick import run_pick

    return run_pick(
        args.refs,
        revert=args.revert,
        continue_=args.continue_,
        abort=args.abort,
        dry_run=args.dry_run,
        as_json=args.json,
    )


def _run_status(args: argparse.Namespace) -> int:
    from .status import run_status

    return run_status(as_json=args.json)


_DISPATCH: dict = {
    "doctor": _run_doctor,
    "setup-agents": _run_setup_agents,
    "setup": _run_setup,
    "audit": _run_audit,
    "summarize": _run_summarize,
    "snapshot": _run_snapshot,
    "clean": _run_clean,
    "branch-clean": _run_clean,
    "optimize": _run_optimize,
    "worktree": _run_worktree,
    "diff": _run_diff,
    "log": _run_log,
    "show": _run_show,
    "commit": _run_commit,
    "branches": _run_branches,
    "sync": _run_sync,
    "pr": _run_pr,
    "undo": _run_undo,
    "context": _run_context,
    "health": _run_health,
    "stash": _run_stash,
    "tag": _run_tag,
    "merge": _run_merge,
    "conflicts": _run_conflicts,
    "suggest": _run_suggest,
    "commit-suggest": _run_suggest,
    "pick": _run_pick,
    "cherry-pick": _run_pick,
    "update": _run_update,
    "status": _run_status,
}


def main() -> int:
    import os

    from ._runtime_config import reset_runtime_config
    from .i18n import set_locale

    parser = _build_parser()
    raw_argv = sys.argv[1:]
    wants_json_pretty = "--json-pretty" in raw_argv or "--pretty" in raw_argv
    if wants_json_pretty:
        set_json_pretty(True)

    wants_json_help = ("--json" in raw_argv or wants_json_pretty) and (
        "--help" in raw_argv or "-h" in raw_argv
    )
    if wants_json_help:
        command = _extract_command_token(raw_argv)
        print_json(_help_payload(parser, command))
        return 0

    args = parser.parse_args()
    if args.json_pretty:
        args.json = True

    if args.command is None:
        if args.json:
            print_json(
                {
                    **_help_payload(parser),
                    "ok": False,
                    "error": "missing_command",
                }
            )
            return 1
        parser.print_usage(sys.stderr)
        return 1

    if args.theme and args.theme != "auto":
        os.environ["GITWISE_THEME"] = args.theme
        reset_runtime_config()

    set_json_pretty(args.json_pretty)

    if args.lang:
        set_locale(args.lang)

    start = time.monotonic()

    handler = _DISPATCH.get(args.command)
    if handler is not None:
        try:
            ret = handler(args)
        except KeyboardInterrupt:
            ret = 130
        except SystemExit:
            raise
        except Exception:
            from .output import error as _error

            _error(t("unexpected_error"))
            ret = 1
    else:
        parser.print_help(sys.stderr)
        ret = 1

    elapsed = time.monotonic() - start
    as_json = getattr(args, "json", False)
    if not as_json and elapsed > 0.2 and args.command not in ("doctor",):
        print_dim(t("completed_in", elapsed=f"{elapsed:.1f}"))

    return ret


if __name__ == "__main__":
    sys.exit(main())
