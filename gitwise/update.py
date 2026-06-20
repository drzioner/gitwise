"""Update gitwise via git pull."""

from pathlib import Path

from gitwise.git import current_branch, has_upstream
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import error, info, print_dim, print_header, print_json, status
from gitwise.utils.json_envelope import error_envelope, ok_envelope


def run_update(*, dry_run: bool = False, as_json: bool = False) -> int:
    """Entry point for the ``gitwise update`` command. Pulls the gitwise repo via git."""
    install_dir = Path(__file__).parent.parent
    if not (install_dir / ".git").is_dir():
        if as_json:
            print_json(error_envelope("update", error=t("update_requires_git_clone")))
        else:
            error(t("update_requires_git_clone"))
        return 1
    if dry_run:
        if as_json:
            print_json(ok_envelope("update", dry_run=True, dir=str(install_dir)))
            return 0
        print_dim(t("update_dry_run", dir=str(install_dir)))
        return 0
    if not has_upstream(install_dir):
        branch = current_branch(install_dir) or "HEAD"
        msg = t("update_no_upstream", branch=branch)
        hint = t("update_no_upstream_hint", branch=branch)
        if as_json:
            print_json(error_envelope("update", error=msg, code="no_upstream", hint=hint))
        else:
            error(msg, hint=hint)
        return 1

    print_header(t("updating_from", dir=str(install_dir)))
    with status(t("status_updating")):
        r = git_run(["pull", "--ff-only"], cwd=install_dir, check=False)
    if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != "Already up to date.":
        if as_json:
            print_json(ok_envelope("update", updated=True, output=r.stdout.strip()))
            return 0
        for line in r.stdout.strip().splitlines():
            info(line)
    elif r.returncode != 0:
        if as_json:
            print_json(error_envelope("update", error=r.stderr.strip() or t("error_updating")))
            return 1
        error(r.stderr.strip() or t("error_updating"))
        return r.returncode
    elif as_json:
        print_json(ok_envelope("update", updated=False, output=t("already_up_to_date")))
        return 0
    return r.returncode
