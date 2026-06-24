"""Tests for gitwise pr."""

import json
from pathlib import Path

from gitwise import pr as pr_module

from conftest import run_gitwise


def test_pr_not_git_repo(tmp_path: Path) -> None:
    r = run_gitwise("pr", cwd=tmp_path)
    assert r.returncode == 1


def test_pr_list(tmp_git_repo: Path) -> None:
    r = run_gitwise("pr", "list", cwd=tmp_git_repo)
    assert r.returncode in (0, 1)


def test_pr_view_human_output(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    payload = {
        "number": 42,
        "title": "Improve PR UX",
        "state": "OPEN",
        "isDraft": False,
        "author": {"login": "alice"},
        "headRefName": "feat/pr-clean",
        "baseRefName": "main",
        "url": "https://example.test/pr/42",
        "createdAt": "2026-05-21T10:00:00Z",
        "updatedAt": "2026-05-21T11:00:00Z",
        "mergedAt": None,
        "closedAt": None,
        "mergeable": "MERGEABLE",
        "reviewDecision": "APPROVED",
        "additions": 25,
        "deletions": 3,
        "changedFiles": 4,
        "labels": [{"name": "enhancement"}],
        "assignees": [{"login": "bob"}],
        "reviewRequests": [{"requestedReviewer": {"login": "carol"}}],
        "body": "Line 1\n\nLine 2",
    }

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)

    def _fake_gh(args: list[str], cwd: Path) -> tuple[int, str, str]:
        assert args[0:2] == ["pr", "view"]
        return 0, json.dumps(payload), ""

    monkeypatch.setattr(pr_module, "_gh", _fake_gh)

    rc = pr_module.run_pr(action="view", selector="42", as_json=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "PR #42" in out
    assert "Improve PR UX" in out
    assert "alice" in out
    assert "feat/pr-clean -> main" in out
    assert "https://example.test/pr/42" in out


def test_pr_view_merged_hides_mergeable_and_review(
    monkeypatch, tmp_git_repo: Path, capsys
) -> None:
    payload = {
        "number": 24,
        "title": "Merged PR",
        "state": "MERGED",
        "isDraft": False,
        "author": {"login": "drzioner"},
        "headRefName": "feature/pretty-output-human-cli",
        "baseRefName": "main",
        "url": "https://example.test/pr/24",
        "createdAt": "2026-05-21T10:00:00Z",
        "updatedAt": "2026-05-21T11:00:00Z",
        "mergedAt": "2026-05-21T12:00:00Z",
        "closedAt": "2026-05-21T12:00:00Z",
        "mergeable": "UNKNOWN",
        "reviewDecision": "REVIEW_REQUIRED",
        "additions": 100,
        "deletions": 10,
        "changedFiles": 8,
        "labels": [],
        "assignees": [],
        "reviewRequests": [],
        "body": "Done",
    }

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    monkeypatch.setattr(pr_module, "_gh", lambda args, cwd: (0, json.dumps(payload), ""))

    rc = pr_module.run_pr(action="view", selector="24", as_json=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "Merged" in out
    assert "Mergeable" not in out
    assert "Review" not in out


def test_pr_comments_human_output(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    payload = {
        "number": 42,
        "title": "Improve PR UX",
        "url": "https://example.test/pr/42",
        "comments": [
            {
                "author": {"login": "alice"},
                "createdAt": "2026-05-21T10:00:00Z",
                "url": "https://example.test/pr/42#issuecomment-1",
                "body": "Please split this function.\\n\\nThen run tests.",
            },
            {
                "author": {"login": "bob"},
                "createdAt": "2026-05-21T10:30:00Z",
                "url": "https://example.test/pr/42#issuecomment-2",
                "body": "Done, thanks.",
            },
        ],
    }

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)

    def _fake_gh(args: list[str], cwd: Path) -> tuple[int, str, str]:
        assert args[0:2] == ["pr", "view"]
        return 0, json.dumps(payload), ""

    monkeypatch.setattr(pr_module, "_gh", _fake_gh)

    rc = pr_module.run_pr(action="comments", selector="42", as_json=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "comments" in out.lower()
    assert "alice" in out
    assert "bob" in out
    assert "Please split this function.\\n\\nThen run tests." in out
    assert "Done, thanks." in out


def test_pr_comments_json_output(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    payload = {
        "number": 99,
        "title": "Refactor output",
        "url": "https://example.test/pr/99",
        "comments": [
            {
                "author": {"login": "alice"},
                "createdAt": "2026-05-21T10:00:00Z",
                "url": "https://example.test/pr/99#issuecomment-1",
                "body": "Looks good",
            }
        ],
    }

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    monkeypatch.setattr(pr_module, "_gh", lambda args, cwd: (0, json.dumps(payload), ""))

    rc = pr_module.run_pr(action="comments", selector="99", as_json=True)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 0
    assert data["ok"] is True
    assert data["data"]["number"] == 99
    assert data["data"]["count"] == 1


def test_pr_view_json_uses_envelope(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    payload = {
        "number": 42,
        "title": "Improve PR UX",
        "state": "OPEN",
        "isDraft": False,
        "author": {"login": "alice"},
        "headRefName": "feat/pr-clean",
        "baseRefName": "main",
        "url": "https://example.test/pr/42",
        "createdAt": "2026-05-21T10:00:00Z",
        "updatedAt": "2026-05-21T11:00:00Z",
        "mergedAt": None,
        "closedAt": None,
        "mergeable": "MERGEABLE",
        "reviewDecision": "APPROVED",
        "additions": 25,
        "deletions": 3,
        "changedFiles": 4,
        "labels": [],
        "assignees": [],
        "reviewRequests": [],
        "body": "Line 1",
    }

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    monkeypatch.setattr(pr_module, "_gh", lambda args, cwd: (0, json.dumps(payload), ""))

    rc = pr_module.run_pr(action="view", selector="42", as_json=True)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 0
    assert data["ok"] is True
    assert data["v"] == 3
    assert data["data"]["number"] == 42


def test_pr_view_json_envelope_overrides_payload_reserved_keys(
    monkeypatch, tmp_git_repo: Path, capsys
) -> None:
    payload = {
        "number": 7,
        "title": "Reserved keys check",
        "state": "OPEN",
        "isDraft": False,
        "author": {"login": "alice"},
        "headRefName": "feat/reserved",
        "baseRefName": "main",
        "url": "https://example.test/pr/7",
        "createdAt": "2026-05-21T10:00:00Z",
        "updatedAt": "2026-05-21T11:00:00Z",
        "mergedAt": None,
        "closedAt": None,
        "mergeable": "MERGEABLE",
        "reviewDecision": "APPROVED",
        "additions": 1,
        "deletions": 0,
        "changedFiles": 1,
        "labels": [],
        "assignees": [],
        "reviewRequests": [],
        "body": "Line 1",
        "v": 999,
        "ok": False,
    }

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    monkeypatch.setattr(pr_module, "_gh", lambda args, cwd: (0, json.dumps(payload), ""))

    rc = pr_module.run_pr(action="view", selector="7", as_json=True)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 0
    assert data["ok"] is True
    assert data["v"] == 3


def test_pr_selector_invalid(monkeypatch, tmp_git_repo: Path) -> None:
    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)

    rc = pr_module.run_pr(action="view", selector="--bad", as_json=False)
    assert rc == 1


def test_pr_checks_human_output(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    payload = [
        {
            "name": "Lint & Format",
            "state": "SUCCESS",
            "startedAt": "2026-05-21T10:00:00Z",
            "completedAt": "2026-05-21T10:00:07Z",
            "link": "https://example.test/check/lint",
            "workflow": "CI",
            "event": "pull_request",
        },
        {
            "name": "Type Check",
            "state": "FAILURE",
            "startedAt": "2026-05-21T10:00:00Z",
            "completedAt": "2026-05-21T10:00:10Z",
            "link": "https://example.test/check/typecheck",
            "workflow": "CI",
            "event": "pull_request",
        },
    ]

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    monkeypatch.setattr(pr_module, "_gh", lambda args, cwd: (0, json.dumps(payload), ""))

    rc = pr_module.run_pr(action="checks", selector="24", as_json=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "Checks 24" in out
    assert "Lint & Format" in out
    assert "Type Check" in out
    assert "pass" in out or "ok" in out
    assert "failed" in out or "fallido" in out


def test_pr_checks_json_output(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    payload = [
        {
            "name": "Tests",
            "state": "SUCCESS",
            "startedAt": "2026-05-21T10:00:00Z",
            "completedAt": "2026-05-21T10:01:40Z",
            "link": "https://example.test/check/tests",
            "workflow": "CI",
            "event": "pull_request",
        }
    ]

    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    monkeypatch.setattr(pr_module, "_gh", lambda args, cwd: (0, json.dumps(payload), ""))

    rc = pr_module.run_pr(action="checks", selector="24", as_json=True)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 0
    assert data["ok"] is True
    assert data["data"]["count"] == 1
    assert data["data"]["summary"]["pass"] == 1


def test_pr_list_passes_filters(monkeypatch, tmp_git_repo: Path) -> None:
    """pr list forwards --state/--author/--label/--limit to gh."""
    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    captured: dict[str, list[str]] = {}

    def _fake_gh(args: list[str], cwd: Path) -> tuple[int, str, str]:
        captured["args"] = args
        return 0, "[]", ""

    monkeypatch.setattr(pr_module, "_gh", _fake_gh)
    rc = pr_module.run_pr(
        action="list",
        as_json=True,
        state="open",
        author="alice",
        label="bug",
        limit=5,
        base="main",
        head="feature-x",
    )
    assert rc == 0
    args = captured["args"]
    assert "--state" in args and "open" in args
    assert "--author" in args and "alice" in args
    assert "--label" in args and "bug" in args
    assert "--limit" in args and "5" in args
    assert "--base" in args and "main" in args
    assert "--head" in args and "feature-x" in args


def test_pr_create_requires_title(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    """pr create without --title/--fill fails with a clear code."""
    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    monkeypatch.setattr(pr_module, "_gh", lambda args, cwd: (0, "https://x", ""))
    rc = pr_module.run_pr(action="create", as_json=True)
    assert rc == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["errors"][0]["code"] == "pr_create_needs_title"


def test_pr_create_delegates_to_gh(monkeypatch, tmp_git_repo: Path, capsys) -> None:
    """pr create --title delegates to gh pr create and returns the URL."""
    monkeypatch.setattr(pr_module, "_gh_available", lambda: True)
    monkeypatch.setattr(pr_module, "require_root", lambda *a, **k: tmp_git_repo)
    captured: dict[str, list[str]] = {}

    def _fake_gh(args: list[str], cwd: Path) -> tuple[int, str, str]:
        captured["args"] = args
        return 0, "https://example.test/pr/7\n", ""

    monkeypatch.setattr(pr_module, "_gh", _fake_gh)
    rc = pr_module.run_pr(
        action="create", as_json=True, title="feat: x", body="body", base="main", head="feat-x"
    )
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["data"]["url"] == "https://example.test/pr/7"
    assert data["data"]["created"] is True
    args = captured["args"]
    assert args[0:2] == ["pr", "create"]
    assert "--title" in args and "feat: x" in args
    assert "--base" in args and "main" in args
    assert "--head" in args and "feat-x" in args
