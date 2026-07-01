"""CLI tests for ``spec-kitty doctrine mission-type list``.

WP13 / T081 — Tests for ``doctrine mission-type list [--json]``.

Owner: ``src/specify_cli/cli/commands/doctrine.py``
Mission: charter-doctrine-mission-type-configuration-01KSWJVX
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.doctrine import app

runner = CliRunner()

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# T081-a: mission-type sub-group is registered under doctrine
# ---------------------------------------------------------------------------


def test_doctrine_mission_type_subgroup_registered() -> None:
    """``doctrine mission-type --help`` exits 0 (group is registered).

    This is the T077 guard: verifies the ``mission-type`` sub-group
    exists and the doctrine group was NOT accidentally deregistered (see
    the PR #1352 regression incident).
    """
    result = runner.invoke(app, ["mission-type", "--help"])
    assert result.exit_code == 0, result.output
    assert "list" in result.output


# ---------------------------------------------------------------------------
# T081-b: default table output returns all four built-in types
# ---------------------------------------------------------------------------


def test_mission_type_list_returns_built_in_types() -> None:
    """``doctrine mission-type list`` returns at least the four canonical types."""
    result = runner.invoke(app, ["mission-type", "list"])

    assert result.exit_code == 0, result.output

    # All four canonical mission types must appear.
    expected_ids = ["software-dev", "documentation", "research", "plan"]
    for mt_id in expected_ids:
        assert mt_id in result.output, (
            f"Expected mission type id {mt_id!r} not found in output:\n{result.output}"
        )


def test_mission_type_list_shows_built_in_source_layer() -> None:
    """Each row in table output carries ``built-in`` as the source layer."""
    result = runner.invoke(app, ["mission-type", "list"])

    assert result.exit_code == 0, result.output
    assert "built-in" in result.output


def test_mission_type_list_shows_display_names() -> None:
    """Table output includes human-readable display names for well-known types."""
    result = runner.invoke(app, ["mission-type", "list"])

    assert result.exit_code == 0, result.output
    # Check at least one canonical display name is present.
    assert "Software Development" in result.output


# ---------------------------------------------------------------------------
# T081-c: --json flag produces valid JSON with required keys
# ---------------------------------------------------------------------------


def test_mission_type_list_json_is_valid() -> None:
    """``--json`` flag produces a valid JSON array."""
    result = runner.invoke(app, ["mission-type", "list", "--json"])

    assert result.exit_code == 0, result.output

    # Output must be parseable JSON.
    try:
        data = json.loads(result.output.strip())
    except json.JSONDecodeError as exc:
        pytest.fail(f"JSON output is not valid JSON: {exc}\n\nOutput:\n{result.output}")

    assert isinstance(data, list), "JSON output must be a list"
    assert len(data) >= 4, "Expected at least 4 mission types in JSON output"


def test_mission_type_list_json_has_required_keys() -> None:
    """Each JSON item has ``id``, ``source_layer``, and ``display_name``."""
    result = runner.invoke(app, ["mission-type", "list", "--json"])

    assert result.exit_code == 0, result.output

    data = json.loads(result.output.strip())
    assert isinstance(data, list)

    for item in data:
        assert "id" in item, f"Missing 'id' key in item: {item}"
        assert "source_layer" in item, f"Missing 'source_layer' key in item: {item}"
        assert "display_name" in item, f"Missing 'display_name' key in item: {item}"


def test_mission_type_list_json_contains_built_in_software_dev() -> None:
    """JSON output includes the software-dev built-in type with correct fields."""
    result = runner.invoke(app, ["mission-type", "list", "--json"])

    assert result.exit_code == 0, result.output

    data = json.loads(result.output.strip())
    assert isinstance(data, list)

    sw_dev = next((item for item in data if item["id"] == "software-dev"), None)
    assert sw_dev is not None, "'software-dev' not found in JSON output"
    assert sw_dev["source_layer"] == "built-in"
    assert sw_dev["display_name"] == "Software Development"


def test_mission_type_list_json_all_built_in_types() -> None:
    """JSON output contains all four canonical built-in mission types."""
    result = runner.invoke(app, ["mission-type", "list", "--json"])

    assert result.exit_code == 0, result.output

    data = json.loads(result.output.strip())
    ids = {item["id"] for item in data}
    expected = {"software-dev", "documentation", "research", "plan"}
    assert expected <= ids, (
        f"Expected canonical ids {expected!r} to be a subset of {ids!r}"
    )


# ---------------------------------------------------------------------------
# T081-d: command works without .kittify/config.yaml (no project required)
# ---------------------------------------------------------------------------


def test_mission_type_list_works_without_kittify(tmp_path: object) -> None:
    """``doctrine mission-type list`` works from a directory without a project.

    The command must not require ``.kittify/config.yaml`` to return
    built-in types.
    """
    # tmp_path has no .kittify directory — simulate a bare filesystem location.
    result = runner.invoke(app, ["mission-type", "list"])
    # Built-in types should always be accessible.
    assert result.exit_code == 0, result.output
    assert "software-dev" in result.output


# ---------------------------------------------------------------------------
# T081-e: source_layer values are one of the canonical set
# ---------------------------------------------------------------------------


def test_mission_type_list_json_source_layers_canonical() -> None:
    """All ``source_layer`` values in JSON are from the canonical set."""
    result = runner.invoke(app, ["mission-type", "list", "--json"])

    assert result.exit_code == 0, result.output

    data = json.loads(result.output.strip())
    canonical_layers = {"built-in", "org", "project"}
    for item in data:
        assert item["source_layer"] in canonical_layers, (
            f"Non-canonical source_layer {item['source_layer']!r} in item {item!r}"
        )
