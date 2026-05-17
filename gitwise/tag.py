"""gitwise tag — semver-aware tag management (list/create/delete)."""

import re
import sys
from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import confirm, ok, print_json, warn

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$")


def _list_tags(root: Path) -> list[dict[str, str]]:
    r = git_run(
        [
            "for-each-ref",
            "--format=%(refname:short)\t%(objectname:short)\t%(creatordate:iso)",
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
    tags = _list_tags(root)
    semver_tags = [tg for tg in tags if _SEMVER_RE.match(tg["name"])]
    if not semver_tags:
        return None

    def _sort_key(tg: dict[str, str]) -> tuple[int, ...]:
        m = _SEMVER_RE.match(tg["name"])
        if not m:
            return (0, 0, 0)
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    semver_tags.sort(key=_sort_key, reverse=True)
    return semver_tags[0]


def _bump_version(version: str, part: str) -> str:
    m = _SEMVER_RE.match(version)
    if not m:
        return version
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    prefix = "v" if version.startswith("v") else ""
    if part == "major":
        major += 1
        minor = patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{prefix}{major}.{minor}.{patch}"


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
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    if action == "list":
        tags = _list_tags(root)
        if as_json:
            print_json({"v": 2, "tags": tags, "count": len(tags), "ok": True})
            return 0
        if not tags:
            ok(t("tag_empty"))
            return 0
        for tg in tags:
            print(f"  {tg['name']}  {tg['sha']}  {tg['date']}")
        return 0

    if action == "latest":
        latest = _latest_semver(root)
        if as_json:
            print_json({"v": 2, "latest": latest, "ok": True})
            return 0
        if latest:
            print(f"  {latest['name']}  {latest['sha']}")
        else:
            warn(t("tag_no_semver"))
        return 0

    if action == "create":
        if bump:
            latest = _latest_semver(root)
            base = latest["name"] if latest else "0.0.0"
            tag_name = _bump_version(base, bump)
        else:
            tag_name = name
        if not tag_name:
            print(t("tag_name_required"), file=sys.stderr)
            return 1

        args = ["tag"]
        if message:
            args += ["-a", tag_name, "-m", message]
        else:
            args.append(tag_name)

        if dry_run:
            ok(t("tag_create_dry", name=tag_name))
            return 0
        r = git_run(args, cwd=root, check=False)
        if r.returncode != 0:
            if as_json:
                print_json({"v": 2, "ok": False, "error": r.stderr.strip()})
            else:
                print(r.stderr.strip(), file=sys.stderr)
            return 1
        if as_json:
            print_json({"v": 2, "created": tag_name, "ok": True})
            return 0
        ok(t("tag_created", name=tag_name))
        return 0

    if action == "delete":
        if not name:
            print(t("tag_name_required"), file=sys.stderr)
            return 1
        if not yes and not confirm(t("confirm_tag_delete", name=name)):
            warn(t("aborted"))
            return 1
        if dry_run:
            ok(t("tag_delete_dry", name=name))
            return 0
        r = git_run(["tag", "-d", name], cwd=root, check=False)
        if r.returncode != 0:
            if as_json:
                print_json({"v": 2, "ok": False, "error": r.stderr.strip()})
            else:
                print(r.stderr.strip(), file=sys.stderr)
            return 1
        if as_json:
            print_json({"v": 2, "deleted": name, "ok": True})
            return 0
        ok(t("tag_deleted", name=name))
        return 0

    print(t("tag_unknown_action", action=action), file=sys.stderr)
    return 1
