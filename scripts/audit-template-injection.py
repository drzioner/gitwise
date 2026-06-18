#!/usr/bin/env python3
"""Audit GitHub Actions workflows for two classes of supply-chain risk.

1. Template-injection vectors: any ``${{ ... }}`` expression used inside a
   ``run:`` block. Expressions in ``run:`` blocks are interpolated by the
   workflow runner into the shell script, which means attacker-controlled
   values (workflow_dispatch inputs, issue titles, PR bodies, head_branch
   from untrusted workflow_run triggers) can execute arbitrary shell code.
   Expressions assigned to ``env:``, ``with:``, or ``if:`` are safe — they
   are treated as string literals by the runner.

2. Unpinned ``uses:`` references: any third-party action referenced by tag
   or branch instead of a commit SHA. Tags and branches are mutable: an
   attacker who compromises the action's repo can move the tag to a malicious
   commit, and every workflow consuming it would silently run the new code.
   SHA-pinned references are immutable. Local actions (``./...``) and
   Docker actions (``docker://...``) are exempt.

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
# Matches SHA-1 (40 hex) or SHA-256 (64 hex); case-insensitive because Git
# SHAs are not canonically lowercase in the wild.
SHA_RE = re.compile(r"^[a-f0-9]{40}$|^[a-f0-9]{64}$", re.IGNORECASE)


def audit_workflow(path: Path) -> list[tuple[str, str, list[str]]]:
    """Return [(job_name, step_name, [expressions])] for each step with template-injection findings."""
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


def audit_uses_pinning(path: Path) -> list[tuple[str, str, str]]:
    """Return [(context, uses_spec, reason)] for each ``uses:`` without SHA pin.

    The context is "job_name" for reusable-workflow ``uses:`` at job level, or
    "job_name/step_name" for step-level ``uses:``. Uses the parsed YAML AST
    rather than regex-on-text to avoid false positives from comments or
    multi-line strings containing the substring ``uses:``.

    Exemptions:
        - Local actions: ``uses: ./path/to/action``
        - Docker actions: ``uses: docker://image:tag``
    """
    with path.open() as f:
        try:
            wf = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"::error::{path}: YAML parse error: {e}", file=sys.stderr)
            sys.exit(2)

    if not isinstance(wf, dict):
        return []

    jobs = wf.get("jobs")
    if not isinstance(jobs, dict):
        return []

    findings: list[tuple[str, str, str]] = []

    def classify(spec: str) -> str | None:
        """Return a reason string if ``spec`` is unpinned, else None."""
        spec = spec.strip()
        # Local composite actions look like `./path` with no @ref. These are
        # in-tree source files and don't need pinning.
        # Local *reusable workflows* look like `./path@<ref>` and DO need a
        # SHA pin — refs are mutable in that case.
        if spec.startswith("./") and "@" not in spec:
            return None
        # Docker actions (container jobs/steps) are immutable by digest.
        if spec.startswith("docker://"):
            return None
        if "@" not in spec:
            return "no @ref (uses: without ref is invalid)"
        _, _, ref = spec.rpartition("@")
        if SHA_RE.match(ref):
            return None
        if ref in {"main", "master", "trunk"}:
            return f"ref '{ref}' is a branch (mutable)"
        return f"ref '{ref}' is a tag (mutable); pin to SHA and add '# <tag>' comment"

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue

        # Job-level uses (reusable workflows).
        job_uses = job.get("uses")
        if isinstance(job_uses, str):
            reason = classify(job_uses)
            if reason:
                findings.append((job_name, job_uses.strip(), reason))

        # Step-level uses.
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            step_uses = step.get("uses")
            if not isinstance(step_uses, str):
                continue
            reason = classify(step_uses)
            if reason:
                step_name = step.get("name", f"step-{i}")
                context = f"{job_name}/{step_name}"
                findings.append((context, step_uses.strip(), reason))
    return findings


def main() -> int:
    """CLI entry point: audit all workflows and exit non-zero on findings.

    Walks ``--workflows`` directory (default ``.github/workflows``) for
    ``*.yml`` and ``*.yaml`` files, runs :func:`audit_workflow` (template
    injection) and :func:`audit_uses_pinning` (unpinned uses) on each,
    prints per-file findings to stdout, and returns 0 if clean, 1 if any
    finding was emitted, or 2 on internal error.

    Use ``--list`` to run in informational mode (always exit 0 even with
    findings); useful for local checks that should not block a developer.
    """
    description = (__doc__ or "Audit GitHub Actions workflows for supply-chain risk.").split(
        "\n\n"
    )[0]
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
        injection_findings = audit_workflow(path)
        pinning_findings = audit_uses_pinning(path)
        if injection_findings or pinning_findings:
            print(f"\n{path}:")
            for job, step, expressions in injection_findings:
                print(f"  [{job}/{step}] template-injection:")
                for expr in expressions:
                    print(f"    {expr}")
                    total_findings += 1
            for line_no, spec, reason in pinning_findings:
                print(f"  [{line_no}] unpinned uses: {spec}")
                print(f"    reason: {reason}")
                total_findings += 1
        else:
            print(f"{path}: OK")

    print(f"\n=== Audited {files_audited} workflow(s), {total_findings} finding(s) ===")

    if total_findings == 0:
        return 0
    return 0 if args.list else 1


if __name__ == "__main__":
    sys.exit(main())
