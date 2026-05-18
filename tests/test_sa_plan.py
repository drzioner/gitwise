"""Unit tests for setup-agents planning modules: plan_gitfiles, plan_skills."""

import os
from pathlib import Path

from gitwise.setup_agents.plan_gitfiles import (
    _MANAGED_MARKER_END,
    _MANAGED_MARKER_START,
    gitattributes_block_basic,
    gitattributes_block_extended,
    gitignore_block_basic,
    gitignore_block_extended,
    plan_managed_block,
)
from gitwise.setup_agents.plan_skills import (
    _SKILLS,
    plan_global_skills,
    plan_skills,
)
from gitwise.setup_agents.types import StateDict


class TestGitignoreBlocks:
    def test_basic_contains_expected_patterns(self) -> None:
        block = gitignore_block_basic()
        assert ".claude/settings.local.json" in block
        assert "*.bak" in block
        assert _MANAGED_MARKER_START in block
        assert _MANAGED_MARKER_END in block
        assert "AGENTS.md.bak*" not in block

    def test_extended_includes_agents_md_bak(self) -> None:
        block = gitignore_block_extended(has_agents_md=True)
        assert "AGENTS.md.bak*" in block
        block_no = gitignore_block_extended(has_agents_md=False)
        assert "AGENTS.md.bak*" not in block_no

    def test_blocks_end_with_newline_after_marker(self) -> None:
        basic = gitignore_block_basic()
        extended = gitignore_block_extended(has_agents_md=True)
        assert basic.endswith(_MANAGED_MARKER_END + "\n")
        assert extended.endswith(_MANAGED_MARKER_END + "\n")


class TestGitattributesBlocks:
    def test_basic_contains_snapshot_rule(self) -> None:
        block = gitattributes_block_basic()
        assert "merge=ours" in block
        assert "linguist-generated=true" in block

    def test_extended_includes_agents_md(self) -> None:
        block = gitattributes_block_extended(has_agents_md=True, has_agents_dir=False)
        assert "AGENTS.md text=auto eol=lf" in block
        assert ".agents/skills" not in block

    def test_extended_includes_agents_dir(self) -> None:
        block = gitattributes_block_extended(has_agents_md=True, has_agents_dir=True)
        assert ".agents/skills/**/SKILL.md text=auto eol=lf" in block

    def test_extended_no_agents_excludes_agents_line(self) -> None:
        block = gitattributes_block_extended(has_agents_md=False, has_agents_dir=False)
        assert "AGENTS.md" not in block


class TestPlanManagedBlock:
    def test_nonexistent_creates_block(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitignore"
        block = "# test content\n"
        actions, warnings = plan_managed_block(path, block, ".gitignore")
        assert len(actions) == 1
        assert actions[0]["action"] == "managed-block-create"
        assert actions[0]["content"] == block

    def test_existing_without_markers_appends(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitignore"
        path.write_text("original content\n", encoding="utf-8")
        block = "# new block\n"
        actions, warnings = plan_managed_block(path, block, ".gitignore")
        assert len(actions) == 1
        assert actions[0]["action"] == "managed-block-create"
        assert actions[0]["_append"] is True

    def test_existing_skip_identical_block(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitattributes"
        content = f"{_MANAGED_MARKER_START}\nline1\n{_MANAGED_MARKER_END}\n"
        path.write_text(content, encoding="utf-8")
        actions, warnings = plan_managed_block(path, content, ".gitattributes")
        assert len(actions) == 1
        assert actions[0]["action"] == "managed-block-skip"

    def test_rstrip_normalization_skips_block(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitattributes"
        desired = f"{_MANAGED_MARKER_START}\nline1\n{_MANAGED_MARKER_END}\n"
        on_disk = desired + "   \n"
        path.write_text(on_disk, encoding="utf-8")
        actions, warnings = plan_managed_block(path, desired, ".gitattributes")
        assert len(actions) == 1
        assert actions[0]["action"] == "managed-block-skip"

    def test_existing_replaces_different_block(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitattributes"
        old = f"{_MANAGED_MARKER_START}\nold content\n{_MANAGED_MARKER_END}\n"
        new = f"{_MANAGED_MARKER_START}\nnew content\n{_MANAGED_MARKER_END}\n"
        path.write_text(old, encoding="utf-8")
        actions, warnings = plan_managed_block(path, new, ".gitattributes")
        assert len(actions) == 1
        assert actions[0]["action"] == "managed-block-replace"
        assert actions[0]["_start_idx"] == 0
        assert actions[0]["_end_idx"] == len(_MANAGED_MARKER_START) + 13 + len(_MANAGED_MARKER_END)

    def test_unclosed_marker_produces_warning(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitignore"
        path.write_text(f"{_MANAGED_MARKER_START}\nno end marker\n", encoding="utf-8")
        actions, warnings = plan_managed_block(path, "new", ".gitignore")
        assert actions == []
        assert len(warnings) > 0

    def test_gitattributes_conflict_detection(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitattributes"
        outside = "CLAUDE.md text=auto eol=crlf\n"
        new_block = f"{_MANAGED_MARKER_START}\nCLAUDE.md text=auto eol=lf\n{_MANAGED_MARKER_END}\n"
        path.write_text(outside + new_block, encoding="utf-8")
        actions, warnings = plan_managed_block(path, new_block, ".gitattributes")
        assert len(actions) == 1
        assert actions[0]["action"] == "managed-block-skip"
        assert any("conflict" in w for w in warnings)

    def test_no_conflict_for_gitignore(self, tmp_path: Path) -> None:
        path = tmp_path / ".gitignore"
        existing = (
            f"{_MANAGED_MARKER_START}\nold\n{_MANAGED_MARKER_END}\nCLAUDE.md text=auto eol=lf\n"
        )
        new_block = f"{_MANAGED_MARKER_START}\n*.bak\n{_MANAGED_MARKER_END}\n"
        path.write_text(existing, encoding="utf-8")
        actions, warnings = plan_managed_block(path, new_block, ".gitignore")
        assert len(actions) == 1
        assert all("conflict" not in w for w in warnings)


def _base_state(**overrides: str | bool | list[str] | None) -> StateDict:
    base: StateDict = {
        "a_state": "absent",
        "c_state": "regular",
        "agents_dir": False,
        "skills_state": "regular",
        "skills_target": None,
        "supports_symlinks": True,
        "errors": [],
        "rules_warnings": [],
    }
    for k, v in overrides.items():
        base[k] = v
    return base


class TestPlanSkillsSymlinkedDir:
    def test_existing_skill_skipped(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".claude" / "skills"
        skill_dir = skills_dir / "git-audit"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_skills(
            tmp_path,
            _base_state(
                c_state="symlink_valid",
                skills_state="symlink_valid",
                skills_target=".claude/skills",
            ),
        )
        skill_actions = [a for a in actions if "git-audit" in a.get("file", "")]
        assert all(a["action"] == "skip" for a in skill_actions)

    def test_missing_skills_created(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".claude" / "skills"
        audit_dir = skills_dir / "git-audit"
        audit_dir.mkdir(parents=True)
        (audit_dir / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_skills(
            tmp_path,
            _base_state(
                c_state="symlink_valid",
                skills_state="symlink_valid",
                skills_target=".claude/skills",
            ),
        )
        created = [
            a for a in actions if a["action"] == "create" and "SKILL.md" in a.get("file", "")
        ]
        skipped = [
            a for a in actions if a["action"] == "skip" and "git-audit" in a.get("file", "")
        ]
        assert len(created) == len(_SKILLS) - 1
        assert len(skipped) == 1

    def test_global_skill_skipped_in_symlinked_dir(self, tmp_path: Path) -> None:
        skills_dir = tmp_path / ".claude" / "skills"
        skill_dir = skills_dir / "git-audit"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_skills(
            tmp_path,
            _base_state(
                c_state="symlink_valid",
                skills_state="symlink_valid",
                skills_target=".claude/skills",
            ),
            global_skills=frozenset(["git-audit"]),
        )
        audit_actions = [a for a in actions if "git-audit" in a.get("file", "")]
        assert len(audit_actions) == 1
        assert audit_actions[0]["action"] == "skip"


class TestPlanSkillsRegularDir:
    def test_regular_dir_with_agents_dir(self, tmp_path: Path) -> None:
        agents_skills = tmp_path / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        claude_skills = tmp_path / ".claude" / "skills"
        claude_skills.mkdir(parents=True)

        actions, warnings = plan_skills(tmp_path, _base_state(agents_dir=True))
        mkdir_actions = [a for a in actions if a["action"] == "mkdir"]
        symlink_actions = [a for a in actions if a["action"] == "symlink-create"]
        assert any("git-audit" in a.get("file", "") for a in mkdir_actions)
        assert any("git-audit" in a.get("file", "") for a in symlink_actions)

    def test_global_skill_availability_warning(self, tmp_path: Path) -> None:
        actions, warnings = plan_skills(
            tmp_path,
            _base_state(),
            global_skills=frozenset(_SKILLS),
        )
        assert any("globally" in w.lower() for w in warnings)

    def test_regular_dir_no_agents_creates_skills(self, tmp_path: Path) -> None:
        claude_skills = tmp_path / ".claude" / "skills"
        claude_skills.mkdir(parents=True)

        actions, warnings = plan_skills(tmp_path, _base_state(agents_dir=False))
        created = [
            a for a in actions if a["action"] == "create" and "SKILL.md" in a.get("file", "")
        ]
        assert len(created) == len(_SKILLS)

    def test_regular_dir_no_agents_skips_existing(self, tmp_path: Path) -> None:
        claude_skills = tmp_path / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        for skill in _SKILLS:
            (claude_skills / skill).mkdir()
            (claude_skills / skill / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_skills(tmp_path, _base_state(agents_dir=False))
        assert all(a["action"] == "skip" for a in actions)

    def test_symlink_mismatch_produces_warning(self, tmp_path: Path) -> None:
        agents_skills = tmp_path / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        claude_skills = tmp_path / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        wrong_target = tmp_path / "wrong-target"
        wrong_target.mkdir()
        skill = claude_skills / "git-audit"
        os.symlink(str(wrong_target), str(skill))

        actions, warnings = plan_skills(tmp_path, _base_state(agents_dir=True))
        assert len(warnings) > 0

    def test_broken_symlink_produces_warning(self, tmp_path: Path) -> None:
        agents_skills = tmp_path / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        claude_skills = tmp_path / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        skill = claude_skills / "git-audit"
        os.symlink(str(tmp_path / "nonexistent-target"), str(skill))

        actions, warnings = plan_skills(tmp_path, _base_state(agents_dir=True))
        assert len(warnings) > 0

    def test_conflict_skip_when_agents_skill_exists(self, tmp_path: Path) -> None:
        agents_skills = tmp_path / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        claude_skills = tmp_path / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        (agents_skills / "git-audit").mkdir()
        (agents_skills / "git-audit" / "SKILL.md").write_text("content", encoding="utf-8")
        (claude_skills / "git-audit").mkdir()
        (claude_skills / "git-audit" / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_skills(tmp_path, _base_state(agents_dir=True))
        audit_actions = [a for a in actions if "git-audit" in a.get("file", "")]
        assert any(a["action"] == "skip" for a in audit_actions)

    def test_migration_action_when_no_agents_skill(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        claude_skills = home / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        agents_skills = home / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        (claude_skills / "git-audit").mkdir()
        (claude_skills / "git-audit" / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_global_skills(home)
        migrate_actions = [a for a in actions if a["action"] == "skill-migrate-to-agents"]
        assert len(migrate_actions) == 1

    def test_legacy_commands_warning(self, tmp_path: Path) -> None:
        claude_skills = tmp_path / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "git-audit.md").write_text("old", encoding="utf-8")

        actions, warnings = plan_skills(tmp_path, _base_state(agents_dir=False))
        assert len(warnings) > 0


class TestPlanGlobalSkills:
    def test_existing_skill_skipped(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        skills_dir = home / ".claude" / "skills"
        for skill in _SKILLS:
            d = skills_dir / skill
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_global_skills(home)
        assert all(a["action"] == "skip" for a in actions)

    def test_missing_skill_created(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        actions, warnings = plan_global_skills(home)
        created = [a for a in actions if a["action"] == "create"]
        assert len(created) == len(_SKILLS)

    def test_skills_not_created_if_already_exist(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        for skill in _SKILLS:
            d = home / ".claude" / "skills" / skill
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_global_skills(home)
        assert all(a["action"] == "skip" for a in actions)

    def test_global_symlinked_dir_skips_existing(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        real_skills = tmp_path / "real-skills"
        real_skills.mkdir()
        (home / ".claude").mkdir(parents=True)
        os.symlink(str(real_skills), str(home / ".claude" / "skills"))
        for skill in _SKILLS:
            d = real_skills / skill
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("content", encoding="utf-8")

        actions, warnings = plan_global_skills(home)
        assert all(a["action"] == "skip" for a in actions)
