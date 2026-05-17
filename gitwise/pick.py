"""gitwise pick — cherry-pick/revert helper."""

import sys

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import ok, print_json


def run_pick(
    refs: list[str],
    *,
    revert: bool = False,
    continue_: bool = False,
    abort: bool = False,
    dry_run: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    if continue_:
        r = git_run([("revert" if revert else "cherry-pick"), "--continue"], cwd=root, check=False)
        if r.returncode != 0:
            print(r.stderr.strip(), file=sys.stderr)
            return 1
        if as_json:
            print_json({"v": 2, "continued": True, "ok": True})
            return 0
        ok(t("pick_continued"))
        return 0

    if abort:
        r = git_run([("revert" if revert else "cherry-pick"), "--abort"], cwd=root, check=False)
        if r.returncode != 0:
            print(r.stderr.strip(), file=sys.stderr)
            return 1
        if as_json:
            print_json({"v": 2, "aborted": True, "ok": True})
            return 0
        ok(t("pick_aborted"))
        return 0

    if not refs:
        print(t("pick_no_refs"), file=sys.stderr)
        return 1

    action = "revert" if revert else "cherry-pick"

    if dry_run:
        if as_json:
            print_json({"v": 2, "dry_run": True, "action": action, "refs": refs, "ok": True})
            return 0
        ok(t("pick_dry", action=action, refs=", ".join(refs)))
        return 0

    args = [action] + refs
    r = git_run(args, cwd=root, check=False)
    if r.returncode != 0:
        if "CONFLICT" in r.stdout or "CONFLICT" in r.stderr:
            print(t("pick_conflicts"), file=sys.stderr)
        else:
            print(r.stderr.strip(), file=sys.stderr)
        return 1

    if as_json:
        print_json({"v": 2, "action": action, "refs": refs, "ok": True})
        return 0
    ok(t("pick_ok", action=action, refs=", ".join(refs)))
    return 0
