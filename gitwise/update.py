"""Update gitwise via git pull."""

import sys
from pathlib import Path

from .git import run as git_run
from .i18n import t
from .output import print_json


def run_update(*, dry_run: bool = False, as_json: bool = False) -> int:
    install_dir = Path(__file__).parent.parent
    if dry_run:
        if as_json:
            print_json({"v": 2, "ok": True, "dry_run": True, "dir": str(install_dir)})
            return 0
        print(t("update_dry_run", dir=str(install_dir)))
        return 0
    print(t("updating_from", dir=str(install_dir)))
    r = git_run(["pull", "--ff-only"], cwd=install_dir, check=False)
    if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != "Already up to date.":
        if as_json:
            print_json({"v": 2, "ok": True, "updated": True, "output": r.stdout.strip()})
            return 0
        print(r.stdout.strip())
    elif r.returncode != 0:
        if as_json:
            print_json({"v": 2, "ok": False, "error": r.stderr.strip() or t("error_updating")})
            return 1
        print(r.stderr.strip() or t("error_updating"), file=sys.stderr)
        return r.returncode
    elif as_json:
        print_json({"v": 2, "ok": True, "updated": False, "output": t("already_up_to_date")})
        return 0
    return r.returncode
