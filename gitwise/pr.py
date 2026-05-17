"""gitwise pr — GitHub PR wrapper via gh CLI."""

import json
import shutil
import sys

from .git import require_root
from .i18n import t


def _gh_available() -> bool:
    return bool(shutil.which("gh"))


def _gh(args: list[str], cwd) -> tuple[int, str, str]:
    import subprocess

    r = subprocess.run(
        ["gh"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def run_pr(
    *,
    action: str = "list",
    as_json: bool = False,
) -> int:
    if not _gh_available():
        print(t("pr_gh_required"), file=sys.stderr)
        return 1
    root, err = require_root()
    if err:
        return err
    assert root is not None

    if action == "list":
        rc, out, err = _gh(["pr", "list", "--json", "number,title,state,headRefName"], cwd=root)
        if rc != 0:
            print(err, file=sys.stderr)
            return 1
        if as_json:
            print(out)
        else:
            prs = json.loads(out) if out else []
            if not prs:
                print(t("pr_none"))
                return 0
            for pr in prs:
                print(f"  #{pr['number']} {pr['title']} ({pr['state']}) ← {pr['headRefName']}")
        return 0

    if action == "checks":
        rc, out, err = _gh(["pr", "checks"], cwd=root)
        if rc != 0:
            print(err, file=sys.stderr)
            return 1
        if as_json:
            rc2, out2, _ = _gh(["pr", "view", "--json", "statusCheckRollup"], cwd=root)
            print(out2 if rc2 == 0 else "{}")
        else:
            print(out)
        return 0

    print(t("pr_unknown_action", action=action), file=sys.stderr)
    return 1
