"""gitwise undo — reflog-based undo to any previous HEAD state."""

import sys

from .git import is_repo, repo_root
from .git import run as git_run
from .i18n import t
from .output import print_json


def _parse_reflog(raw: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in raw.splitlines():
        parts = line.split("|", 3)
        if len(parts) >= 4:
            entries.append(
                {
                    "hash": parts[0].strip(),
                    "ref": parts[1].strip(),
                    "action": parts[2].strip(),
                    "message": parts[3].strip(),
                }
            )
    return entries


def run_undo(
    *,
    ref: str | None = None,
    soft: bool = False,
    steps: int = 1,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    if not is_repo():
        print(t("not_a_git_repo"), file=sys.stderr)
        return 1
    root = repo_root()
    if root is None:
        print(t("no_repo_root"), file=sys.stderr)
        return 1

    r = git_run(
        ["reflog", "--format=%H|gd-ref:%gd|gs:%gs|msg:%s", f"--max-count={steps + 10}"],
        cwd=root,
        check=False,
    )
    if r.returncode != 0:
        print(t("undo_reflog_failed"), file=sys.stderr)
        return 1

    entries = _parse_reflog(r.stdout)
    if not entries:
        print(t("undo_no_entries"), file=sys.stderr)
        return 1

    if ref:
        target = ref
    elif len(entries) >= steps + 1:
        target = entries[steps]["hash"]
    else:
        print(t("undo_not_enough_history"), file=sys.stderr)
        return 1

    if dry_run:
        if as_json:
            print_json(
                {"target": target, "soft": soft, "dry_run": True, "entries": entries[: steps + 1]}
            )
        else:
            print(t("dry_run_no_exec"))
            mode = "--soft" if soft else "--hard"
            print(f"  git reset {mode} {target[:12]}")
        return 0

    args = ["reset"]
    if soft:
        args.append("--soft")
    else:
        args.append("--hard")
    args.append(target)

    r = git_run(args, cwd=root, check=False)
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
        return 1

    if as_json:
        print_json({"ok": True, "target": target, "soft": soft})
    else:
        print(t("undo_complete", ref=target[:12]))
    return 0
