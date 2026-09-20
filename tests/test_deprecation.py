"""Tests for the deprecation of the retired git/gh wrappers."""

from __future__ import annotations

import json
import re
from pathlib import Path

from gitwise._cli_parser import DEPRECATED_COMMANDS

from conftest import run_gitwise

EXPECTED = {
    "branches",
    "clean",
    "health",
    "log",
    "merge",
    "optimize",
    "pick",
    "pr",
    "show",
    "snapshot",
    "stash",
    "status",
    "suggest",
    "sync",
    "tag",
    "undo",
    "update",
}


def test_seventeen_commands_are_deprecated() -> None:
    assert set(DEPRECATED_COMMANDS) == EXPECTED


def test_pillars_are_not_deprecated() -> None:
    """The four pillars and the support commands must stay first class."""
    for command in ("guard", "commit", "worktree", "setup-agents", "doctor", "setup"):
        assert command not in DEPRECATED_COMMANDS


def _listed_commands(help_text: str) -> set[str]:
    """Return the command names argparse renders in the COMMAND section."""
    return {
        match.group(1)
        for match in re.finditer(r"^    ([a-z][a-z-]*)(?: \(|\s{2,}|$)", help_text, re.MULTILINE)
    }


def test_deprecated_commands_are_absent_from_human_help() -> None:
    help_text = run_gitwise("--help").stdout
    assert "==SUPPRESS==" not in help_text
    assert _listed_commands(help_text) & EXPECTED == set()


def test_pillars_remain_in_human_help() -> None:
    listed = _listed_commands(run_gitwise("--help").stdout)
    assert {"guard", "commit", "worktree", "setup-agents", "diff"} <= listed


def test_registry_marks_them_with_a_replacement() -> None:
    payload = json.loads(run_gitwise("commands", "--json").stdout)
    commands = {entry["name"]: entry for entry in payload["data"]["commands"]}
    for name in EXPECTED:
        assert commands[name]["deprecated"] is True
        assert commands[name]["replacement"]
        assert commands[name]["help"], f"{name} lost its help text"
    assert commands["guard"]["deprecated"] is False
    assert commands["guard"]["replacement"] is None


def test_deprecated_command_still_dispatches(tmp_git_repo: Path) -> None:
    result = run_gitwise("status", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert json.loads(result.stdout)["command"] == "status"


def test_notice_goes_to_stderr_and_never_pollutes_stdout(tmp_git_repo: Path) -> None:
    """A notice on stdout would corrupt the envelope for every machine consumer."""
    result = run_gitwise("status", "--json", cwd=tmp_git_repo)
    json.loads(result.stdout)
    assert "deprecated" not in result.stdout
    assert "deprecated" in result.stderr
    assert "git status" in result.stderr


def test_no_notice_for_a_pillar(tmp_git_repo: Path) -> None:
    result = run_gitwise("guard", "check", "--json", cwd=tmp_git_repo)
    assert "deprecated" not in result.stderr


def test_alias_of_a_deprecated_command_still_works(tmp_git_repo: Path) -> None:
    result = run_gitwise("branch-clean", "--branches", "--dry-run", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert json.loads(result.stdout)["command"] == "clean"


def test_alias_of_a_deprecated_command_also_warns(tmp_git_repo: Path) -> None:
    """Invoking by alias must not silently skip the notice."""
    result = run_gitwise("branch-clean", "--branches", "--dry-run", "--json", cwd=tmp_git_repo)
    assert "deprecated" in result.stderr
    assert "clean" in result.stderr
    json.loads(result.stdout)
