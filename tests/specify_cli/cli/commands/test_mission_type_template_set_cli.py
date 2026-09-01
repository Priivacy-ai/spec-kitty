"""CLI tests for the WP01 ``template_set`` atomic cutover.

``mission-type show`` reads the resolved ``template_set`` mapping through
:func:`charter.activation.mission_type_profiles.resolve_mission_type_context` -- never
the retired ``MissionType.template_set`` model field (FR-003).

FR-003, NFR-001 (S-C, mission-step-creatability-01KXQA6R WP01).

Owner: ``src/specify_cli/cli/commands/mission_type.py`` (``:1491``/``:1509-1511``
indicative -- resolve by symbol, ``show_mission_type``).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.mission_type import app as mission_type_app

runner = CliRunner()

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_org_mission_type_yaml(
    org_root: Path,
    mission_type_id: str,
    *,
    action_sequence: list[str],
) -> None:
    """Write a minimal org-layer mission-type YAML (CL-005 flat layout)."""
    mt_dir = org_root / "mission_types"
    mt_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema_version: 1",
        f"id: {mission_type_id}",
        f"display_name: {mission_type_id.title()}",
        "action_sequence:",
        *(f"  - {step}" for step in action_sequence),
    ]
    (mt_dir / f"{mission_type_id}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

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


# ---------------------------------------------------------------------------
# FR-007 (WP07/T017) -- PLAN-FRESH2-001: three independently-hardcoded lying
# sites in ``show_mission_type`` for an activated non-built-in type: (1) the
# ``mt is None`` -> ``typer.Exit(1)`` hard-fail (queries the built-in-only
# repository instead of the layered lookup); (2) the JSON branch's hardcoded
# ``"source_layer": "built-in"``; (3) the Panel branch's own, independently
# hardcoded ``"[cyan]Source Layer:[/cyan] built-in"``. Both --json and the
# default Panel output are asserted in the SAME test so a fix landing only on
# site (2) cannot pass this test while site (3) is left lying -- the exact
# gap PLAN-FRESH2-001 HALTed the plan phase over.
# ---------------------------------------------------------------------------


def test_show_succeeds_and_reports_real_layer_for_activated_org_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-007: an activated org-layer type succeeds and reports layer "org"
    on BOTH the --json output and the default Panel output.

    Pre-fix: site (1) hard-fails with typer.Exit(1) for this type (it queries
    only the built-in-only ``MissionTypeRepository.default()``), so this test
    cannot even reach sites (2)/(3) until site (1) is fixed too.
    """
    from charter.offering.missions.mission_type_repository import MissionTypeRepository

    from charter.activation.pack_context import PackContext

    org_root = tmp_path / "org-pack"
    _write_org_mission_type_yaml(org_root, "qa", action_sequence=["design", "implement"])
    pack_context = PackContext(
        activated_kinds=frozenset(),
        activated_mission_types=frozenset({"qa"}),
        pack_roots=(tmp_path / "unused-builtin-placeholder", org_root),
        org_pack_names=("org-pack",),
        repo_root=tmp_path,
    )
    monkeypatch.chdir(tmp_path)
    MissionTypeRepository.cache_clear()
    try:
        with patch("charter.activation.pack_context.PackContext.from_config", return_value=pack_context):
            json_result = runner.invoke(mission_type_app, ["show", "qa", "--json"])
            panel_result = runner.invoke(mission_type_app, ["show", "qa"])
    finally:
        MissionTypeRepository.cache_clear()

    assert json_result.exit_code == 0, json_result.output
    data = json.loads(json_result.output.strip())
    assert data["source_layer"] == "org"
    assert data["action_sequence"] == ["design", "implement"]

    assert panel_result.exit_code == 0, panel_result.output
    assert "Source Layer: org" in panel_result.output


# ---------------------------------------------------------------------------
# PR-CONTRACT-001 (pre-merge squad, mission up-mission-type-seam-01KZY1JB):
# ``show_mission_type``'s try/except only catches ``UnknownMissionTypeError``
# around the ``resolve_mission_type_context`` call -- ``MissionTypeEmptyAction
# SequenceError`` (CL-003's own loud-fail exception) is a SIBLING
# ``ValueError`` subclass with no inheritance relationship, so it was
# propagating uncaught as a raw traceback for exactly the empty-action-
# sequence case this mission exists to make loud. Mirrors
# ``charter_mission_type_list``'s existing handling
# (src/specify_cli/cli/commands/charter/mission_type.py:151-160).
# ---------------------------------------------------------------------------


def _write_org_mission_type_yaml_no_action_sequence(
    org_root: Path,
    mission_type_id: str,
) -> None:
    """Write an org-layer mission-type YAML with NO ``action_sequence`` key
    (the exact CL-003 scenario -- loads clean, degrades to an empty sequence
    without the FR-004 loud-fail)."""
    mt_dir = org_root / "mission_types"
    mt_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema_version: 1",
        f"id: {mission_type_id}",
        f"display_name: {mission_type_id.title()}",
    ]
    (mt_dir / f"{mission_type_id}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_show_exits_cleanly_for_activated_org_type_with_empty_action_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR-CONTRACT-001: ``mission-type show <id>`` for an activated org type
    whose action sequence is empty must exit 1 with a clean error message --
    never an uncaught ``MissionTypeEmptyActionSequenceError`` traceback.
    """
    from charter.offering.missions.mission_type_repository import MissionTypeRepository

    from charter.activation.pack_context import PackContext

    org_root = tmp_path / "org-pack"
    _write_org_mission_type_yaml_no_action_sequence(org_root, "empty-qa")
    pack_context = PackContext(
        activated_kinds=frozenset(),
        activated_mission_types=frozenset({"empty-qa"}),
        pack_roots=(tmp_path / "unused-builtin-placeholder", org_root),
        org_pack_names=("org-pack",),
        repo_root=tmp_path,
    )
    monkeypatch.chdir(tmp_path)
    MissionTypeRepository.cache_clear()
    try:
        with patch("charter.activation.pack_context.PackContext.from_config", return_value=pack_context):
            result = runner.invoke(mission_type_app, ["show", "empty-qa"])
    finally:
        MissionTypeRepository.cache_clear()

    assert result.exit_code == 1, result.output
    assert result.exception is None or isinstance(
        result.exception, SystemExit
    ), f"expected a clean typer.Exit(1), got an uncaught exception: {result.exception!r}"
    assert "empty action sequence" in result.output
