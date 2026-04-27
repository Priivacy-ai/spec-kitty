"""Unit tests for FakeLatestVersionProvider.

The fake is a deterministic test double that returns whatever it was configured
with at construction time.  These tests verify the round-trip behaviour.

All tests are marked ``pytest.mark.fast``.
"""

from __future__ import annotations

import pytest

from specify_cli.compat.provider import FakeLatestVersionProvider, LatestVersionResult

pytestmark = pytest.mark.fast


class TestFakeLatestVersionProviderDefaults:
    def test_default_returns_version_none(self) -> None:
        result = FakeLatestVersionProvider().get_latest("spec-kitty-cli")
        assert result.version is None

    def test_default_returns_source_none(self) -> None:
        result = FakeLatestVersionProvider().get_latest("spec-kitty-cli")
        assert result.source == "none"

    def test_default_returns_error_none(self) -> None:
        result = FakeLatestVersionProvider().get_latest("spec-kitty-cli")
        assert result.error is None

    def test_default_returns_correct_dataclass(self) -> None:
        result = FakeLatestVersionProvider().get_latest("any-package")
        assert result == LatestVersionResult(version=None, source="none", error=None)


class TestFakeLatestVersionProviderWithVersion:
    def test_configured_version_is_returned(self) -> None:
        result = FakeLatestVersionProvider("2.0.14").get_latest("spec-kitty-cli")
        assert result.version == "2.0.14"

    def test_configured_version_source_is_pypi(self) -> None:
        result = FakeLatestVersionProvider("1.0.0").get_latest("spec-kitty-cli")
        assert result.source == "pypi"

    def test_configured_version_error_is_none(self) -> None:
        result = FakeLatestVersionProvider("3.2.0").get_latest("spec-kitty-cli")
        assert result.error is None

    def test_returns_full_dataclass(self) -> None:
        result = FakeLatestVersionProvider("2.0.14").get_latest("pkg")
        assert result == LatestVersionResult(version="2.0.14", source="pypi", error=None)

    def test_package_argument_ignored(self) -> None:
        fake = FakeLatestVersionProvider("2.0.0")
        assert fake.get_latest("a") == fake.get_latest("b")

    def test_pre_release_version_returned_verbatim(self) -> None:
        result = FakeLatestVersionProvider("3.2.0a4").get_latest("pkg")
        assert result.version == "3.2.0a4"


class TestFakeLatestVersionProviderWithError:
    def test_configured_error_is_returned(self) -> None:
        result = FakeLatestVersionProvider(error="timeout").get_latest("spec-kitty-cli")
        assert result.error == "timeout"

    def test_error_source_is_none(self) -> None:
        result = FakeLatestVersionProvider(error="http_error").get_latest("pkg")
        assert result.source == "none"

    def test_error_version_is_none(self) -> None:
        result = FakeLatestVersionProvider(error="parse_error").get_latest("pkg")
        assert result.version is None

    def test_error_takes_precedence_over_version(self) -> None:
        """If both error and version are provided, error wins."""
        fake = FakeLatestVersionProvider(version="1.0.0", error="oversized")
        result = fake.get_latest("pkg")
        assert result.error == "oversized"
        assert result.version is None

    @pytest.mark.parametrize("token", ["timeout", "http_error", "parse_error", "oversized"])
    def test_all_error_tokens_round_trip(self, token: str) -> None:
        result = FakeLatestVersionProvider(error=token).get_latest("pkg")
        assert result.error == token


class TestFakeLatestVersionProviderDeterminism:
    def test_repeated_calls_return_same_result(self) -> None:
        fake = FakeLatestVersionProvider("1.2.3")
        r1 = fake.get_latest("pkg")
        r2 = fake.get_latest("pkg")
        assert r1 == r2

    def test_independent_instances_same_config_equal(self) -> None:
        r1 = FakeLatestVersionProvider("4.0.0").get_latest("pkg")
        r2 = FakeLatestVersionProvider("4.0.0").get_latest("pkg")
        assert r1 == r2

    def test_different_versions_produce_different_results(self) -> None:
        r1 = FakeLatestVersionProvider("1.0.0").get_latest("pkg")
        r2 = FakeLatestVersionProvider("2.0.0").get_latest("pkg")
        assert r1 != r2
