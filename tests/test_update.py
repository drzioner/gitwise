"""Tests for the deprecated gitwise update command."""

import json
from pathlib import Path

import gitwise.update as update_module
import pytest


def _set_install_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, source_clone: bool
) -> Path:
    package_dir = tmp_path / "gitwise"
    package_dir.mkdir()
    if source_clone:
        (tmp_path / ".git").mkdir()
    monkeypatch.setattr(update_module, "__file__", str(package_dir / "update.py"))
    return tmp_path


def _assert_upgrade_channels(hints: list[str]) -> None:
    combined = " ".join(hints)
    assert "brew upgrade gitwise" in combined
    assert "uv tool upgrade gitwise-cli" in combined


def test_update_non_clone_json_recommends_upgrade_channels(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    _set_install_dir(monkeypatch, tmp_path, source_clone=False)

    rc = update_module.run_update(as_json=True)

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["errors"][0]["code"] == "update_requires_git_clone"
    _assert_upgrade_channels(payload["hints"])


def test_update_clone_dry_run_json_preserves_behavior_and_recommends_channels(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    install_dir = _set_install_dir(monkeypatch, tmp_path, source_clone=True)

    rc = update_module.run_update(dry_run=True, as_json=True)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["dry_run"] is True
    assert payload["data"]["dir"] == str(install_dir)
    _assert_upgrade_channels(payload["hints"])


def test_update_clone_dry_run_human_warns_with_upgrade_channels(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    _set_install_dir(monkeypatch, tmp_path, source_clone=True)

    rc = update_module.run_update(dry_run=True)

    assert rc == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "brew upgrade gitwise" in output
    assert "uv tool upgrade gitwise-cli" in output
