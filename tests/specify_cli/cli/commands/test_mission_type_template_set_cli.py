"""CLI tests for the WP01 ``template_set`` atomic cutover.

``mission-type show`` reads the resolved ``template_set`` mapping through
:func:`charter.mission_type_profiles.resolve_mission_type_context` -- never
the retired ``MissionType.template_set`` model field (FR-003).

FR-003, NFR-001 (S-C, mission-step-creatability-01KXQA6R WP01).

Owner: ``src/specify_cli/cli/commands/mission_type.py`` (``:1491``/``:1509-1511``
indicative -- resolve by symbol, ``show_mission_type``).
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.mission_type import app as mission_type_app

runner = CliRunner()

pytestmark = [pytest.mark.unit, pytest.mark.fast]

#: software-dev's byte-for-byte pre-cutover template_set (NFR-001), in the
#: canonical sequence_index order: specify (idx0) projects "spec", plan
#: (idx1) projects "plan".
_EXPECTED_SOFTWARE_DEV_TEMPLATE_SET = {
    "spec": "spec-template.md",
    "plan": "plan-template.md",
}


# ---------------------------------------------------------------------------
# --json: resolved-context content + determinism
# ---------------------------------------------------------------------------


def test_show_json_template_set_matches_resolved_context() -> None:
    """``--json`` template_set carries the resolved mapping, not the retired field."""
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert data["template_set"] == _EXPECTED_SOFTWARE_DEV_TEMPLATE_SET


def test_show_json_template_set_key_order_is_sequence_index_order() -> None:
    """NFR-001: --json key order is deterministic sequence_index order ({spec, plan}).

    ``json.loads`` preserves the source's key insertion order when building
    the resulting ``dict`` (Python 3.7+), so a canonical-order regression
    (e.g. reintroducing a ``set``-based step traversal) surfaces here as
    "plan" preceding "spec" in ``template_set``'s own key order -- distinct
    from ``action_sequence``, which also contains the substrings "spec"/"plan"
    and would give a false pass/fail if compared via raw string search.
    """
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert list(data["template_set"].keys()) == ["spec", "plan"]


def test_show_json_template_set_is_plain_dict_not_mappingproxy() -> None:
    """Regression: MappingProxyType is not JSON-serializable -- the CLI must dict()-wrap it.

    Before the FR-003 migration this would raise ``TypeError`` inside
    ``json.dumps`` rather than produce a clean exit -- this test pins the
    fix, not just the eventual value.
    """
    result = runner.invoke(mission_type_app, ["show", "software-dev", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert isinstance(data["template_set"], dict)


# ---------------------------------------------------------------------------
# Human panel
# ---------------------------------------------------------------------------


def test_show_panel_includes_template_set_line() -> None:
    """Human panel output still surfaces the resolved template mapping."""
    result = runner.invoke(mission_type_app, ["show", "software-dev"])
    assert result.exit_code == 0, result.output
    assert "Template Set:" in result.output
    assert "spec=spec-template.md" in result.output
    assert "plan=plan-template.md" in result.output


# ---------------------------------------------------------------------------
# documentation -- Concern B authored its spec/plan template refs
# (mission-step-creatability-01KXQA6R WP02, reconciled here by WP05); the CLI
# now surfaces a real mapping, mirroring the software-dev assertions above
# rather than the pre-Concern-B fail-closed ``null``/``(none)`` shape.
# ---------------------------------------------------------------------------

_EXPECTED_DOCUMENTATION_TEMPLATE_SET = {
    "spec": "documentation-spec-template.md",
    "plan": "documentation-plan-template.md",
}


def test_show_documentation_json_template_set_matches_resolved_context() -> None:
    """``--json`` template_set carries documentation's authored mapping (WP05
    reconciliation of the WP02 Concern B authoring; formerly asserted
    ``None`` pre-authoring -- see ``test_show_json_template_set_matches_resolved_context``
    for the software-dev equivalent)."""
    result = runner.invoke(mission_type_app, ["show", "documentation", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output.strip())
    assert data["template_set"] == _EXPECTED_DOCUMENTATION_TEMPLATE_SET


def test_show_documentation_panel_includes_template_set_line() -> None:
    """Human panel output surfaces documentation's resolved template mapping
    (formerly asserted the fail-closed ``(none)`` placeholder pre-authoring)."""
    result = runner.invoke(mission_type_app, ["show", "documentation"])
    assert result.exit_code == 0, result.output
    assert "Template Set:" in result.output
    assert "spec=documentation-spec-template.md" in result.output
    assert "plan=documentation-plan-template.md" in result.output
