"""Version output tests."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from specify_cli import __version__, app as cli_app

pytestmark = [pytest.mark.fast]

runner = CliRunner()


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_output_is_one_copyable_version_line(flag: str) -> None:
    result = runner.invoke(cli_app, [flag])

    assert result.exit_code == 0
    assert result.output == f"spec-kitty-cli version {__version__}\n"


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_output_does_not_render_large_banner(flag: str) -> None:
    result = runner.invoke(cli_app, [flag])

    assert result.exit_code == 0
    assert "Spec Kitty - Spec-Driven Development Toolkit" not in result.output
    assert "████" not in result.output
