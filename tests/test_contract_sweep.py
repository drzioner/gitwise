"""Contract sweep: every command must answer --json with a v3 envelope.

These tests exist because a behavioural sweep found eight error paths that
exited non-zero with an empty stdout. A machine consumer cannot tell those
apart from a crash, which defeats the point of the envelope.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import run_gitwise

# Deliberate error paths. Each must still produce a parseable v3 envelope.
ERROR_CASES = [
    pytest.param(["undo", "--steps", "99", "--dry-run"], id="undo-no-history"),
    pytest.param(["undo", "--ref", "--evil"], id="undo-bad-ref"),
    pytest.param(["diff", "nonexistent-ref-xyz"], id="diff-bad-refspec"),
    pytest.param(["pick", "apply"], id="pick-bad-ref"),
    pytest.param(["worktree", "new", "--evil-branch"], id="worktree-bad-flag"),
    pytest.param(["guard", "nope"], id="guard-bad-action"),
    pytest.param(["completions", "tcsh"], id="completions-bad-shell"),
    pytest.param(["branches", "--sort", "--evil"], id="branches-bad-sort"),
    pytest.param(["show", "deadbeefdeadbeef"], id="show-missing-ref"),
    pytest.param(["tag", "create"], id="tag-no-name"),
    pytest.param(["merge", "no-such-branch"], id="merge-missing-branch"),
    pytest.param(["clean"], id="clean-no-flag"),
    pytest.param(["commit"], id="commit-no-message"),
    pytest.param(["schema", "nocommand"], id="schema-unknown"),
]


@pytest.mark.parametrize("args", ERROR_CASES)
def test_error_paths_emit_a_v3_envelope(args: list[str], tmp_git_repo: Path) -> None:
    result = run_gitwise(*args, "--json", cwd=tmp_git_repo)
    assert result.returncode != 0, f"expected a failure for {args}"
    assert result.stdout.strip(), f"{args} exited {result.returncode} with empty stdout"
    payload = json.loads(result.stdout)
    assert payload["v"] == 3
    assert payload["ok"] is False
    assert payload["errors"], f"{args} produced no structured error"
    assert payload["errors"][0]["code"]


def test_argparse_failure_is_reported_as_an_envelope(tmp_git_repo: Path) -> None:
    """argparse exits 2 writing only usage to stderr; JSON mode needs more."""
    result = run_gitwise("guard", "nope", "--json", cwd=tmp_git_repo)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["command"] == "guard"
    assert payload["errors"][0]["code"] == "invalid_arguments"
    assert "usage" in result.stderr.lower()


def test_help_still_exits_zero_without_an_envelope(tmp_git_repo: Path) -> None:
    """The argparse guard must not hijack --help, which exits 0."""
    result = run_gitwise("guard", "--help", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "check" in result.stdout


def test_undo_interpolates_the_step_count(tmp_git_repo: Path) -> None:
    """The message carried a literal {steps} placeholder."""
    result = run_gitwise("undo", "--steps", "99", "--dry-run", "--json", cwd=tmp_git_repo)
    message = json.loads(result.stdout)["errors"][0]["message"]
    assert "{steps}" not in message
    assert "99" in message


# Commands whose --json output must be the canonical envelope and nothing else.
CANONICAL_KEYS = {"v", "ok", "command", "data", "hints", "errors"}


def test_setup_agents_uses_the_canonical_envelope(tmp_git_repo: Path) -> None:
    """setup-agents used to emit v3 with its fields at the top level.

    It declared its own schema version and a v_compat list, so a consumer
    written against the other 30 commands broke on this one. Standardised in
    0.36.
    """
    result = run_gitwise(
        "setup-agents", "--local", "--dry-run", "--yes", "--json", cwd=tmp_git_repo
    )
    payload = json.loads(result.stdout)
    assert set(payload) == CANONICAL_KEYS
    assert "v_compat" not in payload
    assert isinstance(payload["data"], dict)
    assert "bucket" in payload["data"]
    assert "actions" in payload["data"]


def test_setup_agents_errors_are_structured(tmp_git_repo: Path) -> None:
    """errors was a list of bare strings; every other command uses objects."""
    result = run_gitwise(
        "setup-agents", "--local", "--dry-run", "--yes", "--json", cwd=tmp_git_repo
    )
    payload = json.loads(result.stdout)
    assert isinstance(payload["errors"], list)
    for item in payload["errors"]:
        assert set(item) >= {"code", "message"}


def test_every_command_emits_only_canonical_keys(tmp_git_repo: Path) -> None:
    """One sweep over the read-only commands, so a new one cannot drift."""
    cases = {
        "doctor": [],
        "audit": ["--quick"],
        "summarize": [],
        "context": [],
        "diff": [],
        "status": [],
        "commands": [],
        "guard": ["check"],
        "worktree": ["list"],
        "branches": [],
        "conflicts": [],
        "setup-agents": ["--local", "--dry-run", "--yes"],
    }
    offenders = []
    for command, extra in cases.items():
        result = run_gitwise(command, *extra, "--json", cwd=tmp_git_repo)
        payload = json.loads(result.stdout)
        if set(payload) != CANONICAL_KEYS or not isinstance(payload["data"], dict):
            offenders.append((command, sorted(payload)))
    assert offenders == []
