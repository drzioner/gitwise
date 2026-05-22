"""Tests for gitwise output — color detection, bat_pipe, JSON output."""

import json

from conftest import run_gitwise as _run


def test_no_color_env_disables_color():
    result = _run("audit", "--quick", env={"NO_COLOR": "1", "GITWISE_LANG": "en"})
    assert result.returncode in (0, 1)
    for line in result.stderr.splitlines():
        if "warning:" in line.lower():
            assert "\033[" not in line


def test_gitwise_no_color_env():
    result = _run("audit", "--quick", env={"GITWISE_NO_COLOR": "1"})
    assert result.returncode in (0, 1)


def test_json_output_no_color_codes(tmp_git_repo):
    result = _run("audit", "--json", cwd=tmp_git_repo)
    assert result.returncode in (0, 1)
    assert "\033[" not in result.stdout
    data = json.loads(result.stdout)
    assert "v" in data


def test_json_output_is_valid(tmp_git_repo):
    result = _run("summarize", "--json", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert data["v"] == 3
    assert "branch" in data
    assert "ok" in data


def test_json_pretty_indentation_when_flag_used(tmp_git_repo):
    result = _run("summarize", "--json-pretty", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert '\n  "' in result.stdout


def test_bat_pipe_fallback_without_bat():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from gitwise.output import bat_pipe

    bat_pipe("test output\n", language="plain")


def test_bat_pipe_empty_string():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from gitwise.output import bat_pipe

    bat_pipe("", language="plain")


def test_print_json_output(tmp_git_repo):
    result = _run("diff", "--json", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert "files" in data
    assert "count" in data


def test_error_goes_to_stderr(tmp_git_repo):
    result = _run("clean", "--branches", "--yes", cwd=tmp_git_repo)
    assert result.returncode in (0, 1)


def test_bat_pipe_fallback_when_binary_missing(monkeypatch, capsys):
    import gitwise.output as output_module

    class _Cfg:
        has_bat = True
        is_tty = True
        debug = False

    monkeypatch.setattr(output_module, "get_runtime_config", lambda: _Cfg())
    monkeypatch.setattr(
        output_module.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("missing")),
    )

    output_module.bat_pipe("hello\n", language="python")
    captured = capsys.readouterr()
    assert "hello" in captured.out
