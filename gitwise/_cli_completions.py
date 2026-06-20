"""Shell completions generation: bash, zsh, fish, powershell."""

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

    if shell == "powershell":
        return _build_powershell_completions_script(parser=parser, prog=prog)

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


def _collect_flags(action: argparse.Action) -> list[str]:
    """Return the long/short option strings for an argparse action."""
    return [flag for flag in action.option_strings if flag.startswith("-")]


def _build_powershell_completions_script(*, parser: argparse.ArgumentParser, prog: str) -> str:
    """Generate a PowerShell ``Register-ArgumentCompleter`` script from the parser tree.

    Completes subcommands as the first token and per-command flags thereafter.
    Hand-built because ``shtab`` has no PowerShell backend.
    """
    sub_action = _subparsers_action(parser)
    command_names = sorted(sub_action.choices.keys()) if sub_action else []

    per_command_flags: dict[str, list[str]] = {}
    global_flags: list[str] = []
    for action in parser._actions:
        if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
            continue
        global_flags.extend(_collect_flags(action))

    if sub_action is not None:
        for command, command_parser in sorted(sub_action.choices.items()):
            flags: list[str] = []
            for action in command_parser._actions:
                if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
                    continue
                flags.extend(_collect_flags(action))
            per_command_flags[command] = sorted(set(flags))

    commands_ps = ",".join(f"'{c}'" for c in command_names)
    global_flags_ps = ",".join(f"'{f}'" for f in sorted(set(global_flags)))
    per_command_block = "\n".join(
        "            '{}' = @({})".format(cmd, ", ".join(f'"{f}"' for f in flags))
        for cmd, flags in per_command_flags.items()
    )

    return f"""# PowerShell completion for {prog}
# Source it from your PowerShell profile:
#   Add-Content $PROFILE ('. ' + ((Resolve-Path 'path/to/{prog}.ps1').Path))
# or dot-source: . ./{prog}.ps1
Register-ArgumentCompleter -Native -CommandName '{prog}' -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @({commands_ps})
    $globalFlags = @({global_flags_ps})
    $perCommandFlags = @{{
{per_command_block}
        }}

    $tokens = $commandAst.CommandElements | Select-Object -Skip 1 | Where-Object {{ $_.Value -ne $commandAst.CommandElements[0].Value }}
    $subcommand = ($tokens | Where-Object {{ $_.Value -notlike '-*' }} | Select-Object -First 1).Value

    if (-not $subcommand) {{
        $candidates = $commands + $globalFlags
    }}
    elseif ($perCommandFlags.ContainsKey($subcommand)) {{
        $candidates = $perCommandFlags[$subcommand] + $globalFlags
    }}
    else {{
        $candidates = @()
    }}

    $candidates | Where-Object {{ $_ -like "$wordToComplete*" }} |
        Sort-Object -Unique |
        ForEach-Object {{ [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }}
}}
"""
