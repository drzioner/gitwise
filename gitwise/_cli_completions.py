"""Shell completions generation: bash, zsh, fish."""

import argparse

from ._cli_introspection import _subparsers_action
from ._cli_parser import build_parser


def build_completions_script(*, shell: str, prog: str) -> str:
    """Return a shell completion script for the given shell and program name."""
    parser = build_parser()
    parser.prog = prog

    if shell in ("bash", "zsh"):
        import importlib

        shtab_complete = importlib.import_module("shtab").complete
        return shtab_complete(parser, shell=shell)

    if shell == "fish":
        return _build_fish_completions_script(parser=parser, prog=prog)

    raise ValueError(f"unsupported shell: {shell}")


def _fish_escape(text: str) -> str:
    """Escape single quotes for use inside a fish completion string literal."""
    return text.replace("'", "\\'")


def _build_fish_option_line(*, prog: str, condition: str, flag: str, help_text: str) -> str:
    """Return a single fish ``complete`` line for an option, or an empty string for unrecognized flags."""
    escaped_help = _fish_escape(help_text)
    escaped_prog = _fish_escape(prog)
    escaped_condition = _fish_escape(condition)
    if flag.startswith("--"):
        return (
            f"complete -c '{escaped_prog}' -n \"{escaped_condition}\" "
            f"-l {flag[2:]} -d '{escaped_help}'"
        )
    if flag.startswith("-") and len(flag) == 2:
        return (
            f"complete -c '{escaped_prog}' -n \"{escaped_condition}\" "
            f"-s {flag[1:]} -d '{escaped_help}'"
        )
    return ""


def _build_fish_completions_script(*, parser: argparse.ArgumentParser, prog: str) -> str:
    """Generate a fish completion script from the full argparse parser tree."""
    escaped_prog = _fish_escape(prog)
    lines: list[str] = [f"# fish completion for {escaped_prog}"]

    sub_action = _subparsers_action(parser)
    command_names = sorted(sub_action.choices.keys()) if sub_action else []

    if command_names:
        joined = " ".join(command_names)
        lines.append(
            f"complete -c '{escaped_prog}' -f -n \"__fish_use_subcommand\" -a '{_fish_escape(joined)}'"
        )

    for action in parser._actions:
        if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
            continue
        for flag in action.option_strings:
            line = _build_fish_option_line(
                prog=prog,
                condition="__fish_use_subcommand",
                flag=flag,
                help_text="" if action.help is argparse.SUPPRESS else (action.help or ""),
            )
            if line:
                lines.append(line)

    if sub_action is not None:
        for command, command_parser in sorted(sub_action.choices.items()):
            condition = f"__fish_seen_subcommand_from {command}"
            for action in command_parser._actions:
                if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
                    continue
                for flag in action.option_strings:
                    line = _build_fish_option_line(
                        prog=prog,
                        condition=condition,
                        flag=flag,
                        help_text="" if action.help is argparse.SUPPRESS else (action.help or ""),
                    )
                    if line:
                        lines.append(line)

    return "\n".join(lines) + "\n"
