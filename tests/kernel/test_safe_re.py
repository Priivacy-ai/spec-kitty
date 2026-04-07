"""Unit tests for kernel._safe_re — RE2-backed drop-in for stdlib re.

These tests verify:
- The ``re`` export is a module-like object (types.ModuleType)
- All stdlib re attributes are present (Pattern, Match, RegexFlag, error, flags)
- Core regex functions work correctly
- Fallback to stdlib re when RE2 is unavailable
- ``is_re2_active()`` returns bool
"""

from __future__ import annotations

import re as _stdlib_re
import types

import pytest

from kernel._safe_re import is_re2_active, re

pytestmark = pytest.mark.fast


class TestModuleType:
    """re export must be a proper module, not a plain object."""

    def test_re_is_module_type(self) -> None:
        assert isinstance(re, types.ModuleType)

    def test_re_has_pattern_attribute(self) -> None:
        assert re.Pattern is _stdlib_re.Pattern  # type: ignore[attr-defined]

    def test_re_has_match_attribute(self) -> None:
        assert re.Match is _stdlib_re.Match  # type: ignore[attr-defined]

    def test_re_has_regex_flag_attribute(self) -> None:
        assert re.RegexFlag is _stdlib_re.RegexFlag  # type: ignore[attr-defined]

    def test_re_has_error_attribute(self) -> None:
        assert re.error is _stdlib_re.error  # type: ignore[attr-defined]


class TestFlagConstants:
    """Flag constants are forwarded from stdlib re."""

    def test_ignorecase(self) -> None:
        assert re.IGNORECASE == _stdlib_re.IGNORECASE  # type: ignore[attr-defined]

    def test_i_alias(self) -> None:
        assert re.I == _stdlib_re.IGNORECASE  # type: ignore[attr-defined]

    def test_multiline(self) -> None:
        assert re.MULTILINE == _stdlib_re.MULTILINE  # type: ignore[attr-defined]

    def test_m_alias(self) -> None:
        assert re.M == _stdlib_re.MULTILINE  # type: ignore[attr-defined]

    def test_dotall(self) -> None:
        assert re.DOTALL == _stdlib_re.DOTALL  # type: ignore[attr-defined]

    def test_s_alias(self) -> None:
        assert re.S == _stdlib_re.DOTALL  # type: ignore[attr-defined]

    def test_verbose(self) -> None:
        assert re.VERBOSE == _stdlib_re.VERBOSE  # type: ignore[attr-defined]

    def test_x_alias(self) -> None:
        assert re.X == _stdlib_re.VERBOSE  # type: ignore[attr-defined]

    def test_ascii(self) -> None:
        assert re.ASCII == _stdlib_re.ASCII  # type: ignore[attr-defined]

    def test_unicode(self) -> None:
        assert re.UNICODE == _stdlib_re.UNICODE  # type: ignore[attr-defined]

    def test_noflag(self) -> None:
        assert re.NOFLAG == _stdlib_re.NOFLAG  # type: ignore[attr-defined]


class TestCompile:
    """re.compile returns a compiled pattern that works correctly."""

    def test_compile_returns_pattern_like_object(self) -> None:
        """Compiled result exposes the standard Pattern interface (search/match/etc).

        When RE2 is active the returned object is re2._Regexp, not re.Pattern.
        We verify the duck-type interface rather than the concrete type.
        """
        pat = re.compile(r"\d+")  # type: ignore[attr-defined]
        assert hasattr(pat, "search")
        assert hasattr(pat, "match")
        assert hasattr(pat, "findall")

    def test_compiled_pattern_matches(self) -> None:
        pat = re.compile(r"\d+")  # type: ignore[attr-defined]
        m = pat.search("abc 123 def")
        assert m is not None
        assert m.group() == "123"

    def test_compile_with_multiline_flag(self) -> None:
        pat = re.compile(r"^\w+", re.MULTILINE)  # type: ignore[attr-defined]
        matches = pat.findall("foo\nbar\nbaz")
        assert matches == ["foo", "bar", "baz"]

    def test_compile_with_ignorecase_flag(self) -> None:
        pat = re.compile(r"hello", re.IGNORECASE)  # type: ignore[attr-defined]
        assert pat.search("HELLO world") is not None

    def test_compile_with_dotall_flag(self) -> None:
        pat = re.compile(r"a.b", re.DOTALL)  # type: ignore[attr-defined]
        assert pat.search("a\nb") is not None

    def test_compile_inline_multiline(self) -> None:
        """Inline (?m) flag in the pattern string always works."""
        pat = re.compile(r"(?m)^\w+")  # type: ignore[attr-defined]
        matches = pat.findall("foo\nbar")
        assert matches == ["foo", "bar"]


class TestSearchAndMatch:
    """Module-level search/match/fullmatch functions."""

    def test_search_finds_match(self) -> None:
        m = re.search(r"\d+", "abc 42 xyz")  # type: ignore[attr-defined]
        assert m is not None
        assert m.group() == "42"

    def test_search_no_match_returns_none(self) -> None:
        assert re.search(r"\d+", "no digits here") is None  # type: ignore[attr-defined]

    def test_match_at_start(self) -> None:
        m = re.match(r"\w+", "hello world")  # type: ignore[attr-defined]
        assert m is not None
        assert m.group() == "hello"

    def test_match_not_at_start_returns_none(self) -> None:
        assert re.match(r"\d+", "abc123") is None  # type: ignore[attr-defined]

    def test_fullmatch(self) -> None:
        assert re.fullmatch(r"\d+", "123") is not None  # type: ignore[attr-defined]
        assert re.fullmatch(r"\d+", "123abc") is None  # type: ignore[attr-defined]


class TestFindall:
    """re.findall function."""

    def test_findall_returns_list(self) -> None:
        results = re.findall(r"\d+", "1 two 3 four 5")  # type: ignore[attr-defined]
        assert results == ["1", "3", "5"]

    def test_findall_empty_when_no_match(self) -> None:
        assert re.findall(r"\d+", "no digits") == []  # type: ignore[attr-defined]


class TestFinditer:
    """re.finditer function."""

    def test_finditer_returns_iterator(self) -> None:
        matches = list(re.finditer(r"\d+", "1 and 22 and 333"))  # type: ignore[attr-defined]
        assert [m.group() for m in matches] == ["1", "22", "333"]


class TestSub:
    """re.sub and re.subn functions."""

    def test_sub_replaces_pattern(self) -> None:
        result = re.sub(r"\d+", "NUM", "I have 2 cats and 3 dogs")  # type: ignore[attr-defined]
        assert result == "I have NUM cats and NUM dogs"

    def test_sub_with_count_limit(self) -> None:
        result = re.sub(r"\d+", "NUM", "1 2 3", count=2)  # type: ignore[attr-defined]
        assert result == "NUM NUM 3"

    def test_subn_returns_tuple(self) -> None:
        text, n = re.subn(r"\d+", "NUM", "1 and 2")  # type: ignore[attr-defined]
        assert text == "NUM and NUM"
        assert n == 2


class TestSplit:
    """re.split function."""

    def test_split_on_pattern(self) -> None:
        parts = re.split(r"\s+", "one  two   three")  # type: ignore[attr-defined]
        assert parts == ["one", "two", "three"]


class TestEscape:
    """re.escape function (always uses stdlib)."""

    def test_escape_special_chars(self) -> None:
        """re.escape delegates to stdlib re.escape (always, regardless of engine)."""
        # Use a pattern where stdlib and RE2 agree: backslash-escaping a literal dot
        result = re.escape("a.b")  # type: ignore[attr-defined]
        assert result == _stdlib_re.escape("a.b")


class TestPCREFallback:
    """Patterns with lookaheads fall back gracefully to stdlib re."""

    def test_positive_lookahead(self) -> None:
        m = re.search(r"\w+(?= world)", "hello world")  # type: ignore[attr-defined]
        assert m is not None
        assert m.group() == "hello"

    def test_negative_lookahead(self) -> None:
        m = re.search(r"\w+(?! world)", "hello there")  # type: ignore[attr-defined]
        assert m is not None

    def test_lookbehind(self) -> None:
        m = re.search(r"(?<=hello )\w+", "hello world")  # type: ignore[attr-defined]
        assert m is not None
        assert m.group() == "world"


class TestIsRe2Active:
    """is_re2_active() returns a bool."""

    def test_returns_bool(self) -> None:
        result = is_re2_active()
        assert isinstance(result, bool)


class TestInstanceofPattern:
    """isinstance checks with re.Pattern work correctly."""

    def test_compiled_pattern_is_instance_of_re_pattern(self) -> None:
        """When the pattern falls back to stdlib (lookahead), isinstance works normally."""
        # This pattern has a lookahead — always compiled via stdlib re
        pat = re.compile(r"\w+(?= world)")  # type: ignore[attr-defined]
        assert isinstance(pat, _stdlib_re.Pattern)
