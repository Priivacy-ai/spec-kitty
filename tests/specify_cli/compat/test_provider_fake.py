"""Unit tests for FakeLatestVersionProvider.

The fake is a deterministic test double that returns whatever it was configured
with at construction time.  These tests verify the round-trip behaviour.

All tests are marked ``pytest.mark.fast``.
"""

from __future__ import annotations

import pytest

from specify_cli.compat.provider import FakeLatestVersionProvider, LatestVersionResult

pytestmark = pytest.mark.fast


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        (FakeLatestVersionProvider(), LatestVersionResult(version=None, source="none", error=None)),
        (FakeLatestVersionProvider("2.0.14"), LatestVersionResult(version="2.0.14", source="pypi", error=None)),
        (
            FakeLatestVersionProvider(version="1.0.0", error="oversized"),
            LatestVersionResult(version=None, source="none", error="oversized"),
        ),
    ],
)
def test_fake_provider_returns_configured_result(
    provider: FakeLatestVersionProvider,
    expected: LatestVersionResult,
) -> None:
    assert provider.get_latest("spec-kitty-cli") == expected


class TestFakeLatestVersionProviderWithVersion:
    def test_package_argument_ignored(self) -> None:
        fake = FakeLatestVersionProvider("2.0.0")
        assert fake.get_latest("a") == fake.get_latest("b")

    def test_pre_release_version_returned_verbatim(self) -> None:
        result = FakeLatestVersionProvider("3.2.0a4").get_latest("pkg")
        assert result.version == "3.2.0a4"


class TestFakeLatestVersionProviderWithError:
    @pytest.mark.parametrize("token", ["timeout", "http_error", "parse_error", "oversized"])
    def test_all_error_tokens_round_trip(self, token: str) -> None:
        result = FakeLatestVersionProvider(error=token).get_latest("pkg")
        assert result.error == token


class TestFakeLatestVersionProviderDeterminism:
    def test_different_versions_produce_different_results(self) -> None:
        r1 = FakeLatestVersionProvider("1.0.0").get_latest("pkg")
        r2 = FakeLatestVersionProvider("2.0.0").get_latest("pkg")
        assert r1 != r2
