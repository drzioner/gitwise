"""Tests for gitwise.design — design system tokens, themes, and utilities."""

import argparse

from gitwise.design import (
    ACCENT_HEX,
    ANSI_BOLD,
    ANSI_RESET,
    BRACKET_LEFT,
    BRACKET_RIGHT,
    DARK_ACCENT,
    DARK_BG,
    DARK_ERROR,
    DARK_FG,
    DARK_SUCCESS,
    DEFAULT_WIDTH,
    LIGHT_ACCENT,
    LIGHT_BG,
    LIGHT_ERROR,
    LIGHT_FG,
    LIGHT_SUCCESS,
    MAX_WIDTH,
    MIN_WIDTH,
    ThemeTokens,
    build_theme,
    detect_color_depth,
    detect_terminal_width,
    hex_to_ansi_fg,
    pad_left,
    pad_right,
    strip_ansi,
    truncate,
    visible_length,
)


class TestColorConstants:
    def test_hex_constants_are_valid(self):
        for name, val in [
            ("DARK_FG", DARK_FG),
            ("DARK_BG", DARK_BG),
            ("DARK_ACCENT", DARK_ACCENT),
            ("DARK_SUCCESS", DARK_SUCCESS),
            ("DARK_ERROR", DARK_ERROR),
            ("LIGHT_FG", LIGHT_FG),
            ("LIGHT_BG", LIGHT_BG),
            ("LIGHT_ACCENT", LIGHT_ACCENT),
            ("LIGHT_SUCCESS", LIGHT_SUCCESS),
            ("LIGHT_ERROR", LIGHT_ERROR),
            ("ACCENT", ACCENT_HEX),
        ]:
            assert val.startswith("#") and len(val) == 7, f"{name} hex invalid: {val}"

    def test_dark_and_light_have_different_fg(self):
        assert DARK_FG != LIGHT_FG

    def test_dark_and_light_have_different_accent(self):
        assert DARK_ACCENT != LIGHT_ACCENT


class TestHexToAnsi:
    def test_converts_hex_to_ansi_fg(self):
        result = hex_to_ansi_fg("#FF0000")
        assert result == "\033[38;2;255;0;0m"

    def test_converts_dark_fg(self):
        result = hex_to_ansi_fg(DARK_FG)
        assert result.startswith("\033[38;2;")
        assert result.endswith("m")

    def test_ansi_bold_and_reset_exist(self):
        assert ANSI_BOLD == "\033[1m"
        assert ANSI_RESET == "\033[0m"


class TestDetectColorDepth:
    def test_no_color_env_returns_16color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.delenv("COLORTERM", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        assert detect_color_depth() == "16color"

    def test_gitwise_no_color_returns_16color(self, monkeypatch):
        monkeypatch.setenv("GITWISE_NO_COLOR", "1")
        monkeypatch.delenv("COLORTERM", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        assert detect_color_depth() == "16color"

    def test_truecolor_detection(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("GITWISE_NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setenv("TERM", "xterm-256color")
        assert detect_color_depth() == "truecolor"

    def test_256color_fallback(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("GITWISE_NO_COLOR", raising=False)
        monkeypatch.delenv("COLORTERM", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        assert detect_color_depth() == "256color"

    def test_16color_fallback(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("GITWISE_NO_COLOR", raising=False)
        monkeypatch.delenv("COLORTERM", raising=False)
        monkeypatch.setenv("TERM", "vt100")
        assert detect_color_depth() == "16color"


class TestDetectTerminalWidth:
    def test_returns_int_within_bounds(self):
        w = detect_terminal_width()
        assert isinstance(w, int)
        assert MIN_WIDTH <= w <= MAX_WIDTH

    def test_env_width_not_in_design_module(self, monkeypatch):
        monkeypatch.setenv("COLUMNS", "200")
        w = detect_terminal_width()
        assert MIN_WIDTH <= w <= MAX_WIDTH


class TestBuildTheme:
    def test_dark_theme_returns_tokens(self):
        tokens = build_theme("dark")
        assert isinstance(tokens, ThemeTokens)

    def test_light_theme_returns_tokens(self):
        tokens = build_theme("light")
        assert isinstance(tokens, ThemeTokens)

    def test_dark_fg_differs_from_light(self):
        dark = build_theme("dark")
        light = build_theme("light")
        assert dark.fg != light.fg

    def test_accent_exists_in_both_themes(self):
        dark = build_theme("dark")
        light = build_theme("light")
        assert dark.accent != ""
        assert light.accent != ""
        assert dark.success != light.success

    def test_success_and_error_tokens_exist(self):
        tokens = build_theme("dark")
        assert tokens.success
        assert tokens.error

    def test_invalid_theme_falls_back_to_dark(self):
        tokens = build_theme("invalid")
        dark = build_theme("dark")
        assert tokens.fg == dark.fg

    def test_all_tokens_are_hex_strings(self):
        for theme_name in ("dark", "light"):
            tokens = build_theme(theme_name)
            assert tokens.fg.startswith("#")
            assert tokens.accent.startswith("#")
            assert tokens.success.startswith("#")
            assert tokens.error.startswith("#")


class TestThemeTokens:
    def test_slots(self):
        tokens = build_theme("dark")
        for attr in (
            "accent",
            "bg",
            "brand",
            "dim",
            "error",
            "fg",
            "secondary",
            "success",
            "warning",
        ):
            assert hasattr(tokens, attr)

    def test_fg_is_hex(self):
        tokens = build_theme("dark")
        assert tokens.fg.startswith("#")
        assert len(tokens.fg) == 7

    def test_dim_fallback_to_secondary(self):
        tokens = ThemeTokens(
            fg="#fff", bg="#000", secondary="#888", accent="#f80", success="#0f0", error="#f00"
        )
        assert tokens.dim == ""
        tokens2 = ThemeTokens(
            fg="#fff",
            bg="#000",
            secondary="#888",
            accent="#f80",
            success="#0f0",
            error="#f00",
            dim="#666",
        )
        assert tokens2.dim == "#666"


class TestTruncate:
    def test_short_text_unchanged(self):
        assert truncate("hello", 10) == "hello"

    def test_exact_width_unchanged(self):
        assert truncate("hello", 5) == "hello"

    def test_long_text_truncated(self):
        result = truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_very_small_width(self):
        result = truncate("hello", 2)
        assert result == ".."

    def test_custom_ellipsis(self):
        result = truncate("hello world", 9, ellipsis="..")
        assert result == "hello w.."
        assert len(result) == 9

    def test_width_zero(self):
        assert truncate("hello", 0) == ""

    def test_width_one(self):
        assert truncate("hello", 1) == "."


class TestPadding:
    def test_pad_right(self):
        assert pad_right("ab", 5) == "ab   "

    def test_pad_right_exact(self):
        assert pad_right("abc", 3) == "abc"

    def test_pad_right_over(self):
        result = pad_right("abcde", 3)
        assert visible_length(result) == 5

    def test_pad_left_over(self):
        result = pad_left("abcde", 3)
        assert visible_length(result) == 5

    def test_pad_right_with_ansi(self):
        colored = "\033[32mOK\033[0m"
        result = pad_right(colored, 10)
        assert visible_length(result) == 10

    def test_pad_left_with_ansi(self):
        colored = "\033[32mOK\033[0m"
        result = pad_left(colored, 10)
        assert visible_length(result) == 10


class TestStripAnsi:
    def test_plain_text(self):
        assert strip_ansi("hello") == "hello"

    def test_fg_color(self):
        assert strip_ansi("\033[32mgreen\033[0m") == "green"

    def test_truecolor(self):
        assert strip_ansi("\033[38;2;230;145;56morange\033[0m") == "orange"

    def test_256color(self):
        assert strip_ansi("\033[38;5;214mtext\033[0m") == "text"

    def test_bold(self):
        assert strip_ansi("\033[1mbold\033[0m") == "bold"

    def test_multiple_codes(self):
        assert strip_ansi("\033[1m\033[32mbold green\033[0m") == "bold green"

    def test_empty_string(self):
        assert strip_ansi("") == ""

    def test_non_sgr_csi_clear_screen(self):
        assert strip_ansi("\033[2Jhello") == "hello"

    def test_non_sgr_csi_cursor_up(self):
        assert strip_ansi("\033[Atext") == "text"

    def test_csi_incomplete_at_end(self):
        assert strip_ansi("text\033[") == "text"


class TestVisibleLength:
    def test_plain_text(self):
        assert visible_length("hello") == 5

    def test_with_ansi(self):
        assert visible_length("\033[32mgreen\033[0m") == 5

    def test_with_truecolor(self):
        code = "\033[38;2;230;145;56m"
        assert visible_length(f"{code}abc{ANSI_RESET}") == 3

    def test_empty(self):
        assert visible_length("") == 0


class TestLayoutConstants:
    def test_min_width(self):
        assert MIN_WIDTH == 80

    def test_max_width(self):
        assert MAX_WIDTH == 120

    def test_default_width(self):
        assert DEFAULT_WIDTH == 100

    def test_bracket_chars(self):
        assert BRACKET_LEFT == "["
        assert BRACKET_RIGHT == "]"


class TestThemeDetection:
    def test_gitwise_theme_dark_override(self, monkeypatch):
        monkeypatch.setenv("GITWISE_THEME", "dark")
        monkeypatch.delenv("CLITHEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "dark"

    def test_gitwise_theme_light_override(self, monkeypatch):
        monkeypatch.setenv("GITWISE_THEME", "light")
        monkeypatch.delenv("CLITHEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "light"

    def test_clitheme_dark(self, monkeypatch):
        monkeypatch.delenv("GITWISE_THEME", raising=False)
        monkeypatch.setenv("CLITHEME", "dark")
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "dark"

    def test_clitheme_light_with_modifier(self, monkeypatch):
        monkeypatch.delenv("GITWISE_THEME", raising=False)
        monkeypatch.setenv("CLITHEME", "light:high-contrast")
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "light"

    def test_colorfgbg_dark_background(self, monkeypatch):
        monkeypatch.delenv("GITWISE_THEME", raising=False)
        monkeypatch.delenv("CLITHEME", raising=False)
        monkeypatch.setenv("COLORFGBG", "15;0")
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "dark"

    def test_colorfgbg_light_background(self, monkeypatch):
        monkeypatch.delenv("GITWISE_THEME", raising=False)
        monkeypatch.delenv("CLITHEME", raising=False)
        monkeypatch.setenv("COLORFGBG", "0;15")
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "light"

    def test_fgbg_dark(self, monkeypatch):
        monkeypatch.delenv("GITWISE_THEME", raising=False)
        monkeypatch.delenv("CLITHEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.setenv("FG_BG", "15;0")
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "dark"

    def test_no_env_defaults_to_dark(self, monkeypatch):
        monkeypatch.delenv("GITWISE_THEME", raising=False)
        monkeypatch.delenv("CLITHEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "dark"

    def test_gitwise_theme_takes_priority_over_clitheme(self, monkeypatch):
        monkeypatch.setenv("GITWISE_THEME", "light")
        monkeypatch.setenv("CLITHEME", "dark")
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "light"

    def test_invalid_gitwise_theme_ignored(self, monkeypatch):
        monkeypatch.setenv("GITWISE_THEME", "blue")
        monkeypatch.delenv("CLITHEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("FG_BG", raising=False)
        from gitwise._runtime_config import RuntimeConfig

        cfg = RuntimeConfig()
        assert cfg.theme == "dark"

    def test_both_themes_have_explicit_fg(self):
        for theme_name in ("dark", "light"):
            tokens = build_theme(theme_name)
            assert tokens.fg != ""
            assert tokens.fg.startswith("#")


class TestOsc11Detection:
    def test_query_bg_color_returns_none_non_tty(self):
        from gitwise._runtime_config import _query_bg_color

        assert _query_bg_color() is None

    def test_query_bg_color_skips_screen(self, monkeypatch):
        monkeypatch.setenv("TERM", "screen-256color")
        from gitwise._runtime_config import _query_bg_color

        assert _query_bg_color() is None

    def test_query_bg_color_skips_tmux(self, monkeypatch):
        monkeypatch.setenv("TERM", "tmux-256color")
        from gitwise._runtime_config import _query_bg_color

        assert _query_bg_color() is None

    def test_relative_luminance_white(self):
        from gitwise._runtime_config import _relative_luminance

        assert _relative_luminance("#ffffff") == 1.0

    def test_relative_luminance_black(self):
        from gitwise._runtime_config import _relative_luminance

        assert _relative_luminance("#000000") == 0.0

    def test_relative_luminance_mid_gray(self):
        from gitwise._runtime_config import _relative_luminance

        lum = _relative_luminance("#808080")
        assert 0.2 < lum < 0.3

    def test_is_dark_background_true_for_black(self):
        from gitwise._runtime_config import _is_dark_background

        assert _is_dark_background("#000000") is True

    def test_is_dark_background_false_for_white(self):
        from gitwise._runtime_config import _is_dark_background

        assert _is_dark_background("#ffffff") is False

    def test_is_dark_background_dark_warp(self):
        from gitwise._runtime_config import _is_dark_background

        assert _is_dark_background("#1e1e2e") is True

    def test_is_dark_background_light_parchment(self):
        from gitwise._runtime_config import _is_dark_background

        assert _is_dark_background("#F8F6F1") is False

    def test_is_dark_boundary_near_threshold(self):
        from gitwise._runtime_config import _is_dark_background, _relative_luminance

        lum = _relative_luminance(LIGHT_BG)
        assert lum > 0.5
        assert _is_dark_background(LIGHT_BG) is False


class TestParseOscColor:
    def test_rgb_st_terminated(self):
        from gitwise._runtime_config import _parse_osc_color

        assert _parse_osc_color("\x1b]11;rgb:1e/1e/2e\x1b\\") == "#1e1e2e"

    def test_rgb_bel_terminated(self):
        from gitwise._runtime_config import _parse_osc_color

        assert _parse_osc_color("\x1b]11;rgb:ffff/ffff/ffff\x07") == "#ffffff"

    def test_hash_color_st(self):
        from gitwise._runtime_config import _parse_osc_color

        assert _parse_osc_color("\x1b]11;#1e1e2e\x1b\\") == "#1e1e2e"

    def test_no_osc_marker_returns_none(self):
        from gitwise._runtime_config import _parse_osc_color

        assert _parse_osc_color("no osc here") is None

    def test_with_cursor_response_prefix(self):
        from gitwise._runtime_config import _parse_osc_color

        resp = "\x1b]11;rgb:f8/f6/f1\x1b\\\x1b[1;1R"
        assert _parse_osc_color(resp) == "#f8f6f1"

    def test_16bit_rgb(self):
        from gitwise._runtime_config import _parse_osc_color

        assert _parse_osc_color("\x1b]11;rgb:1e1e/1e1e/2e2e\x1b\\") == "#1e1e2e"


class TestReadOscResponse:
    def test_timeout_returns_none(self):
        from unittest.mock import patch

        from gitwise._runtime_config import _read_osc_response

        with patch("gitwise._runtime_config.select.select", return_value=([], [], [])):
            assert _read_osc_response(99) is None

    def test_reads_st_terminated_osc(self):
        from unittest.mock import patch

        from gitwise._runtime_config import _read_osc_response

        response_bytes = b"\x1b]11;rgb:1e/1e/2e\x1b\\"
        pos = [0]

        def fake_select(r, w, x, timeout):
            if pos[0] < len(response_bytes):
                return ([99], [], [])
            return ([], [], [])

        def fake_read(fd, n):
            if pos[0] < len(response_bytes):
                b = response_bytes[pos[0] : pos[0] + 1]
                pos[0] += 1
                return b
            return b""

        with patch("gitwise._runtime_config.select.select", side_effect=fake_select):
            with patch("gitwise._runtime_config.os.read", side_effect=fake_read):
                result = _read_osc_response(99)
                assert result is not None
                assert "rgb:" in result

    def test_returns_on_csi_sentinel(self):
        from unittest.mock import patch

        from gitwise._runtime_config import _read_osc_response

        response_bytes = b"\x1b]11;rgb:aaaa/bbbb/cccc\x1b[1;1R"
        pos = [0]

        def fake_select(r, w, x, timeout):
            if pos[0] < len(response_bytes):
                return ([99], [], [])
            return ([], [], [])

        def fake_read(fd, n):
            if pos[0] < len(response_bytes):
                b = response_bytes[pos[0] : pos[0] + 1]
                pos[0] += 1
                return b
            return b""

        with patch("gitwise._runtime_config.select.select", side_effect=fake_select):
            with patch("gitwise._runtime_config.os.read", side_effect=fake_read):
                result = _read_osc_response(99)
                assert result is not None
                assert "rgb:" in result
                assert "\x1b[" not in result


class TestRichHelpFormatterCaching:
    def test_no_color_cache_updates_when_env_changes(self, monkeypatch):
        from gitwise.design import GitwiseRichHelpFormatter

        GitwiseRichHelpFormatter._NO_COLOR_ENV_KEY = None
        GitwiseRichHelpFormatter._NO_COLOR_ENABLED = False

        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("GITWISE_NO_COLOR", raising=False)
        assert GitwiseRichHelpFormatter._no_color_enabled() is False
        assert GitwiseRichHelpFormatter._NO_COLOR_ENV_KEY == ("", "")

        monkeypatch.setenv("GITWISE_NO_COLOR", "1")
        assert GitwiseRichHelpFormatter._no_color_enabled() is True
        assert GitwiseRichHelpFormatter._NO_COLOR_ENV_KEY == ("", "1")

    def test_theme_cache_updates_when_env_changes(self, monkeypatch):
        from gitwise.design import GitwiseRichHelpFormatter

        GitwiseRichHelpFormatter._THEME_ENV_VALUE = None
        GitwiseRichHelpFormatter._THEME_NAME = "dark"

        monkeypatch.setenv("GITWISE_THEME", "light")
        assert GitwiseRichHelpFormatter._theme_name() == "light"

        monkeypatch.setenv("GITWISE_THEME", "blue")
        assert GitwiseRichHelpFormatter._theme_name() == "dark"

    def test_group_name_localization_installed_once(self):
        from gitwise.design import GitwiseRichHelpFormatter
        from gitwise.i18n import t

        class DummyFormatter(argparse.RawDescriptionHelpFormatter):
            group_name_formatter = staticmethod(str.upper)

        GitwiseRichHelpFormatter._DEFAULT_GROUP_NAME_FORMATTER = None
        GitwiseRichHelpFormatter._install_group_name_localization(DummyFormatter)
        installed = DummyFormatter.group_name_formatter

        assert callable(installed)
        assert installed("options") == t("help_group_options")
        assert installed("custom") == "CUSTOM"

        GitwiseRichHelpFormatter._install_group_name_localization(DummyFormatter)
        assert DummyFormatter.group_name_formatter is installed
