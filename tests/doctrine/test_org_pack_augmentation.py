"""WP04 — augmentation auto-emit single-source + parity (FR-028..FR-032).

Covers:

* T013 — single-source augmentation kind set (loader + validator derive from one).
* T014 — fragment-authored ``enhances`` / ``overrides`` / ``specializes_from``
  emission; field projection is data-driven from a single relation constant.
* T015 — augmentation eligibility extended to directive / toolguide /
  mission-step-contract (mission-type handled by T017).
* T016 — validator intent-aware parity for the newly-covered kinds via
  fragment edges.
* T017 — mission-type universe expansion (FR-032, decision locked); lockstep
  drift guard against ``charter.activations._ALLOWED_KINDS``.
* T018 — topology field-merge semantics for step contracts / mission types.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg.models import Relation
from doctrine.drg.org_pack_loader import (
    AUGMENTATION_ELIGIBLE_KINDS,
    AUGMENTATION_RELATIONS,
    TOPOLOGY_KINDS,
    TopologyMergeError,
    _MISSION_TYPE_UNIVERSE_EXTENSION,
    _ORG_DRG_CANONICAL_KINDS,
    augmentation_plural_kinds,
    load_org_pack,
    merge_topology_artifact,
)

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_fragment(pack_root: Path, *, edges: str = "edges: []\n") -> Path:
    drg_dir = pack_root / "drg"
    drg_dir.mkdir(parents=True, exist_ok=True)
    fragment = drg_dir / "fragment.yaml"
    fragment.write_text(
        "pack_name: testpack\n"
        "source_kind: local_path\n"
        'source_ref: "/tmp/pack"\n'
        "layer_index: 1\n"
        "nodes: []\n" + edges,
        encoding="utf-8",
    )
    return fragment


# ---------------------------------------------------------------------------
# T013 — single-source augmentation kind set (FR-030)
# ---------------------------------------------------------------------------


def test_loader_and_validator_share_one_augmentation_source() -> None:
    """FR-030: the validator set is *derived* from the loader's single source."""
    from specify_cli.doctrine.pack_validator import _AUGMENTATION_PLURAL_KINDS

    assert augmentation_plural_kinds() == _AUGMENTATION_PLURAL_KINDS


def test_eligible_set_is_artifactkind_minus_template_plus_mission_type() -> None:
    """FR-030/FR-028/FR-032: one definition covering all 9 eligible kinds.

    The set is the eight ``ArtifactKind`` members (minus ``template``) plus the
    mission-type extension; adding a kind is a one-line change.
    """
    expected_singulars = {
        k.value for k in ArtifactKind if k is not ArtifactKind.TEMPLATE
    } | {"mission_type"}
    assert set(AUGMENTATION_ELIGIBLE_KINDS) == expected_singulars
    assert ArtifactKind.TEMPLATE.value not in AUGMENTATION_ELIGIBLE_KINDS


def test_relations_single_source_includes_specializes_from() -> None:
    """T014: one relation constant incl. lineage ``specializes_from``."""
    assert set(AUGMENTATION_RELATIONS) == {
        Relation.ENHANCES,
        Relation.OVERRIDES,
        Relation.SPECIALIZES_FROM,
    }


# ---------------------------------------------------------------------------
# T014 — fragment-authored emission incl. lineage
# ---------------------------------------------------------------------------


def test_fragment_authored_augmentation_and_lineage_edges_survive(tmp_path: Path) -> None:
    """T014: fragment-authored enhances/overrides/specializes_from flow through.

    The DRG fragment is the authoring authority (data-model §3). Edges the pack
    author writes directly are preserved by the loader without depending on
    artifact fields.
    """
    pack_root = tmp_path / "pack"
    _write_fragment(
        pack_root,
        edges=(
            "edges:\n"
            "  - source: tactic:pack-tactic\n"
            "    target: tactic:builtin-tactic\n"
            "    relation: enhances\n"
            "  - source: directive:pack-dir\n"
            "    target: directive:builtin-dir\n"
            "    relation: overrides\n"
            "  - source: agent_profile:child\n"
            "    target: agent_profile:parent\n"
            "    relation: specializes_from\n"
        ),
    )

    fragment = load_org_pack("testpack", pack_root, layer_index=1)
    relations = {(e.source, e.target, e.relation) for e in fragment.edges}
    assert ("tactic:pack-tactic", "tactic:builtin-tactic", "enhances") in relations
    assert ("directive:pack-dir", "directive:builtin-dir", "overrides") in relations
    assert (
        "agent_profile:child",
        "agent_profile:parent",
        "specializes_from",
    ) in relations


def test_specializes_from_field_projects_lineage_edge(tmp_path: Path) -> None:
    """T014: lineage auto-emits via the single relation list (FR-001 plumbing).

    During the migration window the field projection remains; ``specializes_from``
    is now in the relation list, so an agent profile carrying that field emits a
    lineage edge with no per-relation special-casing.
    """
    pack_root = tmp_path / "pack"
    profiles_dir = pack_root / "agent_profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "child.agent.yaml").write_text(
        "id: child\nspecializes_from: parent\n", encoding="utf-8"
    )
    _write_fragment(pack_root)

    fragment = load_org_pack("testpack", pack_root, layer_index=1)
    lineage = [
        e
        for e in fragment.edges
        if e.relation == Relation.SPECIALIZES_FROM.value
        and e.source == "agent_profile:child"
        and e.target == "agent_profile:parent"
    ]
    assert lineage, f"lineage edge not auto-emitted. edges={fragment.edges}"


# ---------------------------------------------------------------------------
# T015 — augmentation eligibility for the 4 newly-covered kinds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "plural",
    ["directives", "toolguides", "mission_step_contracts", "mission_types"],
)
def test_newly_covered_kinds_are_augmentation_eligible(plural: str) -> None:
    """T015/FR-028/FR-032: the four new kinds joined the eligible set."""
    assert plural in augmentation_plural_kinds()


def test_directive_field_projection_emits_edge(tmp_path: Path) -> None:
    """T015: a directive declaring ``enhances`` projects an ENHANCES edge."""
    pack_root = tmp_path / "pack"
    directives_dir = pack_root / "directives"
    directives_dir.mkdir(parents=True)
    (directives_dir / "d.directive.yaml").write_text(
        "id: DIRECTIVE_900\nenhances: DIRECTIVE_001\n", encoding="utf-8"
    )
    _write_fragment(pack_root)

    fragment = load_org_pack("testpack", pack_root, layer_index=1)
    assert any(
        e.source == "directive:DIRECTIVE_900"
        and e.target == "directive:DIRECTIVE_001"
        and e.relation == Relation.ENHANCES.value
        for e in fragment.edges
    )


# ---------------------------------------------------------------------------
# T016 — validator intent-aware parity for new kinds (fragment edges)
# ---------------------------------------------------------------------------


def _fragment_intent(drg_dir: Path):
    from specify_cli.doctrine.pack_validator import _collect_fragment_edge_intent

    return _collect_fragment_edge_intent(drg_dir)


def test_fragment_edge_intent_unknown_target_hard_errors(tmp_path: Path) -> None:
    """T016/FR-031: a fragment ``overrides`` of an unknown built-in hard-errors."""
    from specify_cli.doctrine.pack_validator import (
        _intent_aware_collision_messages_from_edges,
    )

    drg_dir = tmp_path / "drg"
    drg_dir.mkdir()
    (drg_dir / "f.graph.yaml").write_text(
        'schema_version: "1.0"\n'
        'generated_at: "2026-06-01T00:00:00+00:00"\n'
        'generated_by: "test"\n'
        "nodes: []\n"
        "edges:\n"
        '  - source: "directive:pack-dir"\n'
        '    target: "directive:does-not-exist"\n'
        '    relation: "overrides"\n',
        encoding="utf-8",
    )
    intent = _fragment_intent(drg_dir)
    errors, advisories = _intent_aware_collision_messages_from_edges(
        intent, {"directives": {"DIRECTIVE_001"}}, {}
    )
    assert any(e.category == "unknown_target" for e in errors)
    assert advisories == []


def test_fragment_edge_intent_conflict_when_both_declared(tmp_path: Path) -> None:
    """T016/FR-031: enhances + overrides on one source -> intent_conflict."""
    from specify_cli.doctrine.pack_validator import (
        _intent_aware_collision_messages_from_edges,
    )

    drg_dir = tmp_path / "drg"
    drg_dir.mkdir()
    (drg_dir / "f.graph.yaml").write_text(
        'schema_version: "1.0"\n'
        'generated_at: "2026-06-01T00:00:00+00:00"\n'
        'generated_by: "test"\n'
        "nodes: []\n"
        "edges:\n"
        '  - source: "toolguide:pack-tg"\n'
        '    target: "toolguide:builtin-tg"\n'
        '    relation: "enhances"\n'
        '  - source: "toolguide:pack-tg"\n'
        '    target: "toolguide:builtin-tg"\n'
        '    relation: "overrides"\n',
        encoding="utf-8",
    )
    intent = _fragment_intent(drg_dir)
    errors, _ = _intent_aware_collision_messages_from_edges(
        intent, {"toolguides": {"builtin-tg"}}, {}
    )
    assert any(e.category == "intent_conflict" for e in errors)


def test_fragment_edge_valid_intent_suppresses_advisory(tmp_path: Path) -> None:
    """T016/FR-031: a valid declared intent emits no error and no advisory."""
    from specify_cli.doctrine.pack_validator import (
        _intent_aware_collision_messages_from_edges,
    )

    drg_dir = tmp_path / "drg"
    drg_dir.mkdir()
    (drg_dir / "f.graph.yaml").write_text(
        'schema_version: "1.0"\n'
        'generated_at: "2026-06-01T00:00:00+00:00"\n'
        'generated_by: "test"\n'
        "nodes: []\n"
        "edges:\n"
        '  - source: "directive:pack-dir"\n'
        '    target: "directive:DIRECTIVE_001"\n'
        '    relation: "enhances"\n',
        encoding="utf-8",
    )
    intent = _fragment_intent(drg_dir)
    errors, advisories = _intent_aware_collision_messages_from_edges(
        intent, {"directives": {"DIRECTIVE_001"}}, {}
    )
    assert errors == []
    assert advisories == []


def test_fragment_intent_ignores_lineage_relation(tmp_path: Path) -> None:
    """``specializes_from`` is lineage, not augmentation intent — never folded in."""
    drg_dir = tmp_path / "drg"
    drg_dir.mkdir()
    (drg_dir / "f.graph.yaml").write_text(
        'schema_version: "1.0"\n'
        'generated_at: "2026-06-01T00:00:00+00:00"\n'
        'generated_by: "test"\n'
        "nodes: []\n"
        "edges:\n"
        '  - source: "agent_profile:child"\n'
        '    target: "agent_profile:parent"\n'
        '    relation: "specializes_from"\n',
        encoding="utf-8",
    )
    assert _fragment_intent(drg_dir) == {}


# ---------------------------------------------------------------------------
# T017 — mission-type universe expansion + lockstep drift guard (FR-032)
# ---------------------------------------------------------------------------


def test_mission_types_in_canonical_universe() -> None:
    """FR-032 (DIRECTIVE_003): mission types joined the canonical universe."""
    assert "mission_types" in _ORG_DRG_CANONICAL_KINDS
    # The legacy mission-step-contract alias is still accepted on input.
    assert "mission_step_contracts" in _ORG_DRG_CANONICAL_KINDS


def test_mission_type_fragment_augmentation_validates(tmp_path: Path) -> None:
    """FR-032: a mission-type fragment node validates (not silently dropped)."""
    from doctrine.drg.org_pack_loader import OrgDRGFragment

    fragment = OrgDRGFragment.model_validate(
        {
            "pack_name": "acme",
            "source_kind": "local_path",
            "source_ref": "/tmp/acme",
            "layer_index": 1,
            "provenance_marker": "org",
            "nodes": [
                {"id": "custom-mission", "kind": "mission_types", "title": "Custom"}
            ],
            "edges": [
                {
                    "source": "mission_type:custom-mission",
                    "target": "mission_type:software-dev",
                    "relation": "enhances",
                }
            ],
        }
    )
    node = fragment.nodes[0]
    assert node.kind == "mission_types"
    assert fragment.edges[0].relation == "enhances"


def test_mission_type_singular_alias_resolves_to_plural() -> None:
    """FR-032: the ``mission_type`` singular input form resolves to the plural."""
    from doctrine.drg.org_pack_loader import OrgDRGFragment

    fragment = OrgDRGFragment.model_validate(
        {
            "pack_name": "acme",
            "source_kind": "local_path",
            "source_ref": "/tmp/acme",
            "layer_index": 1,
            "nodes": [{"id": "x", "kind": "mission_type", "title": "X"}],
            "edges": [],
        }
    )
    assert fragment.nodes[0].kind == "mission_types"


def test_lockstep_drift_guard_against_allowed_kinds() -> None:
    """FR-032 lockstep: the org-pack universe == ``_ALLOWED_KINDS`` ∪ mission-type.

    This is the contract-test sweep the spec requires: neither
    ``charter.activations._ALLOWED_KINDS`` nor the loader universe may drift
    silently, and mission types must never be dropped. The org-pack universe
    additionally retains the ``mission_step_contracts`` backward-compat alias.
    """
    from charter.activations import _ALLOWED_KINDS

    # Canonical forms only (drop the loader's backward-compat alias for the
    # comparison): the org-pack universe must equal the activation allowed set
    # plus exactly the mission-type extension.
    canonical_universe = _ORG_DRG_CANONICAL_KINDS - {"mission_step_contracts"} - {
        "mission_type"
    }
    # _ALLOWED_KINDS uses ``mission_step_contracts``; the loader canonicalises it
    # to ``mission_steps``. Normalise that one rename for the lockstep equality.
    normalised_allowed = (_ALLOWED_KINDS - {"mission_step_contracts"}) | {
        "mission_steps"
    }
    assert canonical_universe == normalised_allowed | _MISSION_TYPE_UNIVERSE_EXTENSION
    assert frozenset({"mission_types"}) == _MISSION_TYPE_UNIVERSE_EXTENSION


# ---------------------------------------------------------------------------
# T018 — topology field-merge semantics (FR-029, ADR 2026-05-16-1)
# ---------------------------------------------------------------------------


def test_topology_kinds_are_step_contract_and_mission_type() -> None:
    assert frozenset({"mission_step_contract", "mission_type"}) == TOPOLOGY_KINDS


def test_overrides_is_full_replacement() -> None:
    """FR-029: ``overrides`` fully replaces the base topology artifact."""
    base = {"id": "s", "steps": [{"id": "a"}, {"id": "b"}]}
    overlay = {"id": "s", "steps": [{"id": "z"}]}
    merged = merge_topology_artifact(base, overlay, mode=Relation.OVERRIDES)
    assert merged == overlay
    assert merged is not overlay  # deep-copied, inputs untouched


def test_enhances_preserves_base_sequence_when_overlay_omits_it() -> None:
    """FR-029: an enhances overlay that omits ``steps`` keeps base ordering."""
    base = {"id": "s", "title": "Base", "steps": [{"id": "a"}, {"id": "b"}]}
    overlay = {"id": "s", "title": "Enhanced"}
    merged = merge_topology_artifact(base, overlay, mode=Relation.ENHANCES)
    assert merged["title"] == "Enhanced"  # field-level override
    assert [s["id"] for s in merged["steps"]] == ["a", "b"]  # ordering preserved


def test_enhances_merges_step_io_and_keeps_order() -> None:
    """FR-029: step I/O contracts merge; ordering follows the overlay."""
    base = {
        "id": "s",
        "steps": [
            {"id": "a", "inputs": ["x"], "outputs": ["y"]},
            {"id": "b", "inputs": ["p"]},
        ],
    }
    overlay = {
        "id": "s",
        "steps": [
            {"id": "a", "title": "Step A refined"},
            {"id": "b", "inputs": ["p"], "title": "Step B"},
        ],
    }
    merged = merge_topology_artifact(base, overlay, mode=Relation.ENHANCES)
    assert [s["id"] for s in merged["steps"]] == ["a", "b"]
    step_a = merged["steps"][0]
    assert step_a["title"] == "Step A refined"
    # base I/O contract preserved (overlay did not restate it)
    assert step_a["inputs"] == ["x"]
    assert step_a["outputs"] == ["y"]


def test_enhances_rejects_silent_step_drop() -> None:
    """FR-029: an enhances overlay that drops a base step fails closed."""
    base = {"id": "s", "steps": [{"id": "a"}, {"id": "b"}]}
    overlay = {"id": "s", "steps": [{"id": "a"}]}
    with pytest.raises(TopologyMergeError, match="silently drops"):
        merge_topology_artifact(base, overlay, mode=Relation.ENHANCES)


def test_enhances_rejects_stripping_step_io() -> None:
    """FR-029: an enhances overlay may not strip a step's input/output contract."""
    base = {"id": "s", "steps": [{"id": "a", "inputs": ["x"]}]}
    overlay = {"id": "s", "steps": [{"id": "a", "inputs": []}]}
    with pytest.raises(TopologyMergeError, match="strips"):
        merge_topology_artifact(base, overlay, mode=Relation.ENHANCES)


def test_merge_rejects_non_augmentation_relation() -> None:
    with pytest.raises(ValueError, match="ENHANCES / OVERRIDES"):
        merge_topology_artifact({"id": "s"}, {"id": "s"}, mode=Relation.REQUIRES)
