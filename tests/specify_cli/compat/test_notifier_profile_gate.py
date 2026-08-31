"""FR-015: maybe_emit_no_upgrade_notice respects DistributionProfile gate."""

from __future__ import annotations

import pytest

from specify_cli.core.version_checker import maybe_emit_no_upgrade_notice
from specify_cli.distribution.profile import DistributionProfile

pytestmark = [pytest.mark.fast]


def test_suppressed_when_profile_disables_notifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = DistributionProfile(
        package_name="acme-cli",
        disable_public_pypi_notifier=True,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.resolve_distribution_profile",
        lambda: profile,
    )
    monkeypatch.setattr(
        "specify_cli.core.version_checker.should_check_version",
        lambda _name: True,
    )

    called: list[bool] = []

    def _fake_emit(_version: str) -> bool:
        called.append(True)
        return True

    monkeypatch.setattr(
        "specify_cli.core.upgrade_notifier.maybe_emit_upgrade_notice",
        _fake_emit,
    )

    assert maybe_emit_no_upgrade_notice("status") is False
    assert called == []
