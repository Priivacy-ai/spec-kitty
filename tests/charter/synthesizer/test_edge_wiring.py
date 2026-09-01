"""Tests for #3052 edge wiring (WP07): evidence-gated source_urns population.

FR-012 / NFR-007: ``charter synthesize`` emits an edge wherever the interview
mapping declares an upstream doctrine relationship, and emits NO edge where no
such relationship is declared (no fabrication).

The ONLY currently-empty consumer-pack section with genuine declared-evidence
is ``mission_type``: the interview answer, when it names a shipped
mission-type id, *is* the ``mission_type:<id>`` URN (built-in
``NodeKind.MISSION_TYPE`` node) -- an identity match, not an inferred
relationship. This mirrors the existing ``selected_directives`` ->
``how-we-apply-DIRECTIVE_xxx`` pattern, whose evidence is likewise the
verbatim directive id the user selected.

The other currently-empty sections (``testing_philosophy``,
``neutrality_posture``, ``risk_appetite``, ``quality_gates``,
``review_policy``, ``documentation_policy``) are free-text interview prompts
with no fixed vocabulary tying an answer to an existing DRG URN -- wiring
them would require inventing a relationship the interview never declared, so
they are exercised here only as no-fabrication negative cases.

Evidence-population is gated on the run's OWN ``drg_snapshot`` actually
carrying the referenced node (``targets._mission_type_evidence_urns``) --
``resolve_sections()`` cannot itself confirm this (R-9 forbids DRG access at
interview-resolution time), so the presence check lives in
``targets.build_targets()``, which already receives ``drg_snapshot``. This is
what keeps a narrow/incomplete DRG snapshot (e.g. a test double covering an
unrelated directive) from turning a real identity match into a dangling-URN
``ProjectDRGValidationError`` -- see the regression this guards in the
"withheld" tests below.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.offering.drg.loader import merge_layers
from charter.offering.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from charter.offering.drg.validator import validate_graph
from charter.offering.missions.mission_type_repository import builtin_mission_type_ids

from charter.activation.synthesizer.fixture_adapter import FixtureAdapter
from charter.activation.synthesizer.interview_mapping import (
    mission_type_urn_candidate,
    resolve_sections,
)
from charter.activation.synthesizer.project_drg import emit_project_layer
from charter.activation.synthesizer.request import SynthesisRequest, SynthesisTarget
from charter.activation.synthesizer.synthesize_pipeline import run_all
from charter.activation.synthesizer.targets import build_targets

pytestmark = [pytest.mark.unit]


_GENERATED_AT = "2026-04-17T00:00:00+00:00"


def _empty_built_in_drg(
    nodes: list[DRGNode] | None = None,
    edges: list[DRGEdge] | None = None,
) -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at=_GENERATED_AT,
        generated_by="test-built-in-layer",
        nodes=nodes or [],
        edges=edges or [],
    )


# ---------------------------------------------------------------------------
# mission_type_urn_candidate() -- the pure identity-match helper
# ---------------------------------------------------------------------------


class TestMissionTypeUrnCandidate:
    """The declared-evidence lookup is a verbatim identity match, nothing more."""

    def test_every_shipped_mission_type_id_matches_hyphen_form(self) -> None:
        for mission_type_id in builtin_mission_type_ids():
            assert mission_type_urn_candidate(mission_type_id) == (
                f"mission_type:{mission_type_id}"
            )

    def test_underscore_form_matches_the_same_urn(self) -> None:
        """`_normalize_section_selector` treats hyphen/underscore as equivalent."""
        underscore_form = "software_dev"
        assert "software-dev" in builtin_mission_type_ids()
        assert mission_type_urn_candidate(underscore_form) == "mission_type:software-dev"

    def test_free_text_answer_returns_none(self) -> None:
        assert mission_type_urn_candidate("Ship trustworthy agent workflows") is None

    def test_blank_answer_returns_none(self) -> None:
        assert mission_type_urn_candidate("") is None


# ---------------------------------------------------------------------------
# Positive: declared evidence, corroborated by the run's DRG snapshot
# ---------------------------------------------------------------------------


class TestMissionTypeEvidenceProducesAnEdge:
    """A mission_type answer naming a shipped id, with the node present in
    the run's own DRG snapshot, wires the edge instead of `edges: []`."""

    def test_source_urns_populated_on_the_built_target(self) -> None:
        interview_snapshot = {"mission_type": "software-dev"}
        drg_snapshot = {
            "nodes": [{"urn": "mission_type:software-dev", "kind": "mission_type"}],
            "edges": [],
            "schema_version": "1.0",
        }

        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)

        mission_type_target = next(
            t for t in targets if t.source_section == "mission_type"
        )
        assert mission_type_target.source_urns == ("mission_type:software-dev",)

    def test_underscore_form_also_wires_the_edge(self) -> None:
        """The synthesis-canonical answer form (`software_dev`, per the widely
        used `_INTERVIEW_SECTION_ALIASES`/`_MISSION_IDENTIFIER_ANSWERS`
        convention) is evidence too -- the same URN, hyphen-normalized."""
        interview_snapshot = {"mission_type": "software_dev"}
        drg_snapshot = {
            "nodes": [{"urn": "mission_type:software-dev", "kind": "mission_type"}],
            "edges": [],
            "schema_version": "1.0",
        }

        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)

        mission_type_target = next(
            t for t in targets if t.source_section == "mission_type"
        )
        assert mission_type_target.source_urns == ("mission_type:software-dev",)

    def test_overlay_contains_the_edge_not_an_empty_list(self) -> None:
        """emit_project_layer's source_urns -> edge derivation (project_drg.py)
        emits the declared edge; the overlay is not `edges: []` (FR-012)."""
        interview_snapshot = {"mission_type": "research"}
        drg_snapshot = {
            "nodes": [{"urn": "mission_type:research", "kind": "mission_type"}],
            "edges": [],
            "schema_version": "1.0",
        }
        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)

        # Post-tasks squad amendment #1: this evidence's URN ("mission_type:
        # research") has no pre-existing built-in edge, so emission emits
        # rather than raising the FR-020/EC-6 additive-only guard.
        built_in_drg = _empty_built_in_drg(
            nodes=[
                DRGNode(
                    urn="mission_type:research",
                    kind=NodeKind.MISSION_TYPE,
                    label="Research",
                )
            ]
        )
        overlay = emit_project_layer(
            targets, spec_kitty_version="test", built_in_drg=built_in_drg
        )

        mission_type_target = next(
            t for t in targets if t.source_section == "mission_type"
        )
        edges_from_target = [
            e for e in overlay.edges if e.source == mission_type_target.urn
        ]
        assert edges_from_target != []
        edge = edges_from_target[0]
        assert edge.target == "mission_type:research"
        assert edge.relation == Relation.REQUIRES

    def test_merged_overlay_validates_cleanly(self) -> None:
        """The DRG lint's structural gate (`validate_graph`) passes on the
        merged built-in + project overlay -- no dangling reference, no
        duplicate triple, no cycle introduced by the new edge."""
        interview_snapshot = {"mission_type": "documentation"}
        drg_snapshot = {
            "nodes": [{"urn": "mission_type:documentation", "kind": "mission_type"}],
            "edges": [],
            "schema_version": "1.0",
        }
        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)

        built_in_drg = _empty_built_in_drg(
            nodes=[
                DRGNode(
                    urn="mission_type:documentation",
                    kind=NodeKind.MISSION_TYPE,
                    label="Documentation",
                )
            ]
        )
        overlay = emit_project_layer(
            targets, spec_kitty_version="test", built_in_drg=built_in_drg
        )

        merged = merge_layers(built_in_drg, overlay)
        assert validate_graph(merged) == []


# ---------------------------------------------------------------------------
# Negative: no declared evidence anywhere -> no fabrication (NFR-007)
# ---------------------------------------------------------------------------


class TestNoFabricationForFreeTextSections:
    """Sections with no fixed vocabulary tying the answer to a DRG URN must
    never synthesize source_urns -- `edges: []` stays `edges: []`."""

    @pytest.mark.parametrize(
        ("section", "answer"),
        [
            ("testing_philosophy", "test-driven development with high coverage"),
            ("neutrality_posture", "balanced"),
            ("risk_appetite", "moderate"),
            ("quality_gates", "coverage >= 90%"),
            ("review_policy", "two reviewers required"),
            ("documentation_policy", "all public APIs must be documented"),
        ],
    )
    def test_free_text_section_never_populates_source_urns(
        self, section: str, answer: str
    ) -> None:
        interview_snapshot = {section: answer}
        drg_snapshot: dict = {"nodes": [], "edges": [], "schema_version": "1.0"}

        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)

        matching = [t for t in targets if t.source_section == section]
        assert matching, f"expected at least one target for section {section!r}"
        for target in matching:
            assert target.source_urns == ()

    @pytest.mark.parametrize(
        ("section", "answer"),
        [
            ("testing_philosophy", "test-driven development with high coverage"),
            ("neutrality_posture", "balanced"),
            ("risk_appetite", "moderate"),
        ],
    )
    def test_free_text_section_overlay_edges_stay_empty(
        self, section: str, answer: str
    ) -> None:
        interview_snapshot = {section: answer}
        drg_snapshot: dict = {"nodes": [], "edges": [], "schema_version": "1.0"}

        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)

        overlay = emit_project_layer(
            targets, spec_kitty_version="test", built_in_drg=_empty_built_in_drg()
        )
        assert overlay.edges == []


class TestMissionTypeEvidenceWithheldWithoutCorroboration:
    """A verbatim identity match alone is not enough -- the run's own DRG
    snapshot must actually carry the node, or nothing is wired (NFR-007)."""

    def test_shipped_id_answer_but_drg_snapshot_lacks_the_node(self) -> None:
        """A minimal/narrow DRG snapshot (e.g. a test double scoped to an
        unrelated directive) never turns a real identity match into a
        dangling-URN validation failure -- this is the exact regression a
        naive (ungated) implementation introduced against the widely-shared
        `minimal_drg_snapshot` test fixture."""
        interview_snapshot = {"mission_type": "software-dev"}
        drg_snapshot = {
            "nodes": [{"urn": "directive:DIRECTIVE_003", "kind": "directive"}],
            "edges": [],
            "schema_version": "1.0",
        }

        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)  # must not raise

        mission_type_target = next(
            t for t in targets if t.source_section == "mission_type"
        )
        assert mission_type_target.source_urns == ()

        overlay = emit_project_layer(
            targets, spec_kitty_version="test", built_in_drg=_empty_built_in_drg()
        )
        assert overlay.edges == []

    def test_answer_not_naming_a_shipped_id_is_never_evidence(self) -> None:
        """Even with a DRG snapshot that *does* carry mission_type nodes, an
        answer that does not name one of them is not evidence."""
        interview_snapshot = {"mission_type": "Ship trustworthy agent workflows"}
        drg_snapshot = {
            "nodes": [{"urn": "mission_type:software-dev", "kind": "mission_type"}],
            "edges": [],
            "schema_version": "1.0",
        }

        sections = resolve_sections(interview_snapshot)
        targets = build_targets(interview_snapshot, sections, drg_snapshot)

        mission_type_target = next(
            t for t in targets if t.source_section == "mission_type"
        )
        assert mission_type_target.source_urns == ()


# ---------------------------------------------------------------------------
# End-to-end: full pipeline (resolve -> build -> adapter) via a recorded
# fixture (T029 -- the FixtureAdapter is inputs-hash-keyed and raises on a
# miss; a source_urns-bearing target changes the inputs hash, so this
# exercises a NEWLY recorded fixture at
# tests/charter/fixtures/synthesizer/directive/mission-type-scope-directive/).
# ---------------------------------------------------------------------------


class TestFullPipelineWithRecordedFixture:
    def test_run_all_generates_the_evidence_backed_target(self) -> None:
        target = SynthesisTarget(
            kind="directive",
            slug="mission-type-scope-directive",
            title="Mission Type Scope Directive",
            artifact_id="PROJECT_001",
            source_section="mission_type",
        )
        request = SynthesisRequest(
            target=target,
            interview_snapshot={"mission_type": "software-dev"},
            doctrine_snapshot={"directives": {}, "tactics": {}, "styleguides": {}},
            drg_snapshot={
                "nodes": [{"urn": "mission_type:software-dev", "kind": "mission_type"}],
                "edges": [],
                "schema_version": "1.0",
            },
            run_id="01KPE222CD1MMCYEGB3ZCY51VR",
        )
        fixture_root = Path(__file__).parent.parent / "fixtures" / "synthesizer"
        adapter = FixtureAdapter(fixture_root=fixture_root)

        results = run_all(request, adapter=adapter)

        assert len(results) == 1
        body, provenance = results[0]
        assert body["id"] == "PROJECT_001"
        assert list(provenance.source_urns) == ["mission_type:software-dev"]
