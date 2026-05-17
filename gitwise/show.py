"""gitwise show — commit inspector with stat and JSON output."""

import sys

from .git import require_root
from .git import run as git_run
from .i18n import t
from .output import HAS_DELTA, bat_pipe, info, print_json


def _build_show_args(ref: str = "HEAD", stat: bool = False) -> list[str]:
    args = ["show"]
    if stat:
        args.append("--stat")
    else:
        args.append(
            "--format=%C(yellow)%H%C(reset)%n%C(dim)%ad%C(reset) %C(bold)%an%C(reset) <%ae>%n%C(dim)%d%C(reset)%n%n  %s%n"
        )
        args.append("--patch")
    args.append(ref)
    return args


def _build_show_json_args(ref: str = "HEAD") -> list[str]:
    return [
        "show",
        "--format=%H%n%h%n%an%n%ae%n%ad%n%s",
        "-s",
        ref,
    ]


def _parse_show_json(raw: str) -> dict[str, str | list[str] | int | bool]:
    lines = [ln for ln in raw.strip().splitlines() if ln.strip()]
    if len(lines) >= 6:
        return {
            "hash": lines[0],
            "short_hash": lines[1],
            "author": lines[2],
            "email": lines[3],
            "date": lines[4],
            "subject": lines[5],
        }
    return {"raw": raw}


def run_show(
    *,
    ref: str = "HEAD",
    stat: bool = False,
    as_json: bool = False,
) -> int:
    root, err = require_root()
    if err:
        return err
    assert root is not None

    if as_json:
        args = _build_show_json_args(ref)
        r = git_run(args, cwd=root, check=False)
        if r.returncode != 0:
            print(t("git_show_failed", error=r.stderr.strip()), file=sys.stderr)
            return 1
        data = _parse_show_json(r.stdout)
        data["v"] = 2
        data["ok"] = True
        print_json(data)
    else:
        args = _build_show_args(ref, stat)
        r = git_run(args, cwd=root, check=False)
        if r.returncode != 0:
            print(t("git_show_failed", error=r.stderr.strip()), file=sys.stderr)
            return 1
        if HAS_DELTA:
            info(t("using_delta"))
        bat_pipe(r.stdout, language="diff")

    return 0
