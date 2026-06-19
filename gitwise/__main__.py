"""CLI entry point — argparse router for all gitwise subcommands."""

import sys
import time

from ._cli_dispatch import DISPATCH
from ._cli_introspection import extract_command_token, help_payload
from ._cli_parser import build_parser
from .i18n import t
from .output import print_dim, print_json, set_json_pretty


def _is_log_json_enabled() -> bool:
    import os

    return os.environ.get("GITWISE_LOG_JSON", "").lower() in ("1", "true")


def _should_show_rich_traceback() -> bool:
    return (not _is_log_json_enabled()) and sys.stderr.isatty()


def _install_rich_traceback() -> None:
    if not _should_show_rich_traceback():
        return
    try:
        import importlib

        rich_traceback_install = importlib.import_module("rich.traceback").install
        rich_traceback_install(show_locals=False)
    except ImportError:
        return


def _ensure_utf8_stdio() -> None:
    """Force stdout/stderr to UTF-8.

    Windows defaults to a system codepage (often cp1252) for the Python
    embedded in console apps. That codepage cannot encode characters like
    U+2713 (✓) used throughout gitwise's status output, causing
    UnicodeEncodeError when the user is not running through a wrapper that
    sets PYTHONIOENCODING. macOS/Linux are already UTF-8 by default, so
    this reconfigure is a no-op there.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        # TextIOWrapper.reconfigure exists on Python 3.7+; guard just in case
        # the stream has been replaced with something non-standard.
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (TypeError, ValueError):
                # Stream does not accept these kwargs or is closed; ignore.
                pass


def main() -> int:
    import os

    from ._runtime_config import reset_runtime_config
    from .i18n import set_locale

    _ensure_utf8_stdio()
    _install_rich_traceback()

    parser = build_parser()
    raw_argv = sys.argv[1:]
    wants_json_pretty = "--json-pretty" in raw_argv or "--pretty" in raw_argv
    if wants_json_pretty:
        set_json_pretty(True)

    wants_json_help = ("--json" in raw_argv or wants_json_pretty) and (
        "--help" in raw_argv or "-h" in raw_argv
    )
    if wants_json_help:
        command = extract_command_token(raw_argv)
        print_json(help_payload(parser, command))
        return 0

    args = parser.parse_args()
    if args.json_pretty:
        args.json = True

    if args.command is None:
        if args.json:
            print_json(
                {
                    **help_payload(parser),
                    "ok": False,
                    "error": "missing_command",
                }
            )
            return 1
        parser.print_usage(sys.stderr)
        return 1

    if args.theme and args.theme != "auto":
        os.environ["GITWISE_THEME"] = args.theme
        reset_runtime_config()

    set_json_pretty(args.json_pretty)

    if args.lang:
        set_locale(args.lang)

    start = time.monotonic()

    handler = DISPATCH.get(args.command)
    if handler is not None:
        try:
            ret = handler(args)
        except KeyboardInterrupt:
            ret = 130
        except SystemExit:
            raise
        except Exception:
            if _should_show_rich_traceback():
                raise
            # No Rich traceback available (CI / non-tty / LOG_JSON mode).
            # Still emit the raw traceback to stderr so CI logs are
            # diagnostic. Otherwise the user only sees "unexpected error"
            # and has no way to identify the root cause.
            import traceback as _traceback

            _traceback.print_exc()
            from .output import error as _error

            _error(t("unexpected_error"))
            ret = 1
    else:
        parser.print_help(sys.stderr)
        ret = 1

    elapsed = time.monotonic() - start
    as_json = getattr(args, "json", False)
    if not as_json and elapsed > 0.2 and args.command not in ("doctor",):
        print_dim(t("completed_in", elapsed=f"{elapsed:.1f}"))

    return ret


if __name__ == "__main__":
    sys.exit(main())
