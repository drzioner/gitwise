"""Tests for the adapter registry and planning system."""

import json

from conftest import run_gitwise


class TestListAdapters:
    def test_list_adapters_shows_all_seven(self):
        result = run_gitwise("setup-agents", "--list-providers")
        assert result.returncode == 0
        for name in ("claude", "cursor", "continue", "opencode", "codex", "aider", "pi"):
            assert name in result.stdout

    def test_list_adapters_in_json_mode(self):
        result = run_gitwise("setup-agents", "--list-providers", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "providers" in data
        assert "adapters" in data
        for name in ("claude", "cursor", "continue", "opencode", "codex", "aider", "pi"):
            assert name in data["providers"]
            assert name in data["adapters"]

    def test_list_adapters_alias_still_works(self):
        result = run_gitwise("setup-agents", "--list-adapters", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "providers" in data
        assert "adapters" in data

    def test_single_adapter_claude_no_extra_adapter_actions(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "claude",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert "ADAPTER-CREATE" not in result.stdout


class TestAdapterDryRun:
    def test_single_adapter_cursor(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "cursor",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert "ADAPTER-CREATE" in result.stdout
        assert ".cursor/rules/gitwise.mdc" in result.stdout

    def test_single_adapter_aider(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "aider",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".aider.conf.yml" in result.stdout
        assert "CONVENTIONS.md" in result.stdout

    def test_single_adapter_codex(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "codex",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".codex/agents/gitwise.toml" in result.stdout

    def test_single_adapter_opencode(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "opencode",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".opencode/agents/gitwise.md" in result.stdout

    def test_single_adapter_continue(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "continue",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".continue/rules/gitwise.md" in result.stdout

    def test_single_adapter_pi(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "pi",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".pi/agent/skills/gitwise.md" in result.stdout

    def test_multiple_adapters(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "cursor",
            "aider",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".cursor/rules/gitwise.mdc" in result.stdout
        assert ".aider.conf.yml" in result.stdout
        assert "CONVENTIONS.md" in result.stdout

    def test_comma_separated_adapters(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "cursor,aider",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".cursor/rules/gitwise.mdc" in result.stdout
        assert ".aider.conf.yml" in result.stdout

    def test_adapters_none_no_adapter_actions(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "none",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert "ADAPTER-CREATE" not in result.stdout

    def test_adapters_claude_only_no_adapter_actions(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "claude-only",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert "ADAPTER-CREATE" not in result.stdout

    def test_adapters_claude_only_aliases_to_claude(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--json",
            "--providers",
            "claude-only",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert any(a.get("file") == ".claude/settings.json" for a in data.get("actions", []))
        assert any("deprecated alias" in w for w in data.get("warnings", []))

    def test_adapters_claude_only_warns_in_global_mode(self, tmp_path):
        result = run_gitwise(
            "setup-agents",
            "--dry-run",
            "--yes",
            "--json",
            "--providers",
            "claude-only",
            cwd=tmp_path,
            env={"HOME": str(tmp_path), "GITWISE_LANG": "en"},
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["mode"] == "global"
        assert any("deprecated alias" in w for w in data.get("warnings", []))

    def test_global_mode_allows_adapters(self, tmp_path):
        result = run_gitwise(
            "setup-agents",
            "--dry-run",
            "--yes",
            "--json",
            "--providers",
            "cursor",
            cwd=tmp_path,
            env={"HOME": str(tmp_path), "GITWISE_LANG": "en"},
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["mode"] == "global"
        assert any(a.get("file") == ".cursor/rules/gitwise.mdc" for a in data.get("actions", []))

    def test_adapters_none_with_others_errors(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "cursor",
            "none",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 1
        assert "cannot be combined" in result.stderr or "cannot be combined" in result.stdout

    def test_adapters_claude_only_with_others_is_allowed(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "claude-only",
            "cursor",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".cursor/rules/gitwise.mdc" in result.stdout

    def test_duplicate_adapter_idempotent(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "cursor",
            "cursor",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert ".cursor/rules/gitwise.mdc" in result.stdout

    def test_no_adapters_flag_no_adapter_actions(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert "ADAPTER-CREATE" not in result.stdout

    def test_unknown_adapter_errors(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "nonexistent",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 1
        assert "nonexistent" in result.stderr or "nonexistent" in result.stdout


class TestAdapterIdempotency:
    def test_cursor_idempotent_on_rerun(self, tmp_git_repo):
        run_gitwise(
            "setup-agents",
            "--local",
            "--yes",
            "--providers",
            "cursor",
            cwd=tmp_git_repo,
        )
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "cursor",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert "already exists" in (result.stdout + result.stderr)
        assert "ADAPTER-CREATE" not in result.stdout

    def test_all_adapters_install(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--yes",
            "--providers",
            "cursor",
            "continue",
            "opencode",
            "codex",
            "aider",
            "pi",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0

        root = tmp_git_repo
        assert (root / ".cursor" / "rules" / "gitwise.mdc").exists()
        assert (root / ".continue" / "rules" / "gitwise.md").exists()
        assert (root / ".opencode" / "agents" / "gitwise.md").exists()
        assert (root / ".codex" / "agents" / "gitwise.toml").exists()
        assert (root / ".aider.conf.yml").exists()
        assert (root / "CONVENTIONS.md").exists()
        assert (root / ".pi" / "agent" / "skills" / "gitwise.md").exists()

    def test_all_adapters_idempotent(self, tmp_git_repo):
        run_gitwise(
            "setup-agents",
            "--local",
            "--yes",
            "--providers",
            "cursor",
            "continue",
            "opencode",
            "codex",
            "aider",
            "pi",
            cwd=tmp_git_repo,
        )
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--providers",
            "cursor",
            "continue",
            "opencode",
            "codex",
            "aider",
            "pi",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        assert "ADAPTER-CREATE" not in result.stdout


class TestAdapterContent:
    def test_cursor_mdc_has_frontmatter(self, tmp_git_repo):
        run_gitwise(
            "setup-agents",
            "--local",
            "--yes",
            "--providers",
            "cursor",
            cwd=tmp_git_repo,
        )
        content = (tmp_git_repo / ".cursor" / "rules" / "gitwise.mdc").read_text()
        assert content.startswith("---")
        assert "alwaysApply: true" in content
        assert "gitwise diff" in content

    def test_aider_conf_reads_agents_md(self, tmp_git_repo):
        run_gitwise(
            "setup-agents",
            "--local",
            "--yes",
            "--providers",
            "aider",
            cwd=tmp_git_repo,
        )
        content = (tmp_git_repo / ".aider.conf.yml").read_text()
        assert "AGENTS.md" in content
        assert "CONVENTIONS.md" in content

    def test_codex_toml_has_name(self, tmp_git_repo):
        run_gitwise(
            "setup-agents",
            "--local",
            "--yes",
            "--providers",
            "codex",
            cwd=tmp_git_repo,
        )
        content = (tmp_git_repo / ".codex" / "agents" / "gitwise.toml").read_text()
        assert 'name = "gitwise"' in content
        assert "developer_instructions" in content

    def test_conventions_md_has_git_conventions(self, tmp_git_repo):
        run_gitwise(
            "setup-agents",
            "--local",
            "--yes",
            "--providers",
            "aider",
            cwd=tmp_git_repo,
        )
        content = (tmp_git_repo / "CONVENTIONS.md").read_text()
        assert "gitwise diff" in content
        assert "GPG-signed" in content

    def test_adapter_actions_in_json_output(self, tmp_git_repo):
        result = run_gitwise(
            "setup-agents",
            "--local",
            "--dry-run",
            "--yes",
            "--json",
            "--providers",
            "cursor",
            cwd=tmp_git_repo,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        adapter_actions = [
            a for a in data.get("actions", []) if a.get("action") == "adapter-create"
        ]
        assert len(adapter_actions) == 1
        assert ".cursor/rules/gitwise.mdc" in adapter_actions[0]["file"]
