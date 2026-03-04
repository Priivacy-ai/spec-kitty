"""Banner visibility tests for CLI invocations."""

from __future__ import annotations

import importlib
import pytest
import typer

from specify_cli.cli import helpers

cli_module = importlib.import_module("specify_cli.__init__")


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["init"], True),
        (["--version"], True),
        (["-v"], True),
        (["merge", "--feature", "001-test"], False),
        (["research"], False),
        (["agent", "feature", "check-prerequisites", "--json"], False),
    ],
)
def test_banner_scope_is_limited_to_init_and_version(argv: list[str], expected: bool) -> None:
    """ASCII art should be limited to init and version invocations."""
    assert helpers._should_render_banner_for_invocation(argv) is expected


def test_version_callback_renders_banner(monkeypatch: pytest.MonkeyPatch) -> None:
    """--version should still render the banner before printing version text."""
    calls: list[bool] = []

    def _fake_show_banner(*, force: bool = False) -> None:
        calls.append(force)

    monkeypatch.setattr(cli_module, "show_banner", _fake_show_banner)

    with pytest.raises(typer.Exit):
        cli_module.version_callback(True)

    assert calls == [True]
