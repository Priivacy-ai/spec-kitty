"""Stock-path and resolver wiring tests for CLI package identity (WP02)."""

from __future__ import annotations

import importlib.metadata as im

import pytest
import typer

from specify_cli.distribution.package_name import (
    DEFAULT_CLI_PACKAGE_NAME,
    clear_cli_package_name_cache,
)
from specify_cli.version_utils import get_version

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _clear_name_cache() -> None:
    clear_cli_package_name_cache()
    yield
    clear_cli_package_name_cache()


def test_get_version_uses_resolved_package_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.resolve_cli_package_name",
        lambda: "acme-spec-kitty-cli",
    )

    def fake_metadata_version(name: str) -> str:
        assert name == "acme-spec-kitty-cli"
        return "9.9.9"

    monkeypatch.setattr(im, "version", fake_metadata_version)
    assert get_version() == "9.9.9"


def test_get_version_stock_name_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    clear_cli_package_name_cache()

    def fake_metadata_version(name: str) -> str:
        assert name == DEFAULT_CLI_PACKAGE_NAME
        return "3.2.5"

    monkeypatch.setattr(im, "version", fake_metadata_version)
    assert get_version() == "3.2.5"


def test_version_callback_label_uses_resolved_name(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[str] = []

    class FakeConsole:
        def print(self, msg: object) -> None:
            printed.append(str(msg))

    # The banner now flows through the DistributionProfile (the aggregated identity
    # seam), so patch the profile rather than the underlying name resolver.
    from specify_cli.distribution.profile import DistributionProfile

    monkeypatch.setattr(
        "specify_cli.distribution.resolve_distribution_profile",
        lambda: DistributionProfile(package_name="acme-spec-kitty-cli", upgrade_provider=None),
    )
    monkeypatch.setattr("specify_cli.cli.console.console", FakeConsole())
    monkeypatch.setattr("specify_cli.cli.helpers.show_banner", lambda force=False: None)

    import specify_cli

    with pytest.raises(typer.Exit):
        specify_cli.version_callback(True)

    assert printed
    assert printed[0].startswith("acme-spec-kitty-cli version ")
