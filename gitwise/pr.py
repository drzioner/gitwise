"""gitwise pr — GitHub PR wrapper via gh CLI."""

import json
import shutil

from .git import require_root
from .i18n import t
from .output import error, info, print_file_status, print_header, print_json


def _pr_status_code(state: str) -> str:
    normalized = state.strip().upper()
    if normalized in {"OPEN", "DRAFT"}:
        return "M"
    if normalized in {"MERGED"}:
        return "A"
    if normalized in {"CLOSED"}:
        return "D"
    return "M"


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
        timeout=120,
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
    if root is None:
        return 1

    if action == "list":
        rc, out, err = _gh(["pr", "list", "--json", "number,title,state,headRefName"], cwd=root)
        if rc != 0:
            error(err)
            return 1
        if as_json:
            if out:
                try:
                    print_json(json.loads(out))
                except json.JSONDecodeError:
                    print_json({"ok": False, "error": "invalid_gh_json", "raw": out})
            else:
                print_json([])
        else:
            prs = json.loads(out) if out else []
            if not prs:
                info(t("pr_none"))
                return 0
            print_header(t("pr_list_title"))
            for pr in prs:
                print_file_status(_pr_status_code(pr["state"]), f"#{pr['number']}  {pr['title']}")
                info(f"    ({pr['state']}) <- {pr['headRefName']}")
        return 0

    if action == "checks":
        rc, out, err = _gh(["pr", "checks"], cwd=root)
        if rc != 0:
            error(err)
            return 1
        if as_json:
            rc2, out2, _ = _gh(["pr", "view", "--json", "statusCheckRollup"], cwd=root)
            if rc2 == 0 and out2:
                try:
                    print_json(json.loads(out2))
                except json.JSONDecodeError:
                    print_json({"ok": False, "error": "invalid_gh_json", "raw": out2})
            else:
                print_json({})
        else:
            info(out)
        return 0

    error(t("pr_unknown_action", action=action))
    return 1
