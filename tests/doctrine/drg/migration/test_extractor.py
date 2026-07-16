"""Tests for doctrine.drg.migration.extractor.

Includes:
- T012/T013 unit tests against real shipped doctrine
- T016 end-to-end graph generation
- T017 edge-count completeness validation
- Idempotency verification
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from doctrine.drg.migration.calibrator import measure_surface
from doctrine.drg.migration.extractor import (
    _SKIP_REF_TYPES,
    _partition_by_kind,
    extract_action_edges,
    extract_artifact_edges,
    extract_mission_type_edges,
    generate_graph,
)
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.query import resolve_context
from doctrine.drg.validator import validate_graph

# Path to the shipped doctrine root inside the repo.

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]
DOCTRINE_ROOT: Path = Path(__file__).resolve().parents[4] / "src" / "doctrine"

_yaml = YAML(typ="safe")


def _count_inline_refs(doctrine_root: Path) -> int:  # noqa: C901
    """Count every inline reference field entry across all shipped artifacts.

    This mirrors the extraction logic but only counts -- used for the T017
    completeness assertion.
    """
    total = 0

    # Directives
    directives_dir = doctrine_root / "directives" / "built-in"
    if directives_dir.is_dir():
        for path in sorted(directives_dir.glob("*.directive.yaml")):
            data: Any = _yaml.load(path)
            if not data:
                continue
            total += len(data.get("tactic_refs", []) or [])
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1

    # Tactics
    tactics_dir = doctrine_root / "tactics" / "built-in"
    if tactics_dir.is_dir():
        for path in sorted(tactics_dir.rglob("*.tactic.yaml")):
            data = _yaml.load(path)
            if not data:
                continue
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1
            for step in data.get("steps", []) or []:
                for ref in step.get("references", []) or []:
                    if ref.get("type", "") not in _SKIP_REF_TYPES:
                        total += 1

    # Paradigms
    paradigms_dir = doctrine_root / "paradigms" / "built-in"
    if paradigms_dir.is_dir():
        for path in sorted(paradigms_dir.glob("*.paradigm.yaml")):
            data = _yaml.load(path)
            if not data:
                continue
            total += len(data.get("tactic_refs", []) or [])
            total += len(data.get("directive_refs", []) or [])
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1

    # Procedures
    procedures_dir = doctrine_root / "procedures" / "built-in"
    if procedures_dir.is_dir():
        for path in sorted(procedures_dir.glob("*.procedure.yaml")):
            data = _yaml.load(path)
            if not data:
                continue
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    total += 1

    # Action indices
    missions_dir = doctrine_root / "missions"
    if missions_dir.is_dir():
        for index_path in sorted(missions_dir.rglob("actions/*/index.yaml")):
            data = _yaml.load(index_path)
            if not data:
                continue
            for field in (
                "directives",
                "tactics",
                "paradigms",
                "styleguides",
                "toolguides",
                "procedures",
                "agent_profiles",
            ):
                total += len(data.get(field, []) or [])

    # Agent profiles
    profiles_dir = doctrine_root / "agent_profiles" / "built-in"
    if profiles_dir.is_dir():
        for path in sorted(profiles_dir.glob("*.agent.yaml")):
            data = _yaml.load(path)
            if not data:
                continue
            context_sources = data.get("context-sources", {}) or {}
            total += len(context_sources.get("directives", []) or [])
            total += len(data.get("tactic-references", []) or [])

    return total


# ---------------------------------------------------------------------------
# T012: Artifact walker tests
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestExtractArtifactEdges:
    def test_returns_nodes_and_edges(self) -> None:
        nodes, edges = extract_artifact_edges(DOCTRINE_ROOT)
        assert len(nodes) > 0
        assert len(edges) > 0

    def test_directive_nodes_present(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        directive_urns = {n.urn for n in nodes if n.kind == NodeKind.DIRECTIVE}
        # We know DIRECTIVE_001, DIRECTIVE_024, DIRECTIVE_003 exist
        assert "directive:DIRECTIVE_001" in directive_urns
        assert "directive:DIRECTIVE_024" in directive_urns
        assert "directive:DIRECTIVE_003" in directive_urns

    def test_tactic_nodes_present(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        tactic_urns = {n.urn for n in nodes if n.kind == NodeKind.TACTIC}
        assert "tactic:tdd-red-green-refactor" in tactic_urns
        assert "tactic:adr-drafting-workflow" in tactic_urns

    def test_paradigm_nodes_present(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        paradigm_urns = {n.urn for n in nodes if n.kind == NodeKind.PARADIGM}
        assert "paradigm:domain-driven-design" in paradigm_urns
        assert "paradigm:atomic-design" in paradigm_urns
        assert "paradigm:c4-incremental-detail-modeling" in paradigm_urns

    def test_no_duplicate_nodes(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        urns = [n.urn for n in nodes]
        assert len(urns) == len(set(urns)), "Duplicate node URNs found"

    # One migration-extractor regression test was deleted in WP03 of the
    # excise-doctrine-curation-and-inline-references-01KP54J6 mission;
    # it exercised the pre-WP02 inline-reference path that no longer has
    # shipped input data. The migration extractor itself remains covered
    # by test_directive_opposed_by_produces_replaces and the other
    # TestExtractArtifactEdges cases.

    def test_directive_opposed_by_produces_replaces(self) -> None:
        """Directive opposed_by should produce 'replaces' edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        d024_replaces = [
            e for e in edges
            if e.source == "directive:DIRECTIVE_024"
            and e.relation == Relation.REPLACES
        ]
        assert {e.target for e in d024_replaces} == {"directive:DIRECTIVE_025"}
        assert d024_replaces[0].target == "directive:DIRECTIVE_025"

    def test_paradigm_directive_refs_normalised(self) -> None:
        """Paradigm directive_refs (DIRECTIVE_NNN format) should be normalised."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        ddd_requires = [
            e for e in edges
            if e.source == "paradigm:domain-driven-design"
            and e.relation == Relation.REQUIRES
            and e.target.startswith("directive:")
        ]
        targets = {e.target for e in ddd_requires}
        assert "directive:DIRECTIVE_001" in targets
        assert "directive:DIRECTIVE_031" in targets
        assert "directive:DIRECTIVE_032" in targets

    def test_curated_paradigm_tactic_edges_are_preserved(self) -> None:
        """Curated paradigm tactic edges should survive regeneration."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        targets = {
            e.target
            for e in edges
            if e.source == "paradigm:specification-by-example"
            and e.relation == Relation.REQUIRES
        }
        assert "tactic:usage-examples-sync" in targets

    def test_tactic_references_produce_suggests(self) -> None:
        """Tactic references should produce 'suggests' edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        pd_suggests = [
            e for e in edges
            if e.source == "tactic:problem-decomposition"
            and e.relation == Relation.SUGGESTS
        ]
        # problem-decomposition has 4 top-level refs (skipping template)
        # -> eisenhower-prioritisation, stakeholder-alignment, review-intent-and-risk-first
        targets = {e.target for e in pd_suggests}
        assert "tactic:eisenhower-prioritisation" in targets

    def test_duplicate_tactic_refs_preserve_metadata(self, tmp_path: Path) -> None:
        """Duplicate triples merge metadata instead of keeping the bare edge."""
        doctrine_root = tmp_path / "doctrine"
        tactics_dir = doctrine_root / "tactics" / "built-in"
        tactics_dir.mkdir(parents=True)
        (tactics_dir / "metadata-merge.tactic.yaml").write_text(
            "\n".join(
                [
                    "schema_version: '1.0'",
                    "id: metadata-merge",
                    "name: Metadata Merge",
                    "purpose: test",
                    "references:",
                    "  - type: tactic",
                    "    id: target-tactic",
                    "  - type: tactic",
                    "    id: target-tactic",
                    "    when: Preserve this metadata.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        _, edges = extract_artifact_edges(doctrine_root)

        edge = next(
            edge
            for edge in edges
            if edge.source == "tactic:metadata-merge"
            and edge.target == "tactic:target-tactic"
        )
        assert edge.when == "Preserve this metadata."

    def test_procedure_template_references_produce_template_edges(self) -> None:
        """Procedure template references should be represented in the DRG."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        issue_triage_suggests = [
            e
            for e in edges
            if e.source == "procedure:issue-triage-state-machine"
            and e.relation == Relation.SUGGESTS
        ]

        targets = {e.target for e in issue_triage_suggests}
        assert "template:agent-brief-template" in targets
        assert "template:out-of-scope-record-template" in targets

    def test_agent_profile_references_produce_requires(self) -> None:
        """Agent profile context and tactic references should enter the DRG."""
        nodes, edges = extract_artifact_edges(DOCTRINE_ROOT)
        assert any(
            n.urn == "agent_profile:debugger-debbie"
            and n.kind == NodeKind.AGENT_PROFILE
            for n in nodes
        )
        targets = {
            e.target
            for e in edges
            if e.source == "agent_profile:debugger-debbie"
            and e.relation == Relation.REQUIRES
        }
        assert "tactic:five-paradigm-parallel-debugging" in targets

    def test_walks_all_built_in_directives(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        directive_count = len(
            list(
                (DOCTRINE_ROOT / "directives" / "built-in").glob("*.directive.yaml")
            )
        )
        graph_directive_nodes = [
            n for n in nodes
            if n.kind == NodeKind.DIRECTIVE and n.label is not None
        ]
        # Each shipped directive should appear as a labelled node
        assert len(graph_directive_nodes) >= directive_count

    def test_walks_all_shipped_paradigms(self) -> None:
        nodes, _ = extract_artifact_edges(DOCTRINE_ROOT)
        paradigm_files = list(
            (DOCTRINE_ROOT / "paradigms" / "built-in").glob("*.paradigm.yaml")
        )
        graph_paradigm_nodes = [
            n for n in nodes
            if n.kind == NodeKind.PARADIGM and n.label is not None
        ]
        assert len(graph_paradigm_nodes) == len(paradigm_files)


# ---------------------------------------------------------------------------
# T013: Action index walker tests
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestExtractActionEdges:
    def test_returns_nodes_and_edges(self) -> None:
        nodes, edges = extract_action_edges(DOCTRINE_ROOT)
        assert len(nodes) > 0
        assert len(edges) > 0

    def test_action_nodes_created(self) -> None:
        nodes, _ = extract_action_edges(DOCTRINE_ROOT)
        action_urns = {n.urn for n in nodes if n.kind == NodeKind.ACTION}
        expected = {
            "action:software-dev/specify",
            "action:software-dev/plan",
            "action:software-dev/tasks",
            "action:software-dev/implement",
            "action:software-dev/review",
        }
        assert expected.issubset(action_urns)

    def test_directive_slugs_normalised(self) -> None:
        """Directive slugs in action indices should be normalised to DIRECTIVE_NNN."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        implement_edges = [
            e for e in edges
            if e.source == "action:software-dev/implement"
            and e.target.startswith("directive:")
        ]
        for edge in implement_edges:
            assert edge.target.startswith("directive:DIRECTIVE_")

    def test_scope_edges_only(self) -> None:
        """All action edges should be scope edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        for edge in edges:
            assert edge.relation == Relation.SCOPE

    def test_empty_lists_produce_no_edges(self) -> None:
        """Empty styleguides/toolguides/procedures lists should produce no edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        specify_edges = [
            e for e in edges
            if e.source == "action:software-dev/specify"
        ]
        # specify has 2 directives + 1 tactic = 3 scope edges
        assert {e.target for e in specify_edges} == {
            "directive:DIRECTIVE_010",
            "directive:DIRECTIVE_003",
            "tactic:requirements-validation-workflow",
        }

    def test_agent_profile_scope_edges(self) -> None:
        """Action indexes may scope built-in agent profiles."""
        nodes, edges = extract_action_edges(DOCTRINE_ROOT)
        assert any(
            n.urn == "agent_profile:retrospective-facilitator"
            and n.kind == NodeKind.AGENT_PROFILE
            for n in nodes
        )
        assert any(
            e.source == "action:software-dev/retrospect"
            and e.target == "agent_profile:retrospective-facilitator"
            and e.relation == Relation.SCOPE
            for e in edges
        )

    def test_paradigm_scope_edges(self) -> None:
        """Action indexes may scope built-in paradigms."""
        nodes, edges = extract_action_edges(DOCTRINE_ROOT)
        assert any(
            n.urn == "paradigm:execution-lanes"
            and n.kind == NodeKind.PARADIGM
            for n in nodes
        )
        assert any(
            e.source == "action:software-dev/implement"
            and e.target == "paradigm:execution-lanes"
            and e.relation == Relation.SCOPE
            for e in edges
        )

    def test_tasks_action_has_seven_refs(self) -> None:
        """The tasks action index should produce 7 scope edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        tasks_edges = [
            e for e in edges
            if e.source == "action:software-dev/tasks"
        ]
        assert {e.target for e in tasks_edges} == {
            "directive:DIRECTIVE_003",
            "directive:DIRECTIVE_010",
            "directive:DIRECTIVE_024",
            "tactic:adr-drafting-workflow",
            "tactic:problem-decomposition",
            "tactic:requirements-validation-workflow",
            "procedure:issue-triage-state-machine",
        }

    def test_nonexistent_doctrine_root(self) -> None:
        nodes, edges = extract_action_edges(Path("/nonexistent"))
        assert nodes == []
        assert edges == []


# ---------------------------------------------------------------------------
# T016: generate_graph end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestGenerateGraph:
    def test_generates_valid_graph(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        errors = validate_graph(graph)
        assert errors == [], f"Validation errors: {errors}"

    def test_graph_file_exists(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        generate_graph(DOCTRINE_ROOT, output)
        # Sharded layout (mission #2680 WP05): the generator writes per-kind
        # ``*.graph.yaml`` fragments into ``output``'s directory and retires any
        # ``graph.yaml`` monolith in the same write (DD-7).
        assert sorted(tmp_path.glob("*.graph.yaml"))
        assert not output.exists()

    def test_schema_version(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        assert graph.schema_version == "1.0"

    def test_generated_by(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        assert graph.generated_by == "drg-migration-v1"

    def test_all_node_urns_unique(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        urns = [n.urn for n in graph.nodes]
        assert len(urns) == len(set(urns))

    def test_all_edge_triples_unique(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        triples = [(e.source, e.target, e.relation.value) for e in graph.edges]
        assert len(triples) == len(set(triples))

    def test_idempotent(self, tmp_path: Path) -> None:
        """Running generate_graph twice must produce identical fragments (DD-11)."""
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"
        dir1.mkdir()
        dir2.mkdir()
        generate_graph(DOCTRINE_ROOT, dir1 / "graph.yaml")
        generate_graph(DOCTRINE_ROOT, dir2 / "graph.yaml")

        def _fragment_hashes(directory: Path) -> dict[str, str]:
            return {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: TID251 — DRG-output file-integrity idempotency check, not charter freshness hashing
                for p in sorted(directory.glob("*.graph.yaml"))
            }

        first = _fragment_hashes(dir1)
        second = _fragment_hashes(dir2)
        assert first, "generate_graph produced no fragments"
        assert first == second, "generate_graph is not idempotent (per-fragment drift)"

    @pytest.mark.fast
    def test_shipped_graph_yaml_is_fresh(self, tmp_path: Path) -> None:
        """Committed shipped DRG fragments must match generator output byte-for-byte.

        Sharded per mission #2680 (WP05): compare the per-kind ``*.graph.yaml``
        fragment set rather than a single monolith (DD-11 per-file byte-identity).
        """
        generate_graph(DOCTRINE_ROOT, tmp_path / "graph.yaml")

        def _fragments(directory: Path) -> dict[str, str]:
            return {
                p.name: p.read_text(encoding="utf-8")
                for p in sorted(directory.glob("*.graph.yaml"))
            }

        regenerated = _fragments(tmp_path)
        committed = _fragments(DOCTRINE_ROOT)
        assert regenerated, "generate_graph produced no fragments"
        assert regenerated == committed, (
            "src/doctrine/*.graph.yaml fragments are stale. Regenerate the "
            "shipped DRG with `spec-kitty doctrine regenerate-graph` and commit "
            "the result."
        )

    def test_surface_inequalities(self, tmp_path: Path) -> None:
        """Verify governance surface inequalities after calibration."""
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)

        specify = measure_surface("action:software-dev/specify", graph.edges)
        plan = measure_surface("action:software-dev/plan", graph.edges)
        tasks = measure_surface("action:software-dev/tasks", graph.edges)
        implement = measure_surface("action:software-dev/implement", graph.edges)
        review = measure_surface("action:software-dev/review", graph.edges)

        assert specify < plan, f"|specify| ({specify}) should be < |plan| ({plan})"
        assert plan < implement, f"|plan| ({plan}) should be < |implement| ({implement})"
        assert tasks < implement, f"|tasks| ({tasks}) should be < |implement| ({implement})"
        assert review >= 0.80 * implement, (
            f"|review| ({review}) should be >= 80% of |implement| ({implement})"
        )

    def test_resolved_surface_inequalities(self, tmp_path: Path) -> None:
        """Generated graph must satisfy shipped resolved-context calibration."""
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)

        def _resolved(action: str) -> int:
            return len(
                resolve_context(
                    graph,
                    f"action:software-dev/{action}",
                    depth=2,
                ).artifact_urns
            )

        specify = _resolved("specify")
        plan = _resolved("plan")
        tasks = _resolved("tasks")
        implement = _resolved("implement")
        review = _resolved("review")

        assert specify < plan, f"resolved specify ({specify}) should be < plan ({plan})"
        assert plan < implement, (
            f"resolved plan ({plan}) should be < implement ({implement})"
        )
        assert tasks < implement, (
            f"resolved tasks ({tasks}) should be < implement ({implement})"
        )
        assert review >= 0.80 * implement, (
            f"resolved review ({review}) should be >= 80% of implement ({implement})"
        )

    def test_discovers_styleguide_nodes(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        styleguide_nodes = [n for n in graph.nodes if n.kind == NodeKind.STYLEGUIDE]
        # At least the shipped styleguides should be present
        assert len(styleguide_nodes) >= 1

    def test_discovers_toolguide_nodes(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        toolguide_nodes = [n for n in graph.nodes if n.kind == NodeKind.TOOLGUIDE]
        assert len(toolguide_nodes) >= 1

    def test_discovers_procedure_nodes(self, tmp_path: Path) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        procedure_nodes = [n for n in graph.nodes if n.kind == NodeKind.PROCEDURE]
        assert len(procedure_nodes) >= 1


# ---------------------------------------------------------------------------
# T017: Edge-count completeness validation
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
class TestEdgeCountCompleteness:
    def test_edge_count_gte_inline_refs(self, tmp_path: Path) -> None:
        """Total edge count must be >= total inline reference field count.

        The >= accounts for calibration-added edges.
        """
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)
        total_inline = _count_inline_refs(DOCTRINE_ROOT)
        assert len(graph.edges) >= total_inline, (
            f"Edge count ({len(graph.edges)}) < inline refs ({total_inline}). "
            f"Some references were dropped."
        )

    def test_per_directive_edges_complete(self) -> None:
        """Each directive's inline refs should have corresponding edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        directives_dir = DOCTRINE_ROOT / "directives" / "built-in"
        for path in sorted(directives_dir.glob("*.directive.yaml")):
            data: Any = _yaml.load(path)
            if not data:
                continue
            src_id = data.get("id", "")
            src_urn = f"directive:{src_id}"
            src_edges = [e for e in edges if e.source == src_urn]

            expected_count = len(data.get("tactic_refs", []) or [])
            for ref in data.get("references", []) or []:
                if ref.get("type", "") not in _SKIP_REF_TYPES:
                    expected_count += 1
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    expected_count += 1

            assert len(src_edges) >= expected_count, (
                f"{path.name}: expected >= {expected_count} edges from "
                f"{src_urn}, found {len(src_edges)}"
            )

    def test_per_paradigm_edges_complete(self) -> None:
        """Each paradigm's inline refs should have corresponding edges."""
        _, edges = extract_artifact_edges(DOCTRINE_ROOT)
        paradigms_dir = DOCTRINE_ROOT / "paradigms" / "built-in"
        for path in sorted(paradigms_dir.glob("*.paradigm.yaml")):
            data: Any = _yaml.load(path)
            if not data:
                continue
            src_id = data.get("id", "")
            src_urn = f"paradigm:{src_id}"
            src_edges = [e for e in edges if e.source == src_urn]

            expected_count = (
                len(data.get("tactic_refs", []) or [])
                + len(data.get("directive_refs", []) or [])
            )
            for opp in data.get("opposed_by", []) or []:
                if opp.get("type", "") not in _SKIP_REF_TYPES:
                    expected_count += 1

            assert len(src_edges) >= expected_count, (
                f"{path.name}: expected >= {expected_count} edges from "
                f"{src_urn}, found {len(src_edges)}"
            )

    def test_per_action_edges_complete(self) -> None:
        """Each action's scope refs should have corresponding edges."""
        _, edges = extract_action_edges(DOCTRINE_ROOT)
        missions_dir = DOCTRINE_ROOT / "missions"
        for index_path in sorted(missions_dir.rglob("actions/*/index.yaml")):
            data: Any = _yaml.load(index_path)
            if not data:
                continue
            action_name = data.get("action", index_path.parent.name)
            mission_name = index_path.parent.parent.parent.name
            action_urn = f"action:{mission_name}/{action_name}"
            action_edges = [e for e in edges if e.source == action_urn]

            expected_count = 0
            for field in (
                "directives",
                "tactics",
                "paradigms",
                "styleguides",
                "toolguides",
                "procedures",
                "agent_profiles",
            ):
                expected_count += len(data.get(field, []) or [])

            assert len(action_edges) == expected_count, (
                f"{action_name}: expected {expected_count} edges, "
                f"found {len(action_edges)}"
            )


# ---------------------------------------------------------------------------
# Mission-type edge emission (mission-type-drg-edges mission, SC-001)
# ---------------------------------------------------------------------------

MISSION_TYPES_DIR = DOCTRINE_ROOT / "missions" / "mission_types"


def _shipped_action_sequences() -> dict[str, list[str]]:
    """Read every shipped mission-type YAML's ``action_sequence``."""
    sequences: dict[str, list[str]] = {}
    for path in sorted(MISSION_TYPES_DIR.glob("*.yaml")):
        data: Any = _yaml.load(path)
        assert isinstance(data, dict)
        sequences[data["id"]] = list(data.get("action_sequence", []) or [])
    return sequences


@pytest.mark.doctrine
class TestMissionTypeEdges:
    """Green-pinning for the ``mission_type --requires--> action`` edges.

    WP01 landed the emission (and demonstrated red-first inside its own loop);
    these tests pin the full behaviour comprehensively against the shipped
    generator entry points.
    """

    def test_plan_emits_exactly_its_four_requires_edges(self) -> None:
        """``mission_type:plan`` emits exactly 4 requires edges to its actions."""
        edges = extract_mission_type_edges(DOCTRINE_ROOT)
        plan_edges = [
            e for e in edges if e.source == "mission_type:plan"
        ]

        assert all(e.relation is Relation.REQUIRES for e in plan_edges)
        assert {e.target for e in plan_edges} == {
            "action:plan/specify",
            "action:plan/research",
            "action:plan/plan",
            "action:plan/review",
        }
        assert len(plan_edges) == 4  # golden-count: cardinality-is-contract

    def test_documentation_emits_full_seven_edge_sequence(self) -> None:
        """A non-plan type emits its full 7-step sequence (FR-001 breadth)."""
        edges = extract_mission_type_edges(DOCTRINE_ROOT)
        doc_edges = [
            e for e in edges if e.source == "mission_type:documentation"
        ]

        assert all(e.relation is Relation.REQUIRES for e in doc_edges)
        assert {e.target for e in doc_edges} == {
            "action:documentation/discover",
            "action:documentation/audit",
            "action:documentation/design",
            "action:documentation/generate",
            "action:documentation/validate",
            "action:documentation/publish",
            "action:documentation/accept",
        }
        assert len(doc_edges) == 7  # golden-count: cardinality-is-contract

    def test_every_mission_type_edge_matches_its_action_sequence(self) -> None:
        """Each shipped type emits one requires edge per action_sequence step."""
        edges = extract_mission_type_edges(DOCTRINE_ROOT)
        sequences = _shipped_action_sequences()

        for mission_id, steps in sequences.items():
            source_urn = f"mission_type:{mission_id}"
            emitted = {
                e.target
                for e in edges
                if e.source == source_urn and e.relation is Relation.REQUIRES
            }
            assert emitted == {
                f"action:{mission_id}/{step}" for step in steps
            }, f"{source_urn} edges do not match its action_sequence"

    def test_total_mission_type_edge_count_is_twenty_one(self) -> None:
        """SC-001: the four shipped types emit 21 requires edges in total.

        4 (plan) + 7 (documentation) + 5 (research) + 5 (software-dev) = 21.
        This is a deliberate cardinality contract over the built-in mission
        types, not incidental golden-count debt.
        """
        edges = extract_mission_type_edges(DOCTRINE_ROOT)
        requires_edges = [
            e
            for e in edges
            if e.source.startswith("mission_type:")
            and e.relation is Relation.REQUIRES
        ]
        assert len(requires_edges) == 21  # golden-count: cardinality-is-contract

    def test_no_mission_type_or_sequence_action_node_is_orphan(
        self, tmp_path: Path
    ) -> None:
        """No mission_type node -- and no action node named in a sequence --
        remains an orphan in the fully generated graph (SC-001)."""
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)

        incident: set[str] = set()
        for edge in graph.edges:
            incident.add(edge.source)
            incident.add(edge.target)

        mission_type_urns = {
            n.urn for n in graph.nodes if n.kind == NodeKind.MISSION_TYPE
        }
        assert mission_type_urns, "expected shipped mission_type nodes"
        orphan_mission_types = mission_type_urns - incident
        assert not orphan_mission_types, (
            f"mission_type nodes are orphaned: {orphan_mission_types}"
        )

        sequence_action_urns = {
            f"action:{mission_id}/{step}"
            for mission_id, steps in _shipped_action_sequences().items()
            for step in steps
        }
        orphan_sequence_actions = sequence_action_urns - incident
        assert not orphan_sequence_actions, (
            f"sequence action nodes are orphaned: {orphan_sequence_actions}"
        )


def _hand_partition_graph() -> DRGGraph:
    """A small, deliberately-unsorted hand-made graph exercising every
    ``_partition_by_kind`` invariant (FR-007 source-kind routing + DD-11 order).

    Shape (input order is intentionally NOT canonical so the sort is exercised):

    * three populated kinds -- ``MISSION_TYPE``, ``ACTION`` and a **target-only**
      ``TEMPLATE`` (owns a node but is never an edge source);
    * multi-kind edges: ``MISSION_TYPE``-sourced ``requires`` edges to actions
      AND an ``ACTION``-sourced ``instantiates`` edge to the template -- so a
      wrong (e.g. target-kind) routing would still reconstitute the same merged
      graph yet land edges in the wrong fragment.
    """
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-07-16T00:00:00+00:00",
        generated_by="test",
        # Unsorted within each kind: software_dev before research; specify before plan.
        nodes=[
            DRGNode(urn="mission_type:software_dev", kind=NodeKind.MISSION_TYPE),
            DRGNode(urn="action:specify", kind=NodeKind.ACTION),
            DRGNode(urn="template:spec_tmpl", kind=NodeKind.TEMPLATE),
            DRGNode(urn="mission_type:research", kind=NodeKind.MISSION_TYPE),
            DRGNode(urn="action:plan", kind=NodeKind.ACTION),
        ],
        # Unsorted: software_dev->specify before software_dev->plan, research last.
        edges=[
            DRGEdge(
                source="mission_type:software_dev",
                target="action:specify",
                relation=Relation.REQUIRES,
            ),
            DRGEdge(
                source="mission_type:software_dev",
                target="action:plan",
                relation=Relation.REQUIRES,
            ),
            DRGEdge(
                source="mission_type:research",
                target="action:specify",
                relation=Relation.REQUIRES,
            ),
            DRGEdge(
                source="action:specify",
                target="template:spec_tmpl",
                relation=Relation.INSTANTIATES,
            ),
        ],
    )


class TestPartitionByKind:
    """Focused unit coverage for ``_partition_by_kind`` (DD-8/DD-11, FR-007).

    The end-to-end fragment tests reconstitute the merged graph, so a
    wrong-source-kind routing (e.g. by target kind) would still round-trip and
    pass every one of them. These assertions pin the currently-invisible
    per-fragment placement + ordering contract directly.
    """

    def test_one_fragment_per_populated_kind_including_target_only(self) -> None:
        """Totality (DD-8): every populated kind -- including a target-only
        kind that is never an edge source -- yields exactly one fragment, and
        the target-only kind's fragment carries an empty edge list."""
        fragments = _partition_by_kind(_hand_partition_graph())

        assert set(fragments) == {
            NodeKind.MISSION_TYPE,
            NodeKind.ACTION,
            NodeKind.TEMPLATE,
        }
        # TEMPLATE owns a node but sources no edge -> present, with no edges.
        assert [n.urn for n in fragments[NodeKind.TEMPLATE].nodes] == [
            "template:spec_tmpl"
        ]
        assert fragments[NodeKind.TEMPLATE].edges == []

    def test_each_fragment_is_kind_homogeneous(self) -> None:
        """Homogeneity: every node in a fragment is of that fragment's kind."""
        fragments = _partition_by_kind(_hand_partition_graph())
        for kind, fragment in fragments.items():
            assert all(node.kind == kind for node in fragment.nodes)

    def test_edge_lands_in_its_source_node_kind_fragment(self) -> None:
        """FR-007 (the invisible clause): each edge is placed in the fragment of
        its **source** node's kind -- not its target's."""
        fragments = _partition_by_kind(_hand_partition_graph())
        kind_by_urn = {
            n.urn: n.kind
            for frag in fragments.values()
            for n in frag.nodes
        }
        for kind, fragment in fragments.items():
            for edge in fragment.edges:
                assert kind_by_urn[edge.source] == kind

        # Concrete guard against target-kind routing: the ACTION-sourced edge to
        # the template lands in ACTION (not TEMPLATE), and the mission_type
        # edges land in MISSION_TYPE (not ACTION).
        action_edges = fragments[NodeKind.ACTION].edges
        assert [(e.source, e.target) for e in action_edges] == [
            ("action:specify", "template:spec_tmpl")
        ]
        mt_sources = {e.source for e in fragments[NodeKind.MISSION_TYPE].edges}
        assert mt_sources == {
            "mission_type:research",
            "mission_type:software_dev",
        }

    def test_intra_fragment_canonical_order(self) -> None:
        """DD-11: fragment nodes are sorted by URN and edges by
        ``(source, target, relation)`` regardless of input order."""
        fragments = _partition_by_kind(_hand_partition_graph())

        assert [n.urn for n in fragments[NodeKind.MISSION_TYPE].nodes] == [
            "mission_type:research",
            "mission_type:software_dev",
        ]
        assert [n.urn for n in fragments[NodeKind.ACTION].nodes] == [
            "action:plan",
            "action:specify",
        ]
        assert [
            (e.source, e.target, e.relation.value)
            for e in fragments[NodeKind.MISSION_TYPE].edges
        ] == [
            ("mission_type:research", "action:specify", "requires"),
            ("mission_type:software_dev", "action:plan", "requires"),
            ("mission_type:software_dev", "action:specify", "requires"),
        ]

    def test_disjoint_union_reconstructs_input_exactly(self) -> None:
        """Fragments partition the input: their disjoint union reproduces the
        original node and edge sets with nothing lost or duplicated."""
        graph = _hand_partition_graph()
        fragments = _partition_by_kind(graph)

        recomposed_nodes = [n.urn for frag in fragments.values() for n in frag.nodes]
        recomposed_edges = [
            (e.source, e.target, e.relation.value)
            for frag in fragments.values()
            for e in frag.edges
        ]
        # No duplication (disjointness) + exact set equality (completeness).
        assert len(recomposed_nodes) == len(graph.nodes)
        assert set(recomposed_nodes) == {n.urn for n in graph.nodes}
        assert len(recomposed_edges) == len(graph.edges)
        assert set(recomposed_edges) == {
            (e.source, e.target, e.relation.value) for e in graph.edges
        }
