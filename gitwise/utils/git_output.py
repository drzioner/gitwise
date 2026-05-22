"""Reusable parsers for git command output formats."""


def parse_diffstat_entries(raw: str, *, default_status: str | None = None) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in raw.splitlines():
        if "|" not in line:
            continue
        path_raw, changes_raw = line.split("|", 1)
        path = path_raw.strip()
        changes = changes_raw.strip()
        if not path:
            continue
        entry: dict[str, str] = {"path": path, "changes": changes}
        if default_status is not None:
            entry["status"] = default_status
        entries.append(entry)
    return entries


def parse_name_status_entries(raw: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        code = status[:1].upper() if status else ""
        if code in {"R", "C"} and len(parts) >= 3:
            old_path = parts[1].strip()
            path = parts[2].strip()
            if not path:
                continue
            entry: dict[str, str] = {"status": status, "path": path}
            if code and code != status:
                entry["code"] = code
            if old_path:
                entry["old_path"] = old_path
            if len(status) > 1 and status[1:].isdigit():
                entry["score"] = status[1:]
            entries.append(entry)
            continue

        path = parts[-1].strip()
        if not path:
            continue
        entry = {"status": status, "path": path}
        if code and code != status:
            entry["code"] = code
        entries.append(entry)
    return entries
