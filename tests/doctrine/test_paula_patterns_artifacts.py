"""Smoke tests for the Paula Patterns doctrine artifacts."""

from __future__ import annotations

import pytest

from doctrine.drg.models import DRGGraph
from doctrine.service import DoctrineService
from tests.doctrine.conftest import DOCTRINE_SOURCE_ROOT

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


BUILT_IN_ROOT = DOCTRINE_SOURCE_ROOT


@pytest.fixture(scope="module")
def service() -> DoctrineService:
    return DoctrineService(built_in_root=BUILT_IN_ROOT)


def test_paula_patterns_tactic_loads(service: DoctrineService) -> None:
    tactic = service.tactics.get("paula-patterns-architecture-scout-review")

    assert tactic is not None
    assert tactic.schema_version == "1.0"
    assert tactic.name == "Paula Patterns Architecture Scout Review"
    assert len(tactic.steps) == 6
    assert any(ref.id == "DIRECTIVE_001" for ref in tactic.references)
    assert "InstalledCliRuntime" in (tactic.notes or "")


def test_paula_patterns_profile_loads(service: DoctrineService) -> None:
    profile = service.agent_profiles.get("paula-patterns")

    assert profile is not None
    assert profile.profile_id == "paula-patterns"
    assert profile.name == "Paula Patterns"
    assert [str(role) for role in profile.roles] == [
        "architecture-scout",
        "architect",
        "reviewer",
    ]
    assert profile.specialization.primary_focus
    assert any(
        ref.id == "paula-patterns-architecture-scout-review"
        for ref in profile.tactic_references
    )


def test_paula_patterns_graph_node_and_edges_exist(built_in_graph: DRGGraph) -> None:
    graph = built_in_graph
    nodes = graph.node_urns()

    assert "agent_profile:paula-patterns" in nodes
    assert "tactic:paula-patterns-architecture-scout-review" in nodes

    edges = {(edge.source, edge.target, str(edge.relation)) for edge in graph.edges}
    assert (
        "agent_profile:paula-patterns",
        "tactic:paula-patterns-architecture-scout-review",
        "requires",
    ) in edges
    assert (
        "directive:DIRECTIVE_001",
        "tactic:paula-patterns-architecture-scout-review",
        "requires",
    ) in edges
    assert (
        "tactic:paula-patterns-architecture-scout-review",
        "directive:DIRECTIVE_001",
        "suggests",
    ) in edges
    assert (
        "tactic:paula-patterns-architecture-scout-review",
        "tactic:review-intent-and-risk-first",
        "suggests",
    ) in edges
