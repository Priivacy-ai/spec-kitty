"""Focused tests for the width-invariant ``--help`` snapshot helpers.

These prove the property the golden ``--help`` suites rely on: with
:func:`force_wide_help_console` active, Typer/Rich help renders identically no
matter the ambient terminal width or ``TERM`` — the exact drift that made the
CI ``fast-tests-cli`` snapshots flaky (local wide vs CI 80-column wrap points).
"""

from __future__ import annotations

import typer
import pytest
from typer.testing import CliRunner

from tests.specify_cli.cli.commands._help_snapshot import (
    force_wide_help_console,
    normalize_help,
)

pytestmark = pytest.mark.fast

_LONG_HELP = (
    "A deliberately long option description that is guaranteed to wrap at any "
    "realistic terminal width so the width-invariance property is actually "
    "exercised rather than trivially satisfied by short text."
)


def _sample_app() -> typer.Typer:
    app = typer.Typer(add_completion=False)

    @app.command()
    def demo(  # pragma: no cover - body never runs; only --help is rendered
        flag: bool = typer.Option(False, "--flag", help=_LONG_HELP),
    ) -> None:
        """Sample command used to render a wrapping help body."""

    return app


def test_normalize_help_strips_box_and_collapses_whitespace() -> None:
    raw = "\n".join(
        [
            "╭─ Options ────────────────╮",
            "│ --flag      Do a   thing │",
            "│             spanning     │",
            "",
            "╰──────────────────────────╯",
        ]
    )
    assert normalize_help(raw) == [
        "Options",
        "--flag Do a thing",
        "spanning",
    ]


def test_normalize_help_strips_windows_safe_box_corners() -> None:
    raw = "\n".join(
        [
            "┌─ Options ─┐",
            "│ --flag  Do a thing │",
            "└──────────────────┘",
        ]
    )
    assert normalize_help(raw) == ["Options", "--flag Do a thing"]


@pytest.mark.parametrize("columns", ["40", "100", "200"])
def test_force_wide_help_console_is_width_invariant(
    columns: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normalized help is identical regardless of the ambient ``COLUMNS``.

    Without the pin, a 40-column render wraps the long option description at a
    different point than a 200-column render; with it, both collapse to the same
    single logical line.
    """
    force_wide_help_console(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        _sample_app(), ["--help"], env={"COLUMNS": columns, "TERM": "xterm"}
    )
    assert result.exit_code == 0
    lines = normalize_help(result.stdout)
    assert f"--flag {_LONG_HELP}" in lines
    assert "\x1b[" not in result.stdout  # no ANSI leaked in


def test_force_wide_help_console_matches_across_widths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    force_wide_help_console(monkeypatch)
    runner = CliRunner()
    narrow = runner.invoke(_sample_app(), ["--help"], env={"COLUMNS": "40"})
    wide = runner.invoke(_sample_app(), ["--help"], env={"COLUMNS": "220"})
    assert normalize_help(narrow.stdout) == normalize_help(wide.stdout)
