"""CLI entry point — argparse router for all gitwise subcommands."""

import argparse
import sys
import time
from pathlib import Path

from . import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitwise",
        description="CLI personal para optimizar git + Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"gitwise {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="COMANDO")

    # doctor
    p = sub.add_parser("doctor", help="verifica requisitos y entorno")
    p.add_argument("--json", action="store_true", help="output JSON")

    # setup-agents
    p = sub.add_parser(
        "setup-agents",
        help="instala skills/rules/settings en ~/.claude/ (default) o en el repo actual (--local)",
    )
    p.add_argument(
        "--local",
        action="store_true",
        help="instala en .claude/ del repo actual en lugar de ~/.claude/ global",
    )
    p.add_argument(
        "--no-skills",
        action="store_true",
        dest="no_skills",
        help="no instalar skills (solo aplica en modo global)",
    )
    p.add_argument("--dry-run", action="store_true", help="muestra acciones sin ejecutar")
    p.add_argument("--yes", "-y", action="store_true", help="no pide confirmación")
    p.add_argument("--json", action="store_true", help="output JSON")
    p.add_argument(
        "--no-symlinks",
        action="store_true",
        help="forzar fallback @AGENTS.md import (sin symlinks) — solo con --local",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="convertir warnings en errores (CI) — solo con --local",
    )
    p.add_argument(
        "--replace-claude-with-symlink",
        action="store_true",
        dest="replace_claude_with_symlink",
        help="bucket 4: reemplaza CLAUDE.md por symlink a AGENTS.md — solo con --local",
    )
    p.add_argument(
        "--frozen-time",
        action="store_true",
        dest="frozen_time",
        help="congela timestamp del snapshot — solo con --local",
    )
    p.add_argument(
        "--no-git-files",
        action="store_true",
        dest="no_git_files",
        help="no tocar .gitignore ni .gitattributes — solo con --local",
    )

    # setup [Fase 1]
    p = sub.add_parser("setup", help="aplica defaults modernos de git [Fase 1]")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument("--json", action="store_true")

    # audit [Fase 1]
    p = sub.add_parser("audit", help="diagnóstico del repositorio [Fase 1]")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--json", action="store_true")

    # summarize [Fase 1]
    p = sub.add_parser("summarize", help="status + log compacto [Fase 1]")
    p.add_argument("--json", action="store_true")
    p.add_argument("--diff", action="store_true")
    p.add_argument("--max-commits", type=int, default=10, dest="max_commits")

    # snapshot [Fase 1]
    p = sub.add_parser("snapshot", help="genera .claude/git-snapshot.md [Fase 1]")
    p.add_argument("--json", action="store_true")

    # clean [Fase 2]
    p = sub.add_parser("clean", help="limpia ramas stale y refs [Fase 2]")
    p.add_argument("--branches", action="store_true")
    p.add_argument("--refs", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument("--json", action="store_true")

    # optimize [Fase 2]
    p = sub.add_parser("optimize", help="optimiza el repositorio [Fase 2]")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument("--json", action="store_true")

    # worktree [Fase 2]
    p = sub.add_parser("worktree", help="helpers de worktree para agentes Claude [Fase 2]")
    p.add_argument("action", choices=["new", "clean"], nargs="?", metavar="new|clean")
    p.add_argument("branch", nargs="?")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")

    # diff
    p = sub.add_parser("diff", help="changed file list (git diff --name-status HEAD)")
    diff_group = p.add_mutually_exclusive_group()
    diff_group.add_argument("--staged", action="store_true", help="show staged changes only")
    diff_group.add_argument(
        "--stat", action="store_true", help="show insertions/deletions per file"
    )
    p.add_argument("--json", action="store_true", help="output JSON")

    # update
    p = sub.add_parser("update", help="actualiza gitwise (git pull en directorio de instalación)")
    p.add_argument("--dry-run", action="store_true")

    return parser


def _run_update(args: argparse.Namespace) -> int:
    from .git import run as git_run

    install_dir = Path(__file__).parent.parent
    if args.dry_run:
        print(f"would run: git pull --ff-only in {install_dir}")
        return 0
    print(f"actualizando desde {install_dir}...")
    r = git_run(["pull", "--ff-only"], cwd=install_dir, check=False)
    if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != "Already up to date.":
        print(r.stdout.strip())
    elif r.returncode != 0:
        print(r.stderr.strip() or "error al actualizar", file=sys.stderr)
    return r.returncode


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_usage(sys.stderr)
        return 1

    start = time.monotonic()

    if args.command == "doctor":
        from .doctor import run_doctor

        ret = run_doctor(as_json=args.json)

    elif args.command == "setup-agents":
        from .setup_agents import run_setup_agents

        ret = run_setup_agents(
            local=args.local,
            no_skills=args.no_skills,
            dry_run=args.dry_run,
            yes=args.yes,
            as_json=args.json,
            no_symlinks=args.no_symlinks,
            strict=args.strict,
            replace_claude_with_symlink=args.replace_claude_with_symlink,
            frozen_time=args.frozen_time,
            no_git_files=args.no_git_files,
        )

    elif args.command == "setup":
        from .setup import run_setup

        ret = run_setup(dry_run=args.dry_run, yes=args.yes, as_json=args.json)

    elif args.command == "audit":
        from .audit import run_audit

        ret = run_audit(quick=args.quick, as_json=args.json)

    elif args.command == "summarize":
        from .summarize import run_summarize

        ret = run_summarize(as_json=args.json, diff=args.diff, max_commits=args.max_commits)

    elif args.command == "snapshot":
        from .snapshot import run_snapshot

        ret = run_snapshot(as_json=args.json)

    elif args.command == "clean":
        from .clean import run_clean

        ret = run_clean(
            branches=args.branches,
            refs=args.refs,
            dry_run=args.dry_run,
            yes=args.yes,
            as_json=args.json,
        )

    elif args.command == "optimize":
        from .optimize import run_optimize

        ret = run_optimize(dry_run=args.dry_run, yes=args.yes, as_json=args.json)

    elif args.command == "worktree":
        from .worktree import run_worktree

        ret = run_worktree(
            args.action, getattr(args, "branch", None), dry_run=args.dry_run, as_json=args.json
        )

    elif args.command == "diff":
        from .diff import run_diff

        ret = run_diff(staged=args.staged, stat=args.stat, as_json=args.json)

    elif args.command == "update":
        ret = _run_update(args)

    else:
        parser.print_help()
        ret = 0

    elapsed = time.monotonic() - start
    as_json = getattr(args, "json", False)
    if not as_json and elapsed > 0.2 and args.command not in ("doctor",):
        print(f"\ncompletado en {elapsed:.1f}s")

    return ret


if __name__ == "__main__":
    sys.exit(main())
