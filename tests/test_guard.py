"""Tests for the policy evaluation engine.

All git state comes from real temp repos (see .agents/rules/testing.md): the
engine is exercised against an actual index, an actual MERGE_HEAD, and actual
object names rather than stand-ins.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

from gitwise.policy import DEFAULT_POLICY, Policy

from conftest import _git

ZERO = "0" * 40


def _policy(**overrides: object) -> Policy:
    """Return the default policy with *overrides* applied."""
    policy = cast("Policy", {**DEFAULT_POLICY, **overrides})
    return policy


def _stage(repo: Path, relative: str, content: str = "x\n") -> None:
    """Create and stage *relative* inside *repo*."""
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(["add", "--", relative], repo)


def _rules(violations) -> set[str]:
    return {v["rule"] for v in violations}


def _blocking(violations) -> list:
    return [v for v in violations if v["severity"] == "block"]


# --- commit context -------------------------------------------------------


def test_clean_repo_on_feature_branch_has_no_violations(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/x"], tmp_git_repo)
    _stage(tmp_git_repo, "src/app.py")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    assert evaluate_commit(_policy(), ctx) == []


def test_commit_on_protected_branch_blocks(tmp_git_repo: Path) -> None:
    _stage(tmp_git_repo, "src/app.py")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    policy = _policy(protected_branches=["main"], block_direct_commits=True)
    violations = evaluate_commit(policy, ctx)
    assert "protected_branch" in _rules(violations)
    assert _blocking(violations)


def test_direct_commit_on_protected_branch_is_allowed_by_default(tmp_git_repo: Path) -> None:
    """Protecting a branch means no rewrites, not no commits; that is opt-in."""
    _stage(tmp_git_repo, "src/app.py")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    policy = _policy(protected_branches=["main"])
    assert "protected_branch" not in _rules(evaluate_commit(policy, ctx))


def test_unprotected_branch_is_allowed(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/y"], tmp_git_repo)
    _stage(tmp_git_repo, "src/app.py")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    assert "protected_branch" not in _rules(evaluate_commit(_policy(), ctx))


def test_forbidden_path_glob_matches_nested_file(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/z"], tmp_git_repo)
    _stage(tmp_git_repo, "secrets/prod.key")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    violations = evaluate_commit(_policy(forbidden_paths=["secrets/**"]), ctx)
    assert "forbidden_path" in _rules(violations)
    assert violations[0]["path"] == "secrets/prod.key"


def test_forbidden_path_matches_basename_at_any_depth(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/z2"], tmp_git_repo)
    _stage(tmp_git_repo, "deep/nested/key.pem")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    assert "forbidden_path" in _rules(evaluate_commit(_policy(forbidden_paths=["*.pem"]), ctx))


def test_forbidden_path_does_not_match_unrelated_file(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/z3"], tmp_git_repo)
    _stage(tmp_git_repo, "src/app.py")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    assert "forbidden_path" not in _rules(evaluate_commit(_policy(forbidden_paths=[".env"]), ctx))


def test_staged_secret_blocks_when_block_secrets_enabled(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/s"], tmp_git_repo)
    _stage(tmp_git_repo, "config.py", 'TOKEN = "ghp_' + "a" * 36 + '"\n')

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    violations = evaluate_commit(_policy(block_secrets=True), ctx)
    assert "secret" in _rules(violations)
    assert _blocking(violations)


def test_staged_secret_warns_when_block_secrets_disabled(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/s2"], tmp_git_repo)
    _stage(tmp_git_repo, "config.py", 'TOKEN = "ghp_' + "a" * 36 + '"\n')

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    violations = evaluate_commit(_policy(block_secrets=False), ctx)
    assert "secret" in _rules(violations)
    assert not _blocking(violations)


def test_secret_violation_never_carries_the_credential(tmp_git_repo: Path) -> None:
    """The verbatim secret must not travel in the violation payload."""
    token = "ghp_" + "b" * 36
    _git(["switch", "-c", "feat/s3"], tmp_git_repo)
    _stage(tmp_git_repo, "config.py", f'TOKEN = "{token}"\n')

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    rendered = repr(evaluate_commit(_policy(), ctx))
    assert token not in rendered


def test_unreadable_staged_diff_blocks(tmp_path: Path) -> None:
    """Fail closed: a scan that cannot run is not a clean scan."""
    from gitwise.guard import CommitContext, evaluate_commit

    ctx = cast(
        "CommitContext",
        {
            "branch": "feat/x",
            "staged_paths": [],
            "secret_findings": [],
            "secret_scan_error": "index unreadable",
            "in_progress": {"state": "none", "ref": None},
            "gpg": {"ready": True, "gpgsign_enabled": True},
            "amend": False,
        },
    )
    violations = evaluate_commit(_policy(), ctx)
    assert "secret_scan_unavailable" in _rules(violations)
    assert _blocking(violations)


def test_paused_merge_does_not_block_the_engine(tmp_git_repo: Path) -> None:
    """The commit that closes a conflicted merge is the one git runs the hook for.

    Refusing it would leave the user unable to finish or abort the merge
    without --no-verify. `gitwise commit` still refuses on its own.
    """
    _git(["switch", "-c", "feat/a"], tmp_git_repo)
    (tmp_git_repo / "f.txt").write_text("a\n", encoding="utf-8")
    _git(["add", "f.txt"], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: a"], tmp_git_repo)
    _git(["switch", "main"], tmp_git_repo)
    (tmp_git_repo / "f.txt").write_text("b\n", encoding="utf-8")
    _git(["add", "f.txt"], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: b"], tmp_git_repo)
    subprocess.run(["git", "merge", "feat/a"], cwd=tmp_git_repo, capture_output=True, check=False)

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    assert ctx["in_progress"]["state"] == "merge"
    assert "in_progress" not in _rules(evaluate_commit(_policy(), ctx))


def test_require_gpg_blocks_when_not_ready(tmp_git_repo: Path) -> None:
    # Local config wins over the developer's global one, so the repo really is
    # unsigned regardless of who runs the suite.
    _git(["config", "commit.gpgsign", "false"], tmp_git_repo)
    _git(["switch", "-c", "feat/g"], tmp_git_repo)
    _stage(tmp_git_repo, "src/app.py")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    violations = evaluate_commit(_policy(require_gpg=True), ctx)
    assert "gpg" in _rules(violations)
    assert _blocking(violations)


def test_require_gpg_off_by_default(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/g2"], tmp_git_repo)
    _stage(tmp_git_repo, "src/app.py")

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    assert "gpg" not in _rules(evaluate_commit(_policy(), ctx))


# --- push context ---------------------------------------------------------


def test_parse_push_stdin_reads_the_githooks_format() -> None:
    from gitwise.guard import parse_push_stdin

    line = f"refs/heads/main abc123 refs/heads/main {ZERO}\n"
    refs = parse_push_stdin(line)
    assert refs == [("refs/heads/main", "abc123", "refs/heads/main", ZERO)]


def test_parse_push_stdin_ignores_blank_and_short_lines() -> None:
    from gitwise.guard import parse_push_stdin

    assert parse_push_stdin("\n  \nnot-enough fields\n") == []


def test_new_remote_branch_is_not_a_force_push(tmp_git_repo: Path) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    from gitwise.guard import collect_push_context, evaluate_push

    ctx = collect_push_context(tmp_git_repo, f"refs/heads/main {head} refs/heads/main {ZERO}\n")
    assert evaluate_push(_policy(), ctx) == []


def test_non_fast_forward_push_to_protected_branch_blocks(tmp_git_repo: Path) -> None:
    """A remote tip that is not an ancestor of the local tip is a force push."""
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    _git(["switch", "-c", "diverged"], tmp_git_repo)
    (tmp_git_repo / "other.txt").write_text("o\n", encoding="utf-8")
    _git(["add", "other.txt"], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: diverged"], tmp_git_repo)
    diverged = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    from gitwise.guard import collect_push_context, evaluate_push

    # Pushing `first` over a remote that already holds `diverged` rewrites history.
    ctx = collect_push_context(
        tmp_git_repo, f"refs/heads/main {first} refs/heads/main {diverged}\n"
    )
    violations = evaluate_push(_policy(protected_branches=["main"]), ctx)
    assert "force_push" in _rules(violations)
    assert _blocking(violations)


def test_force_push_allowed_when_policy_permits(tmp_git_repo: Path) -> None:
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    _git(["switch", "-c", "diverged2"], tmp_git_repo)
    (tmp_git_repo / "other.txt").write_text("o\n", encoding="utf-8")
    _git(["add", "other.txt"], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: diverged"], tmp_git_repo)
    diverged = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    from gitwise.guard import collect_push_context, evaluate_push

    ctx = collect_push_context(
        tmp_git_repo, f"refs/heads/main {first} refs/heads/main {diverged}\n"
    )
    policy = _policy(protected_branches=["main"], allow_force_push=True)
    assert "force_push" not in _rules(evaluate_push(policy, ctx))


def test_deleting_a_protected_branch_blocks(tmp_git_repo: Path) -> None:
    from gitwise.guard import collect_push_context, evaluate_push

    ctx = collect_push_context(tmp_git_repo, f"(delete) {ZERO} refs/heads/main {'a' * 40}\n")
    violations = evaluate_push(_policy(protected_branches=["main"]), ctx)
    assert "protected_branch_delete" in _rules(violations)
    assert _blocking(violations)


def test_deleting_an_unprotected_branch_is_allowed(tmp_git_repo: Path) -> None:
    from gitwise.guard import collect_push_context, evaluate_push

    ctx = collect_push_context(tmp_git_repo, f"(delete) {ZERO} refs/heads/scratch {'a' * 40}\n")
    assert evaluate_push(_policy(protected_branches=["main"]), ctx) == []


# --- CLI surface ----------------------------------------------------------


def test_guard_check_emits_v3_envelope(tmp_git_repo: Path) -> None:
    import json

    from conftest import run_gitwise

    result = run_gitwise("guard", "check", "--json", cwd=tmp_git_repo)
    payload = json.loads(result.stdout)
    assert payload["v"] == 3
    assert payload["command"] == "guard"
    assert payload["data"]["policy_source"] == "default"


def test_guard_check_output_validates_against_schema(tmp_git_repo: Path) -> None:
    import json

    from gitwise.schema import load_command_output_schema
    from jsonschema import Draft202012Validator

    from conftest import run_gitwise

    schema = load_command_output_schema(command="guard", version="v1")
    assert schema is not None
    result = run_gitwise("guard", "check", "--json", cwd=tmp_git_repo)
    Draft202012Validator(schema).validate(json.loads(result.stdout))


def test_guard_check_exits_2_on_blocking_violation(tmp_git_repo: Path) -> None:
    import json

    from conftest import run_gitwise

    _git(["switch", "-c", "feat/cli"], tmp_git_repo)
    (tmp_git_repo / ".gitwise").mkdir()
    (tmp_git_repo / ".gitwise" / "policy.json").write_text(
        json.dumps({"version": 1, "forbidden_paths": [".env"]}), encoding="utf-8"
    )
    _stage(tmp_git_repo, ".env", "SECRET=1\n")

    result = run_gitwise("guard", "check", "--json", cwd=tmp_git_repo)
    assert result.returncode == 2, result.stdout
    payload = json.loads(result.stdout)
    assert payload["data"]["allowed"] is False
    assert payload["data"]["policy_source"] == ".gitwise/policy.json"
    assert _rules(payload["data"]["violations"]) == {"forbidden_path"}


def test_guard_check_exits_1_on_invalid_policy(tmp_git_repo: Path) -> None:
    import json

    from conftest import run_gitwise

    (tmp_git_repo / ".gitwise").mkdir()
    (tmp_git_repo / ".gitwise" / "policy.json").write_text("{nope", encoding="utf-8")

    result = run_gitwise("guard", "check", "--json", cwd=tmp_git_repo)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["errors"][0]["code"] == "policy_invalid"


def test_guard_without_action_reports_an_error(tmp_git_repo: Path) -> None:
    import json

    from conftest import run_gitwise

    result = run_gitwise("guard", "--json", cwd=tmp_git_repo)
    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0]["code"] == "action_required"


def test_guard_check_outside_a_repo_reports_not_a_git_repo(tmp_path: Path) -> None:
    import json

    from conftest import run_gitwise

    result = run_gitwise("guard", "check", "--json", cwd=tmp_path)
    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0]["code"] == "not_a_git_repo"


# --- commit message -------------------------------------------------------


def test_message_with_allowed_type_passes() -> None:
    from gitwise.guard import evaluate_message

    assert evaluate_message(_policy(), "feat(guard): add the engine") == []


def test_message_with_disallowed_type_blocks() -> None:
    from gitwise.guard import evaluate_message

    violations = evaluate_message(_policy(commit_types=["feat", "fix"]), "chore: tidy up")
    assert "commit_type" in _rules(violations)
    assert _blocking(violations)


def test_message_without_conventional_prefix_blocks() -> None:
    from gitwise.guard import evaluate_message

    assert "commit_type" in _rules(evaluate_message(_policy(), "tidy up the thing"))


def test_breaking_marker_is_accepted() -> None:
    from gitwise.guard import evaluate_message

    assert evaluate_message(_policy(), "feat!: rotate the contract") == []


def test_merge_and_revert_messages_are_exempt() -> None:
    """git authors these itself; holding them to the contract blocks merges."""
    from gitwise.guard import evaluate_message

    assert evaluate_message(_policy(), "Merge branch 'main' into feat/x") == []
    assert evaluate_message(_policy(), 'Revert "feat: something"') == []


def test_comments_and_blank_lines_are_skipped() -> None:
    from gitwise.guard import evaluate_message

    message = "\n# a comment git adds\nfeat: real subject\n"
    assert evaluate_message(_policy(), message) == []


def test_empty_message_blocks() -> None:
    from gitwise.guard import evaluate_message

    assert "commit_type" in _rules(evaluate_message(_policy(), "\n# only comments\n"))


def test_guard_check_commit_msg_reads_the_file(tmp_git_repo: Path) -> None:
    import json

    from conftest import run_gitwise

    message_file = tmp_git_repo / "MSG"
    message_file.write_text("nope: not a type\n", encoding="utf-8")

    result = run_gitwise(
        "guard", "check", "--commit-msg", str(message_file), "--json", cwd=tmp_git_repo
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["data"]["scope"] == "message"
    assert _rules(payload["data"]["violations"]) == {"commit_type"}


def test_guard_check_commit_msg_missing_file_is_an_error(tmp_git_repo: Path) -> None:
    import json

    from conftest import run_gitwise

    result = run_gitwise(
        "guard", "check", "--commit-msg", str(tmp_git_repo / "absent"), "--json", cwd=tmp_git_repo
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0]["code"] == "message_unreadable"


# --- install --------------------------------------------------------------


def _gitwise_shim(directory: Path) -> Path:
    """Create a `gitwise` executable on PATH that runs this checkout.

    The hooks invoke the real binary by name; a test that stubbed the call out
    would prove the config was written, not that the hook refuses a commit.
    """
    import sys

    from conftest import PROJECT_ROOT

    shim = directory / "gitwise"
    shim.write_text(
        f'#!/bin/sh\nPYTHONPATH="{PROJECT_ROOT}" exec "{sys.executable}" -m gitwise "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return shim


def test_guard_install_dry_run_writes_nothing(tmp_git_repo: Path) -> None:
    import json

    from gitwise.git import config as git_config

    from conftest import run_gitwise

    result = run_gitwise(
        "guard", "install", "--hooks-mode", "legacy", "--dry-run", "--json", cwd=tmp_git_repo
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["data"]["dry_run"] is True
    assert payload["data"]["changes"]
    assert git_config("core.hooksPath", cwd=tmp_git_repo) is None


def test_guard_install_legacy_sets_hooks_path(tmp_git_repo: Path) -> None:
    from gitwise.git import config as git_config
    from gitwise.guard import guard_hooks_dir

    from conftest import run_gitwise

    result = run_gitwise(
        "guard", "install", "--hooks-mode", "legacy", "--yes", "--json", cwd=tmp_git_repo
    )
    assert result.returncode == 0, result.stdout
    assert git_config("core.hooksPath", cwd=tmp_git_repo) == str(guard_hooks_dir())


def test_guard_uninstall_removes_the_hooks_path(tmp_git_repo: Path) -> None:
    from gitwise.git import config as git_config

    from conftest import run_gitwise

    run_gitwise("guard", "install", "--hooks-mode", "legacy", "--yes", "--json", cwd=tmp_git_repo)
    result = run_gitwise("guard", "install", "--uninstall", "--yes", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0, result.stdout
    assert git_config("core.hooksPath", cwd=tmp_git_repo) is None


def test_guard_install_skips_when_another_hook_manager_owns_the_repo(tmp_git_repo: Path) -> None:
    import json

    from conftest import run_gitwise

    (tmp_git_repo / "lefthook.yml").write_text("pre-commit:\n", encoding="utf-8")
    result = run_gitwise("guard", "install", "--json", cwd=tmp_git_repo)
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["data"]["backend"] == "skip"
    assert payload["data"]["changes"] == []
    assert payload["data"]["warnings"]


def test_installed_hook_blocks_a_forbidden_commit(tmp_git_repo: Path, tmp_path: Path) -> None:
    """End to end: the hook refuses a `git commit` the policy forbids."""
    import json
    import os
    import subprocess as sp

    from conftest import run_gitwise

    _git(["switch", "-c", "feat/hooked"], tmp_git_repo)
    (tmp_git_repo / ".gitwise").mkdir()
    (tmp_git_repo / ".gitwise" / "policy.json").write_text(
        json.dumps({"version": 1, "forbidden_paths": ["*.pem"]}), encoding="utf-8"
    )
    run_gitwise("guard", "install", "--hooks-mode", "legacy", "--yes", "--json", cwd=tmp_git_repo)

    bin_dir = tmp_path / "shim-bin"
    bin_dir.mkdir()
    _gitwise_shim(bin_dir)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    _stage(tmp_git_repo, "deploy/key.pem", "-----BEGIN-----\n")
    result = sp.run(
        ["git", "commit", "--no-gpg-sign", "-m", "feat: add key"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode != 0, result.stdout + result.stderr
    head = sp.run(
        ["git", "log", "--oneline"], cwd=tmp_git_repo, capture_output=True, text=True, check=True
    )
    assert "add key" not in head.stdout


def test_installed_hook_allows_a_compliant_commit(tmp_git_repo: Path, tmp_path: Path) -> None:
    import json
    import os
    import subprocess as sp

    from conftest import run_gitwise

    _git(["switch", "-c", "feat/ok"], tmp_git_repo)
    (tmp_git_repo / ".gitwise").mkdir()
    (tmp_git_repo / ".gitwise" / "policy.json").write_text(
        json.dumps({"version": 1, "forbidden_paths": ["*.pem"]}), encoding="utf-8"
    )
    run_gitwise("guard", "install", "--hooks-mode", "legacy", "--yes", "--json", cwd=tmp_git_repo)

    bin_dir = tmp_path / "shim-bin2"
    bin_dir.mkdir()
    _gitwise_shim(bin_dir)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    _stage(tmp_git_repo, "src/ok.py", "print('ok')\n")
    result = sp.run(
        ["git", "commit", "--no-gpg-sign", "-m", "feat: add module"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_install_refuses_when_a_hook_script_is_not_executable(
    tmp_git_repo: Path, monkeypatch, capsys
) -> None:
    """A hook without +x is protection that silently does not run.

    Wheels do not reliably preserve the executable bit, so install verifies it
    instead of trusting the packaging.
    """
    import shutil

    import gitwise.guard as guard_mod
    from gitwise.git import config as git_config

    staging = tmp_git_repo.parent / "hooks-staging"
    shutil.copytree(guard_mod.guard_hooks_dir(), staging)
    for script in staging.iterdir():
        script.chmod(0o644)
    monkeypatch.setattr(guard_mod, "guard_hooks_dir", lambda: staging)
    monkeypatch.chdir(tmp_git_repo)

    assert guard_mod.hook_scripts_executable(staging) == ["commit-msg", "pre-commit", "pre-push"]
    assert guard_mod.run_guard_install(hooks_mode="legacy", yes=True, as_json=False) == 1
    assert git_config("core.hooksPath", cwd=tmp_git_repo) is None


def test_shipped_hook_scripts_are_executable() -> None:
    """The scripts in the source tree carry +x, so a checkout install works."""
    from gitwise.guard import guard_hooks_dir, hook_scripts_executable

    assert hook_scripts_executable(guard_hooks_dir()) == []


# --- regressions from the review gate ------------------------------------


def test_forbidden_path_matching_is_case_insensitive() -> None:
    """A policy forbidding .env means the secret, not the spelling."""
    from gitwise.guard import path_is_forbidden

    assert path_is_forbidden(".ENV", [".env"])
    assert path_is_forbidden("deploy/KEY.PEM", ["*.pem"])
    assert path_is_forbidden("Secrets/Prod.Key", ["secrets/**"])
    assert not path_is_forbidden("src/app.py", [".env"])


def test_object_names_from_stdin_never_reach_git_as_options(tmp_git_repo: Path) -> None:
    """A ref update carrying `--help` must not be handed to the subprocess."""
    from gitwise.guard import collect_push_context

    ctx = collect_push_context(
        tmp_git_repo, "refs/heads/main --help refs/heads/main --upload-pack=evil\n"
    )
    # Unusable names are reported as a rewrite, so the push is refused, not run.
    assert ctx["refs"][0]["non_fast_forward"] is True


def test_long_subject_is_not_reported_as_a_type_violation() -> None:
    """Length is not a policy rule; reporting it as `commit_type` would mislead."""
    from gitwise.guard import evaluate_message

    assert evaluate_message(_policy(), "feat: " + "x" * 80) == []


def test_install_in_json_mode_requires_yes(tmp_git_repo: Path) -> None:
    """A machine caller gets no prompt, so silence must not mean consent."""
    import json

    from gitwise.git import config as git_config

    from conftest import run_gitwise

    result = run_gitwise("guard", "install", "--hooks-mode", "legacy", "--json", cwd=tmp_git_repo)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "confirmation_required"
    assert git_config("core.hooksPath", cwd=tmp_git_repo) is None


def test_push_check_without_stdin_reports_instead_of_hanging(tmp_git_repo: Path) -> None:
    """Reading a tty would block the caller forever."""
    import json
    import os
    import subprocess as sp
    import sys

    from conftest import PROJECT_ROOT

    result = sp.run(
        [sys.executable, "-m", "gitwise", "guard", "check", "--push", "--json"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        stdin=sp.DEVNULL,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        timeout=30,
        check=False,
    )
    # DEVNULL is not a tty, so this path reads an empty stdin and finds no refs.
    assert result.returncode == 0
    assert json.loads(result.stdout)["data"]["violations"] == []


def test_non_ascii_path_is_still_matched(tmp_git_repo: Path) -> None:
    """git quotes non-ASCII paths by default; a quoted name matches no glob.

    Without `-z`, `git diff --cached --name-only` returns
    `"configuraci\\303\\263n/.env"`, so putting a secret under an accented
    directory walked straight past forbidden_paths.
    """
    _git(["switch", "-c", "feat/uni"], tmp_git_repo)
    target = tmp_git_repo / "configuración"
    target.mkdir()
    (target / ".env").write_text("SECRET=1\n", encoding="utf-8")
    _git(["add", "--", "configuración/.env"], tmp_git_repo)

    from gitwise.guard import collect_commit_context, evaluate_commit, staged_paths

    assert staged_paths(tmp_git_repo) == ["configuración/.env"]
    ctx = collect_commit_context(tmp_git_repo)
    violations = evaluate_commit(_policy(forbidden_paths=[".env"]), ctx)
    assert "forbidden_path" in _rules(violations)


def test_path_with_spaces_is_matched(tmp_git_repo: Path) -> None:
    _git(["switch", "-c", "feat/spaces"], tmp_git_repo)
    target = tmp_git_repo / "mi carpeta"
    target.mkdir()
    (target / "clave privada.pem").write_text("k\n", encoding="utf-8")
    _git(["add", "--", "mi carpeta/clave privada.pem"], tmp_git_repo)

    from gitwise.guard import collect_commit_context, evaluate_commit

    ctx = collect_commit_context(tmp_git_repo)
    assert "forbidden_path" in _rules(evaluate_commit(_policy(forbidden_paths=["*.pem"]), ctx))


def test_installed_hook_lets_a_conflicted_merge_be_completed(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    """Regression: the hook made conflicted merges impossible to finish.

    The user resolved the conflict, staged it, and `git commit` was refused
    because a merge was in progress -- by the very commit that ends it.
    """
    import os
    import subprocess as sp

    from conftest import run_gitwise

    _git(["switch", "-c", "feat/m"], tmp_git_repo)
    (tmp_git_repo / "f.txt").write_text("branch\n", encoding="utf-8")
    _git(["add", "f.txt"], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: branch"], tmp_git_repo)
    _git(["switch", "main"], tmp_git_repo)
    (tmp_git_repo / "f.txt").write_text("main\n", encoding="utf-8")
    _git(["add", "f.txt"], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "feat: main"], tmp_git_repo)

    run_gitwise("guard", "install", "--hooks-mode", "legacy", "--yes", "--json", cwd=tmp_git_repo)
    bin_dir = tmp_path / "merge-bin"
    bin_dir.mkdir()
    _gitwise_shim(bin_dir)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    merge = sp.run(
        ["git", "merge", "feat/m"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert "CONFLICT" in merge.stdout

    (tmp_git_repo / "f.txt").write_text("resolved\n", encoding="utf-8")
    sp.run(["git", "add", "f.txt"], cwd=tmp_git_repo, env=env, check=True, capture_output=True)
    result = sp.run(
        ["git", "commit", "--no-gpg-sign", "-m", "fix: resolve the conflict"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_hook_output_is_silent_on_success(tmp_git_repo: Path, tmp_path: Path) -> None:
    """A pre-commit hook that prints on every commit is a hook people uninstall."""
    import os
    import subprocess as sp

    from conftest import run_gitwise

    _git(["switch", "-c", "feat/quiet"], tmp_git_repo)
    run_gitwise("guard", "install", "--hooks-mode", "legacy", "--yes", "--json", cwd=tmp_git_repo)
    bin_dir = tmp_path / "quiet-bin"
    bin_dir.mkdir()
    _gitwise_shim(bin_dir)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    _stage(tmp_git_repo, "src/ok.py", "x = 1\n")
    result = sp.run(
        ["git", "commit", "--no-gpg-sign", "-m", "feat: add"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0
    assert "policy violations" not in result.stderr
    assert "policy violations" not in result.stdout


def test_quiet_still_reports_violations(tmp_git_repo: Path) -> None:
    from conftest import run_gitwise

    _git(["switch", "-c", "feat/quiet2"], tmp_git_repo)
    (tmp_git_repo / ".gitwise").mkdir()
    (tmp_git_repo / ".gitwise" / "policy.json").write_text(
        '{"version": 1, "forbidden_paths": ["*.pem"]}', encoding="utf-8"
    )
    _stage(tmp_git_repo, "k.pem", "k\n")
    result = run_gitwise("guard", "check", "--quiet", cwd=tmp_git_repo)
    assert result.returncode == 2
    assert "forbidden_path" in result.stdout + result.stderr
