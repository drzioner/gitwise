"""Tests for the policy evaluation engine.

All git state comes from real temp repos (see .agents/rules/testing.md): the
engine is exercised against an actual index, an actual MERGE_HEAD, and actual
object names rather than stand-ins.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from gitwise.policy import DEFAULT_POLICY

from conftest import _git

ZERO = "0" * 40


def _policy(**overrides) -> dict:
    """Return the default policy with *overrides* applied."""
    policy = dict(DEFAULT_POLICY)
    policy.update(overrides)
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
    violations = evaluate_commit(_policy(protected_branches=["main"]), ctx)
    assert "protected_branch" in _rules(violations)
    assert _blocking(violations)


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
    from gitwise.guard import evaluate_commit

    ctx = {
        "branch": "feat/x",
        "staged_paths": [],
        "secret_findings": [],
        "secret_scan_error": "index unreadable",
        "in_progress": {"state": "none", "ref": None},
        "gpg": {"ready": True, "gpgsign_enabled": True},
        "amend": False,
    }
    violations = evaluate_commit(_policy(), ctx)
    assert "secret_scan_unavailable" in _rules(violations)
    assert _blocking(violations)


def test_in_progress_merge_blocks(tmp_git_repo: Path) -> None:
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
    violations = evaluate_commit(_policy(protected_branches=[]), ctx)
    assert "in_progress" in _rules(violations)


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
