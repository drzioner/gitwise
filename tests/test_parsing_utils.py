"""Tests for shared parsing utilities."""

from gitwise.utils.parsing import (
    dict_list,
    non_empty_lines,
    parse_two_ints,
    stripped_non_empty_lines,
    to_int,
)


def test_non_empty_lines_filters_blank_lines() -> None:
    assert non_empty_lines("a\n\n b \n") == ["a", " b "]


def test_stripped_non_empty_lines_trims_lines() -> None:
    assert stripped_non_empty_lines(" a \n\n b\n") == ["a", "b"]


def test_to_int_accepts_signed_string() -> None:
    assert to_int("-12") == -12
    assert to_int("+7") == 7
    assert to_int("xx", default=3) == 3


def test_parse_two_ints_parses_pair() -> None:
    assert parse_two_ints("3 4") == (3, 4)
    assert parse_two_ints("x 4") is None


def test_dict_list_filters_non_dict_values() -> None:
    assert dict_list([{"a": 1}, 2, "x", {"b": 2}]) == [{"a": 1}, {"b": 2}]
    assert dict_list(None) == []
