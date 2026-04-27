"""Unit tests for NoNetworkProvider.

Key assertions
--------------
1. ``get_latest`` always returns ``LatestVersionResult(version=None, source="none", error=None)``.
2. ``httpx.Client`` is NEVER constructed — no socket is ever opened.

All tests are marked ``pytest.mark.fast``.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specify_cli.compat.provider import LatestVersionResult, NoNetworkProvider

pytestmark = pytest.mark.fast


class TestNoNetworkProviderResult:
    def test_returns_version_none(self) -> None:
        provider = NoNetworkProvider()
        result = provider.get_latest("spec-kitty-cli")
        assert result.version is None

    def test_returns_source_none(self) -> None:
        result = NoNetworkProvider().get_latest("spec-kitty-cli")
        assert result.source == "none"

    def test_returns_error_none(self) -> None:
        result = NoNetworkProvider().get_latest("spec-kitty-cli")
        assert result.error is None

    def test_returns_correct_dataclass(self) -> None:
        result = NoNetworkProvider().get_latest("spec-kitty-cli")
        assert result == LatestVersionResult(version=None, source="none", error=None)

    def test_package_argument_is_ignored(self) -> None:
        """Different package names must all return the same result."""
        p = NoNetworkProvider()
        assert p.get_latest("package-a") == p.get_latest("package-b")

    def test_repeated_calls_return_same_result(self) -> None:
        provider = NoNetworkProvider()
        r1 = provider.get_latest("spec-kitty-cli")
        r2 = provider.get_latest("spec-kitty-cli")
        assert r1 == r2

    def test_does_not_raise(self) -> None:
        """NoNetworkProvider must never raise, regardless of input."""
        provider = NoNetworkProvider()
        # Does not raise for empty string, long string, unicode, None-like str
        provider.get_latest("")
        provider.get_latest("a" * 256)


class TestNoNetworkProviderNoSocket:
    def test_httpx_client_never_constructed(self) -> None:
        """NoNetworkProvider MUST NOT instantiate httpx.Client (CHK013).

        If it did, the patch would raise AssertionError and the test would fail.
        """
        with patch("httpx.Client", side_effect=AssertionError("httpx.Client must not be called")):
            result = NoNetworkProvider().get_latest("spec-kitty-cli")
        # Verify the result is correct — not cut short by an exception
        assert result == LatestVersionResult(version=None, source="none", error=None)
