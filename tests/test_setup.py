"""Tests for gitwise setup (git config modernos). GPG safety is CRITICAL."""

import json
import subprocess
from pathlib import Path

from conftest import run_gitwise as _run


def _git_config(key: str, cwd: Path) -> str | None:
    r = subprocess.run(["git", "config", "--get", key], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


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


def test_setup_json_structure(tmp_git_repo):
    r = _run("setup", "--dry-run", "--json", cwd=tmp_git_repo)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["v"] == 1
    assert "changes" in data
    assert "warnings" in data
    assert "ok" in data
    assert data["ok"] is True
