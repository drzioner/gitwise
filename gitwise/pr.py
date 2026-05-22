"""gitwise pr — GitHub PR wrapper via gh CLI."""

import json
import shutil
from datetime import datetime
from pathlib import Path

from .git import require_root
from .i18n import t
from .output import (
    error,
    info,
    print_blank,
    print_bracket,
    print_dim,
    print_file_status,
    print_header,
    print_json,
    print_table,
)
from .utils.json_envelope import error_envelope, ok_envelope
from .utils.parsing import dict_list, to_int

_STATE_LABEL_KEYS: dict[str, str] = {
    "pass": "pr_check_state_pass",
    "fail": "pr_check_state_fail",
    "running": "pr_check_state_running",
    "pending": "pr_check_state_pending",
    "queued": "pr_check_state_queued",
    "cancel": "pr_check_state_cancel",
    "skip": "pr_check_state_skip",
    "other": "pr_check_state_other",
}

_PR_LIST_FIELDS = "number,title,state,headRefName"
_PR_CHECKS_FIELDS = "name,state,startedAt,completedAt,link,workflow,event"
_PR_VIEW_FIELDS = (
    "number,title,state,isDraft,author,headRefName,baseRefName,"
    "url,createdAt,updatedAt,mergedAt,closedAt,mergeable,reviewDecision,additions,deletions,"
    "changedFiles,labels,assignees,reviewRequests,body"
)
_PR_COMMENTS_FIELDS = "number,title,url,comments"


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


def _actor_name(actor: object) -> str:
    if isinstance(actor, dict):
        login = actor.get("login")
        if isinstance(login, str) and login.strip():
            return login.strip()
        name = actor.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return "-"


def _clean_lines(text: str, *, max_lines: int) -> list[str]:
    normalized = _normalize_body_text(text)
    lines = [line.rstrip() for line in normalized.splitlines()]
    compact = [line for line in lines if line.strip()]
    if len(compact) <= max_lines:
        return compact
    return compact[:max_lines]


def _normalize_body_text(text: str) -> str:
    return text


def _json_or_error(out: str) -> tuple[bool, object | None]:
    if not out:
        return True, None
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return False, None
    return True, parsed


def _selector_args(selector: str | None) -> list[str]:
    if selector is None:
        return []
    cleaned = selector.strip()
    if not cleaned:
        return []
    if cleaned.startswith("-"):
        raise ValueError(t("pr_invalid_selector", selector=selector))
    return [cleaned]


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    iso = value.strip()
    if not iso:
        return None
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def _format_datetime(value: str) -> str:
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return value or "-"
    return parsed.strftime("%Y-%m-%d %H:%M")


def _non_empty_line_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    minutes, rem = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m{rem:02d}s"
    return f"{rem}s"


def _state_label(state: str) -> str:
    normalized = state.strip().upper()
    mapping = {
        "SUCCESS": "pass",
        "PASSED": "pass",
        "FAILURE": "fail",
        "FAILED": "fail",
        "CANCELLED": "cancel",
        "SKIPPED": "skip",
        "PENDING": "pending",
        "IN_PROGRESS": "running",
        "QUEUED": "queued",
    }
    return mapping.get(normalized, normalized.lower() if normalized else "-")


def _state_label_human(state: str) -> str:
    return t(_STATE_LABEL_KEYS[state]) if state in _STATE_LABEL_KEYS else state


def _duration_from_check(check: dict[str, object]) -> str:
    started = str(check.get("startedAt") or "")
    completed = str(check.get("completedAt") or "")
    started_dt = _parse_iso_datetime(started)
    completed_dt = _parse_iso_datetime(completed)
    if started_dt is None or completed_dt is None:
        return "-"
    seconds = int((completed_dt - started_dt).total_seconds())
    if seconds < 0:
        return "-"
    return _format_duration(seconds)


def _normalize_checks(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, list):
        return []
    checks: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "-").strip()
        state = _state_label(str(item.get("state") or ""))
        duration = _duration_from_check(item)
        workflow_value = item.get("workflow")
        workflow = "-"
        if isinstance(workflow_value, dict):
            candidate = workflow_value.get("name")
            if isinstance(candidate, str) and candidate.strip():
                workflow = candidate.strip()
        elif isinstance(workflow_value, str) and workflow_value.strip():
            workflow = workflow_value.strip()
        elif isinstance(item.get("event"), str) and str(item.get("event") or "").strip():
            workflow = str(item.get("event") or "").strip()
        link = str(item.get("link") or "").strip()
        checks.append(
            {
                "name": name,
                "state": state,
                "duration": duration,
                "workflow": workflow,
                "link": link,
            }
        )
    return checks


def _checks_summary(checks: list[dict[str, str]]) -> dict[str, int]:
    summary = {"pass": 0, "fail": 0, "running": 0, "other": 0}
    for check in checks:
        state = check.get("state", "")
        if state == "pass":
            summary["pass"] += 1
        elif state == "fail":
            summary["fail"] += 1
        elif state in {"running", "queued", "pending"}:
            summary["running"] += 1
        else:
            summary["other"] += 1
    return summary


def _pr_label_for_selector(selected: list[str]) -> str:
    if not selected:
        return t("pr_current_label")
    return selected[0]


def _render_pr_checks(checks: list[dict[str, str]], *, selector_label: str) -> int:
    print_header(t("pr_checks_title", selector=selector_label))
    if not checks:
        info(t("pr_checks_none"))
        return 0

    summary = _checks_summary(checks)
    print_bracket(
        t("pr_checks_summary"),
        t(
            "pr_checks_summary_value",
            total=str(len(checks)),
            passed=str(summary["pass"]),
            failed=str(summary["fail"]),
            running=str(summary["running"]),
            other=str(summary["other"]),
            label_pass=t("pr_check_state_pass"),
            label_fail=t("pr_check_state_fail"),
            label_running=t("pr_check_state_running"),
            label_other=t("pr_check_state_other"),
        ),
    )

    columns = [
        (t("pr_checks_col_name"), "name"),
        (t("pr_checks_col_status"), "state"),
        (t("pr_checks_col_duration"), "duration"),
        (t("pr_checks_col_workflow"), "workflow"),
    ]
    rows = [
        [c["name"], _state_label_human(c["state"]), c["duration"], c["workflow"]] for c in checks
    ]
    print_table(
        title=t("pr_checks_table_title"),
        columns=columns,
        rows=rows,
        no_wrap_columns={1, 2},
        max_widths={0: 42, 1: 10, 2: 10, 3: 28},
        overflow_columns={0: "ellipsis", 3: "ellipsis"},
        column_ratios={0: 3, 3: 2},
    )

    links = [c["link"] for c in checks if c.get("link")]
    if links:
        print_blank()
        print_header(t("pr_checks_links_title"))
        for idx, link in enumerate(links, start=1):
            print_dim(f"  {idx}. {link}")
    return 0


def _render_pr_view(payload: dict[str, object]) -> None:
    number = str(payload.get("number", "-"))
    title = str(payload.get("title") or "")
    state = str(payload.get("state") or "-")
    if payload.get("isDraft") is True:
        state = f"{state} (draft)"

    head = str(payload.get("headRefName") or "-")
    base = str(payload.get("baseRefName") or "-")
    mergeable = str(payload.get("mergeable") or "-")
    review = str(payload.get("reviewDecision") or "-")
    additions = to_int(payload.get("additions"))
    deletions = to_int(payload.get("deletions"))
    changed_files = to_int(payload.get("changedFiles"))
    url = str(payload.get("url") or "")
    merged_at = str(payload.get("mergedAt") or "")
    closed_at = str(payload.get("closedAt") or "")
    labels = dict_list(payload.get("labels"))
    assignees = dict_list(payload.get("assignees"))
    review_requests = dict_list(payload.get("reviewRequests"))

    label_names = ", ".join(
        str(item.get("name")).strip() for item in labels if str(item.get("name") or "").strip()
    )
    assignee_names = ", ".join(_actor_name(item) for item in assignees)
    review_request_names = ", ".join(
        _actor_name(item.get("requestedReviewer"))
        for item in review_requests
        if item.get("requestedReviewer")
    )

    print_header(t("pr_view_title", number=number, title=title or "-"))
    print_bracket(t("pr_field_state"), state)
    print_bracket(t("pr_field_branch"), f"{head} -> {base}")
    print_bracket(t("pr_field_author"), _actor_name(payload.get("author")))
    if state == "MERGED" and merged_at:
        print_bracket(t("pr_field_merged_at"), _format_datetime(merged_at))
    elif state == "CLOSED" and closed_at:
        print_bracket(t("pr_field_closed_at"), _format_datetime(closed_at))
    else:
        print_bracket(t("pr_field_mergeable"), mergeable)
        print_bracket(t("pr_field_review"), review)
    print_bracket(t("pr_field_changes"), f"{changed_files} files, +{additions}/-{deletions}")
    if label_names:
        print_bracket(t("pr_field_labels"), label_names)
    if assignee_names:
        print_bracket(t("pr_field_assignees"), assignee_names)
    if review_request_names:
        print_bracket(t("pr_field_review_requests"), review_request_names)
    if url:
        print_bracket(t("pr_field_url"), url)

    body = str(payload.get("body") or "").strip()
    if body:
        print_blank()
        print_header(t("pr_body_title"))
        for line in _clean_lines(body, max_lines=12):
            info(f"  {line}")
        if _non_empty_line_count(body) > 12:
            print_dim(f"  {t('pr_body_truncated')}")


def _render_pr_comments(payload: dict[str, object]) -> int:
    number = str(payload.get("number", "-"))
    title = str(payload.get("title") or "")
    url = str(payload.get("url") or "")
    comments = dict_list(payload.get("comments"))

    print_header(t("pr_comments_title", number=number, title=title or "-"))
    if url:
        print_bracket(t("pr_field_url"), url)

    if not comments:
        info(t("pr_comments_none"))
        return 0

    print_bracket(t("pr_field_comments"), str(len(comments)))
    print_blank()

    for idx, comment in enumerate(comments, start=1):
        author = _actor_name(comment.get("author"))
        created_at = _format_datetime(str(comment.get("createdAt") or "-"))
        comment_url = str(comment.get("url") or "")
        body = str(comment.get("body") or "").strip()

        print_header(t("pr_comment_header", index=str(idx), author=author, created=created_at))
        if comment_url:
            print_dim(f"  {comment_url}")
        if body:
            for line in _clean_lines(body, max_lines=20):
                info(f"  {line}")
            if _non_empty_line_count(body) > 20:
                print_dim(f"  {t('pr_comment_truncated')}")
        else:
            print_dim(f"  {t('pr_comment_empty')}")
        if idx < len(comments):
            print_blank()

    return 0


def _invalid_json_response(*, as_json: bool, raw: str) -> int:
    if as_json:
        print_json(error_envelope(error="invalid_gh_json", raw=raw))
    else:
        error(t("pr_invalid_json"))
    return 1


def _run_action_list(*, root: Path, as_json: bool) -> int:
    rc, out, err = _gh(["pr", "list", "--json", _PR_LIST_FIELDS], cwd=root)
    if rc != 0:
        error(err)
        return 1

    if as_json:
        ok_json, payload = _json_or_error(out)
        if not ok_json:
            print_json(error_envelope(error="invalid_gh_json", raw=out))
        elif payload is None:
            print_json([])
        else:
            print_json(payload)
        return 0

    prs = json.loads(out) if out else []
    if not prs:
        info(t("pr_none"))
        return 0

    print_header(t("pr_list_title"))
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        state = str(pr.get("state") or "")
        number = str(pr.get("number") or "-")
        title = str(pr.get("title") or "-")
        head = str(pr.get("headRefName") or "-")
        print_file_status(_pr_status_code(state), f"#{number}  {title}")
        info(f"    ({state}) <- {head}")
    return 0


def _run_action_checks(*, root: Path, selected: list[str], as_json: bool) -> int:
    rc, out, err = _gh(["pr", "checks", *selected, "--json", _PR_CHECKS_FIELDS], cwd=root)
    if rc != 0:
        error(err)
        return 1

    ok_json, payload = _json_or_error(out)
    if not ok_json:
        return _invalid_json_response(as_json=as_json, raw=out)

    checks = _normalize_checks(payload)
    if as_json:
        summary = _checks_summary(checks)
        print_json(
            ok_envelope(
                selector=_pr_label_for_selector(selected),
                checks=checks,
                count=len(checks),
                summary=summary,
            )
        )
        return 0

    return _render_pr_checks(checks, selector_label=_pr_label_for_selector(selected))


def _run_action_view(*, root: Path, selected: list[str], as_json: bool) -> int:
    rc, out, err = _gh(["pr", "view", *selected, "--json", _PR_VIEW_FIELDS], cwd=root)
    if rc != 0:
        error(err)
        return 1

    ok_json, payload = _json_or_error(out)
    if not ok_json or not isinstance(payload, dict):
        return _invalid_json_response(as_json=as_json, raw=out)

    if as_json:
        print_json(ok_envelope(payload=payload))
        return 0

    _render_pr_view(payload)
    return 0


def _run_action_comments(*, root: Path, selected: list[str], as_json: bool) -> int:
    rc, out, err = _gh(["pr", "view", *selected, "--json", _PR_COMMENTS_FIELDS], cwd=root)
    if rc != 0:
        error(err)
        return 1

    ok_json, payload = _json_or_error(out)
    if not ok_json or not isinstance(payload, dict):
        return _invalid_json_response(as_json=as_json, raw=out)

    comments = payload.get("comments")
    if not isinstance(comments, list):
        comments = []
    if as_json:
        print_json(
            ok_envelope(
                number=payload.get("number"),
                title=payload.get("title"),
                url=payload.get("url"),
                comments=comments,
                count=len(comments),
            )
        )
        return 0

    return _render_pr_comments(payload)


def run_pr(
    *,
    action: str = "list",
    selector: str | None = None,
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
        return _run_action_list(root=root, as_json=as_json)

    try:
        selected = _selector_args(selector)
    except ValueError as e:
        error(str(e))
        return 1

    if action == "checks":
        return _run_action_checks(root=root, selected=selected, as_json=as_json)

    if action == "view":
        return _run_action_view(root=root, selected=selected, as_json=as_json)

    if action == "comments":
        return _run_action_comments(root=root, selected=selected, as_json=as_json)

    error(t("pr_unknown_action", action=action))
    return 1
