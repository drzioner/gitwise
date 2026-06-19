"""gitwise pick — cherry-pick/revert helper."""

from .git import require_root, validate_ref
from .git import run as git_run
from .i18n import t
from .output import error, ok, print_json, warn
from .utils.json_envelope import error_envelope, ok_envelope


def _pick_mode_args(*, revert: bool, continue_: bool, abort: bool) -> list[str] | None:
    """Build git args for continue/abort mode, or None if neither applies."""
    base = "revert" if revert else "cherry-pick"
    if continue_:
        return [base, "--continue"]
    if abort:
        return [base, "--abort"]
    return None


def _run_pick_mode(*, root, args: list[str], as_json: bool) -> int:
    """Execute a cherry-pick/revert continue or abort."""
    result = git_run(args, cwd=root, check=False)
    if result.returncode != 0:
        error(result.stderr.strip())
        return 1
    if as_json:
        if args[-1] == "--continue":
            print_json(ok_envelope(continued=True))
        else:
            print_json(ok_envelope(aborted=True))
        return 0
    if args[-1] == "--continue":
        ok(t("pick_continued"))
    else:
        ok(t("pick_aborted"))
    return 0


def _validate_pick_refs(refs: list[str], *, as_json: bool) -> int:
    """Validate that refs are non-empty and all pass ``validate_ref``."""
    if not refs:
        if as_json:
            print_json(error_envelope(error=t("pick_no_refs")))
            return 1
        error(t("pick_no_refs"))
        return 1
    for ref in refs:
        if not validate_ref(ref):
            error(t("invalid_ref", ref=ref))
            return 1
    return 0


def _run_pick_dry_run(*, action: str, refs: list[str], as_json: bool) -> int:
    """Print or envelope the dry-run pick plan."""
    if as_json:
        print_json(ok_envelope(dry_run=True, action=action, refs=refs))
        return 0
    ok(t("pick_dry", action=action, refs=", ".join(refs)))
    return 0


def _run_pick_execute(*, root, action: str, refs: list[str], as_json: bool) -> int:
    """Execute cherry-pick or revert and report conflicts if detected."""
    result = git_run([action, "--"] + refs, cwd=root, check=False)
    if result.returncode != 0:
        if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
            warn(t("pick_conflicts"))
        else:
            error(result.stderr.strip())
        return 1
    if as_json:
        print_json(ok_envelope(action=action, refs=refs))
        return 0
    ok(t("pick_ok", action=action, refs=", ".join(refs)))
    return 0


def run_pick(
    refs: list[str],
    *,
    revert: bool = False,
    continue_: bool = False,
    abort: bool = False,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    """Entry point for the ``gitwise pick`` (cherry-pick/revert) command."""
    root, err = require_root()
    if err:
        return err
    if root is None:
        return 1

    mode_args = _pick_mode_args(revert=revert, continue_=continue_, abort=abort)
    if mode_args is not None:
        return _run_pick_mode(root=root, args=mode_args, as_json=as_json)

    refs_rc = _validate_pick_refs(refs, as_json=as_json)
    if refs_rc != 0:
        return refs_rc

    action = "revert" if revert else "cherry-pick"

    if dry_run:
        return _run_pick_dry_run(action=action, refs=refs, as_json=as_json)

    return _run_pick_execute(root=root, action=action, refs=refs, as_json=as_json)
