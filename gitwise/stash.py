"""gitwise stash — manage stashes by index or age (list/show/pop/drop/clear)."""

from pathlib import Path

from gitwise.git import require_root
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import (
    confirm,
    error,
    info,
    ok,
    print_diffstat,
    print_header,
    print_json,
    print_table,
    status,
    warn,
)
from gitwise.utils.git_output import parse_diffstat_entries
from gitwise.utils.json_envelope import error_envelope, ok_envelope


def _parse_diffstat_entries(raw: str) -> list[dict[str, str]]:
    """Parse diffstat output, defaulting file status to 'M'."""
    return parse_diffstat_entries(raw, default_status="M")


def _stash_list(root: Path) -> list[dict[str, str]]:
    """Return stash entries as ``[{ref, branch?, message?}]``."""
    with status(t("status_reading_stashes")):
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
    """Execute ``stash list`` sub-action."""
    stashes = _stash_list(root)
    if as_json:
        print_json(ok_envelope("stash", stashes=stashes, count=len(stashes)))
        return 0
    if not stashes:
        ok(t("stash_empty"))
        return 0

    columns = [
        (t("stash_col_ref"), "ref"),
        (t("stash_col_branch"), "branch"),
        (t("stash_col_message"), "message"),
    ]

    rows: list[list[str]] = []
    for s in stashes:
        rows.append(
            [
                s.get("ref", ""),
                s.get("branch", ""),
                s.get("message", ""),
            ]
        )

    print_table(
        title=t("stash_list_title"),
        columns=columns,
        rows=rows,
    )
    return 0


def _cmd_show(root: Path, index: int, *, as_json: bool, patch: bool = False) -> int:
    """Execute ``stash show`` sub-action; pass *patch=True* for full diff."""
    ref = f"stash@{{{index}}}"
    stat_args = ["stash", "show", "--stat", ref]
    if patch:
        stat_args = ["stash", "show", "-p", ref]
    with status(t("status_reading_stashes")):
        r = git_run(stat_args, cwd=root, check=False)
    if r.returncode != 0:
        msg = t("stash_not_found", index=str(index))
        if as_json:
            print_json(
                error_envelope("stash", error=msg, code="stash_not_found", hint=t("stash_hint"))
            )
            return 1
        error(msg, hint=t("stash_hint"))
        return 1
    if as_json:
        print_json(ok_envelope("stash", ref=ref, stat=r.stdout.strip()))
        return 0
    if patch:
        print_header(ref)
        for line in r.stdout.strip().splitlines():
            info(line)
        return 0

    entries = _parse_diffstat_entries(r.stdout)
    if entries:
        print_diffstat(ref, entries)
    else:
        print_header(ref)
        for line in r.stdout.strip().splitlines():
            info(line)
    return 0


def _cmd_pop(root: Path, index: int, *, as_json: bool) -> int:
    """Execute ``stash pop`` sub-action."""
    ref = f"stash@{{{index}}}"
    r = git_run(["stash", "pop", ref], cwd=root, check=False)
    if r.returncode != 0:
        error(r.stderr.strip())
        return 1
    if as_json:
        print_json(ok_envelope("stash", popped=ref))
        return 0
    ok(t("stash_popped", ref=ref))
    return 0


def _cmd_drop(root: Path, index: int, *, as_json: bool, yes: bool = False) -> int:
    """Execute ``stash drop`` sub-action with optional confirmation."""
    ref = f"stash@{{{index}}}"
    if not yes and not confirm(t("confirm_stash_drop", ref=ref)):
        warn(t("aborted"))
        return 1
    r = git_run(["stash", "drop", ref], cwd=root, check=False)
    if r.returncode != 0:
        error(r.stderr.strip())
        return 1
    if as_json:
        print_json(ok_envelope("stash", dropped=ref))
        return 0
    ok(t("stash_dropped", ref=ref))
    return 0


def _cmd_clean(root: Path, *, as_json: bool, yes: bool = False, dry_run: bool = False) -> int:
    """Execute ``stash clear`` sub-action with optional dry-run and confirmation."""
    stashes = _stash_list(root)
    if not stashes:
        ok(t("stash_empty"))
        return 0
    if dry_run:
        if as_json:
            print_json(ok_envelope("stash", would_drop=len(stashes), dry_run=True))
            return 0
        ok(t("stash_clean_dry", count=str(len(stashes))))
        return 0
    if not yes and not confirm(t("confirm_stash_clean", count=str(len(stashes)))):
        warn(t("aborted"))
        return 1
    r = git_run(["stash", "clear"], cwd=root, check=False)
    if r.returncode != 0:
        error(r.stderr.strip())
        return 1
    if as_json:
        print_json(ok_envelope("stash", cleared=len(stashes)))
        return 0
    ok(t("stash_cleaned", count=str(len(stashes))))
    return 0


def _cmd_apply(root: Path, index: int, *, as_json: bool) -> int:
    """Execute ``stash apply`` sub-action (restore without dropping the stash)."""
    ref = f"stash@{{{index}}}"
    r = git_run(["stash", "apply", ref], cwd=root, check=False)
    if r.returncode != 0:
        msg = r.stderr.strip() or t("stash_not_found", index=str(index))
        if as_json:
            print_json(
                error_envelope("stash", error=msg, code="stash_apply_failed", hint=t("stash_hint"))
            )
            return 1
        error(msg, hint=t("stash_hint"))
        return 1
    if as_json:
        print_json(ok_envelope("stash", applied=ref))
        return 0
    ok(t("stash_applied", ref=ref))
    return 0


def _cmd_push(
    root: Path,
    *,
    message: str | None = None,
    include_untracked: bool = False,
    keep_index: bool = False,
    paths: list[str] | None = None,
    as_json: bool = False,
) -> int:
    """Execute ``stash push`` sub-action (create a new stash)."""
    args = ["stash", "push"]
    if message:
        args += ["-m", message]
    if include_untracked:
        args.append("-u")
    if keep_index:
        args.append("--keep-index")
    if paths:
        args.append("--")
        args += [p for p in paths if p]
    r = git_run(args, cwd=root, check=False)
    if r.returncode != 0:
        msg = r.stderr.strip() or t("stash_push_failed")
        if as_json:
            print_json(error_envelope("stash", error=msg, code="stash_push_failed"))
            return 1
        error(msg)
        return 1
    # git prints "Saved working directory and index state ..." on success.
    created = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
    if as_json:
        print_json(ok_envelope("stash", pushed=True, message=created))
        return 0
    ok(t("stash_pushed"))
    return 0


def run_stash(
    action: str = "list",
    index: int = 0,
    *,
    as_json: bool = False,
    yes: bool = False,
    dry_run: bool = False,
    patch: bool = False,
    message: str | None = None,
    include_untracked: bool = False,
    keep_index: bool = False,
    paths: list[str] | None = None,
) -> int:
    """Entry point for the ``gitwise stash`` command."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    if action == "list":
        return _cmd_list(root, as_json=as_json)
    if action == "show":
        return _cmd_show(root, index, as_json=as_json, patch=patch)
    if action == "apply":
        return _cmd_apply(root, index, as_json=as_json)
    if action == "pop":
        return _cmd_pop(root, index, as_json=as_json)
    if action == "push":
        return _cmd_push(
            root,
            message=message,
            include_untracked=include_untracked,
            keep_index=keep_index,
            paths=paths,
            as_json=as_json,
        )
    if action == "drop":
        return _cmd_drop(root, index, as_json=as_json, yes=yes)
    if action in ("clean", "clear"):
        return _cmd_clean(root, as_json=as_json, yes=yes, dry_run=dry_run)
    error(t("stash_unknown_action", action=action))
    return 1
