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
    def test_package_argument_is_ignored(self) -> None:
        """Different package names must all return the same result."""
        p = NoNetworkProvider()
        expected = LatestVersionResult(version=None, source="none", error=None)
        assert p.get_latest("package-a") == expected
        assert p.get_latest("package-b") == expected


class TestNoNetworkProviderNoSocket:
    def test_httpx_client_never_constructed(self) -> None:
        """NoNetworkProvider MUST NOT instantiate httpx.Client (CHK013).

        If it did, the patch would raise AssertionError and the test would fail.
        """
        with patch("httpx.Client", side_effect=AssertionError("httpx.Client must not be called")):
            result = NoNetworkProvider().get_latest("spec-kitty-cli")
        # Verify the result is correct — not cut short by an exception
        assert result == LatestVersionResult(version=None, source="none", error=None)
