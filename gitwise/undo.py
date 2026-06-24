"""gitwise undo — reflog-based undo to any previous HEAD state."""

from gitwise.git import require_root, validate_ref
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import confirm, error, print_bracket, print_dim, print_header, print_json
from gitwise.utils.json_envelope import ok_envelope


def _resolve_undo_target(
    *, ref: str | None, entries: list[dict[str, str]], steps: int
) -> str | None:
    """Resolve the target commit hash from an explicit ref or N steps back in reflog."""
    if ref:
        if not validate_ref(ref):
            error(t("invalid_ref", ref=ref))
            return None
        return ref
    if len(entries) >= steps + 1:
        return entries[steps]["hash"]
    error(t("undo_not_enough_history"))
    return None


def _print_undo_dry_run(*, target: str, soft: bool) -> None:
    """Print the dry-run reset plan."""
    print_header(t("undo_dry_run_title"))
    mode = "--soft" if soft else "--hard"
    print_bracket(f"git reset {mode}", target[:12])


def _reset_to_target(*, root, target: str, soft: bool) -> int:
    """Run ``git reset --soft/--hard`` to *target*."""
    args = ["reset", "--soft" if soft else "--hard", target]
    result = git_run(args, cwd=root, check=False)
    if result.returncode != 0:
        error(result.stderr.strip())
        return 1
    return 0


def _load_reflog_entries(*, root, steps: int) -> list[dict[str, str]] | None:
    """Load reflog entries; returns None on error or empty reflog."""
    result = git_run(
        ["reflog", "--format=%H|gd-ref:%gd|gs:%gs|msg:%s", f"--max-count={steps + 10}"],
        cwd=root,
        check=False,
    )
    if result.returncode != 0:
        error(t("undo_reflog_failed"))
        return None
    entries = _parse_reflog(result.stdout)
    if not entries:
        error(t("undo_no_entries"))
        return None
    return entries


def _run_undo_dry_run(
    *, as_json: bool, target: str, soft: bool, entries: list[dict[str, str]], steps: int
) -> int:
    """Print or envelope the dry-run undo plan."""
    if as_json:
        print_json(
            ok_envelope(
                "undo",
                target=target,
                soft=soft,
                dry_run=True,
                entries=entries[: steps + 1],
            )
        )
    else:
        _print_undo_dry_run(target=target, soft=soft)
    return 0


def _confirm_hard_reset(*, soft: bool, yes: bool, target: str) -> bool:
    """Return True if the hard reset should proceed (auto-approved when soft or --yes)."""
    if soft or yes:
        return True
    if confirm(t("undo_confirm_hard", ref=target[:12])):
        return True
    print_dim(t("cancelled"))
    return False


def _report_undo_complete(*, as_json: bool, target: str, soft: bool) -> int:
    """Print or envelope the undo-complete message."""
    if as_json:
        print_json(ok_envelope("undo", target=target, soft=soft))
        return 0
    print_header(t("undo_complete_title"))
    print_bracket(t("undo_reset_to"), target[:12])
    return 0


def _parse_reflog(raw: str) -> list[dict[str, str]]:
    """Parse custom-format reflog lines into ``[{hash, ref, action, message}]``."""
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
    """Entry point for the ``gitwise undo`` command."""
    root = require_root()
    if root is None:
        return 1

    entries = _load_reflog_entries(root=root, steps=steps)
    if entries is None:
        return 1

    target = _resolve_undo_target(ref=ref, entries=entries, steps=steps)
    if target is None:
        return 1

    if dry_run:
        return _run_undo_dry_run(
            as_json=as_json,
            target=target,
            soft=soft,
            entries=entries,
            steps=steps,
        )

    if not _confirm_hard_reset(soft=soft, yes=yes, target=target):
        return 0

    reset_rc = _reset_to_target(root=root, target=target, soft=soft)
    if reset_rc != 0:
        return reset_rc

    return _report_undo_complete(as_json=as_json, target=target, soft=soft)
