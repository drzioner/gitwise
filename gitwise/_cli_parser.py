"""Argparse parser builder for all gitwise subcommands."""

import argparse

from gitwise import __version__
from gitwise.design import GitwiseRichHelpFormatter
from gitwise.i18n import t


def _root_help_epilog() -> str:
    """Return the localized environment-variable epilog for root help."""
    return t("help_root_environment_epilog")


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argparse parser with all subcommands registered."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--lang",
        choices=["es", "en"],
        default=None,
        help="output language (default: auto-detect from locale)",
    )
    parent.add_argument(
        "--theme",
        choices=["dark", "light", "auto"],
        default=None,
        help="color theme: dark, light, or auto-detect (default: auto)",
    )
    parent.add_argument("--json", action="store_true", help="output JSON")
    parent.add_argument(
        "--json-pretty",
        "--pretty",
        dest="json_pretty",
        action="store_true",
        help="pretty-print JSON output",
    )

    parser = argparse.ArgumentParser(
        prog="gitwise",
        description="CLI for optimizing git workflows and coding agents integration",
        formatter_class=GitwiseRichHelpFormatter,
        epilog=_root_help_epilog(),
        parents=[parent],
    )
    parser.add_argument("--version", action="version", version=f"gitwise {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("doctor", help="check requirements and environment", parents=[parent])

    p = sub.add_parser(
        "setup-agents",
        help="install canonical agents layout + optional providers globally or locally",
        parents=[parent],
    )
    p.add_argument(
        "--local",
        action="store_true",
        help="install into current repo instead of global home",
    )
    p.add_argument(
        "--no-skills",
        action="store_true",
        dest="no_skills",
        help="skip skills installation (global mode only)",
    )
    p.add_argument("--dry-run", action="store_true", help="show actions without executing")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    p.add_argument(
        "--no-symlinks",
        action="store_true",
        help="force @AGENTS.md import fallback (no symlinks) — --local only",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as errors (CI) — --local only",
    )
    p.add_argument(
        "--replace-claude-with-symlink",
        action="store_true",
        dest="replace_claude_with_symlink",
        help="bucket 4: replace CLAUDE.md with symlink to AGENTS.md — --local only",
    )
    p.add_argument(
        "--migrate-legacy-claude",
        action="store_true",
        dest="migrate_legacy_claude",
        help="migrate legacy Claude-only layout to canonical AGENTS/.agents — --local only",
    )
    p.add_argument(
        "--frozen-time",
        action="store_true",
        dest="frozen_time",
        help="freeze snapshot timestamp — --local only",
    )
    p.add_argument(
        "--no-git-files",
        action="store_true",
        dest="no_git_files",
        help="don't touch .gitignore or .gitattributes — --local only",
    )
    p.add_argument(
        "--providers",
        nargs="*",
        default=None,
        dest="providers",
        help="install config for coding providers (comma-separated: claude,cursor or multiple: --providers claude cursor)",
    )
    p.add_argument(
        "--adapters",
        nargs="*",
        default=None,
        dest="adapters",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--list-providers",
        action="store_true",
        dest="list_providers",
        help="list available providers and exit",
    )
    p.add_argument(
        "--list-adapters",
        action="store_true",
        dest="list_adapters",
        help=argparse.SUPPRESS,
    )

    p = sub.add_parser("setup", help="apply modern git defaults", parents=[parent])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")
    p.add_argument(
        "--hooks-mode",
        choices=["preserve", "native", "legacy", "skip"],
        default="preserve",
        help="hooks strategy: preserve (default), native, legacy, or skip",
    )

    p = sub.add_parser("audit", help="repository diagnostics", parents=[parent])
    p.add_argument("--quick", action="store_true")

    p = sub.add_parser("summarize", help="compact status + log", parents=[parent])
    p.add_argument("--diff", action="store_true")
    p.add_argument("--max-commits", type=int, default=10, dest="max_commits")

    p = sub.add_parser("snapshot", help="generate .claude/git-snapshot.md", parents=[parent])

    p = sub.add_parser(
        "clean",
        help="clean up stale branches and refs",
        aliases=["branch-clean"],
        parents=[parent],
    )
    p.add_argument("--branches", action="store_true")
    p.add_argument("--refs", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")

    p = sub.add_parser("optimize", help="optimize the repository", parents=[parent])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", "-y", action="store_true")

    p = sub.add_parser("worktree", help="worktree helpers for Claude agents", parents=[parent])
    p.add_argument(
        "action",
        choices=["new", "clean", "list", "remove"],
        nargs="?",
        metavar="new|clean|list|remove",
    )
    p.add_argument("branch", nargs="?")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--force", action="store_true", help="force removal even with modifications (remove only)"
    )

    p = sub.add_parser(
        "diff",
        help="changed files with diffstat (default), or patch view",
        parents=[parent],
    )
    diff_group = p.add_mutually_exclusive_group()
    diff_group.add_argument("--staged", action="store_true", help="show staged changes only")
    diff_group.add_argument("--name-only", action="store_true", help="show only file names")
    diff_group.add_argument(
        "--full", "--patch", action="store_true", help="show full patch with delta integration"
    )
    diff_group.add_argument(
        "--summary",
        action="store_true",
        help="compact summary: additions/deletions per file, no patch",
    )
    p.add_argument("--stat", action="store_true", help="show diffstat (default behavior)")
    p.add_argument(
        "--scan-secrets",
        action="store_true",
        help="scan the diff for leaked credentials (advisory, opt-in)",
    )
    p.add_argument(
        "--json-lines",
        action="store_true",
        dest="json_lines",
        help="stream one JSON envelope per changed file (NDJSON)",
    )
    p.add_argument(
        "refspec",
        nargs="?",
        default=None,
        help="commit, branch, or range to diff (e.g. HEAD~3, main..feat, main...feat)",
    )
    p.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="limit to paths (use -- to separate from refspec)",
    )
    p.add_argument(
        "--git-arg",
        action="append",
        dest="git_args",
        default=None,
        metavar="OPT",
        help="forward an extra option to the underlying git diff (repeatable; "
        "code-exec/write/redirect options like --output/-c/--git-dir are refused)",
    )

    p = sub.add_parser("log", help="pretty git log with filters", parents=[parent])
    p.add_argument("--oneline", action="store_true", help="one line per commit")
    p.add_argument("--graph", action="store_true", help="show branch topology graph")
    p.add_argument("--author", type=str, default=None, help="filter by author")
    p.add_argument("--grep", type=str, default=None, help="filter by message pattern")
    p.add_argument("--since", type=str, default=None, help="show commits since date")
    p.add_argument("--until", type=str, default=None, help="show commits until date")
    p.add_argument("--file", type=str, default=None, help="show commits for file")
    p.add_argument("--max-count", type=int, default=20, dest="max_count", help="max commits")
    p.add_argument(
        "--json-lines",
        action="store_true",
        dest="json_lines",
        help="stream one JSON envelope per commit (NDJSON; implies JSON mode)",
    )
    p.add_argument(
        "--git-arg",
        action="append",
        dest="git_args",
        default=None,
        metavar="OPT",
        help="forward an extra option to the underlying git log (repeatable; "
        "code-exec/write/redirect options are refused)",
    )

    p = sub.add_parser("show", help="commit inspector", parents=[parent])
    p.add_argument("ref", nargs="?", default="HEAD", help="commit ref (default: HEAD)")
    p.add_argument("--stat", action="store_true", help="show diffstat")
    p.add_argument(
        "--git-arg",
        action="append",
        dest="git_args",
        default=None,
        metavar="OPT",
        help="forward an extra option to the underlying git show (repeatable; "
        "code-exec/write/redirect options are refused)",
    )

    p = sub.add_parser("commit", help="smart conventional commit", parents=[parent])
    p.add_argument("-m", "--message", type=str, default=None, help="commit message")
    p.add_argument("--type", type=str, default=None, help="commit type (feat/fix/etc)")
    p.add_argument("--scope", type=str, default=None, help="commit scope")
    p.add_argument("--breaking", action="store_true", help="breaking change (!)")
    p.add_argument("--amend", action="store_true", help="amend last commit")
    p.add_argument("--dry-run", action="store_true", help="show without committing")
    p.add_argument(
        "--allow-secret",
        action="store_true",
        help="proceed past a high-severity secret finding (with confirmation)",
    )

    p = sub.add_parser("branches", help="branch intelligence dashboard", parents=[parent])
    p.add_argument("--stale", action="store_true", help="show stale [gone] branches only")
    p.add_argument("--remote", action="store_true", help="show remote branches")
    p.add_argument(
        "--sort",
        type=str,
        default="refname",
        help="sort field: refname, committerdate, -committerdate",
    )
    p.add_argument(
        "--git-arg",
        action="append",
        dest="git_args",
        default=None,
        metavar="OPT",
        help="forward an extra option to the underlying git for-each-ref (repeatable; "
        "code-exec/write/redirect options are refused)",
    )

    p = sub.add_parser("sync", help="remote fetch, safe pull/push", parents=[parent])
    p.add_argument("--pull", action="store_true", help="pull --ff-only after fetch")
    p.add_argument("--push", action="store_true", help="push unpushed commits")
    p.add_argument("--remote", type=str, default=None, help="specific remote (default: all)")
    p.add_argument("--dry-run", action="store_true", help="show planned actions")

    p = sub.add_parser("pr", help="GitHub PR wrapper (requires gh)", parents=[parent])
    p.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=["list", "checks", "view", "comments"],
        help="pr action",
    )
    p.add_argument(
        "selector",
        nargs="?",
        default=None,
        help="PR number/url/branch (default: current branch PR)",
    )

    p = sub.add_parser("undo", help="reflog-based undo", parents=[parent])
    p.add_argument("ref", nargs="?", default=None, help="target ref (default: HEAD~1)")
    p.add_argument("--soft", action="store_true", help="soft reset (keep working tree)")
    p.add_argument("--steps", type=int, default=1, help="number of steps back")
    p.add_argument("--dry-run", action="store_true", help="show without resetting")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation for --hard")

    p = sub.add_parser("context", help="enriched repo snapshot for LLMs", parents=[parent])

    p = sub.add_parser("health", help="repo health score (0-100)", parents=[parent])

    p = sub.add_parser(
        "stash",
        help="manage stashes (list/show/pop/drop/clear)",
        parents=[parent],
    )
    p.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=["list", "show", "pop", "apply", "push", "drop", "clear", "clean"],
    )
    p.add_argument("--index", type=int, default=0, help="stash index (default: 0)")
    p.add_argument("--dry-run", action="store_true", help="dry run (clear only)")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    p.add_argument("--patch", action="store_true", help="show full patch (show only)")
    p.add_argument("-m", "--message", type=str, default=None, help="stash message (push only)")
    p.add_argument(
        "-u",
        "--include-untracked",
        action="store_true",
        help="include untracked files (push only)",
    )
    p.add_argument(
        "--keep-index", action="store_true", help="keep staged changes in the index (push only)"
    )
    p.add_argument(
        "paths", nargs="*", default=None, help="paths to stash (push only, use -- to separate)"
    )

    p = sub.add_parser("tag", help="semver-aware tag management", parents=[parent])
    p.add_argument(
        "action", nargs="?", default="list", choices=["list", "latest", "create", "delete"]
    )
    p.add_argument("name", nargs="?", help="tag name (for create/delete)")
    p.add_argument("--bump", choices=["major", "minor", "patch"], help="bump semver part")
    p.add_argument("-m", "--message", type=str, help="annotated tag message")
    p.add_argument("--dry-run", action="store_true", help="show without executing")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")

    p = sub.add_parser("merge", help="merge/rebase with pre-flight checks", parents=[parent])
    p.add_argument(
        "branch", nargs="?", help="branch to merge/rebase from (omit with --abort/--continue)"
    )
    p.add_argument("--rebase", action="store_true", help="rebase instead of merge")
    p.add_argument("--no-ff", action="store_true", help="force no-fast-forward")
    p.add_argument("--dry-run", action="store_true", help="show checks without merging")
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    p.add_argument("--abort", action="store_true", help="abort an in-progress merge or rebase")
    p.add_argument(
        "--continue",
        dest="continue_merge",
        action="store_true",
        help="continue an in-progress merge or rebase after resolving conflicts",
    )

    p = sub.add_parser(
        "conflicts", help="conflict detection and resolution helper", parents=[parent]
    )
    strategy = p.add_mutually_exclusive_group()
    strategy.add_argument("--ours", action="store_true", help="resolve all conflicts using ours")
    strategy.add_argument(
        "--theirs", action="store_true", help="resolve all conflicts using theirs"
    )
    strategy.add_argument(
        "--union",
        action="store_true",
        help="resolve all conflicts keeping both sides (union)",
    )
    p.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="limit resolution to these files (use -- to separate from flags)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be resolved without touching the working tree",
    )

    p = sub.add_parser(
        "suggest",
        help="suggest commit message from staged diff",
        aliases=["commit-suggest"],
        parents=[parent],
    )

    p = sub.add_parser(
        "pick", help="cherry-pick or revert commits", aliases=["cherry-pick"], parents=[parent]
    )
    p.add_argument("refs", nargs="*", help="commit refs to pick/revert")
    p.add_argument("--revert", action="store_true", help="revert instead of cherry-pick")
    p.add_argument(
        "--continue", dest="continue_", action="store_true", help="continue after conflict"
    )
    p.add_argument("--abort", action="store_true", help="abort in-progress pick/revert")
    p.add_argument("--dry-run", action="store_true", help="show without executing")

    p = sub.add_parser(
        "update", help="update gitwise (git pull in install directory)", parents=[parent]
    )
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("status", help="enhanced git status for humans and AI", parents=[parent])

    p = sub.add_parser(
        "commands",
        help="list available subcommands and metadata",
        parents=[parent],
    )

    p = sub.add_parser(
        "schema",
        help="print JSON schema for a command",
        parents=[parent],
    )
    p.add_argument("name", help="command name to inspect")
    p.add_argument(
        "--version",
        default="v1",
        help="schema catalog version (default: v1)",
    )
    p.add_argument(
        "--output",
        action="store_true",
        help="show the command's --json output schema (default: input schema)",
    )

    p = sub.add_parser(
        "completions",
        help="print shell completion script (bash/zsh/fish/powershell)",
        parents=[parent],
    )
    p.add_argument(
        "shell",
        choices=["bash", "zsh", "fish", "powershell"],
        default="bash",
        nargs="?",
        help="target shell for completion script",
    )
    p.add_argument(
        "--prog",
        default="gitwise",
        help="command name used inside completion script (default: gitwise)",
    )

    return parser
