"""Declarative repository policy loaded from ``.gitwise/policy.json``.

The policy is the single source of truth for what gitwise refuses to let into
the object database. It lives in the repository rather than in git config for
two reasons: it is reviewable in a pull request, and a user's global config
cannot silently weaken it. A policy that lives outside the repository is not a
policy.

Loading fails closed. A malformed file, an unknown key, or a value of the wrong
type raises instead of degrading to "everything allowed": a typo in the policy
must never be a silent downgrade of the protections it declares.

JSON, not TOML: ``tomllib`` is stdlib only from Python 3.11 and this package
supports 3.10, so TOML would require the ``tomli`` backport -- a new runtime
dependency, which the project's contributor rules forbid without review.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TypedDict

POLICY_RELATIVE_PATH = Path(".gitwise") / "policy.json"
POLICY_VERSION = 1


class Policy(TypedDict):
    """Effective repository policy after merging the file over the defaults."""

    version: int
    protected_branches: list[str]
    forbidden_paths: list[str]
    commit_types: list[str]
    require_gpg: bool
    block_secrets: bool
    allow_force_push: bool
    block_direct_commits: bool


class PolicyError(ValueError):
    """Raised when the policy file exists but cannot be trusted."""


DEFAULT_POLICY: Policy = {
    "version": POLICY_VERSION,
    "protected_branches": ["main", "master"],
    "forbidden_paths": [],
    "commit_types": [
        "feat",
        "fix",
        "refactor",
        "docs",
        "chore",
        "test",
        "style",
        "perf",
        "ci",
        "build",
        "revert",
    ],
    "require_gpg": False,
    "block_secrets": True,
    "allow_force_push": False,
    "block_direct_commits": False,
}

_LIST_KEYS: tuple[str, ...] = ("protected_branches", "forbidden_paths", "commit_types")
_BOOL_KEYS: tuple[str, ...] = (
    "require_gpg",
    "block_secrets",
    "allow_force_push",
    "block_direct_commits",
)


class _DuplicateKey(ValueError):
    """Internal marker for a repeated key inside the policy document."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build a dict from *pairs*, refusing repeated keys.

    ``json.loads`` keeps the last value for a repeated key, so a document that
    declares ``block_secrets`` twice silently honours the second one while a
    reviewer reads the first. For a policy that is a rejected document, not a
    quirk.
    """
    seen: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise _DuplicateKey(key)
        seen[key] = value
    return seen


def policy_path(root: Path) -> Path:
    """Return the absolute path of the policy file for *root*."""
    return root / POLICY_RELATIVE_PATH


def policy_source(root: Path) -> str:
    """Return a human/machine label for where the effective policy came from."""
    if policy_path(root).is_file():
        return POLICY_RELATIVE_PATH.as_posix()
    return "default"


def load_policy(root: Path) -> Policy:
    """Load and validate the repository policy, or return the built-in defaults.

    Raises :class:`PolicyError` when the file exists but is unparseable,
    declares an unsupported version, carries an unknown key, or holds a value of
    the wrong type.
    """
    path = policy_path(root)
    if not path.exists():
        return copy.deepcopy(DEFAULT_POLICY)
    if not path.is_file():
        # A directory (or socket, or dangling link) at the policy path is not
        # "no policy": treating it as absent would let anyone disable the
        # repository's rules by creating a directory with that name.
        raise PolicyError(f"{path}: policy path exists but is not a regular file")
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except OSError as exc:
        raise PolicyError(f"{path}: cannot read policy file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PolicyError(f"{path}: invalid JSON: {exc}") from exc
    except _DuplicateKey as exc:
        raise PolicyError(f"{path}: duplicate key {exc.key!r}") from exc

    if not isinstance(raw, dict):
        raise PolicyError(f"{path}: top-level value must be a JSON object")

    version = raw.get("version", POLICY_VERSION)
    if version != POLICY_VERSION:
        raise PolicyError(
            f"{path}: unsupported policy version {version!r}; this gitwise supports {POLICY_VERSION}"
        )

    unknown = sorted(set(raw) - set(DEFAULT_POLICY))
    if unknown:
        raise PolicyError(f"{path}: unknown key(s): {', '.join(unknown)}")

    merged: Policy = copy.deepcopy(DEFAULT_POLICY)
    for key in _LIST_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise PolicyError(f"{path}: {key} must be a list of strings")
        merged[key] = value  # type: ignore[literal-required]
    for key in _BOOL_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, bool):
            raise PolicyError(f"{path}: {key} must be a boolean")
        merged[key] = value  # type: ignore[literal-required]
    return merged
