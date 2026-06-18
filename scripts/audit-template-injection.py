#!/usr/bin/env python3
"""Audit GitHub Actions workflows for template-injection vectors.

Flags any `${{ ... }}` expression used inside a `run:` block. Expressions in
`run:` blocks are interpolated by the workflow runner into the shell script,
which means attacker-controlled values (workflow_dispatch inputs, issue titles,
PR bodies, head_branch from untrusted workflow_run triggers) can execute
arbitrary shell code. Expressions assigned to `env:`, `with:`, or `if:` are
safe — they are treated as string literals by the runner.

Usage:
    python3 scripts/audit-template-injection.py [--workflows .github/workflows]

Exit codes:
    0 — no findings (or only --list mode)
    1 — findings present (CI failure)
    2 — error (e.g., workflows dir not found)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

EXPRESSION_RE = re.compile(r"\$\{\{.*?\}\}")


def audit_workflow(path: Path) -> list[tuple[str, str, list[str]]]:
    """Return [(job_name, step_name, [expressions])] for each step with findings."""
    with path.open() as f:
        try:
            wf = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"::error::{path}: YAML parse error: {e}", file=sys.stderr)
            sys.exit(2)

    # yaml.safe_load returns None for empty or comment-only files.
    if not isinstance(wf, dict):
        return []

    jobs = wf.get("jobs")
    if not isinstance(jobs, dict):
        return []

    findings: list[tuple[str, str, list[str]]] = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            run_cmd = step.get("run")
            if not isinstance(run_cmd, str):
                continue
            step_name = step.get("name", f"step-{i}")
            matches = EXPRESSION_RE.findall(run_cmd)
            if matches:
                findings.append((job_name, step_name, matches))
    return findings


def main() -> int:
    """CLI entry point: audit all workflows and exit non-zero on findings.

    Walks ``--workflows`` directory (default ``.github/workflows``) for
    ``*.yml`` and ``*.yaml`` files, runs :func:`audit_workflow` on each,
    prints per-file findings to stdout, and returns 0 if clean, 1 if any
    ``${{ }}`` was found inside a ``run:`` block, or 2 on internal error.

    Use ``--list`` to run in informational mode (always exit 0 even with
    findings); useful for local checks that should not block a developer.
    """
    description = (
        __doc__ or "Audit GitHub Actions workflows for template-injection vectors."
    ).split("\n\n")[0]
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--workflows",
        default=".github/workflows",
        help="Directory containing workflow YAML files (default: .github/workflows)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List findings but always exit 0 (informational mode).",
    )
    args = parser.parse_args()

    workflows_dir = Path(args.workflows)
    if not workflows_dir.is_dir():
        print(f"::error::workflows directory not found: {workflows_dir}", file=sys.stderr)
        return 2

    total_findings = 0
    files_audited = 0
    # GitHub Actions accepts both .yml and .yaml extensions.
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    for path in sorted(workflow_files):
        files_audited += 1
        findings = audit_workflow(path)
        if findings:
            print(f"\n{path}:")
            for job, step, expressions in findings:
                print(f"  [{job}/{step}]")
                for expr in expressions:
                    print(f"    {expr}")
                    total_findings += 1
        else:
            print(f"{path}: OK")

    print(f"\n=== Audited {files_audited} workflow(s), {total_findings} finding(s) ===")

    if total_findings == 0:
        return 0
    return 0 if args.list else 1


if __name__ == "__main__":
    sys.exit(main())
