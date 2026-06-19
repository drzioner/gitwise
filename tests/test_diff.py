"""Tests for gitwise diff command."""

import json
from pathlib import Path

from conftest import _git, _init_repo
from conftest import run_gitwise as _run


def _write_and_stage(repo: Path, filename: str, content: str = "change\n") -> None:
    (repo / filename).write_text(content)
    _git(["add", filename], repo)


# ── Empty repo (no commits) ──────────────────────────────────────────────────


def test_diff_no_commits(tmp_path):
    _init_repo(tmp_path)
    result = _run("diff", cwd=tmp_path)
    assert result.returncode == 0
    assert "no commits yet" in result.stdout


def test_diff_no_commits_json(tmp_path):
    _init_repo(tmp_path)
    result = _run("diff", "--json", cwd=tmp_path)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["files"] == []
    assert data["count"] == 0
    assert "note" in data


# ── Clean repo ───────────────────────────────────────────────────────────────


def test_diff_no_changes(tmp_git_repo):
    result = _run("diff", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "no uncommitted changes" in result.stdout


def test_diff_no_changes_json(tmp_git_repo):
    result = _run("diff", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["files"] == []
    assert data["count"] == 0


# ── Unstaged changes ─────────────────────────────────────────────────────────


def test_diff_unstaged_shows_file(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("modified\n")
    result = _run("diff", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout


def test_diff_unstaged_json(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("modified\n")
    result = _run("diff", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] >= 1
    assert any("README.md" in f.get("path", "") for f in data["files"])


# ── Staged changes ───────────────────────────────────────────────────────────


def test_diff_staged_shows_file(tmp_git_repo):
    _write_and_stage(tmp_git_repo, "newfile.txt")
    result = _run("diff", "--staged", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "changed files:" in result.stdout
    assert "newfile.txt" in result.stdout


def test_diff_staged_empty(tmp_git_repo):
    result = _run("diff", "--staged", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "nothing staged" in result.stdout


def test_diff_staged_json(tmp_git_repo):
    _write_and_stage(tmp_git_repo, "newfile.txt")
    result = _run("diff", "--staged", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] == 1
    assert any(f["path"] == "newfile.txt" for f in data["files"])


# ── --stat mode ──────────────────────────────────────────────────────────────


def test_diff_stat_shows_changes_column(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("line1\nline2\nline3\n")
    result = _run("diff", "--stat", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "changed files:" in result.stdout
    assert "README.md" in result.stdout


def test_diff_stat_json(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("line1\nline2\n")
    result = _run("diff", "--stat", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] >= 1
    assert all("path" in f and "changes" in f for f in data["files"])
    assert "totals" in data
    assert "insertions" in data["totals"]
    assert "deletions" in data["totals"]
    assert "lines_changed" in data["totals"]


def test_diff_stat_json_includes_structured_fields(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("line1\nline2\nline3\n")
    result = _run("diff", "--stat", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    readme_entry = next((f for f in data["files"] if f.get("path") == "README.md"), None)
    assert readme_entry is not None
    assert readme_entry["status"] == "M"
    assert "lines_changed" in readme_entry
    assert "insertions" in readme_entry
    assert "deletions" in readme_entry
    assert isinstance(readme_entry.get("graph", ""), str)


# ── Mutual exclusion ─────────────────────────────────────────────────────────


def test_diff_name_only_exclusive(tmp_git_repo):
    result = _run("diff", "--name-only", cwd=tmp_git_repo)
    assert result.returncode == 0


def test_diff_full(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("changed content\n")
    _git(["add", "."], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: modify readme"], tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("more changes\n")
    result = _run("diff", "--full", cwd=tmp_git_repo)
    assert result.returncode == 0


def test_diff_full_json(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("changed content\n")
    _git(["add", "."], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: modify readme"], tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("more changes\n")
    result = _run("diff", "--full", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert '"diff"' in result.stdout


def test_diff_patch_alias(tmp_git_repo):
    (tmp_git_repo / "README.md").write_text("changed content\n")
    _git(["add", "."], tmp_git_repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: modify readme"], tmp_git_repo)
    (tmp_git_repo / "README.md").write_text("more changes\n")
    result = _run("diff", "--patch", cwd=tmp_git_repo)
    assert result.returncode == 0


# ── D1: refspecs (commit, branch, two-dot range, three-dot range) ────────────


def _repo_with_history(repo: Path) -> str:
    """Create a second commit and return the first commit hash for range tests."""
    first = _git(["rev-parse", "HEAD"], repo).stdout.decode().strip()
    (repo / "README.md").write_text("v2 content\n")
    _git(["add", "."], repo)
    _git(["commit", "--no-gpg-sign", "-m", "chore: second commit"], repo)
    return first


def test_diff_ref_single_commit(tmp_git_repo):
    """diff against an ancestor commit shows files changed since then."""
    first = _repo_with_history(tmp_git_repo)
    result = _run("diff", first, cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout


def test_diff_ref_single_commit_json(tmp_git_repo):
    """diff <refspec> --json returns structured file entries."""
    first = _repo_with_history(tmp_git_repo)
    result = _run("diff", first, "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] >= 1
    assert any("README.md" in f.get("path", "") for f in data["files"])


def test_diff_two_dot_range(tmp_git_repo):
    """two-dot range (a..b) compares the two endpoints directly."""
    first = _repo_with_history(tmp_git_repo)
    refspec = f"{first}..HEAD"
    result = _run("diff", refspec, cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout


def test_diff_three_dot_range(tmp_git_repo):
    """three-dot range (a...b) diffs from the merge base to the second ref."""
    first = _repo_with_history(tmp_git_repo)
    refspec = f"{first}...HEAD"
    result = _run("diff", refspec, cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout


def test_diff_invalid_refspec_fails(tmp_git_repo):
    """an unresolvable refspec exits non-zero via git's own error."""
    result = _run("diff", "nonexistent-ref-xyz", cwd=tmp_git_repo)
    assert result.returncode == 1


# ── D2: path scope (-- separator) ────────────────────────────────────────────


def test_diff_path_scope(tmp_git_repo):
    """`-- <path>` limits output to that path, excluding other changed files."""
    (tmp_git_repo / "README.md").write_text("changed\n")
    (tmp_git_repo / "other.txt").write_text("changed\n")
    result = _run("diff", "--", "README.md", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout
    assert "other.txt" not in result.stdout


def test_diff_refspec_with_paths(tmp_git_repo):
    """refspec and path scope compose: `diff <ref> -- <path>`."""
    first = _repo_with_history(tmp_git_repo)
    (tmp_git_repo / "extra.txt").write_text("extra change\n")
    result = _run("diff", first, "--", "README.md", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout
    assert "extra.txt" not in result.stdout


def test_diff_path_only_separator_disambiguates_from_ref(tmp_git_repo):
    """`-- <name>` treats <name> as a path even when a same-named branch exists.

    Without honoring `--` as a pathspec separator, argparse mis-assigns the
    name to refspec and git diffs against the branch instead of the file.
    """
    (tmp_git_repo / "conflict").write_text("file content\n")
    _git(["add", "conflict"], tmp_git_repo)
    (tmp_git_repo / "other.txt").write_text("other\n")
    _git(["add", "other.txt"], tmp_git_repo)
    _git(["branch", "conflict"], tmp_git_repo)
    result = _run("diff", "--staged", "--", "conflict", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "conflict" in result.stdout
    assert "other.txt" not in result.stdout


def test_diff_too_many_refs_before_separator_fails(tmp_git_repo):
    """two positionals before `--` fails fast (gitwise takes one refspec)."""
    first = _repo_with_history(tmp_git_repo)
    result = _run("diff", first, "HEAD", "--", "README.md", cwd=tmp_git_repo)
    assert result.returncode == 1


# ── D5: --summary ────────────────────────────────────────────────────────────


def test_diff_summary(tmp_git_repo):
    """--summary prints additions/deletions per file without the full patch."""
    (tmp_git_repo / "README.md").write_text("line1\nline2\nline3\n")
    result = _run("diff", "--summary", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout


def test_diff_summary_json(tmp_git_repo):
    """--summary --json returns per-file insertions/deletions and totals."""
    (tmp_git_repo / "README.md").write_text("line1\nline2\nline3\n")
    result = _run("diff", "--summary", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["count"] >= 1
    assert all("path" in f and "insertions" in f and "deletions" in f for f in data["files"])
    assert "totals" in data


def test_diff_summary_with_refspec(tmp_git_repo):
    """--summary composes with a refspec."""
    first = _repo_with_history(tmp_git_repo)
    result = _run("diff", "--summary", first, cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "README.md" in result.stdout


# ── D4: large binary warning ─────────────────────────────────────────────────


def _stage_large_binary(repo: Path) -> None:
    """Stage a ~2 MiB binary file (null bytes so git marks it binary)."""
    (repo / "blob.bin").write_bytes(b"\x00\x01\x02\x03" * 500_000)
    _git(["add", "blob.bin"], repo)


def test_diff_binary_lfs_warning(tmp_git_repo):
    """a staged binary >= 1 MiB surfaces a Git LFS hint on stderr."""
    _stage_large_binary(tmp_git_repo)
    result = _run("diff", "--stat", "--staged", cwd=tmp_git_repo)
    assert result.returncode == 0
    assert "Git LFS" in result.stderr
    assert "blob.bin" in result.stderr


def test_diff_binary_lfs_warning_json(tmp_git_repo):
    """JSON mode carries binary_warnings so agents get the same LFS signal."""
    _stage_large_binary(tmp_git_repo)
    result = _run("diff", "--stat", "--staged", "--json", cwd=tmp_git_repo)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "binary_warnings" in data
    assert len(data["binary_warnings"]) >= 1
