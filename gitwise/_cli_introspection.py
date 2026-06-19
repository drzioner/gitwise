"""CLI introspection: help payload, command metadata, JSON schema generation."""

import argparse
from typing import TypedDict

from . import __version__


def _json_safe(value: object) -> object:
    """Recursively convert an argparse value to a JSON-serializable form."""
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
    """Return the first _SubParsersAction from a parser, or None."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _serialize_actions(parser: argparse.ArgumentParser) -> list[dict[str, object]]:
    """Serialize a parser's non-help, non-subparser actions into JSON-friendly dicts."""
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


def extract_command_token(argv: list[str]) -> str | None:
    """Extract the subcommand name from a raw argv, skipping global flags and their values."""
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


def help_payload(parser: argparse.ArgumentParser, command: str | None = None) -> dict[str, object]:
    """Build a structured help payload for the root parser or a specific subcommand."""
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


class CommandMetadata(TypedDict):
    """Minimal metadata for a single subcommand."""

    name: str
    help: str
    aliases: list[str]
    supports_json: bool


def canonical_command_name(command_parser: argparse.ArgumentParser) -> str:
    """Return the canonical name (last prog token) of a subcommand parser."""
    prog = command_parser.prog.strip()
    if not prog:
        return ""
    parts = prog.split()
    return parts[-1] if parts else ""


def commands_metadata(parser: argparse.ArgumentParser) -> list[CommandMetadata]:
    """Return metadata for every unique subcommand, deduplicating by parser identity."""
    sub_action = _subparsers_action(parser)
    if sub_action is None:
        return []

    help_by_parser_id: dict[int, str] = {}
    for pseudo in sub_action._choices_actions:
        parser_name = str(pseudo.dest)
        parser_obj = sub_action.choices.get(parser_name)
        if parser_obj is None:
            continue
        parser_id = id(parser_obj)
        if parser_id not in help_by_parser_id:
            help_by_parser_id[parser_id] = pseudo.help or ""

    entries: list[CommandMetadata] = []
    seen_parser_ids: set[int] = set()
    for command_parser in sub_action.choices.values():
        parser_id = id(command_parser)
        if parser_id in seen_parser_ids:
            continue
        seen_parser_ids.add(parser_id)

        name = canonical_command_name(command_parser)
        aliases = sorted(
            [
                n
                for n, candidate in sub_action.choices.items()
                if candidate is command_parser and n != name
            ]
        )

        entries.append(
            {
                "name": name,
                "help": help_by_parser_id.get(parser_id, command_parser.description or ""),
                "aliases": aliases,
                "supports_json": True,
            }
        )

    return sorted(entries, key=lambda item: str(item["name"]))


def _json_type_for_action(action: argparse.Action) -> str:
    """Map an argparse action to a JSON Schema type string."""
    if isinstance(action, argparse._StoreTrueAction | argparse._StoreFalseAction):
        return "boolean"

    action_type = getattr(action, "type", None)
    if action_type is int:
        return "integer"
    if action_type is float:
        return "number"
    return "string"


def _action_property_schema(action: argparse.Action) -> dict[str, object]:
    """Build a JSON Schema property dict for a single argparse action."""
    value_schema: dict[str, object] = {"type": _json_type_for_action(action)}

    if action.choices:
        value_schema["enum"] = [_json_safe(choice) for choice in action.choices]

    description = "" if action.help is argparse.SUPPRESS else (action.help or "")
    if description:
        value_schema["description"] = description

    if action.default is not argparse.SUPPRESS and action.default is not None:
        value_schema["default"] = _json_safe(action.default)

    nargs = action.nargs
    if nargs in ("*", "+") or (isinstance(nargs, int) and nargs > 1):
        array_schema: dict[str, object] = {
            "type": "array",
            "items": value_schema,
        }
        if nargs == "+":
            array_schema["minItems"] = 1
        if isinstance(nargs, int) and nargs > 1:
            array_schema["minItems"] = nargs
            array_schema["maxItems"] = nargs
        return array_schema

    return value_schema


def _action_required(action: argparse.Action) -> bool:
    """Determine whether an argparse action produces a required JSON field."""
    if action.option_strings:
        return bool(getattr(action, "required", False))

    nargs = action.nargs
    if nargs in (None, "+"):
        return True
    if isinstance(nargs, int):
        return nargs > 0
    return False


def command_input_schema(command_parser: argparse.ArgumentParser) -> dict[str, object]:
    """Generate a JSON Schema (draft 2020-12) describing the CLI input of a subcommand."""
    properties: dict[str, object] = {}
    required: list[str] = []

    for action in command_parser._actions:
        if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
            continue
        properties[action.dest] = _action_property_schema(action)
        if _action_required(action):
            required.append(action.dest)

    schema: dict[str, object] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://gitwise.dev/schemas/v1/input/{canonical_command_name(command_parser)}.json",
        "title": f"gitwise {canonical_command_name(command_parser)} cli input",
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }
    if required:
        schema["required"] = sorted(set(required))

    return schema


def resolve_command_parser(
    *, parser: argparse.ArgumentParser, name: str
) -> argparse.ArgumentParser | None:
    """Look up the sub-parser registered under *name*, or return None."""
    sub_action = _subparsers_action(parser)
    if sub_action is None:
        return None
    return sub_action.choices.get(name)
