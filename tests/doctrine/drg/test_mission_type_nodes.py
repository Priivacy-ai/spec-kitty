"""Coverage for ``mission_type`` as a first-class DRG node kind and its
edge-complete contract.

T001: ``NodeKind.MISSION_TYPE`` validates a ``mission_type:<id>`` URN and
rejects a mismatched kind/prefix pairing.

T002: ``generate_graph`` discovers exactly one ``mission_type`` node per
shipped ``src/doctrine/missions/mission_types/*.yaml`` file, labelled with
that file's ``display_name``.

Each ``mission_type`` node now emits one ``requires`` edge per step in its
``action_sequence`` to the matching ``action:<id>/<step>`` node (the
edge-complete contract landed in the mission-type-drg-edges mission). The
edges close the S0-continuation follow-on: mission_type nodes are no longer
edge-free placeholders.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from doctrine.drg.migration.extractor import generate_graph
from doctrine.drg.models import DRGNode, NodeKind, Relation

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

DOCTRINE_ROOT: Path = Path(__file__).resolve().parents[3] / "src" / "doctrine"
MISSION_TYPES_DIR = DOCTRINE_ROOT / "missions" / "mission_types"

_yaml = YAML(typ="safe")


class TestMissionTypeNodeKind:
    """T001: NodeKind.MISSION_TYPE URN validation."""

    def test_mission_type_urn_validates(self) -> None:
        node = DRGNode(
            urn="mission_type:software-dev",
            kind=NodeKind.MISSION_TYPE,
            label="software-dev",
        )

        assert node.kind is NodeKind.MISSION_TYPE
        assert node.urn == "mission_type:software-dev"

    def test_mismatched_prefix_raises(self) -> None:
        with pytest.raises(ValidationError):
            DRGNode(urn="directive:x", kind=NodeKind.MISSION_TYPE)


class TestMissionTypeNodeGeneration:
    """T002: generate_graph discovers one node per shipped mission type."""

    def _shipped_mission_type_ids_and_labels(self) -> dict[str, str]:
        ids_and_labels: dict[str, str] = {}
        for path in sorted(MISSION_TYPES_DIR.glob("*.yaml")):
            data = _yaml.load(path)
            assert isinstance(data, dict)
            ids_and_labels[data["id"]] = data["display_name"]
        return ids_and_labels

    def test_shipped_mission_types_fixture_has_four_entries(self) -> None:
        # Sanity check on the fixture itself: WP01 assumes exactly 4 shipped
        # mission types (documentation, plan, research, software-dev). The
        # count of 4 is a deliberate cardinality contract (the built-in
        # mission-type set), not incidental golden-count debt.
        assert len(self._shipped_mission_type_ids_and_labels()) == 4  # golden-count: cardinality-is-contract

    def test_generates_exactly_one_node_per_shipped_mission_type(
        self, tmp_path: Path
    ) -> None:
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)

        mission_type_nodes = [
            n for n in graph.nodes if n.kind == NodeKind.MISSION_TYPE
        ]
        expected = self._shipped_mission_type_ids_and_labels()

        assert len(mission_type_nodes) == len(expected) == 4

        actual_by_urn = {n.urn: n.label for n in mission_type_nodes}
        expected_by_urn = {
            f"mission_type:{mission_id}": label
            for mission_id, label in expected.items()
        }
        assert actual_by_urn == expected_by_urn

    def _shipped_action_sequences(self) -> dict[str, list[str]]:
        sequences: dict[str, list[str]] = {}
        for path in sorted(MISSION_TYPES_DIR.glob("*.yaml")):
            data = _yaml.load(path)
            assert isinstance(data, dict)
            sequences[data["id"]] = list(data.get("action_sequence", []) or [])
        return sequences

    def test_mission_type_nodes_have_outbound_requires_edges(
        self, tmp_path: Path
    ) -> None:
        # Edge-complete contract: every mission_type node emits exactly one
        # ``requires`` edge per ``action_sequence`` step to its
        # ``action:<id>/<step>`` node. This re-pins the retired nodes-only
        # placeholder (the S0-continuation edges have since landed).
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)

        sequences = self._shipped_action_sequences()
        for mission_id, steps in sequences.items():
            source_urn = f"mission_type:{mission_id}"
            outbound_requires = {
                edge.target
                for edge in graph.edges
                if edge.source == source_urn
                and edge.relation is Relation.REQUIRES
            }
            expected_targets = {
                f"action:{mission_id}/{step}" for step in steps
            }

            # The sequence is non-empty for every shipped mission type, so a
            # mission_type node with zero outbound edges would be a regression.
            assert outbound_requires, (
                f"{source_urn} has no outbound requires edges; the "
                f"edge-complete contract was not applied."
            )
            assert outbound_requires == expected_targets, (
                f"{source_urn} outbound requires targets {outbound_requires} "
                f"do not match its action_sequence {expected_targets}."
            )
