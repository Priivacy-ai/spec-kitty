"""Tests for DistributionProfile resolution."""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.compat.provider import FakeLatestVersionProvider, PyPIProvider
from specify_cli.distribution.package_name import (
    DEFAULT_CLI_PACKAGE_NAME,
    clear_cli_package_name_cache,
)
from specify_cli.distribution.profile import (
    DISTRIBUTION_PROFILE_GROUP,
    DistributionProfile,
    clear_distribution_profile_cache,
    resolve_distribution_profile,
    stock_distribution_profile,
)
from specify_cli.distribution.upgrade_provider import clear_upgrade_provider_cache


class _FakeEntryPoint:
    def __init__(self, name: str, payload: Any) -> None:
        self.name = name
        self._payload = payload

    def load(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_distribution_profile_cache()
    clear_cli_package_name_cache()
    clear_upgrade_provider_cache()
    yield
    clear_distribution_profile_cache()
    clear_cli_package_name_cache()
    clear_upgrade_provider_cache()


def test_stock_profile_defaults() -> None:
    profile = stock_distribution_profile()
    assert profile.package_name == DEFAULT_CLI_PACKAGE_NAME
    assert profile.package_aliases == ()
    assert isinstance(profile.upgrade_provider, PyPIProvider)
    assert profile.disable_public_pypi_notifier is False
    assert profile.index_url is None
    assert profile.extra_index_url is None
    assert profile.version_label is None


def test_stock_defaults_contain_no_private_hostnames() -> None:
    profile = stock_distribution_profile()
    for value in (profile.index_url, profile.extra_index_url, profile.version_label):
        if value is None:
            continue
        assert "invalid" not in value
        assert "localhost" not in value
        assert "127.0.0.1" not in value


def test_entry_point_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    custom = DistributionProfile(
        package_name="acme-spec-kitty-cli",
        package_aliases=("spec-kitty-cli",),
        upgrade_provider=FakeLatestVersionProvider(version="1.0.0"),
        index_url="https://example.invalid/simple/",
        disable_public_pypi_notifier=True,
        version_label="acme-cli",
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [_FakeEntryPoint("acme", custom)],
    )
    profile = resolve_distribution_profile()
    assert profile.package_name == "acme-spec-kitty-cli"
    assert profile.package_aliases == ("spec-kitty-cli",)
    assert profile.index_url == "https://example.invalid/simple/"
    assert profile.disable_public_pypi_notifier is True
    assert profile.version_label == "acme-cli"


def test_entry_point_callable_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    custom = DistributionProfile(package_name="from-factory")
    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [_FakeEntryPoint("acme", lambda: custom)],
    )
    assert resolve_distribution_profile().package_name == "from-factory"


def test_entry_point_type_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    class AcmeProfile(DistributionProfile):
        def __init__(self) -> None:
            super().__init__(package_name="from-type")

    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [_FakeEntryPoint("acme", AcmeProfile)],
    )
    assert resolve_distribution_profile().package_name == "from-type"


def test_synthesize_from_phase1_when_no_profile_ep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_cli_package_name",
        lambda: "fork-cli",
    )
    provider = FakeLatestVersionProvider(version="2.0.0")
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_upgrade_provider",
        lambda: provider,
    )
    profile = resolve_distribution_profile()
    assert profile.package_name == "fork-cli"
    assert profile.upgrade_provider is provider


def test_load_failure_falls_back_to_synthesize(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [_FakeEntryPoint("broken", RuntimeError("nope"))],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_cli_package_name",
        lambda: "fallback-cli",
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_upgrade_provider",
        lambda: FakeLatestVersionProvider(version="0.1.0"),
    )
    profile = resolve_distribution_profile()
    assert profile.package_name == "fallback-cli"


def test_alphabetical_when_multiple_profiles(monkeypatch: pytest.MonkeyPatch) -> None:
    alpha = DistributionProfile(package_name="alpha-cli")
    zeta = DistributionProfile(package_name="zeta-cli")
    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [
            _FakeEntryPoint("zeta", zeta),
            _FakeEntryPoint("alpha", alpha),
        ],
    )
    assert resolve_distribution_profile().package_name == "alpha-cli"


def test_never_raises_on_entry_points_blowup(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*, group: str) -> list[Any]:
        raise RuntimeError(f"metadata broken for {group}")

    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        boom,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_cli_package_name",
        lambda: DEFAULT_CLI_PACKAGE_NAME,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_upgrade_provider",
        lambda: PyPIProvider(),
    )
    profile = resolve_distribution_profile()
    assert profile.package_name == DEFAULT_CLI_PACKAGE_NAME


def test_memoizes_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def counting(*, group: str) -> list[_FakeEntryPoint]:
        calls["n"] += 1
        assert group == DISTRIBUTION_PROFILE_GROUP
        return [_FakeEntryPoint("once", DistributionProfile(package_name="once-cli"))]

    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        counting,
    )
    assert resolve_distribution_profile().package_name == "once-cli"
    assert resolve_distribution_profile().package_name == "once-cli"
    assert calls["n"] == 1
