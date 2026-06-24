"""gitwise show — commit inspector with stat and JSON output."""

from gitwise.git import require_root, validate_passthrough_args, validate_ref
from gitwise.git import run as git_run
from gitwise.i18n import t
from gitwise.output import bat_pipe, error, print_diffstat, print_header, print_json, status
from gitwise.utils.git_output import parse_diffstat_entries, parse_name_status_entries
from gitwise.utils.json_envelope import error_envelope, ok_envelope


def _report_error(*, as_json: bool, err: str, code: str) -> int:
    """Emit a show error as a JSON envelope or human message; return 1."""
    if as_json:
        print_json(error_envelope("show", error=err, code=code))
    else:
        error(err)
    return 1


def _build_show_args(
    ref: str = "HEAD", stat: bool = False, git_args: list[str] | None = None
) -> list[str]:
    """Build the ``git show`` argv for human output (patch or stat mode)."""
    args = ["show"]
    if git_args:
        args.extend(git_args)
    if stat:
        args.append("--stat")
    else:
        args.append(
            "--format=%C(yellow)%H%C(reset)%n%C(dim)%ad%C(reset) %C(bold)%an%C(reset) <%ae>%n%C(dim)%d%C(reset)%n%n  %s%n"
        )
        args.append("--patch")
    args.append(ref)
    return args


def _show_status_map(root, ref: str) -> dict[str, str]:
    """Return a path-to-status-letter map from the commit's name-status diff."""
    r = git_run(["show", "--name-status", "--format=", ref], cwd=root, check=False)
    if r.returncode != 0:
        return {}
    status_map: dict[str, str] = {}
    for item in parse_name_status_entries(r.stdout):
        status = str(item.get("status") or "")[:1].upper()
        path = str(item.get("path") or "").strip()
        if path:
            status_map[path] = status
    return status_map


def _build_show_json_args(ref: str = "HEAD", git_args: list[str] | None = None) -> list[str]:
    """Build the ``git show`` argv for structured JSON output (no patch)."""
    args = ["show"]
    if git_args:
        args.extend(git_args)
    args += [
        "--format=%H%n%h%n%an%n%ae%n%ad%n%s",
        "-s",
        ref,
    ]
    return args


def _parse_show_json(raw: str) -> dict[str, str | list[str] | int | bool]:
    """Parse the structured show output into a commit metadata dict.

    Returns ``{"raw": raw}`` when the output has fewer than six lines.
    """
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
    git_args: list[str] | None = None,
) -> int:
    """Inspect a commit with patch, stat, or structured JSON output."""
    root = require_root()
    if root is None:
        return 1

    if not validate_ref(ref):
        return _report_error(as_json=as_json, err=t("invalid_ref", ref=ref), code="invalid_ref")

    denied = validate_passthrough_args(git_args)
    if denied is not None:
        return _report_error(as_json=as_json, err=denied, code="git_arg_denied")

    if as_json:
        args = _build_show_json_args(ref, git_args=git_args)
        r = git_run(args, cwd=root, check=False)
        if r.returncode != 0:
            return _report_error(
                as_json=as_json,
                err=t("git_show_failed", error=r.stderr.strip()),
                code="git_show_failed",
            )
        data = _parse_show_json(r.stdout)
        print_json(ok_envelope("show", data=data))
    else:
        if stat:
            with status(t("status_loading_commit")):
                r = git_run(["show", "--stat", "--format=", ref], cwd=root, check=False)
            if r.returncode != 0:
                return _report_error(
                    as_json=as_json,
                    err=t("git_show_failed", error=r.stderr.strip()),
                    code="git_show_failed",
                )
            entries = parse_diffstat_entries(r.stdout)
            if entries:
                status_map = _show_status_map(root, ref)
                styled_entries = [
                    {
                        "path": entry["path"],
                        "changes": entry["changes"],
                        "status": status_map.get(entry["path"], "M"),
                    }
                    for entry in entries
                ]
                print_diffstat(t("show_header", ref=ref), styled_entries)
            else:
                print_header(t("show_header", ref=ref))
                bat_pipe(r.stdout, language="diff")
        else:
            args = _build_show_args(ref, stat, git_args=git_args)
            with status(t("status_loading_commit")):
                r = git_run(args, cwd=root, check=False)
            if r.returncode != 0:
                error(t("git_show_failed", error=r.stderr.strip()))
                return 1
            print_header(t("show_header", ref=ref))
            bat_pipe(r.stdout, language="diff")

    return 0
