"""Tests for gitwise setup (git config modernos). GPG safety is CRITICAL."""

import json
import subprocess
from pathlib import Path

from conftest import run_gitwise as _run


def _git_config(key: str, cwd: Path) -> str | None:
    r = subprocess.run(["git", "config", "--get", key], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def _git_config_all(key: str, cwd: Path) -> list[str]:
    r = subprocess.run(
        ["git", "config", "--get-all", key], cwd=cwd, capture_output=True, text=True
    )
    if r.returncode != 0:
        return []
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def _supports_config_hooks(cwd: Path) -> bool:
    r = subprocess.run(
        ["git", "hook", "list", "pre-commit"], cwd=cwd, capture_output=True, text=True
    )
    combined = f"{r.stdout}\n{r.stderr}".lower()
    return "not a git command" not in combined and "unknown subcommand" not in combined


def test_gpg_config_not_modified(tmp_git_repo_with_gpg_config):
    """CRÍTICO: setup NUNCA debe tocar commit.gpgsign ni user.signingkey."""
    repo = tmp_git_repo_with_gpg_config
    _run("setup", "--yes", cwd=repo)
    assert _git_config("commit.gpgsign", repo) == "true"
    assert _git_config("user.signingkey", repo) == "TESTKEY123ABC"


def test_idempotent(tmp_git_repo):
    """Ejecutar setup --dry-run dos veces produce el mismo JSON."""
    r1 = _run("setup", "--dry-run", "--json", cwd=tmp_git_repo)
    r2 = _run("setup", "--dry-run", "--json", cwd=tmp_git_repo)
    d1 = json.loads(r1.stdout)
    d2 = json.loads(r2.stdout)
    assert d1["changes"] == d2["changes"]


def test_idempotent_after_apply(tmp_git_repo):
    """Después de --yes, re-ejecutar con --dry-run no reporta más cambios."""
    _run("setup", "--yes", cwd=tmp_git_repo)
    r = _run("setup", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0


def test_dry_run_no_changes(tmp_git_repo):
    """--dry-run no modifica ninguna config."""
    before = {
        "fetch.prune": _git_config("fetch.prune", tmp_git_repo),
        "diff.algorithm": _git_config("diff.algorithm", tmp_git_repo),
    }
    _run("setup", "--dry-run", cwd=tmp_git_repo)
    after = {
        "fetch.prune": _git_config("fetch.prune", tmp_git_repo),
        "diff.algorithm": _git_config("diff.algorithm", tmp_git_repo),
    }
    assert before == after


def test_setup_json_requires_yes(tmp_git_repo: Path) -> None:
    """Q1: setup --json without --yes must return yes_required envelope without applying."""
    r = _run("setup", "--json", cwd=tmp_git_repo)
    assert r.returncode == 2
    data = json.loads(r.stdout)
    assert data["ok"] is False
    assert data["errors"][0]["code"] == "yes_required"
    assert "hint" in data["errors"][0]
    # Verify no config keys were applied: e.g. merge.conflictstyle should not be set.
    assert _git_config("merge.conflictstyle", tmp_git_repo) is None


def test_setup_json_structure(tmp_git_repo):
    r = _run("setup", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 2
    assert "changes" in data
    assert "warnings" in data
    assert "ok" in data
    assert "hooks_backend" in data
    assert "hooks_mode_requested" in data
    assert data["ok"] is True


def test_setup_legacy_mode_sets_core_hookspath(tmp_git_repo):
    _run("setup", "--yes", "--hooks-mode", "legacy", cwd=tmp_git_repo)
    hooks_dir = str(Path(__file__).parent.parent / "share" / "hooks")
    assert _git_config("core.hooksPath", tmp_git_repo) == hooks_dir


def test_setup_skip_mode_does_not_manage_hooks(tmp_git_repo):
    _run("setup", "--yes", "--hooks-mode", "skip", cwd=tmp_git_repo)
    assert _git_config("core.hooksPath", tmp_git_repo) is None
    assert _git_config("hook.gitwise-gpg.command", tmp_git_repo) is None
    assert _git_config_all("hook.gitwise-gpg.event", tmp_git_repo) == []


def test_setup_preserve_keeps_existing_hookspath(tmp_git_repo):
    subprocess.run(
        ["git", "config", "core.hooksPath", ".husky/_"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    _run("setup", "--yes", cwd=tmp_git_repo)
    assert _git_config("core.hooksPath", tmp_git_repo) == ".husky/_"


def test_setup_native_mode_uses_config_hooks_when_supported(tmp_git_repo):
    r = _run("setup", "--yes", "--hooks-mode", "native", cwd=tmp_git_repo)
    assert r.returncode == 0

    if _supports_config_hooks(tmp_git_repo):
        hooks_dir = str(Path(__file__).parent.parent / "share" / "hooks")
        assert _git_config("hook.gitwise-gpg.command", tmp_git_repo) == str(
            Path(hooks_dir) / "pre-commit"
        )
        assert "pre-commit" in _git_config_all("hook.gitwise-gpg.event", tmp_git_repo)
        assert _git_config("core.hooksPath", tmp_git_repo) is None
    else:
        assert _git_config("hook.gitwise-gpg.command", tmp_git_repo) is None


def test_setup_legacy_mode_reports_overwrite_warning_in_json(tmp_git_repo):
    subprocess.run(
        ["git", "config", "commit.gpgsign", "true"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.signingkey", "TESTKEY123ABC"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "core.hooksPath", ".husky/_"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    r = _run(
        "setup",
        "--dry-run",
        "--json",
        "--hooks-mode",
        "legacy",
        cwd=tmp_git_repo,
        env={"GITWISE_LANG": "en"},
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert any("legacy mode will overwrite current core.hooksPath" in w for w in data["warnings"])


def test_setup_preserve_skips_when_existing_hook_scripts_present(tmp_git_repo):
    hooks_dir = tmp_git_repo / ".git" / "hooks"
    hook_file = hooks_dir / "pre-commit"
    hook_file.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    r = _run(
        "setup",
        "--dry-run",
        "--json",
        cwd=tmp_git_repo,
        env={"GITWISE_LANG": "en"},
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["hooks_backend"] == "skip"
    assert any("existing hooks detected (pre-commit)" in w for w in data["warnings"])


def test_setup_preserve_keeps_legacy_when_gitwise_hookspath_already_set(tmp_git_repo):
    hooks_dir = str(Path(__file__).parent.parent / "share" / "hooks")
    subprocess.run(
        ["git", "config", "core.hooksPath", hooks_dir],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    r = _run("setup", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["hooks_backend"] == "legacy"
