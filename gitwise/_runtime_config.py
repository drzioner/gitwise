"""Runtime configuration: immutable settings detected from environment at import time."""

import os
import select
import shutil
import sys

if sys.platform != "win32":
    import termios
else:
    termios = None  # type: ignore[assignment,misc]
from .design import ColorDepth, ThemeTokens, build_theme

_BRIGHTNESS_THRESHOLD = 0.5
_OSC_TIMEOUT = 0.5


def _drain_fd(fd: int, timeout: float = 0.1) -> None:
    """Read and discard pending data from a file descriptor."""
    while True:
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            break
        try:
            os.read(fd, 256)
        except OSError:
            break


def _query_bg_color() -> str | None:
    """Query the terminal background color via OSC 11; returns a hex string or None."""
    if os.environ.get("NO_COLOR", "") != "":
        return None
    if os.environ.get("GITWISE_NO_COLOR", "").lower() in ("1", "true"):
        return None
    term = os.environ.get("TERM", "")
    if term.startswith(("screen", "tmux", "dumb")):
        return None
    if not sys.stdout.isatty():
        return None
    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return None
    try:
        if termios is None:
            return None
        old = termios.tcgetattr(fd)
        new = list(old)
        new[3] = new[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(fd, termios.TCSADRAIN, new)
        try:
            os.write(fd, b"\x1b]11;?\x1b\\")
            resp = _read_osc_response(fd)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        _drain_fd(fd)
        if resp is None:
            return None
        return _parse_osc_color(resp)
    except (OSError, ValueError):
        return None
    finally:
        try:
            os.close(fd)
        except OSError as e:
            if os.environ.get("GITWISE_DEBUG", "").lower() in ("1", "true"):
                sys.stderr.write(f"[gitwise debug] tty close failed: {e}\n")


def _read_osc_response(fd: int) -> str | None:
    """Read an OSC response from a tty fd, with a timeout."""
    buf = bytearray()
    osc_received = False
    while len(buf) < 50:
        ready, _, _ = select.select([fd], [], [], _OSC_TIMEOUT)
        if not ready:
            break
        try:
            ch = os.read(fd, 1)
        except OSError:
            break
        if not ch:
            break
        buf.extend(ch)
        decoded = buf.decode("ascii", errors="ignore")
        if "\x1b]" in decoded and not osc_received:
            osc_received = True
        if osc_received:
            if decoded.endswith("\x1b\\") or decoded.endswith("\x07"):
                return decoded
            if "\x1b[" in decoded[decoded.index("\x1b]") + 1 :]:
                return decoded[: decoded.index("\x1b[", decoded.index("\x1b]") + 1)]
    return None


def _parse_osc_color(resp: str) -> str | None:
    """Extract a hex color from an OSC 11 response string."""
    idx = resp.find("\x1b]")
    if idx == -1:
        return None
    after_osc = resp[idx + 2 :]
    semicolon = after_osc.find(";")
    if semicolon == -1:
        return None
    color_part = after_osc[semicolon + 1 :]
    color_part = color_part.rstrip("\x07").rstrip("\x1b\\").strip()
    for terminator in ("\x1b[", "\x1b"):
        tidx = color_part.find(terminator)
        if tidx >= 0:
            color_part = color_part[:tidx]
    if color_part.startswith("rgb:"):
        parts = color_part[4:].split("/")
        if len(parts) == 3:
            r, g, b = (
                _parse_rgb_component(parts[0]),
                _parse_rgb_component(parts[1]),
                _parse_rgb_component(parts[2]),
            )
            return f"#{r:02x}{g:02x}{b:02x}"
    elif color_part.startswith("#"):
        clean = color_part.rstrip()
        for terminator in ("\x1b[", "\x1b"):
            tidx = clean.find(terminator)
            if tidx >= 0:
                clean = clean[:tidx]
        return clean
    return None


def _parse_rgb_component(s: str) -> int:
    """Parse a single hex RGB component, normalizing values wider than 8 bits."""
    val = int(s, 16)
    if len(s) > 2:
        val = val >> (4 * (len(s) - 2))
    return val & 0xFF


def _relative_luminance(hex_color: str) -> float:
    """Compute the sRGB relative luminance of a hex color (WCG 2.4)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255

    def linearize(c: float) -> float:
        """Apply the sRGB gamma curve."""
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _is_dark_background(bg_hex: str) -> bool:
    """Return True if the background luminance is below the dark threshold."""
    return _relative_luminance(bg_hex) < _BRIGHTNESS_THRESHOLD


class RuntimeConfig:
    """Immutable runtime settings detected from the environment."""

    __slots__ = (
        "_theme_tokens",
        "color_depth",
        "debug",
        "has_bat",
        "has_delta",
        "is_tty",
        "terminal_width",
        "theme",
    )

    _theme_tokens: ThemeTokens
    color_depth: ColorDepth
    debug: bool
    has_bat: bool
    has_delta: bool
    is_tty: bool
    terminal_width: int
    theme: str

    def __init__(self) -> None:
        """Detect theme, TTY, tools, and color settings from the current environment."""
        self.has_bat = bool(shutil.which("bat"))
        self.has_delta = bool(shutil.which("delta"))
        self.theme = self._detect_theme()
        self.is_tty = sys.stdout.isatty()
        self.debug = os.environ.get("GITWISE_DEBUG", "").lower() in ("1", "true")
        self.terminal_width = self._detect_terminal_width()
        self.color_depth = self._detect_color_depth()
        self._theme_tokens = build_theme(self.theme)

    @property
    def theme_tokens(self) -> ThemeTokens:
        """Return the resolved ThemeTokens for the current theme."""
        return self._theme_tokens

    @staticmethod
    def _detect_theme() -> str:
        """Detect theme preference from env vars, OSC 11 query, or COLORFGBG."""
        explicit = os.environ.get("GITWISE_THEME", "").lower()
        if explicit in ("dark", "light"):
            return explicit

        cli_theme = os.environ.get("CLITHEME", "").split(":")[0].lower()
        if cli_theme in ("dark", "light"):
            return cli_theme

        bg_hex = _query_bg_color()
        if bg_hex is not None:
            return "dark" if _is_dark_background(bg_hex) else "light"

        colorfgbg = os.environ.get("COLORFGBG", "")
        if colorfgbg:
            parts = colorfgbg.split(";")
            if len(parts) >= 2:
                bg = parts[-1]
                if bg in ("0", "8", "16"):
                    return "dark"
                return "light"

        fg_bg = os.environ.get("FG_BG", "")
        if fg_bg:
            parts = fg_bg.split(";")
            if len(parts) >= 2:
                bg = parts[-1]
                if bg in ("0", "8", "16"):
                    return "dark"
                return "light"

        return "dark"

    @staticmethod
    def _detect_terminal_width() -> int:
        """Return terminal width from GITWISE_WIDTH or shutil detection."""
        from .design import MAX_WIDTH, MIN_WIDTH, detect_terminal_width

        env_width = os.environ.get("GITWISE_WIDTH", "")
        if env_width.isdigit():
            w = int(env_width)
            return max(MIN_WIDTH, min(w, MAX_WIDTH))
        return detect_terminal_width()

    @staticmethod
    def _detect_color_depth() -> ColorDepth:
        """Delegate color-depth detection to design.detect_color_depth."""
        from .design import detect_color_depth

        return detect_color_depth()


_runtime_config: RuntimeConfig | None = None


def get_runtime_config() -> RuntimeConfig:
    """Return the module-level RuntimeConfig singleton, creating it on first call."""
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = RuntimeConfig()
    return _runtime_config


def reset_runtime_config() -> None:
    """Clear the cached RuntimeConfig so it is re-detected on next access."""
    global _runtime_config
    _runtime_config = None
