"""gitwise stash — manage stashes by index or age (list/show/pop/drop/clean)."""

import sys
from pathlib import Path

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import confirm, ok, print_json, warn


def _stash_list(root: Path) -> list[dict[str, str]]:
    r = git_run(["stash", "list"], cwd=root, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    result: list[dict[str, str]] = []
    for line in r.stdout.splitlines():
        parts = line.split(": ", 2)
        entry: dict[str, str] = {"ref": parts[0]}
        if len(parts) >= 2:
            entry["branch"] = parts[1].strip()
        if len(parts) >= 3:
            entry["message"] = parts[2].strip()
        result.append(entry)
    return result


def _cmd_list(root: Path, *, as_json: bool) -> int:
    stashes = _stash_list(root)
    if as_json:
        print_json({"v": 1, "stashes": stashes, "count": len(stashes)})
        return 0
    if not stashes:
        ok(t("stash_empty"))
        return 0
    for s in stashes:
        line = s["ref"]
        if "branch" in s:
            line += f"  [{s['branch']}]"
        if "message" in s:
            line += f"  {s['message']}"
        print(line)
    return 0


def _cmd_show(root: Path, index: int, *, as_json: bool) -> int:
    ref = f"stash@{{{index}}}"
    r = git_run(["stash", "show", "--stat", ref], cwd=root, check=False)
    if r.returncode != 0:
        print(t("stash_not_found", index=str(index)), file=sys.stderr)
        return 1
    if as_json:
        print_json({"v": 1, "ref": ref, "stat": r.stdout.strip()})
        return 0
    print(r.stdout.strip())
    return 0


def _cmd_pop(root: Path, index: int, *, as_json: bool) -> int:
    ref = f"stash@{{{index}}}"
    r = git_run(["stash", "pop", ref], cwd=root, check=False)
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
        return 1
    if as_json:
        print_json({"v": 1, "popped": ref, "ok": True})
        return 0
    ok(t("stash_popped", ref=ref))
    return 0


def _cmd_drop(root: Path, index: int, *, as_json: bool, yes: bool = False) -> int:
    ref = f"stash@{{{index}}}"
    if not yes and not confirm(t("confirm_stash_drop", ref=ref)):
        warn(t("aborted"))
        return 1
    r = git_run(["stash", "drop", ref], cwd=root, check=False)
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
        return 1
    if as_json:
        print_json({"v": 1, "dropped": ref, "ok": True})
        return 0
    ok(t("stash_dropped", ref=ref))
    return 0


def _cmd_clean(root: Path, *, as_json: bool, yes: bool = False, dry_run: bool = False) -> int:
    stashes = _stash_list(root)
    if not stashes:
        ok(t("stash_empty"))
        return 0
    if dry_run:
        if as_json:
            print_json({"v": 1, "would_drop": len(stashes), "dry_run": True})
            return 0
        ok(t("stash_clean_dry", count=str(len(stashes))))
        return 0
    if not yes and not confirm(t("confirm_stash_clean", count=str(len(stashes)))):
        warn(t("aborted"))
        return 1
    r = git_run(["stash", "clear"], cwd=root, check=False)
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
        return 1
    if as_json:
        print_json({"v": 1, "dropped": len(stashes), "ok": True})
        return 0
    ok(t("stash_cleaned", count=str(len(stashes))))
    return 0


def run_stash(
    action: str = "list",
    index: int = 0,
    *,
    as_json: bool = False,
    yes: bool = False,
    dry_run: bool = False,
) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    if action == "list":
        return _cmd_list(root, as_json=as_json)
    if action == "show":
        return _cmd_show(root, index, as_json=as_json)
    if action == "pop":
        return _cmd_pop(root, index, as_json=as_json)
    if action == "drop":
        return _cmd_drop(root, index, as_json=as_json, yes=yes)
    if action == "clean":
        return _cmd_clean(root, as_json=as_json, yes=yes, dry_run=dry_run)
    print(t("stash_unknown_action", action=action), file=sys.stderr)
    return 1
