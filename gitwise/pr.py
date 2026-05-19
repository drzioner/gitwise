"""gitwise pr — GitHub PR wrapper via gh CLI."""

import json
import shutil

from .git import require_root
from .i18n import t
from .output import error, info, print_accent, print_bracket, print_header


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
        error(t("pr_gh_required"))
        return 1
    root, err = require_root()
    if err:
        return err
    assert root is not None

    if action == "list":
        rc, out, err = _gh(["pr", "list", "--json", "number,title,state,headRefName"], cwd=root)
        if rc != 0:
            error(err)
            return 1
        if as_json:
            print(out)
        else:
            prs = json.loads(out) if out else []
            if not prs:
                info(t("pr_none"))
                return 0
            print_header(t("pr_list_title"))
            for pr in prs:
                print_bracket(f"#{pr['number']}", f"{pr['title']}")
                print_accent(f"  ({pr['state']}) ← {pr['headRefName']}")
        return 0

    if action == "checks":
        rc, out, err = _gh(["pr", "checks"], cwd=root)
        if rc != 0:
            error(err)
            return 1
        if as_json:
            rc2, out2, _ = _gh(["pr", "view", "--json", "statusCheckRollup"], cwd=root)
            print(out2 if rc2 == 0 else "{}")
        else:
            info(out)
        return 0

    error(t("pr_unknown_action", action=action))
    return 1
