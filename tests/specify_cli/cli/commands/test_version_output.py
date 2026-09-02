"""Version output tests."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from specify_cli import __version__, app as cli_app
from specify_cli.distribution.profile import DistributionProfile

pytestmark = [pytest.mark.fast]

runner = CliRunner()


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_output_is_one_copyable_version_line(flag: str) -> None:
    result = runner.invoke(cli_app, [flag], env={"COLUMNS": "10"})

    assert result.exit_code == 0
    assert result.output == f"spec-kitty-cli version {__version__}\n"


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_output_keeps_long_custom_label_on_one_line(
    flag: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = "acme-" + "custom-distribution-" * 8
    monkeypatch.setattr(
        "specify_cli.distribution.resolve_distribution_profile",
        lambda: DistributionProfile(
            package_name="acme-spec-kitty-cli",
            upgrade_provider=None,
            version_label=label,
        ),
    )

    result = runner.invoke(cli_app, [flag], env={"COLUMNS": "20"})

    assert result.exit_code == 0
    assert result.output == f"{label} version {__version__}\n"


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_output_does_not_render_large_banner(flag: str) -> None:
    result = runner.invoke(cli_app, [flag])

    assert result.exit_code == 0
    assert "Spec Kitty - Spec-Driven Development Toolkit" not in result.output
    assert "████" not in result.output
