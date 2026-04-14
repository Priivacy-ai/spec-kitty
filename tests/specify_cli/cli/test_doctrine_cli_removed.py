"""Regression test: `spec-kitty doctrine ...` must be an unknown command.

This test prevents reintroduction of the curation CLI surface deleted in
Phase 1 (WP01 of mission
``excise-doctrine-curation-and-inline-references-01KP54J6``).

See EPIC #461 / Phase 1 issue #463 / WP issue #476.

The test imports the root Typer app through the canonical
``specify_cli`` package path so the assertions survive future CLI
restructures. If the doctrine parent group is ever re-registered, all
three of these tests should fail loudly.
"""

from __future__ import annotations

from typer.testing import CliRunner

from specify_cli import app


def test_doctrine_curate_is_unknown_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "curate"])
    assert result.exit_code != 0


def test_doctrine_parent_group_is_unregistered() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "--help"])
    assert result.exit_code != 0


def test_doctrine_promote_is_unknown_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["doctrine", "promote"])
    assert result.exit_code != 0
