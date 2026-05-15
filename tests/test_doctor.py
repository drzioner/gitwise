"""Tests for gitwise doctor command."""

import json

from conftest import run_gitwise


def test_version():
    result = run_gitwise("--version")
    assert result.returncode == 0
    assert "gitwise" in result.stdout


def test_doctor_json_structure():
    result = run_gitwise("doctor", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["v"] == 1
    assert "git_version_ok" in data
    assert "python_version_ok" in data
    assert "platform" in data
    assert "optional_tools" in data
    assert "ok" in data


def test_doctor_json_git_version_ok():
    result = run_gitwise("doctor", "--json")
    data = json.loads(result.stdout)
    assert data["git_version_ok"] is True, f"git version check failed: {data['git_version']}"


def test_doctor_json_python_version_ok():
    result = run_gitwise("doctor", "--json")
    data = json.loads(result.stdout)
    assert data["python_version_ok"] is True


def test_doctor_human_output():
    result = run_gitwise("doctor")
    assert result.returncode == 0
    assert "gitwise" in result.stdout
    assert "git" in result.stdout.lower()


def test_doctor_detects_optional_tools():
    result = run_gitwise("doctor", "--json")
    data = json.loads(result.stdout)
    tools = data["optional_tools"]
    assert isinstance(tools["bat"], bool)
    assert isinstance(tools["delta"], bool)
    assert isinstance(tools["rg"], bool)
