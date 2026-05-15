"""Tests for gitwise setup-agents command."""

import json
import os
import subprocess
from pathlib import Path

from conftest import run_gitwise as _run


def _run_local(*args: str, cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run setup-agents in per-repo (--local) mode.

    Sets HOME to an isolated directory so real ~/.claude/skills/ on the dev machine
    doesn't populate global_skills and cause local skill creation to be skipped.
    """
    # Isolated fake home: no real global skills can interfere
    clean_home = cwd.parent / f"_fakehome_{cwd.name}"
    base_env: dict = {"HOME": str(clean_home), "GITWISE_LANG": "es"}
    if env:
        base_env.update(
            env
        )  # caller can override HOME (e.g. test_global_skills_shadow_local_warn)
    return _run("setup-agents", "--local", *args, cwd=cwd, env=base_env)


def _run_global(
    *args: str, fake_home: Path, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    """Run setup-agents in global mode with a fake HOME directory."""
    return _run(
        "setup-agents",
        *args,
        cwd=cwd or fake_home,
        env={"HOME": str(fake_home), "GITWISE_LANG": "es"},
    )


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Mini-parser YAML del frontmatter (key: value lineales). Suficiente para tests."""
    assert text.startswith("---\n"), "missing frontmatter opening"
    end = text.index("\n---\n", 4)
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm


# ── Existing tests (renamed from setup-claude, updated to setup-agents) ──────


def test_setup_agents_fails_outside_git_repo(tmp_path):
    result = _run_local("--dry-run", cwd=tmp_path)
    assert result.returncode != 0
    assert "no es un repositorio git" in result.stderr


def test_setup_agents_dry_run_no_changes(tmp_git_repo):
    result = _run_local("--dry-run", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert not (tmp_git_repo / "CLAUDE.md").exists()
    assert not (tmp_git_repo / ".claude" / "settings.json").exists()


def test_setup_agents_json_output_v2(tmp_git_repo):
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["v"] == 2
    assert 2 in data["v_compat"]
    assert 1 in data["v_compat"]
    assert data["ok"] is True
    assert "actions" in data
    assert "root" in data
    assert "bucket" in data
    assert "errors" in data
    assert "summary" in data


def test_setup_agents_creates_files(tmp_git_repo):
    result = _run_local("--yes", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert (tmp_git_repo / "CLAUDE.md").exists()
    assert (tmp_git_repo / ".claude" / "settings.json").exists()
    assert (tmp_git_repo / ".claude" / "skills" / "git-audit" / "SKILL.md").exists()
    assert (tmp_git_repo / ".claude" / "git-snapshot.md").exists()


def test_setup_agents_settings_json_valid(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    settings_path = tmp_git_repo / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text())
    assert "permissions" in data
    deny = data["permissions"]["deny"]
    gpg_rules = [r for r in deny if "gpgsign" in r or "no-gpg-sign" in r]
    assert len(gpg_rules) >= 2, "GPG deny rules missing from settings.json"


def test_setup_agents_idempotent(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    claude_md_first = (tmp_git_repo / "CLAUDE.md").read_text()
    settings_first = (tmp_git_repo / ".claude" / "settings.json").read_text()

    _run_local("--yes", cwd=tmp_git_repo)
    claude_md_second = (tmp_git_repo / "CLAUDE.md").read_text()
    settings_second = (tmp_git_repo / ".claude" / "settings.json").read_text()

    assert claude_md_first == claude_md_second
    assert json.loads(settings_first) == json.loads(settings_second)


def test_setup_agents_does_not_modify_gpg_config(tmp_git_repo_with_gpg_config):
    repo = tmp_git_repo_with_gpg_config
    _run_local("--yes", cwd=repo)

    gpgsign = subprocess.run(
        ["git", "config", "--get", "commit.gpgsign"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    signing_key = subprocess.run(
        ["git", "config", "--get", "user.signingkey"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    assert gpgsign == "true", "setup-agents must not modify commit.gpgsign"
    assert signing_key == "TESTKEY123ABC", "setup-agents must not modify user.signingkey"


def test_setup_agents_skills_have_valid_frontmatter(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    for name in ("git-audit", "git-clean", "git-optimize"):
        skill_md = tmp_git_repo / ".claude" / "skills" / name / "SKILL.md"
        assert skill_md.exists()
        text = skill_md.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        assert fm["name"] == name
        assert len(fm.get("description", "")) > 20
        assert fm.get("disable-model-invocation") == "true"
        assert "allowed-tools" in fm
        body = text[text.index("\n---\n", 4) + 5 :]
        assert "!`gitwise" in body, f"{name}: missing bash exec marker"


def test_setup_agents_skips_existing_skill(tmp_git_repo):
    skill_dir = tmp_git_repo / ".claude" / "skills" / "git-audit"
    skill_dir.mkdir(parents=True)
    custom = "---\nname: git-audit\ndescription: custom\n---\n# custom\n"
    (skill_dir / "SKILL.md").write_text(custom)
    _run_local("--yes", cwd=tmp_git_repo)
    assert (skill_dir / "SKILL.md").read_text() == custom


def test_setup_agents_warns_on_legacy_commands(tmp_git_repo):
    legacy = tmp_git_repo / ".claude" / "commands"
    legacy.mkdir(parents=True)
    (legacy / "git-audit.md").write_text("# legacy\n")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert any("legacy" in w for w in data["warnings"])


# ── Marker regex ──────────────────────────────────────────────────────────────


def test_marker_regex_bilingual_strict():
    import re

    _MARKER_RE = re.compile(
        r"^##\s+(Convenciones git para este proyecto|Git conventions for this project)\b",
        re.MULTILINE,
    )
    assert _MARKER_RE.search("## Convenciones git para este proyecto\n")
    assert _MARKER_RE.search("## Git conventions for this project\n")
    assert _MARKER_RE.search("## Git conventions for this project — extra text\n")


def test_marker_regex_no_false_positive():
    import re

    _MARKER_RE = re.compile(
        r"^##\s+(Convenciones git para este proyecto|Git conventions for this project)\b",
        re.MULTILINE,
    )
    assert not _MARKER_RE.search("## Conventions git for testing\n")
    assert not _MARKER_RE.search("## Git conventions\n")
    assert not _MARKER_RE.search("# Convenciones git para este proyecto\n")  # single #


# ── Bucket 1 (no AGENTS.md) — zero-regression JSON schema v2 ─────────────────


def test_bucket1_json_schema_v2_shape(tmp_git_repo):
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["bucket"] == 1
    assert data["agents_md_detected"] is False
    assert data["agents_dir_detected"] is False
    assert data["ok"] is True
    assert data["errors"] == []
    assert "summary" in data
    assert set(data["summary"].keys()) == {
        "created",
        "appended",
        "symlinked",
        "skipped",
        "errored",
    }


# ── Bucket 2 — AGENTS.md exists, CLAUDE.md absent ────────────────────────────


def test_bucket2_agents_md_creates_symlink_pointer(tmp_git_repo):
    (tmp_git_repo / "AGENTS.md").write_text("# project agents\n")

    result = _run_local("--yes", cwd=tmp_git_repo)
    assert result.returncode == 0

    claude_md = tmp_git_repo / "CLAUDE.md"
    assert claude_md.is_symlink(), "CLAUDE.md debe ser symlink en POSIX"
    assert os.readlink(claude_md) == "AGENTS.md"

    agents_text = (tmp_git_repo / "AGENTS.md").read_text()
    assert "Convenciones git" in agents_text or "Git conventions" in agents_text


def test_bucket2_json_reports_correct_bucket(tmp_git_repo):
    (tmp_git_repo / "AGENTS.md").write_text("# project agents\n")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert data["bucket"] == 2
    assert data["agents_md_detected"] is True
    assert data["ok"] is True


def test_bucket2_no_symlinks_flag_uses_at_import(tmp_git_repo):
    (tmp_git_repo / "AGENTS.md").write_text("# project agents\n")
    result = _run_local("--yes", "--no-symlinks", cwd=tmp_git_repo)
    assert result.returncode == 0

    claude_md = tmp_git_repo / "CLAUDE.md"
    assert claude_md.exists()
    assert not claude_md.is_symlink(), "CLAUDE.md no debe ser symlink con --no-symlinks"
    content = claude_md.read_text()
    assert "@AGENTS.md" in content


# ── Bucket 3 — CLAUDE.md ya es symlink válido → idempotente ──────────────────


def test_bucket3_idempotent_with_existing_symlink(tmp_git_repo):
    agents_md = tmp_git_repo / "AGENTS.md"
    agents_md.write_text("# project agents\n## Git conventions for this project\nfoo\n")
    claude_md = tmp_git_repo / "CLAUDE.md"
    os.symlink("AGENTS.md", claude_md)

    result = _run_local("--yes", cwd=tmp_git_repo)
    assert result.returncode == 0
    # AGENTS.md content unchanged (has marker already, no append)
    assert agents_md.read_text() == "# project agents\n## Git conventions for this project\nfoo\n"
    # CLAUDE.md still symlink pointing to AGENTS.md
    assert claude_md.is_symlink()
    assert os.readlink(claude_md) == "AGENTS.md"


def test_bucket3_idempotent_second_run_no_changes(tmp_git_repo):
    (tmp_git_repo / "AGENTS.md").write_text("# project agents\n")
    _run_local("--yes", cwd=tmp_git_repo)
    agents_after_first = (tmp_git_repo / "AGENTS.md").read_text()

    _run_local("--yes", cwd=tmp_git_repo)
    agents_after_second = (tmp_git_repo / "AGENTS.md").read_text()

    assert agents_after_first == agents_after_second


# ── Bucket 4 — CLAUDE.md y AGENTS.md son archivos distintos ──────────────────


def test_bucket4_warns_no_overwrite_distinct_files(tmp_git_repo):
    (tmp_git_repo / "CLAUDE.md").write_text("# claude one\n")
    (tmp_git_repo / "AGENTS.md").write_text("# agents two\n")

    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["bucket"] == 4
    assert any(
        "contenido distinto" in w or "replace-claude-with-symlink" in w for w in data["warnings"]
    )

    # Files must be untouched
    assert (tmp_git_repo / "CLAUDE.md").read_text() == "# claude one\n"


def test_bucket4_replace_flag_creates_backup_and_symlink(tmp_git_repo):
    (tmp_git_repo / "CLAUDE.md").write_text("# claude content\n")
    (tmp_git_repo / "AGENTS.md").write_text("# agents content\n")

    result = _run_local("--yes", "--replace-claude-with-symlink", cwd=tmp_git_repo)
    assert result.returncode == 0

    claude_md = tmp_git_repo / "CLAUDE.md"
    assert claude_md.is_symlink()
    assert os.readlink(claude_md) == "AGENTS.md"

    # Backup must exist
    baks = list(tmp_git_repo.glob("CLAUDE.md.bak*"))
    assert len(baks) >= 1
    assert baks[0].read_text() == "# claude content\n"


# ── Bucket 5 — estado inválido, aborta limpio ─────────────────────────────────


def test_bucket5_broken_symlink_aborts_with_errors(tmp_git_repo):
    claude_md = tmp_git_repo / "CLAUDE.md"
    os.symlink("nonexistent.md", claude_md)

    result = _run_local("--json", cwd=tmp_git_repo)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["bucket"] == 5
    assert len(data["errors"]) >= 1
    # Nothing should have been written
    assert not (tmp_git_repo / ".claude" / "settings.json").exists()


def test_bucket5_broken_skills_symlink_aborts(tmp_git_repo):
    claude_dir = tmp_git_repo / ".claude"
    claude_dir.mkdir()
    skills_link = claude_dir / "skills"
    os.symlink("/nonexistent/skills", skills_link)

    result = _run_local("--json", cwd=tmp_git_repo)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert len(data["errors"]) >= 1


# ── Skills symlink granular con .agents/ ──────────────────────────────────────


def test_skills_symlink_created_when_agents_dir_exists(tmp_git_repo):
    (tmp_git_repo / ".agents").mkdir()

    result = _run_local("--yes", cwd=tmp_git_repo)
    assert result.returncode == 0

    # .claude/skills/ is a regular dir; each skill is a per-skill symlink
    skills_dir = tmp_git_repo / ".claude" / "skills"
    assert skills_dir.is_dir() and not skills_dir.is_symlink()
    for skill in ("git-audit", "git-clean", "git-optimize"):
        skill_link = skills_dir / skill
        assert skill_link.is_symlink(), f".claude/skills/{skill} debe ser symlink"
        target = os.readlink(skill_link)
        assert ".agents" in target
    # SKILL.md se crea en .agents/skills/ (write_text sigue el symlink)
    assert (tmp_git_repo / ".agents" / "skills" / "git-audit" / "SKILL.md").exists()


def test_skills_symlink_idempotent_on_second_run(tmp_git_repo):
    (tmp_git_repo / ".agents").mkdir()
    _run_local("--yes", cwd=tmp_git_repo)
    targets_first = {
        skill: os.readlink(tmp_git_repo / ".claude" / "skills" / skill)
        for skill in ("git-audit", "git-clean", "git-optimize")
    }

    _run_local("--yes", cwd=tmp_git_repo)
    targets_second = {
        skill: os.readlink(tmp_git_repo / ".claude" / "skills" / skill)
        for skill in ("git-audit", "git-clean", "git-optimize")
    }

    assert targets_first == targets_second


def test_skills_no_symlink_without_agents_dir(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    skills_path = tmp_git_repo / ".claude" / "skills"
    assert skills_path.is_dir()
    assert not skills_path.is_symlink()


# ── .gitignore managed block ──────────────────────────────────────────────────


def test_gitignore_creates_block_when_absent(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    gi = tmp_git_repo / ".gitignore"
    assert gi.exists()
    content = gi.read_text()
    assert "# >>> gitwise managed" in content
    assert "# <<< gitwise managed" in content
    assert ".claude/settings.local.json" in content
    assert ".claude/git-snapshot.md" in content


def test_gitignore_appends_block_to_existing(tmp_git_repo):
    (tmp_git_repo / ".gitignore").write_text("node_modules/\n*.log\n")
    _run_local("--yes", cwd=tmp_git_repo)
    content = (tmp_git_repo / ".gitignore").read_text()
    assert "node_modules/" in content
    assert "*.log" in content
    assert "# >>> gitwise managed" in content


def test_gitignore_preserves_user_lines_outside_block(tmp_git_repo):
    (tmp_git_repo / ".gitignore").write_text("my_secret.env\n")
    _run_local("--yes", cwd=tmp_git_repo)
    content = (tmp_git_repo / ".gitignore").read_text()
    assert "my_secret.env" in content


def test_gitignore_replaces_block_idempotent(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    content_first = (tmp_git_repo / ".gitignore").read_text()

    _run_local("--yes", cwd=tmp_git_repo)
    content_second = (tmp_git_repo / ".gitignore").read_text()

    assert content_first == content_second


def test_gitignore_bucket2_includes_agents_bak(tmp_git_repo):
    (tmp_git_repo / "AGENTS.md").write_text("# agents\n")
    _run_local("--yes", cwd=tmp_git_repo)
    content = (tmp_git_repo / ".gitignore").read_text()
    assert "AGENTS.md.bak*" in content


def test_gitignore_skipped_in_bucket5(tmp_git_repo):
    claude_md = tmp_git_repo / "CLAUDE.md"
    os.symlink("nonexistent.md", claude_md)
    _run_local("--yes", cwd=tmp_git_repo)
    # .gitignore must NOT have been created
    assert not (tmp_git_repo / ".gitignore").exists()


# ── .gitattributes managed block ─────────────────────────────────────────────


def test_gitattributes_managed_block(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    ga = tmp_git_repo / ".gitattributes"
    assert ga.exists()
    content = ga.read_text()
    assert "# >>> gitwise managed" in content
    assert "merge=ours" in content
    assert "eol=lf" in content


def test_gitattributes_agents_extended_when_agents_md(tmp_git_repo):
    (tmp_git_repo / "AGENTS.md").write_text("# agents\n")
    _run_local("--yes", cwd=tmp_git_repo)
    content = (tmp_git_repo / ".gitattributes").read_text()
    assert "AGENTS.md text=auto eol=lf" in content


# ── --strict flag ─────────────────────────────────────────────────────────────


def test_strict_flag_exits_2_on_warnings(tmp_git_repo):
    (tmp_git_repo / "CLAUDE.md").write_text("# claude\n")
    (tmp_git_repo / "AGENTS.md").write_text("# agents\n")
    result = _run_local("--strict", "--yes", cwd=tmp_git_repo)
    assert result.returncode == 2


# ── --no-git-files opt-out ────────────────────────────────────────────────────


def test_no_git_files_skips_gitignore(tmp_git_repo):
    _run_local("--yes", "--no-git-files", cwd=tmp_git_repo)
    assert not (tmp_git_repo / ".gitignore").exists()
    assert not (tmp_git_repo / ".gitattributes").exists()


# ── .gitattributes conflict detection ────────────────────────────────────────


def test_gitattributes_no_conflict_fresh_repo(tmp_git_repo):
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert not any(".gitattributes" in w and "conflict" in w for w in data["warnings"])


def test_gitattributes_warns_on_conflicting_rule(tmp_git_repo):
    # User has CLAUDE.md with eol=crlf; gitwise wants eol=lf
    (tmp_git_repo / ".gitattributes").write_text("CLAUDE.md text=auto eol=crlf\n")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert any(
        "CLAUDE.md" in w and ("conflict" in w or "conflicto" in w) for w in data["warnings"]
    )


def test_gitattributes_no_warning_when_same_rule(tmp_git_repo):
    # User already has the exact same rule gitwise would write
    (tmp_git_repo / ".gitattributes").write_text("CLAUDE.md text=auto eol=lf\n")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert not any("CLAUDE.md" in w and "conflict" in w for w in data["warnings"])


def test_gitattributes_no_false_positive_on_second_run(tmp_git_repo):
    # After setup, second run must not generate false conflict warnings
    _run_local("--yes", cwd=tmp_git_repo)
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert not any("conflict" in w for w in data["warnings"])


def test_gitattributes_no_warning_for_bare_path_entry(tmp_git_repo):
    # A bare path without attributes in user's file should not trigger a warning
    (tmp_git_repo / ".gitattributes").write_text("CLAUDE.md\n")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert not any("CLAUDE.md" in w and "conflict" in w for w in data["warnings"])


# ── gitwise rule file ────────────────────────────────────────────────────────


def test_gitwise_rule_created(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    rule = tmp_git_repo / ".claude" / "rules" / "gitwise.md"
    assert rule.exists()
    content = rule.read_text()
    assert "globs:" in content
    assert "gitwise diff" in content
    assert "gitwise summarize" in content


def test_gitwise_rule_skipped_if_exists(tmp_git_repo):
    rule = tmp_git_repo / ".claude" / "rules" / "gitwise.md"
    rule.parent.mkdir(parents=True)
    rule.write_text("# custom\n")
    _run_local("--yes", cwd=tmp_git_repo)
    assert rule.read_text() == "# custom\n"


def test_gitwise_rule_no_warning_from_detector(tmp_git_repo):
    _run_local("--yes", cwd=tmp_git_repo)
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert not any("gitwise.md" in w for w in data["rules_warnings"])


# ── Rules detection (.claude/rules/*.md) ─────────────────────────────────────


def test_rules_no_dir_no_warnings(tmp_git_repo):
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert data["rules_warnings"] == []


def test_rules_valid_globs_no_warning(tmp_git_repo):
    rules_dir = tmp_git_repo / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "my-rule.md").write_text(
        "---\nname: my-rule\nglobs: src/**/*.py\n---\n# My rule\n"
    )
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert data["rules_warnings"] == []


def test_rules_broken_no_globs_warns(tmp_git_repo):
    rules_dir = tmp_git_repo / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad-rule.md").write_text("# No frontmatter at all\n")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert any("bad-rule.md" in w and "globs" in w for w in data["rules_warnings"])


def test_rules_symlink_escape_ignored(tmp_git_repo):
    rules_dir = tmp_git_repo / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    outside = tmp_git_repo.parent / "outside_rule.md"
    outside.write_text("# outside\n")
    os.symlink(str(outside), rules_dir / "escape.md")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert any("escape.md" in w and "symlink" in w for w in data["rules_warnings"])


def test_rules_warnings_subset_of_warnings(tmp_git_repo):
    rules_dir = tmp_git_repo / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "missing-globs.md").write_text("---\nname: test\n---\n# no globs\n")
    result = _run_local("--json", "--dry-run", cwd=tmp_git_repo)
    data = json.loads(result.stdout)
    assert len(data["rules_warnings"]) > 0
    assert all(w in data["warnings"] for w in data["rules_warnings"])


# ── Global mode (default, no --local) ────────────────────────────────────────


def test_global_mode_installs_to_claude_dir(tmp_path):
    """Global mode installs skills/rules/settings to fake ~/.claude/ without a git repo."""
    result = _run_global("--yes", fake_home=tmp_path)
    assert result.returncode == 0
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "rules" / "gitwise.md").exists()
    for skill in ("git-audit", "git-clean", "git-optimize"):
        assert (tmp_path / ".claude" / "skills" / skill / "SKILL.md").exists()


def test_global_mode_works_outside_git_repo(tmp_path):
    """Global mode does not require a git repo."""
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir()
    result = _run_global("--yes", fake_home=tmp_path, cwd=non_git)
    assert result.returncode == 0
    assert (tmp_path / ".claude" / "settings.json").exists()


def test_global_mode_json_output(tmp_path):
    result = _run_global("--json", "--dry-run", fake_home=tmp_path)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["v"] == 2
    assert data["mode"] == "global"
    assert data["ok"] is True
    assert "actions" in data
    assert "summary" in data


def test_global_mode_idempotent(tmp_path):
    _run_global("--yes", fake_home=tmp_path)
    settings_first = json.loads((tmp_path / ".claude" / "settings.json").read_text())

    _run_global("--yes", fake_home=tmp_path)
    settings_second = json.loads((tmp_path / ".claude" / "settings.json").read_text())

    assert settings_first == settings_second


def test_global_no_skills_flag(tmp_path):
    result = _run_global("--yes", "--no-skills", fake_home=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / ".claude" / "skills").exists()
    # settings and rules should still be created
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "rules" / "gitwise.md").exists()


def test_global_skills_shadow_local_warn(tmp_path):
    """When skills exist globally, local setup warns about user > project priority."""
    import subprocess as sp

    fake_home = tmp_path / "home"
    repo = tmp_path / "repo"
    fake_home.mkdir()
    repo.mkdir()
    # Minimal git repo
    sp.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    sp.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t.com"],
        check=True,
        capture_output=True,
    )
    sp.run(["git", "-C", str(repo), "config", "user.name", "T"], check=True, capture_output=True)
    (repo / "README.md").write_text("# test\n")
    sp.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    sp.run(
        ["git", "-C", str(repo), "commit", "--no-gpg-sign", "-m", "init"],
        check=True,
        capture_output=True,
    )

    # Install globally to fake_home
    _run_global("--yes", fake_home=fake_home)

    # Local setup should warn that skills are shadowed by global
    result = _run_local("--json", "--dry-run", cwd=repo, env={"HOME": str(fake_home)})
    data = json.loads(result.stdout)
    shadow_warnings = [w for w in data["warnings"] if "globalmente" in w]
    assert len(shadow_warnings) >= 1


def test_local_flag_requires_git_repo(tmp_path):
    """--local fails outside a git repo."""
    result = _run_local("--dry-run", cwd=tmp_path)
    assert result.returncode != 0
    assert "no es un repositorio git" in result.stderr


def test_global_agents_dir_creates_skill_symlinks(tmp_path):
    """When ~/.agents/ exists, global mode creates per-skill symlinks to ~/.agents/skills/."""
    fake_home = tmp_path
    (fake_home / ".agents").mkdir()

    result = _run_global("--yes", fake_home=fake_home)
    assert result.returncode == 0

    for skill in ("git-audit", "git-clean", "git-optimize"):
        skill_link = fake_home / ".claude" / "skills" / skill
        assert skill_link.is_symlink(), f"~/.claude/skills/{skill} debe ser symlink"
        target = os.readlink(skill_link)
        assert ".agents" in target
    assert (fake_home / ".agents" / "skills" / "git-audit" / "SKILL.md").exists()


def test_global_agents_dir_migrates_existing_regular_skill(tmp_path):
    """When ~/.agents/ exists and skill is a regular dir, it is moved to .agents/skills/ + symlinked."""
    fake_home = tmp_path
    (fake_home / ".agents").mkdir()
    # Pre-create skill as regular dir (simulates old global install without .agents/)
    skill_dir = fake_home / ".claude" / "skills" / "git-audit"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: git-audit\n---\n# old\n")

    result = _run_global("--yes", fake_home=fake_home)
    assert result.returncode == 0

    # git-audit must now be a symlink (migrated)
    assert skill_dir.is_symlink(), "git-audit debe ser symlink tras migración"
    target = os.readlink(skill_dir)
    assert ".agents" in target
    # Original content must be in .agents/skills/git-audit/
    assert (fake_home / ".agents" / "skills" / "git-audit" / "SKILL.md").exists()
    assert "old" in (fake_home / ".agents" / "skills" / "git-audit" / "SKILL.md").read_text()


def test_global_agents_dir_symlinks_idempotent(tmp_path):
    """Second global run with ~/.agents/ does not change symlinks."""
    fake_home = tmp_path
    (fake_home / ".agents").mkdir()

    _run_global("--yes", fake_home=fake_home)
    targets_first = {
        skill: os.readlink(fake_home / ".claude" / "skills" / skill)
        for skill in ("git-audit", "git-clean", "git-optimize")
    }

    _run_global("--yes", fake_home=fake_home)
    targets_second = {
        skill: os.readlink(fake_home / ".claude" / "skills" / skill)
        for skill in ("git-audit", "git-clean", "git-optimize")
    }

    assert targets_first == targets_second
