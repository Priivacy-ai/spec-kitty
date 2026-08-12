"""Consumed CLI contracts for mission-type discovery.

Each test crosses Typer's public command boundary.  Table-field spot checks,
help registration, and charter-layer source-shape checks live elsewhere or are
implied by these executable routes.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import charter_app
from specify_cli.cli.commands.mission_type import app as mission_type_app


runner = CliRunner()
pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_charter_mission_type_list_json_contract() -> None:
    """The canonical list route emits usable activated mission descriptors."""
    result = runner.invoke(charter_app, ["mission-type", "list", "--json"])
    assert result.exit_code == 0, result.output

    rows = json.loads(result.output)
    assert rows
    assert all({"id", "source_layer", "display_name", "action_sequence"} <= row.keys() and isinstance(row["action_sequence"], list) for row in rows)


def test_mission_type_list_alias_reaches_the_same_catalog() -> None:
    """The documented top-level alias resolves the canonical catalog."""
    alias = runner.invoke(mission_type_app, ["list", "--json"])
    canonical = runner.invoke(charter_app, ["mission-type", "list", "--json"])
    assert alias.exit_code == canonical.exit_code == 0
    assert {row["id"] for row in json.loads(alias.output)} == {row["id"] for row in json.loads(canonical.output)}


def test_mission_type_show_json_contract() -> None:
    """A selected descriptor exposes the fields consumed by callers."""
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output

    row = json.loads(result.output)
    assert row["id"] == "software-dev"
    assert row["source_layer"] == "built-in"
    assert isinstance(row["action_sequence"], list) and row["action_sequence"]


def test_mission_type_show_rejects_an_unknown_id() -> None:
    """The negative route fails closed and identifies the rejected input."""
    result = runner.invoke(mission_type_app, ["show", "unknown-type"])
    assert result.exit_code == 1
    assert "unknown-type" in result.output
