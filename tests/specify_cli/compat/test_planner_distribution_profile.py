"""WP04: planner consumes DistributionProfile (FR-011, FR-012)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock

import pytest

from specify_cli.compat.cache import NagCacheRecord
from specify_cli.compat.planner import Invocation, plan
from specify_cli.compat.provider import LatestVersionResult
from specify_cli.distribution.profile import DistributionProfile

pytestmark = [pytest.mark.fast]


@dataclass
class _RecordingProvider:
    """Records get_latest package args."""

    version: str = "9.9.9"
    source: Literal["pypi", "simple_index", "none"] = "pypi"
    calls: list[str] | None = None

    def __post_init__(self) -> None:
        if self.calls is None:
            self.calls = []

    def get_latest(self, package: str) -> LatestVersionResult:
        assert self.calls is not None
        self.calls.append(package)
        return LatestVersionResult(version=self.version, source=self.source, error=None)


def test_planner_queries_profile_package_name(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _RecordingProvider()
    profile = DistributionProfile(
        package_name="acme-spec-kitty-cli",
        package_aliases=("spec-kitty-cli",),
        upgrade_provider=provider,
        disable_public_pypi_notifier=True,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.profile.resolve_distribution_profile",
        lambda: profile,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.resolve_distribution_profile",
        lambda: profile,
    )

    result = plan(
        Invocation.from_argv(["spec-kitty", "status"]),
        latest_version_provider=provider,
        nag_cache=_empty_cache(),
        config=_config(throttle_seconds=3600),
        now=datetime(2026, 7, 21, tzinfo=UTC),
        project_root_resolver=lambda _p: None,
    )

    assert provider.calls == ["acme-spec-kitty-cli"]
    assert result.cli_status.latest_version == "9.9.9"


def test_data_freshness_uses_profile_ttl_not_display_throttle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """has_fresh_data uses profile TTL; is_fresh still uses config throttle."""
    provider = _RecordingProvider(version="2.0.0")
    profile = DistributionProfile(
        package_name="spec-kitty-cli",
        upgrade_provider=provider,
        data_freshness_seconds=60,  # 1 minute data TTL
    )
    monkeypatch.setattr(
        "specify_cli.distribution.resolve_distribution_profile",
        lambda: profile,
    )

    now = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
    # fetched 30s ago — within profile data TTL (60) but we still may re-query
    # only if data is stale. 30 < 60 → skip provider.
    record = NagCacheRecord(
        cli_version_key="1.0.0",
        latest_version="1.5.0",
        latest_source="pypi",
        fetched_at=now - timedelta(seconds=30),
        last_shown_at=None,  # never shown → is_fresh False
    )
    cache = MagicMock()
    cache.read.return_value = record

    monkeypatch.setattr(
        "specify_cli.distribution.installed_version.resolve_installed_distribution_version",
        lambda *_a, **_k: "1.0.0",
    )
    # Also patch planner's import path via distribution package
    monkeypatch.setattr(
        "specify_cli.distribution.resolve_installed_distribution_version",
        lambda *_a, **_k: "1.0.0",
    )

    result = plan(
        Invocation.from_argv(["spec-kitty", "status"]),
        latest_version_provider=provider,
        nag_cache=cache,
        config=_config(throttle_seconds=86_400),  # 24h display throttle
        now=now,
        project_root_resolver=lambda _p: None,
    )

    assert provider.calls == []  # data still fresh under 60s TTL
    assert result.cli_status.latest_version == "1.5.0"


def test_stale_under_profile_ttl_queries_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _RecordingProvider(version="3.0.0")
    profile = DistributionProfile(
        package_name="fork-cli",
        upgrade_provider=provider,
        data_freshness_seconds=60,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.resolve_distribution_profile",
        lambda: profile,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.resolve_installed_distribution_version",
        lambda *_a, **_k: "1.0.0",
    )

    now = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
    record = NagCacheRecord(
        cli_version_key="1.0.0",
        latest_version="1.5.0",
        latest_source="pypi",
        fetched_at=now - timedelta(seconds=120),  # > 60s data TTL
        last_shown_at=None,
    )
    cache = MagicMock()
    cache.read.return_value = record

    result = plan(
        Invocation.from_argv(["spec-kitty", "status"]),
        latest_version_provider=provider,
        nag_cache=cache,
        config=_config(throttle_seconds=86_400),
        now=now,
        project_root_resolver=lambda _p: None,
    )

    assert provider.calls == ["fork-cli"]
    assert result.cli_status.latest_version == "3.0.0"


def _empty_cache() -> MagicMock:
    cache = MagicMock()
    cache.read.return_value = None
    return cache


def _config(*, throttle_seconds: int) -> MagicMock:
    cfg = MagicMock()
    cfg.throttle_seconds = throttle_seconds
    cfg.nag_enabled = True
    return cfg
