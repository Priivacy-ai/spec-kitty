"""Tests for DistributionProfile resolution."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

import pytest

from specify_cli.compat.provider import (
    FakeLatestVersionProvider,
    NoNetworkProvider,
    PyPIProvider,
)
from specify_cli.distribution import profile
from specify_cli.distribution.package_name import (
    DEFAULT_CLI_PACKAGE_NAME,
    clear_cli_package_name_cache,
)
from specify_cli.distribution.profile import (
    DISTRIBUTION_PROFILE_GROUP,
    DistributionProfile,
    clear_distribution_profile_cache,
    is_degraded_distribution_profile,
    resolve_distribution_profile,
    stock_distribution_profile,
)
from specify_cli.distribution.upgrade_provider import clear_upgrade_provider_cache

pytestmark = pytest.mark.fast


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
    assert profile.disable_no_upgrade_notifier is False
    assert profile.index_url is None
    assert profile.extra_index_url is None
    assert profile.version_label is None


def test_retired_profile_field_and_export_are_removed() -> None:
    assert not hasattr(DistributionProfile, "disable_public_pypi_notifier")
    assert "disable_public_pypi_notifier" not in {field.name for field in fields(DistributionProfile)}
    assert "disable_public_pypi_notifier" not in profile.__all__

    with pytest.raises(TypeError):
        DistributionProfile(
            package_name="fork-cli",
            disable_public_pypi_notifier=True,
        )


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
        disable_no_upgrade_notifier=True,
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
    assert profile.disable_no_upgrade_notifier is True
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


def test_incompatible_factory_signature_fails_closed(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """A fork still passing a retired field name (e.g. disable_public_pypi_notifier)
    raises TypeError inside the factory call; this must be logged loudly (not
    swallowed at debug) and fail closed instead of silently substituting
    public-PyPI remediation."""

    def broken_factory() -> DistributionProfile:
        return DistributionProfile(disable_public_pypi_notifier=True)  # type: ignore[call-arg]

    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [_FakeEntryPoint("legacy-fork", broken_factory)],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_cli_package_name",
        lambda: "fallback-cli",
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_upgrade_provider",
        lambda: FakeLatestVersionProvider(version="0.1.0"),
    )

    import logging as _logging

    with caplog.at_level(_logging.ERROR, logger="specify_cli.distribution.profile"):
        profile = resolve_distribution_profile()

    assert is_degraded_distribution_profile(profile)
    assert profile.package_name == ""
    assert isinstance(profile.upgrade_provider, NoNetworkProvider)
    assert profile.disable_no_upgrade_notifier is True
    assert any(record.levelno == _logging.ERROR and "legacy-fork" in record.message for record in caplog.records)


def test_load_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert is_degraded_distribution_profile(profile)
    assert profile.package_name == ""
    assert isinstance(profile.upgrade_provider, NoNetworkProvider)


def test_invalid_factory_result_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.profile.entry_points",
        lambda group: [_FakeEntryPoint("wrong-type", lambda: object())],
    )

    profile = resolve_distribution_profile()

    assert is_degraded_distribution_profile(profile)
    assert profile.package_name == ""


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
