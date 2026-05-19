"""gitwise undo — reflog-based undo to any previous HEAD state."""

from .git import require_root, validate_ref
from .git import run as git_run
from .i18n import t
from .output import confirm, error, print_bracket, print_dim, print_header, print_json


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
    yes: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    r = git_run(
        ["reflog", "--format=%H|gd-ref:%gd|gs:%gs|msg:%s", f"--max-count={steps + 10}"],
        cwd=root,
        check=False,
    )
    if r.returncode != 0:
        error(t("undo_reflog_failed"))
        return 1

    entries = _parse_reflog(r.stdout)
    if not entries:
        error(t("undo_no_entries"))
        return 1

    if ref:
        if not validate_ref(ref):
            error(t("invalid_ref", ref=ref))
            return 1
        target = ref
    elif len(entries) >= steps + 1:
        target = entries[steps]["hash"]
    else:
        error(t("undo_not_enough_history"))
        return 1

    if dry_run:
        if as_json:
            print_json(
                {
                    "v": 2,
                    "ok": True,
                    "target": target,
                    "soft": soft,
                    "dry_run": True,
                    "entries": entries[: steps + 1],
                }
            )
        else:
            print_header(t("undo_dry_run_title"))
            mode = "--soft" if soft else "--hard"
            print_bracket(f"git reset {mode}", target[:12])
        return 0

    if not soft and not yes:
        if not confirm(t("undo_confirm_hard", ref=target[:12])):
            print_dim(t("cancelled"))
            return 0

    args = ["reset"]
    if soft:
        args.append("--soft")
    else:
        args.append("--hard")
    args.extend(["--", target])

    r = git_run(args, cwd=root, check=False)
    if r.returncode != 0:
        error(r.stderr.strip())
        return 1

    if as_json:
        print_json({"v": 2, "ok": True, "target": target, "soft": soft})
    else:
        print_header(t("undo_complete_title"))
        print_bracket(t("undo_reset_to"), target[:12])
    return 0
