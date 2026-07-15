"""Coverage for ``mission_type`` as a first-class DRG node kind (WP01).

T001: ``NodeKind.MISSION_TYPE`` validates a ``mission_type:<id>`` URN and
rejects a mismatched kind/prefix pairing.

T002: ``generate_graph`` discovers exactly one ``mission_type`` node per
shipped ``src/doctrine/missions/mission_types/*.yaml`` file, labelled with
that file's ``display_name``. Additive only -- no edges are emitted for
these nodes (S0-continuation is a follow-up).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from doctrine.drg.migration.extractor import generate_graph
from doctrine.drg.models import DRGNode, NodeKind

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
        # mission types (documentation, plan, research, software-dev).
        assert len(self._shipped_mission_type_ids_and_labels()) == 4

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

    def test_mission_type_nodes_have_no_incident_edges(
        self, tmp_path: Path
    ) -> None:
        # Nodes-only in WP01 -- edges are a deliberate S0-continuation.
        output = tmp_path / "graph.yaml"
        graph = generate_graph(DOCTRINE_ROOT, output)

        mission_type_urns = {
            n.urn for n in graph.nodes if n.kind == NodeKind.MISSION_TYPE
        }
        for edge in graph.edges:
            assert edge.source not in mission_type_urns
            assert edge.target not in mission_type_urns
