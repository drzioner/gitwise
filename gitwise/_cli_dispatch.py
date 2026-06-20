"""Command dispatchers: thin wrappers that delegate to subcommand modules."""

import argparse
import sys
from collections.abc import Callable

from gitwise.utils.json_envelope import error_envelope, ok_envelope

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


def _run_update(args: argparse.Namespace) -> int:
    """Dispatch to ``update`` subcommand."""
    from .update import run_update

    return run_update(dry_run=args.dry_run, as_json=args.json)


def _run_doctor(args: argparse.Namespace) -> int:
    """Dispatch to ``doctor`` subcommand."""
    from .doctor import run_doctor

    return run_doctor(as_json=args.json)


def _run_setup_agents(args: argparse.Namespace) -> int:
    """Dispatch to ``setup-agents`` subcommand, handling provider listing."""
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
    """Dispatch to ``setup`` subcommand."""
    from .setup import run_setup

    return run_setup(
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
        hooks_mode=args.hooks_mode,
    )


def _run_audit(args: argparse.Namespace) -> int:
    """Dispatch to ``audit`` subcommand."""
    from .audit import run_audit

    return run_audit(quick=args.quick, as_json=args.json)


def _run_summarize(args: argparse.Namespace) -> int:
    """Dispatch to ``summarize`` subcommand."""
    from .summarize import run_summarize

    return run_summarize(as_json=args.json, diff=args.diff, max_commits=args.max_commits)


def _run_snapshot(args: argparse.Namespace) -> int:
    """Dispatch to ``snapshot`` subcommand."""
    from .snapshot import run_snapshot

    return run_snapshot(as_json=args.json)


def _run_clean(args: argparse.Namespace) -> int:
    """Dispatch to ``clean`` subcommand."""
    from .clean import run_clean

    return run_clean(
        branches=args.branches,
        refs=args.refs,
        dry_run=args.dry_run,
        yes=args.yes,
        as_json=args.json,
    )


def _run_optimize(args: argparse.Namespace) -> int:
    """Dispatch to ``optimize`` subcommand."""
    from .optimize import run_optimize

    return run_optimize(dry_run=args.dry_run, yes=args.yes, as_json=args.json)


def _run_worktree(args: argparse.Namespace) -> int:
    """Dispatch to ``worktree`` subcommand."""
    from .worktree import run_worktree

    return run_worktree(
        args.action, getattr(args, "branch", None), dry_run=args.dry_run, as_json=args.json
    )


def _recover_diff_pathspec_boundary() -> tuple[str | None, list[str] | None]:
    """Recover the explicit ``--`` pathspec boundary argparse loses.

    With ``refspec nargs="?"`` + ``paths nargs="*"``, a path-only invocation
    like ``gitwise diff -- src/`` mis-assigns ``src/`` to ``refspec``. git
    treats ``--`` as a hard pathspec separator, so honor it here: anything
    positional before ``--`` (excluding flags) feeds ``refspec``; anything
    after ``--`` is literal paths, even values starting with ``-``.

    Raises ``ValueError`` when more than one positional precedes ``--``, since
    ``gitwise diff`` accepts a single refspec (two-commit diffs use ``a..b``);
    failing fast beats silently dropping the extras.
    """
    try:
        sub_idx = sys.argv.index("diff")
    except ValueError:
        return None, None
    cmd_argv = sys.argv[sub_idx + 1 :]
    if "--" not in cmd_argv:
        return None, None
    sep = cmd_argv.index("--")
    before = [a for a in cmd_argv[:sep] if not a.startswith("-")]
    after = list(cmd_argv[sep + 1 :])
    if len(before) > 1:
        raise ValueError(t("diff_too_many_refs", count=str(len(before))))
    refspec = before[0] if before else None
    paths = after if after else None
    return refspec, paths


def _run_diff(args: argparse.Namespace) -> int:
    """Dispatch to ``diff`` subcommand."""
    from .diff import run_diff
    from .output import error as error_out

    refspec = args.refspec
    paths = args.paths
    # Honor `--` as a pathspec separator (git semantics). argparse's nargs="?"
    # + nargs="*" otherwise mis-assigns path-only invocations to refspec.
    if "--" in sys.argv:
        try:
            recovered_refspec, recovered_paths = _recover_diff_pathspec_boundary()
        except ValueError as exc:
            if args.json:
                print_json(error_envelope("diff", error=str(exc), code="too_many_refs"))
            else:
                error_out(str(exc))
            return 1
        if recovered_refspec is not None or recovered_paths is not None:
            refspec = recovered_refspec
            paths = recovered_paths

    return run_diff(
        refspec=refspec,
        paths=paths,
        staged=args.staged,
        stat=args.stat,
        name_only=args.name_only,
        full=args.full,
        summary=args.summary,
        scan_secrets=args.scan_secrets,
        as_json=args.json,
    )


def _run_log(args: argparse.Namespace) -> int:
    """Dispatch to ``log`` subcommand."""
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
    """Dispatch to ``show`` subcommand."""
    from .show import run_show

    return run_show(ref=args.ref, stat=args.stat, as_json=args.json)


def _run_commit(args: argparse.Namespace) -> int:
    """Dispatch to ``commit`` subcommand."""
    from .commit import run_commit

    return run_commit(
        message=args.message,
        type=args.type,
        scope=args.scope,
        breaking=args.breaking,
        amend=args.amend,
        dry_run=args.dry_run,
        allow_secret=args.allow_secret,
        as_json=args.json,
    )


def _run_branches(args: argparse.Namespace) -> int:
    """Dispatch to ``branches`` subcommand."""
    from .branches import run_branches

    return run_branches(stale=args.stale, remote=args.remote, sort=args.sort, as_json=args.json)


def _run_sync(args: argparse.Namespace) -> int:
    """Dispatch to ``sync`` subcommand."""
    from .sync import run_sync

    return run_sync(
        pull=args.pull,
        push=args.push,
        remote=args.remote,
        dry_run=args.dry_run,
        as_json=args.json,
    )


def _run_pr(args: argparse.Namespace) -> int:
    """Dispatch to ``pr`` subcommand."""
    from .pr import run_pr

    return run_pr(action=args.action, selector=args.selector, as_json=args.json)


def _run_undo(args: argparse.Namespace) -> int:
    """Dispatch to ``undo`` subcommand."""
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
    """Dispatch to ``context`` subcommand."""
    from .context import run_context

    return run_context(as_json=args.json)


def _run_health(args: argparse.Namespace) -> int:
    """Dispatch to ``health`` subcommand."""
    from .health import run_health

    return run_health(as_json=args.json)


def _run_stash(args: argparse.Namespace) -> int:
    """Dispatch to ``stash`` subcommand."""
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
    """Dispatch to ``tag`` subcommand."""
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
    """Dispatch to ``merge`` subcommand."""
    from .merge import run_merge

    return run_merge(
        args.branch,
        rebase=args.rebase,
        no_ff=args.no_ff,
        dry_run=args.dry_run,
        yes=args.yes,
        abort=args.abort,
        continue_merge=args.continue_merge,
        as_json=args.json,
    )


def _run_conflicts(args: argparse.Namespace) -> int:
    """Dispatch to ``conflicts`` subcommand."""
    from .conflicts import run_conflicts

    return run_conflicts(ours=args.ours, theirs=args.theirs, as_json=args.json)


def _run_suggest(args: argparse.Namespace) -> int:
    """Dispatch to ``suggest`` subcommand."""
    from .suggest import run_suggest

    return run_suggest(as_json=args.json)


def _run_pick(args: argparse.Namespace) -> int:
    """Dispatch to ``pick`` / ``cherry-pick`` subcommand."""
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
    """Dispatch to ``status`` subcommand."""
    from .status import run_status

    return run_status(as_json=args.json)


def _run_completions(args: argparse.Namespace) -> int:
    """Generate and output a shell completions script.

    Returns 1 on missing dependency (shtab), unsupported shell, or
    runtime error.
    """
    shell = args.shell
    prog = args.prog
    try:
        script = build_completions_script(shell=shell, prog=prog)
    except ModuleNotFoundError:
        from .output import error as _error

        hint = t("missing_dependency_hint")
        message = t("missing_dependency_completions_shtab")
        if args.json:
            print_json(
                error_envelope("completions", error=message, code="missing_dependency", hint=hint)
            )
        else:
            _error(message, hint=hint)
        return 1
    except RuntimeError as e:
        message = str(e)
        if args.json:
            print_json(error_envelope("completions", error=message, code="runtime_error"))
        else:
            from .output import error as _error

            _error(message)
        return 1
    except ValueError:
        message = t("completions_unsupported_shell", shell=shell)
        if args.json:
            print_json(error_envelope("completions", error=message, code="unsupported_shell"))
        else:
            from .output import error as _error

            _error(message)
        return 1

    if args.json:
        print_json(
            ok_envelope(
                "completions",
                data={
                    "kind": "completions",
                    "schema": "gitwise/completions/v1",
                    "version": __version__,
                    "shell": shell,
                    "prog": prog,
                    "script": script,
                },
            )
        )
        return 0

    print(script)
    return 0


def _run_commands(args: argparse.Namespace) -> int:
    """List all registered subcommands with aliases."""
    parser = build_parser()
    commands = commands_metadata(parser)
    payload = ok_envelope(
        "commands",
        data={
            "kind": "commands",
            "schema": "gitwise/commands/v1",
            "version": __version__,
            "commands": commands,
        },
    )

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
    """Print the JSON Schema for a subcommand's CLI input.

    Returns 1 when the command is unknown or its schema file is missing.
    """
    from .schema import load_command_input_schema

    parser = build_parser()
    command_parser = resolve_command_parser(parser=parser, name=args.name)
    if command_parser is None:
        message = t("schema_unknown_command", name=args.name)
        hint = t("schema_unknown_command_hint")
        if args.json:
            print_json(
                error_envelope(
                    "schema",
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

    if getattr(args, "output", False):
        from .schema import generic_output_schema, load_command_output_schema

        output_schema = load_command_output_schema(command=name, version=args.version)
        if output_schema is None:
            output_schema = generic_output_schema(command=name, version=args.version)
        print_json(
            ok_envelope(
                "schema",
                data={
                    "kind": "schema",
                    "schema": "gitwise/schema/v1",
                    "version": __version__,
                    "schema_version": args.version,
                    "command": name,
                    "schema_kind": "cli_output",
                    "json_schema": output_schema,
                },
            )
        )
        return 0

    schema = load_command_input_schema(command=name, version=args.version)
    if schema is None:
        message = t("schema_file_missing", command=name, version=args.version)
        hint = t("schema_file_missing_hint")
        if args.json:
            print_json(
                error_envelope(
                    "schema",
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

    payload = ok_envelope(
        "schema",
        data={
            "kind": "schema",
            "schema": "gitwise/schema/v1",
            "version": __version__,
            "schema_version": args.version,
            "command": name,
            "schema_kind": "cli_input",
            "json_schema": schema,
        },
    )

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
