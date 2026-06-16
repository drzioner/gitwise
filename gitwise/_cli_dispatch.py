"""Command dispatchers: thin wrappers that delegate to subcommand modules."""

import argparse
from collections.abc import Callable

from . import __version__
from ._cli_completions import build_completions_script
from ._cli_introspection import (
    canonical_command_name,
    commands_metadata,
    resolve_command_parser,
)
from ._cli_parser import build_parser
from .i18n import t
from .output import print_json
from .utils.json_envelope import error_envelope


def _run_update(args: argparse.Namespace) -> int:
    from .update import run_update

    return run_update(dry_run=args.dry_run, as_json=args.json)


def _run_doctor(args: argparse.Namespace) -> int:
    from .doctor import run_doctor

    return run_doctor(as_json=args.json)


def _run_setup_agents(args: argparse.Namespace) -> int:
    if getattr(args, "list_providers", False) or getattr(args, "list_adapters", False):
        from .i18n import t as _t
        from .setup_agents.providers import list_providers

        adapter_list = list_providers()
        if args.json:
            print_json({"providers": adapter_list, "adapters": adapter_list})
        else:
            from .output import info

            info(_t("providers_available", list=", ".join(adapter_list)))
        return 0

    providers: list[str] | None = args.providers
    adapters_legacy_used = False
    if args.adapters is not None:
        adapters_legacy_used = True
        providers = args.adapters if providers is None else providers + args.adapters

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
        migrate_legacy_claude=args.migrate_legacy_claude,
        frozen_time=args.frozen_time,
        no_git_files=args.no_git_files,
        providers=providers,
        adapters_legacy_used=adapters_legacy_used,
    )


def _run_setup(args: argparse.Namespace) -> int:
    from .setup import run_setup

    return run_setup(
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
        hooks_mode=args.hooks_mode,
    )


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


def _run_completions(args: argparse.Namespace) -> int:
    shell = args.shell
    prog = args.prog
    try:
        script = build_completions_script(shell=shell, prog=prog)
    except ModuleNotFoundError:
        from .output import error as _error

        hint = t("missing_dependency_hint")
        message = t("missing_dependency_completions_shtab")
        if args.json:
            print_json(error_envelope(error=message, code="missing_dependency", hint=hint))
        else:
            _error(message, hint=hint)
        return 1
    except RuntimeError as e:
        message = str(e)
        if args.json:
            print_json(error_envelope(error=message, code="runtime_error"))
        else:
            from .output import error as _error

            _error(message)
        return 1
    except ValueError:
        message = t("completions_unsupported_shell", shell=shell)
        if args.json:
            print_json(error_envelope(error=message, code="unsupported_shell"))
        else:
            from .output import error as _error

            _error(message)
        return 1

    if args.json:
        print_json(
            {
                "v": 2,
                "ok": True,
                "kind": "completions",
                "schema": "gitwise/completions/v1",
                "version": __version__,
                "shell": shell,
                "prog": prog,
                "script": script,
            }
        )
        return 0

    print(script)
    return 0


def _run_commands(args: argparse.Namespace) -> int:
    parser = build_parser()
    commands = commands_metadata(parser)
    payload = {
        "v": 2,
        "ok": True,
        "kind": "commands",
        "schema": "gitwise/commands/v1",
        "version": __version__,
        "commands": commands,
    }

    if args.json:
        print_json(payload)
        return 0

    aliases_label = t("aliases_label")
    for item in commands:
        aliases_list = item["aliases"]
        alias_text = (
            f" ({aliases_label}: {', '.join(str(alias) for alias in aliases_list)})"
            if aliases_list
            else ""
        )
        print(f"{item['name']}: {item['help']}{alias_text}")
    return 0


def _run_schema(args: argparse.Namespace) -> int:
    from .schema import load_command_input_schema

    parser = build_parser()
    command_parser = resolve_command_parser(parser=parser, name=args.name)
    if command_parser is None:
        message = t("schema_unknown_command", name=args.name)
        hint = t("schema_unknown_command_hint")
        if args.json:
            print_json(
                error_envelope(
                    error=message,
                    code="unknown_command",
                    hint=hint,
                    schema="gitwise/schema/v1",
                    kind="schema",
                )
            )
        else:
            from .output import error as _error

            _error(message, hint=hint)
        return 1

    name = canonical_command_name(command_parser)
    schema = load_command_input_schema(command=name, version=args.version)
    if schema is None:
        message = t("schema_file_missing", command=name, version=args.version)
        hint = t("schema_file_missing_hint")
        if args.json:
            print_json(
                error_envelope(
                    error=message,
                    code="schema_not_found",
                    hint=hint,
                    schema="gitwise/schema/v1",
                    kind="schema",
                )
            )
        else:
            from .output import error as _error

            _error(message, hint=hint)
        return 1

    payload = {
        "v": 2,
        "ok": True,
        "kind": "schema",
        "schema": "gitwise/schema/v1",
        "version": __version__,
        "schema_version": args.version,
        "command": name,
        "schema_kind": "cli_input",
        "json_schema": schema,
    }

    print_json(payload)
    return 0


DISPATCH: dict[str, Callable[[argparse.Namespace], int]] = {
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
    "completions": _run_completions,
    "commands": _run_commands,
    "schema": _run_schema,
}
