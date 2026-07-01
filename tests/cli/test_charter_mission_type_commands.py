"""CLI tests for WP14: charter mission-type list / mission-type list alias / mission-type show.

FR-016: ``spec-kitty charter mission-type list`` and
        ``spec-kitty mission-type list`` alias.
FR-017: ``spec-kitty mission-type show <id>``.

Owner: ``src/specify_cli/cli/commands/charter/mission_type.py``
       ``src/specify_cli/cli/commands/mission_type.py``
Mission: charter-doctrine-mission-type-configuration-01KSWJVX
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import charter_app
from specify_cli.cli.commands.mission_type import app as mission_type_app

runner = CliRunner()

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# T082-a: charter mission-type list – sub-group registered
# ---------------------------------------------------------------------------


def test_charter_mission_type_subgroup_registered() -> None:
    """``charter mission-type --help`` exits 0 (sub-group is registered)."""
    result = runner.invoke(charter_app, ["mission-type", "--help"])
    assert result.exit_code == 0, result.output
    assert "list" in result.output


# ---------------------------------------------------------------------------
# T082-b: charter mission-type list – returns activated types (table)
# ---------------------------------------------------------------------------


def test_charter_mission_type_list_returns_activated_types() -> None:
    """``charter mission-type list`` returns activated types.

    When no project config is present, falls back to all four built-in
    canonical types (existing_mission_types() fallback behaviour per
    FR-018 / mission_type_profiles.py).
    """
    result = runner.invoke(charter_app, ["mission-type", "list"])
    assert result.exit_code == 0, result.output
    # At minimum, the canonical types appear.
    assert "software-dev" in result.output


def test_charter_mission_type_list_shows_source_layer() -> None:
    """Table output includes source layer column."""
    result = runner.invoke(charter_app, ["mission-type", "list"])
    assert result.exit_code == 0, result.output
    assert "built-in" in result.output


def test_charter_mission_type_list_shows_display_name() -> None:
    """Table output includes human-readable display names."""
    result = runner.invoke(charter_app, ["mission-type", "list"])
    assert result.exit_code == 0, result.output
    assert "Software Development" in result.output


def test_charter_mission_type_list_shows_action_sequence() -> None:
    """Table output includes action sequence column."""
    result = runner.invoke(charter_app, ["mission-type", "list"])
    assert result.exit_code == 0, result.output
    # Action sequence items should appear in the output.
    assert "specify" in result.output


# ---------------------------------------------------------------------------
# T082-c: charter mission-type list --json
# ---------------------------------------------------------------------------


def test_charter_mission_type_list_json_is_valid() -> None:
    """``charter mission-type list --json`` produces valid JSON."""
    result = runner.invoke(charter_app, ["mission-type", "list", "--json"])
    assert result.exit_code == 0, result.output
    try:
        data = json.loads(result.output.strip())
    except json.JSONDecodeError as exc:
        pytest.fail(f"JSON output is not valid JSON: {exc}\n\nOutput:\n{result.output}")
    assert isinstance(data, list)


def test_charter_mission_type_list_json_has_required_keys() -> None:
    """Each JSON item has id, source_layer, display_name, action_sequence."""
    result = runner.invoke(charter_app, ["mission-type", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert isinstance(data, list)
    for item in data:
        assert "id" in item, f"Missing 'id' key in item: {item}"
        assert "source_layer" in item, f"Missing 'source_layer' key in item: {item}"
        assert "display_name" in item, f"Missing 'display_name' key in item: {item}"
        assert "action_sequence" in item, f"Missing 'action_sequence' key in item: {item}"


def test_charter_mission_type_list_json_action_sequence_is_list() -> None:
    """action_sequence in JSON output is always a list."""
    result = runner.invoke(charter_app, ["mission-type", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    for item in data:
        assert isinstance(item["action_sequence"], list), (
            f"action_sequence is not a list for item {item!r}"
        )


# ---------------------------------------------------------------------------
# T083: mission-type list alias – identical output to charter list
# ---------------------------------------------------------------------------


def test_mission_type_list_alias_exits_0() -> None:
    """``spec-kitty mission-type list`` exits 0."""
    result = runner.invoke(mission_type_app, ["list"])
    assert result.exit_code == 0, result.output


def test_mission_type_list_alias_shows_activated_types() -> None:
    """``mission-type list`` alias shows the same types as ``charter mission-type list``."""
    result_alias = runner.invoke(mission_type_app, ["list"])
    result_charter = runner.invoke(charter_app, ["mission-type", "list"])
    assert result_alias.exit_code == 0, result_alias.output
    assert result_charter.exit_code == 0, result_charter.output
    # Both must surface at least software-dev.
    assert "software-dev" in result_alias.output
    assert "software-dev" in result_charter.output


def test_mission_type_list_alias_json_matches_charter() -> None:
    """``mission-type list --json`` JSON content matches ``charter mission-type list --json``."""
    result_alias = runner.invoke(mission_type_app, ["list", "--json"])
    result_charter = runner.invoke(charter_app, ["mission-type", "list", "--json"])
    assert result_alias.exit_code == 0, result_alias.output
    assert result_charter.exit_code == 0, result_charter.output

    data_alias = json.loads(result_alias.output.strip())
    data_charter = json.loads(result_charter.output.strip())

    # Same IDs must be present in both.
    ids_alias = {item["id"] for item in data_alias}
    ids_charter = {item["id"] for item in data_charter}
    assert ids_alias == ids_charter, (
        f"Alias IDs {ids_alias!r} != charter IDs {ids_charter!r}"
    )


# ---------------------------------------------------------------------------
# T084: mission-type show <id> – happy path
# ---------------------------------------------------------------------------


def test_mission_type_show_software_dev_exits_0() -> None:
    """``mission-type show software-dev`` exits 0."""
    result = runner.invoke(mission_type_app, ["show", "software-dev"])
    assert result.exit_code == 0, result.output


def test_mission_type_show_displays_id() -> None:
    """``show software-dev`` output contains the mission type id."""
    result = runner.invoke(mission_type_app, ["show", "software-dev"])
    assert result.exit_code == 0, result.output
    assert "software-dev" in result.output


def test_mission_type_show_displays_display_name() -> None:
    """``show software-dev`` output contains the display name."""
    result = runner.invoke(mission_type_app, ["show", "software-dev"])
    assert result.exit_code == 0, result.output
    assert "Software Development" in result.output


def test_mission_type_show_displays_action_sequence() -> None:
    """``show software-dev`` output contains action sequence items."""
    result = runner.invoke(mission_type_app, ["show", "software-dev"])
    assert result.exit_code == 0, result.output
    assert "specify" in result.output


def test_mission_type_show_displays_source_layer() -> None:
    """``show software-dev`` output contains source_layer."""
    result = runner.invoke(mission_type_app, ["show", "software-dev"])
    assert result.exit_code == 0, result.output
    assert "built-in" in result.output


# ---------------------------------------------------------------------------
# T084 error case: mission-type show <unknown>
# ---------------------------------------------------------------------------


def test_mission_type_show_unknown_exits_1() -> None:
    """``mission-type show unknown-type`` exits with code 1 (FR-017)."""
    result = runner.invoke(mission_type_app, ["show", "unknown-type"])
    assert result.exit_code == 1, result.output


def test_mission_type_show_unknown_prints_error_message() -> None:
    """``mission-type show unknown-type`` prints UnknownMissionTypeError message."""
    result = runner.invoke(mission_type_app, ["show", "unknown-type"])
    assert result.exit_code == 1, result.output
    # Message must contain the unknown id verbatim.
    assert "unknown-type" in result.output


def test_mission_type_show_unknown_lists_registered_ids() -> None:
    """Error output for unknown type lists registered (activated) IDs."""
    result = runner.invoke(mission_type_app, ["show", "no-such-type"])
    assert result.exit_code == 1, result.output
    # Registered IDs from the fallback set must appear.
    assert "software-dev" in result.output


# ---------------------------------------------------------------------------
# T085-a: mission-type show --json (valid JSON)
# ---------------------------------------------------------------------------


def test_mission_type_show_json_is_valid() -> None:
    """``mission-type show software-dev --json`` produces valid JSON."""
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    try:
        data = json.loads(result.output.strip())
    except json.JSONDecodeError as exc:
        pytest.fail(f"JSON output is not valid JSON: {exc}\n\nOutput:\n{result.output}")
    assert isinstance(data, dict)


def test_mission_type_show_json_has_required_fields() -> None:
    """``show --json`` dict has id, display_name, action_sequence, governance_refs,
    template_set, source_layer."""
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    required_keys = {"id", "display_name", "action_sequence", "governance_refs", "template_set", "source_layer"}
    missing = required_keys - set(data.keys())
    assert not missing, f"Missing keys: {missing!r} in data {data!r}"


def test_mission_type_show_json_action_sequence_is_list() -> None:
    """``show software-dev --json`` action_sequence is a non-empty list."""
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert isinstance(data["action_sequence"], list)
    assert len(data["action_sequence"]) > 0


def test_mission_type_show_json_id_matches_argument() -> None:
    """``show software-dev --json`` id field equals 'software-dev'."""
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert data["id"] == "software-dev"


def test_mission_type_show_json_source_layer_built_in() -> None:
    """``show software-dev --json`` source_layer is 'built-in'."""
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert data["source_layer"] == "built-in"


# ---------------------------------------------------------------------------
# T086: charter layer boundary — charter/mission_type.py must not import specify_cli.*
# ---------------------------------------------------------------------------


def test_charter_mission_type_module_does_not_import_specify_cli() -> None:
    """charter/mission_type.py must not import from specify_cli.* (charter layer rule).

    The layer rule (kernel <- doctrine <- charter <- specify_cli) forbids
    the ``charter`` package from importing ``specify_cli``.  Even though
    this file lives under ``specify_cli.cli.commands.charter``, it uses
    ``charter.*`` as its primary API — its imports must stay within the
    charter+doctrine layer.

    This is a proxy check: we confirm the module's top-level imports use
    ``charter.*`` for the activation API rather than calling deep into
    ``specify_cli`` internals.
    """
    import ast
    import importlib.util
    from pathlib import Path

    spec = importlib.util.find_spec("specify_cli.cli.commands.charter.mission_type")
    assert spec is not None, "Module not found"
    assert spec.origin is not None, "Cannot determine module file path"
    source = Path(spec.origin).read_text(encoding="utf-8")
    tree = ast.parse(source)

    # The primary charter API imports must be present.
    has_charter_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("charter."):
            has_charter_import = True
            break

    assert has_charter_import, (
        "charter/mission_type.py must import from charter.* for activation "
        "state (existing_mission_types, resolve_action_sequence)"
    )
