"""Tests for the fail-closed repository policy loader."""

import json

import pytest
from gitwise.policy import DEFAULT_POLICY, PolicyError, load_policy


def _write_policy(root, payload):
    """Write *payload* as the repository policy file under *root*."""
    (root / ".gitwise").mkdir(exist_ok=True)
    (root / ".gitwise" / "policy.json").write_text(json.dumps(payload), encoding="utf-8")


def test_missing_file_returns_defaults(tmp_path):
    assert load_policy(tmp_path) == DEFAULT_POLICY


def test_defaults_are_not_shared_between_calls(tmp_path):
    first = load_policy(tmp_path)
    first["protected_branches"].append("mutated")
    assert "mutated" not in load_policy(tmp_path)["protected_branches"]


def test_partial_file_merges_over_defaults(tmp_path):
    _write_policy(tmp_path, {"version": 1, "protected_branches": ["trunk"]})
    policy = load_policy(tmp_path)
    assert policy["protected_branches"] == ["trunk"]
    assert policy["block_secrets"] is DEFAULT_POLICY["block_secrets"]


def test_unknown_key_fails_closed(tmp_path):
    _write_policy(tmp_path, {"version": 1, "blok_secrets": False})
    with pytest.raises(PolicyError, match="blok_secrets"):
        load_policy(tmp_path)


def test_malformed_json_fails_closed(tmp_path):
    (tmp_path / ".gitwise").mkdir()
    (tmp_path / ".gitwise" / "policy.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(PolicyError):
        load_policy(tmp_path)


def test_non_object_top_level_fails_closed(tmp_path):
    (tmp_path / ".gitwise").mkdir()
    (tmp_path / ".gitwise" / "policy.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(PolicyError, match="object"):
        load_policy(tmp_path)


def test_wrong_list_type_fails_closed(tmp_path):
    _write_policy(tmp_path, {"version": 1, "protected_branches": "main"})
    with pytest.raises(PolicyError, match="protected_branches"):
        load_policy(tmp_path)


def test_non_string_list_item_fails_closed(tmp_path):
    _write_policy(tmp_path, {"version": 1, "forbidden_paths": [".env", 7]})
    with pytest.raises(PolicyError, match="forbidden_paths"):
        load_policy(tmp_path)


def test_wrong_bool_type_fails_closed(tmp_path):
    _write_policy(tmp_path, {"version": 1, "block_secrets": "yes"})
    with pytest.raises(PolicyError, match="block_secrets"):
        load_policy(tmp_path)


def test_future_version_fails_closed(tmp_path):
    _write_policy(tmp_path, {"version": 99})
    with pytest.raises(PolicyError, match="version"):
        load_policy(tmp_path)


def test_policy_source_reports_file_when_present(tmp_path):
    from gitwise.policy import policy_source

    assert policy_source(tmp_path) == "default"
    _write_policy(tmp_path, {"version": 1})
    assert policy_source(tmp_path) == ".gitwise/policy.json"


def test_directory_at_the_policy_path_fails_closed(tmp_path):
    """A directory named policy.json must not read as "no policy at all"."""
    (tmp_path / ".gitwise" / "policy.json").mkdir(parents=True)
    with pytest.raises(PolicyError, match="not a regular file"):
        load_policy(tmp_path)


def test_duplicate_key_fails_closed(tmp_path):
    """json.loads keeps the last value; a reviewer reads the first."""
    (tmp_path / ".gitwise").mkdir()
    (tmp_path / ".gitwise" / "policy.json").write_text(
        '{"version": 1, "block_secrets": true, "block_secrets": false}', encoding="utf-8"
    )
    with pytest.raises(PolicyError, match="duplicate key"):
        load_policy(tmp_path)


def test_absent_policy_still_returns_defaults(tmp_path):
    """The fail-closed checks must not break the no-policy case."""
    assert load_policy(tmp_path) == DEFAULT_POLICY
