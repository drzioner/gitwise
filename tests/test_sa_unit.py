"""Unit tests for setup-agents internal modules: state, exec."""

import os
from pathlib import Path

import pytest
from gitwise.i18n import set_locale
from gitwise.setup_agents.exec import (
    PlanExecutionError,
    SymlinkConflict,
    _apply_managed_block,
    _execute_actions,
    _safe_create_symlink,
    _undo_partial,
)
from gitwise.setup_agents.plan import _bucket4_default, _bucket4_replace
from gitwise.setup_agents.providers.claude import ADAPTER as CLAUDE_PROVIDER
from gitwise.setup_agents.state import (
    _classify_path,
    _detect_rules,
    _detect_state,
    _files_equal,
    _has_marker,
    reset_caches,
)
from gitwise.setup_agents.types import StateDict


class TestClassifyPath:
    def test_absent_file(self, tmp_path: Path) -> None:
        assert _classify_path(tmp_path / "nonexistent") == "absent"

    def test_regular_file(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello")
        assert _classify_path(f) == "regular"

    def test_valid_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "target.txt"
        target.write_text("data")
        link = tmp_path / "link.txt"
        link.symlink_to("target.txt")
        assert _classify_path(link) == "symlink_valid"

    def test_broken_symlink(self, tmp_path: Path) -> None:
        link = tmp_path / "broken"
        link.symlink_to("nonexistent")
        assert _classify_path(link) == "symlink_broken"

    def test_regular_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "dir"
        d.mkdir()
        assert _classify_path(d) == "regular"


class TestDetectState:
    def test_empty_repo(self, tmp_git_repo: Path) -> None:
        reset_caches()
        state = _detect_state(tmp_git_repo)
        assert state["a_state"] == "absent"
        assert state["c_state"] == "absent"
        assert state["agents_dir"] is False
        assert state["supports_symlinks"] is True
        assert state["errors"] == []

    def test_with_agents_md(self, tmp_git_repo: Path) -> None:
        reset_caches()
        (tmp_git_repo / "AGENTS.md").write_text("# Agents\n")
        state = _detect_state(tmp_git_repo)
        assert state["a_state"] == "regular"

    def test_with_broken_symlink(self, tmp_git_repo: Path) -> None:
        reset_caches()
        link = tmp_git_repo / "CLAUDE.md"
        link.symlink_to("nonexistent")
        state = _detect_state(tmp_git_repo)
        assert state["c_state"] == "symlink_broken"
        assert len(state["errors"]) > 0

    def test_with_valid_symlink(self, tmp_git_repo: Path) -> None:
        reset_caches()
        (tmp_git_repo / "AGENTS.md").write_text("# Agents\n")
        link = tmp_git_repo / "CLAUDE.md"
        link.symlink_to("AGENTS.md")
        state = _detect_state(tmp_git_repo)
        assert state["c_state"] == "symlink_valid"

    def test_detects_rules_warnings(self, tmp_git_repo: Path) -> None:
        reset_caches()
        rules_dir = tmp_git_repo / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "bad.md").write_text("no frontmatter here\n")
        state = _detect_state(tmp_git_repo)
        assert len(state["rules_warnings"]) > 0

    def test_detects_valid_rules(self, tmp_git_repo: Path) -> None:
        reset_caches()
        rules_dir = tmp_git_repo / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "good.md").write_text("---\nglobs: **/*.py\n---\ncontent\n")
        state = _detect_state(tmp_git_repo)
        assert state["rules_warnings"] == []

    def test_skills_symlink_read_error_reported(self, tmp_git_repo: Path, monkeypatch) -> None:
        reset_caches()
        skills_dir = tmp_git_repo / ".claude" / "skills"
        skills_dir.parent.mkdir(parents=True)
        skills_dir.symlink_to("../missing-target")

        monkeypatch.setattr("gitwise.setup_agents.state._classify_path", lambda p: "symlink_valid")
        monkeypatch.setattr(
            "gitwise.setup_agents.state.os.readlink",
            lambda p: (_ for _ in ()).throw(OSError("boom")),
        )

        state = _detect_state(tmp_git_repo)
        assert any("skills" in e.lower() for e in state["errors"])


class TestSafeCreateSymlink:
    def test_creates_symlink(self, tmp_path: Path) -> None:
        link = tmp_path / "CLAUDE.md"
        _safe_create_symlink(link, "AGENTS.md", tmp_path)
        assert link.is_symlink()
        assert os.readlink(link) == "AGENTS.md"

    def test_idempotent_same_target(self, tmp_path: Path) -> None:
        link = tmp_path / "CLAUDE.md"
        _safe_create_symlink(link, "AGENTS.md", tmp_path)
        _safe_create_symlink(link, "AGENTS.md", tmp_path)
        assert os.readlink(link) == "AGENTS.md"

    def test_conflict_different_target(self, tmp_path: Path) -> None:
        link = tmp_path / "CLAUDE.md"
        _safe_create_symlink(link, "AGENTS.md", tmp_path)
        with pytest.raises(SymlinkConflict):
            _safe_create_symlink(link, "OTHER.md", tmp_path)

    def test_conflict_regular_file(self, tmp_path: Path) -> None:
        link = tmp_path / "CLAUDE.md"
        link.write_text("content")
        with pytest.raises(SymlinkConflict):
            _safe_create_symlink(link, "AGENTS.md", tmp_path)

    def test_sandbox_escape(self, tmp_path: Path) -> None:
        link = tmp_path / "CLAUDE.md"
        with pytest.raises(SymlinkConflict):
            _safe_create_symlink(link, "/etc/passwd", tmp_path)

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        link = tmp_path / ".claude" / "skills"
        _safe_create_symlink(link, "../agents/skills", tmp_path)
        assert link.is_symlink()


class TestUndoPartial:
    def test_undo_symlink_create(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("agents")
        link = tmp_path / "CLAUDE.md"
        link.symlink_to("AGENTS.md")
        assert link.is_symlink()
        actions = [{"action": "symlink-create", "file": "CLAUDE.md"}]
        _undo_partial(actions, tmp_path)
        assert not link.exists()

    def test_undo_created_file(self, tmp_path: Path) -> None:
        f = tmp_path / "CLAUDE.md"
        f.write_text("content")
        actions = [{"action": "create", "file": "CLAUDE.md", "_created": True}]
        _undo_partial(actions, tmp_path)
        assert not f.exists()

    def test_undo_replace_with_symlink(self, tmp_path: Path) -> None:
        original = tmp_path / "CLAUDE.md"
        original.write_text("original")
        backup = tmp_path / "CLAUDE.md.bak"
        original.rename(backup)
        link = tmp_path / "CLAUDE.md"
        link.symlink_to("AGENTS.md")
        actions = [
            {
                "action": "claude-md-replace-with-symlink",
                "file": "CLAUDE.md",
                "backup_path": str(backup),
            }
        ]
        _undo_partial(actions, tmp_path)
        assert not link.is_symlink()
        assert original.read_text() == "original"

    def test_empty_actions_noop(self, tmp_path: Path) -> None:
        _undo_partial([], tmp_path)

    def test_skip_actions_not_undone(self, tmp_path: Path) -> None:
        actions = [{"action": "skip", "file": "CLAUDE.md"}]
        _undo_partial(actions, tmp_path)


class TestApplyManagedBlock:
    def test_create_new_file(self, tmp_path: Path) -> None:
        f = tmp_path / ".gitignore"
        action = {
            "action": "managed-block-create",
            "_path": str(f),
            "content": "# managed\n*.pyc\n",
        }
        _apply_managed_block(action)
        assert f.read_text() == "# managed\n*.pyc\n"

    def test_append_to_existing(self, tmp_path: Path) -> None:
        f = tmp_path / ".gitignore"
        f.write_text("node_modules/\n")
        action = {
            "action": "managed-block-create",
            "_path": str(f),
            "content": "# managed\n*.pyc\n",
            "_append": True,
        }
        _apply_managed_block(action)
        text = f.read_text()
        assert "node_modules/" in text
        assert "# managed" in text

    def test_replace_block(self, tmp_path: Path) -> None:
        f = tmp_path / ".gitignore"
        f.write_text("before\n# old block\nold content\n# end\nafter\n")
        action = {
            "action": "managed-block-replace",
            "_path": str(f),
            "content": "# new block\nnew content\n",
            "_start_idx": 7,
            "_end_idx": 33,
        }
        _apply_managed_block(action)
        text = f.read_text()
        assert "new content" in text
        assert "old content" not in text


class TestExecuteActions:
    def test_create_claude_md(self, tmp_path: Path) -> None:
        actions = [
            {"file": "CLAUDE.md", "action": "create", "content": "# Claude\n"},
        ]
        _execute_actions(tmp_path, actions)
        assert (tmp_path / "CLAUDE.md").read_text() == "# Claude\n"

    def test_create_settings_json(self, tmp_path: Path) -> None:
        actions = [
            {"file": ".claude/settings.json", "action": "create", "data": {"key": "val"}},
        ]
        _execute_actions(tmp_path, actions)
        result = (tmp_path / ".claude" / "settings.json").read_text()
        assert "key" in result

    def test_skip_action(self, tmp_path: Path) -> None:
        actions = [
            {"file": "CLAUDE.md", "action": "skip"},
        ]
        _execute_actions(tmp_path, actions)
        assert not (tmp_path / "CLAUDE.md").exists()

    def test_raises_on_symlink_conflict(self, tmp_path: Path) -> None:
        actions = [
            {"file": "CLAUDE.md", "action": "symlink-create", "target_relative": "/etc/passwd"},
        ]
        with pytest.raises(PlanExecutionError):
            _execute_actions(tmp_path, actions)

    def test_rollback_on_failure(self, tmp_path: Path) -> None:
        actions = [
            {"file": "CLAUDE.md", "action": "create", "content": "# Claude\n"},
            {"file": "CLAUDE.md", "action": "symlink-create", "target_relative": "/etc/passwd"},
        ]
        with pytest.raises(PlanExecutionError):
            _execute_actions(tmp_path, actions)
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "# Claude\n"

    def test_generate_snapshot_to_agents_path(self, tmp_path: Path) -> None:
        actions = [
            {"file": ".agents/git-snapshot.md", "action": "generate", "frozen_time": True},
        ]
        _execute_actions(tmp_path, actions)
        snapshot = tmp_path / ".agents" / "git-snapshot.md"
        assert snapshot.exists()
        content = snapshot.read_text(encoding="utf-8")
        assert "generated_at: 1970-01-01T00:00:00Z" in content

    def test_transactional_rollback_restores_managed_block_append(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n", encoding="utf-8")
        actions = [
            {
                "file": ".gitignore",
                "action": "managed-block-create",
                "_path": str(gitignore),
                "content": "# managed\n*.pyc\n",
                "_append": True,
            },
            {"file": "CLAUDE.md", "action": "symlink-create", "target_relative": "/etc/passwd"},
        ]
        with pytest.raises(PlanExecutionError):
            _execute_actions(tmp_path, actions)
        assert gitignore.read_text(encoding="utf-8") == "node_modules/\n"

    def test_transactional_rollback_restores_append_on_agents_md(self, tmp_path: Path) -> None:
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text("# Existing\n", encoding="utf-8")
        actions = [
            {"file": "AGENTS.md", "action": "append", "content": "## Added\n"},
            {"file": "CLAUDE.md", "action": "symlink-create", "target_relative": "/etc/passwd"},
        ]
        with pytest.raises(PlanExecutionError):
            _execute_actions(tmp_path, actions)
        assert agents_md.read_text(encoding="utf-8") == "# Existing\n"

    def test_transactional_rollback_restores_managed_block_replace(self, tmp_path: Path) -> None:
        gitattributes = tmp_path / ".gitattributes"
        original = "CLAUDE.md text=auto eol=lf\n"
        gitattributes.write_text(original, encoding="utf-8")
        actions = [
            {
                "file": ".gitattributes",
                "action": "managed-block-replace",
                "_path": str(gitattributes),
                "content": "# >>> gitwise managed (do not edit between markers) >>>\nnew\n# <<< gitwise managed <<<\n",
                "_start_idx": 0,
                "_end_idx": len(original),
            },
            {"file": "CLAUDE.md", "action": "symlink-create", "target_relative": "/etc/passwd"},
        ]
        with pytest.raises(PlanExecutionError):
            _execute_actions(tmp_path, actions)
        assert gitattributes.read_text(encoding="utf-8") == original


class TestHasMarker:
    def test_with_git_conventions_marker(self, tmp_path: Path) -> None:
        f = tmp_path / "AGENTS.md"
        f.write_text("# Title\n## Git conventions for this project\n- rule1\n")
        assert _has_marker(f) is True

    def test_with_spanish_marker(self, tmp_path: Path) -> None:
        f = tmp_path / "AGENTS.md"
        f.write_text("# Title\n## Convenciones git para este proyecto\n- regla1\n")
        assert _has_marker(f) is True

    def test_without_marker(self, tmp_path: Path) -> None:
        f = tmp_path / "AGENTS.md"
        f.write_text("# Title\nOther content\n")
        assert _has_marker(f) is False

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        assert _has_marker(tmp_path / "nonexistent") is False


class TestFilesEqual:
    def test_equal_files(self, tmp_path: Path) -> None:
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("same content")
        b.write_text("same content")
        assert _files_equal(a, b) is True

    def test_different_files(self, tmp_path: Path) -> None:
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("content a")
        b.write_text("content b")
        assert _files_equal(a, b) is False

    def test_missing_file(self, tmp_path: Path) -> None:
        a = tmp_path / "a.txt"
        b = tmp_path / "missing.txt"
        a.write_text("content")
        assert _files_equal(a, b) is False


class TestDetectRules:
    def test_empty_rules_dir(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        assert _detect_rules(tmp_path) == []

    def test_valid_rule_with_globs(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "test.md").write_text("---\nglobs: **/*.py\n---\nrule\n")
        assert _detect_rules(tmp_path) == []

    def test_missing_globs_warning(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "bad.md").write_text("---\ntitle: bad\n---\nno globs\n")
        warnings = _detect_rules(tmp_path)
        assert len(warnings) > 0

    def test_no_frontmatter_warning(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "no_fm.md").write_text("plain text\n")
        warnings = _detect_rules(tmp_path)
        assert len(warnings) > 0


class TestPlanI18nKeys:
    def test_bucket4_default_emits_existing_key(self, tmp_path: Path) -> None:
        set_locale("en")
        claude_md = tmp_path / "CLAUDE.md"
        agents_actions: list[dict] = []
        state: StateDict = {
            "c_state": "symlink_valid",
            "a_state": "regular",
            "agents_dir": False,
            "skills_state": "absent",
            "skills_target": None,
            "supports_symlinks": True,
            "errors": [],
            "rules_warnings": [],
        }

        _, _, warnings = _bucket4_default(state, claude_md, agents_actions)
        assert len(warnings) == 1
        assert "claude_md_symlink_other" not in warnings[0]
        assert "CLAUDE.md" in warnings[0]

    def test_bucket4_replace_emits_existing_key(self, tmp_path: Path) -> None:
        set_locale("en")
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("custom\n", encoding="utf-8")

        _, actions, warnings = _bucket4_replace([], claude_md)
        assert len(actions) == 1
        assert actions[0]["action"] == "claude-md-replace-with-symlink"
        assert len(warnings) == 1
        assert "claude_md_replaced" not in warnings[0]
        assert "CLAUDE.md" in warnings[0]


class TestClaudeProviderWrapper:
    def test_plan_settings_returns_create_or_merge(self, tmp_git_repo: Path) -> None:
        actions, warnings = CLAUDE_PROVIDER.plan_settings(tmp_git_repo)
        assert len(actions) == 1
        assert actions[0]["file"] == ".claude/settings.json"
        assert actions[0]["action"] in {"create", "merge"}
        assert isinstance(warnings, list)

    def test_plan_rules_returns_create_or_skip(self, tmp_git_repo: Path) -> None:
        actions, warnings = CLAUDE_PROVIDER.plan_rules(tmp_git_repo)
        assert len(actions) == 1
        assert actions[0]["file"] == ".claude/rules/gitwise.md"
        assert actions[0]["action"] in {"create", "skip"}
        assert isinstance(warnings, list)

    def test_plan_snapshot_uses_frozen_time_flag(self) -> None:
        actions = CLAUDE_PROVIDER.plan_snapshot(frozen_time=True)
        assert actions == [
            {
                "file": ".claude/git-snapshot.md",
                "action": "generate",
                "frozen_time": True,
            }
        ]
