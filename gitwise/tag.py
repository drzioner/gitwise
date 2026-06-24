"""gitwise tag — semver-aware tag management (list/create/delete)."""

import re
from pathlib import Path

from gitwise.git import require_root, validate_ref
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import (
    confirm,
    error,
    ok,
    print_bracket,
    print_header,
    print_json,
    print_table,
    status,
    warn,
)
from gitwise.utils.json_envelope import error_envelope, ok_envelope

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$")


def _list_tags(root: Path) -> list[dict[str, str]]:
    """Return all tags as ``[{name, sha, date}]``."""
    with status(t("status_reading_tags")):
        r = git_run(
            [
                "for-each-ref",
                "--format=%(refname:short)\t%(objectname:short)\t%(creatordate:iso-strict)",
                "refs/tags/",
            ],
            cwd=root,
            check=False,
        )
    if r.returncode != 0 or not r.stdout.strip():
        return []
    tags: list[dict[str, str]] = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        tags.append({"name": parts[0], "sha": parts[1], "date": parts[2]})
    return tags


def _latest_semver(root: Path) -> dict[str, str] | None:
    """Return the highest semver tag dict, or None if no semver tags exist."""
    tags = _list_tags(root)
    semver_tags = [tg for tg in tags if _SEMVER_RE.match(tg["name"])]
    if not semver_tags:
        return None

    def _sort_key(tg: dict[str, str]) -> tuple[int, ...]:
        """Extract numeric semver tuple for sorting."""
        m = _SEMVER_RE.match(tg["name"])
        if not m:
            return (0, 0, 0)
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    semver_tags.sort(key=_sort_key, reverse=True)
    return semver_tags[0]


def _bump_version(version: str, part: str) -> str:
    """Increment *part* (major/minor/patch) of a semver *version* string."""
    m = _SEMVER_RE.match(version)
    if not m:
        return version
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre = m.group(4) or ""
    build = m.group(5) or ""
    prefix = "v" if version.startswith("v") else ""
    if part == "major":
        major += 1
        minor = patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{prefix}{major}.{minor}.{patch}{pre}{build}"


def _print_tag_list(tags: list[dict[str, str]]) -> None:
    """Render a table of tags, highlighting semver rows."""
    if not tags:
        ok(t("tag_empty"))
        return
    columns = [
        (t("col_tag"), "name"),
        (t("col_sha"), "sha"),
        (t("col_date"), "date"),
    ]
    rows: list[list[str]] = []
    highlight_rows: set[int] = set()
    for i, tag_item in enumerate(tags):
        rows.append([tag_item["name"], tag_item["sha"], tag_item["date"]])
        if _SEMVER_RE.match(tag_item["name"]):
            highlight_rows.add(i)
    print_table(
        title=t("tag_list_title"),
        columns=columns,
        rows=rows,
        highlight_rows=highlight_rows,
    )


def _resolve_tag_name(
    *,
    root: Path,
    bump: str | None,
    name: str | None,
) -> str | None:
    """Resolve the tag name from explicit *name* or by bumping the latest semver."""
    if bump:
        latest = _latest_semver(root)
        base = latest["name"] if latest else "0.0.0"
        return _bump_version(base, bump)
    return name


def _run_tag_list(*, root: Path, as_json: bool) -> int:
    """Execute ``tag list`` sub-action."""
    tags = _list_tags(root)
    if as_json:
        print_json(ok_envelope("tag", tags=tags, count=len(tags)))
        return 0
    _print_tag_list(tags)
    return 0


def _run_tag_latest(*, root: Path, as_json: bool) -> int:
    """Execute ``tag latest`` sub-action."""
    latest = _latest_semver(root)
    if as_json:
        print_json(ok_envelope("tag", latest=latest))
        return 0
    if latest:
        print_header(t("tag_latest_title"))
        print_bracket(latest["name"], latest["sha"])
    else:
        warn(t("tag_no_semver"))
    return 0


def _run_tag_create(
    *,
    root: Path,
    bump: str | None,
    name: str | None,
    message: str | None,
    dry_run: bool,
    as_json: bool,
) -> int:
    """Execute ``tag create`` sub-action."""
    tag_name = _resolve_tag_name(root=root, bump=bump, name=name)
    if not tag_name:
        if as_json:
            print_json(
                error_envelope("tag", error=t("tag_name_required"), code="tag_name_required")
            )
        else:
            error(t("tag_name_required"))
        return 1
    if not validate_ref(tag_name):
        if as_json:
            print_json(
                error_envelope("tag", error=t("invalid_ref", ref=tag_name), code="invalid_ref")
            )
        else:
            error(t("invalid_ref", ref=tag_name))
        return 1

    args = ["tag", tag_name]
    if message:
        args = ["tag", "-a", tag_name, "-m", message]

    if dry_run:
        if as_json:
            print_json(ok_envelope("tag", created=tag_name, dry_run=True))
        else:
            ok(t("tag_create_dry", name=tag_name))
        return 0

    result = git_run(args, cwd=root, check=False)
    if result.returncode != 0:
        err = t("git_command_failed", cmd="tag", error=result.stderr.strip())
        if as_json:
            print_json(error_envelope("tag", error=err, code="tag_create_failed"))
        else:
            error(err)
        return 1

    if as_json:
        print_json(ok_envelope("tag", created=tag_name))
        return 0
    ok(t("tag_created", name=tag_name))
    return 0


def _run_tag_delete(
    *,
    root: Path,
    name: str | None,
    yes: bool,
    dry_run: bool,
    as_json: bool,
) -> int:
    """Execute ``tag delete`` sub-action with optional confirmation."""
    if not name:
        if as_json:
            print_json(
                error_envelope("tag", error=t("tag_name_required"), code="tag_name_required")
            )
        else:
            error(t("tag_name_required"))
        return 1
    if not validate_ref(name):
        if as_json:
            print_json(error_envelope("tag", error=t("invalid_ref", ref=name), code="invalid_ref"))
        else:
            error(t("invalid_ref", ref=name))
        return 1
    if dry_run:
        if as_json:
            print_json(ok_envelope("tag", deleted=name, dry_run=True))
        else:
            ok(t("tag_delete_dry", name=name))
        return 0
    if not yes and not confirm(t("confirm_tag_delete", name=name)):
        if as_json:
            print_json(error_envelope("tag", error=t("aborted"), code="aborted"))
        else:
            warn(t("aborted"))
        return 1

    result = git_run(["tag", "-d", name], cwd=root, check=False)
    if result.returncode != 0:
        err = t("git_command_failed", cmd="tag -d", error=result.stderr.strip())
        if as_json:
            print_json(error_envelope("tag", error=err, code="tag_delete_failed"))
        else:
            error(err)
        return 1

    if as_json:
        print_json(ok_envelope("tag", deleted=name))
        return 0
    ok(t("tag_deleted", name=name))
    return 0


def run_tag(
    action: str = "list",
    name: str | None = None,
    *,
    bump: str | None = None,
    message: str | None = None,
    dry_run: bool = False,
    yes: bool = False,
    as_json: bool = False,
) -> int:
    """Entry point for the ``gitwise tag`` command."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    if action == "list":
        return _run_tag_list(root=root, as_json=as_json)

    if action == "latest":
        return _run_tag_latest(root=root, as_json=as_json)

    if action == "create":
        return _run_tag_create(
            root=root,
            bump=bump,
            name=name,
            message=message,
            dry_run=dry_run,
            as_json=as_json,
        )

    if action == "delete":
        return _run_tag_delete(root=root, name=name, yes=yes, dry_run=dry_run, as_json=as_json)

    error(t("tag_unknown_action", action=action))
    return 1
