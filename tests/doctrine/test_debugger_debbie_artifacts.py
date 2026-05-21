"""Smoke tests for the Debugger Debbie doctrine artifacts."""

from __future__ import annotations

import pytest

from doctrine.drg.loader import load_graph
from doctrine.service import DoctrineService

from tests.doctrine.conftest import DOCTRINE_SOURCE_ROOT

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


SHIPPED_ROOT = DOCTRINE_SOURCE_ROOT


@pytest.fixture(scope="module")
def service() -> DoctrineService:
    return DoctrineService(shipped_root=SHIPPED_ROOT)


def test_debugger_debbie_profile_loads(service: DoctrineService) -> None:
    profile = service.agent_profiles.get("debugger-debbie")

    assert profile is not None
    assert profile.profile_id == "debugger-debbie"
    assert profile.name == "Debugger Debbie"
    assert "investigator" in [str(role) for role in profile.roles]
    assert profile.specialization.primary_focus
    assert any(ref.id == "five-paradigm-parallel-debugging" for ref in profile.tactic_references)


def test_five_paradigm_tactic_loads(service: DoctrineService) -> None:
    tactic = service.tactics.get("five-paradigm-parallel-debugging")

    assert tactic is not None
    assert tactic.schema_version == "1.0"
    assert tactic.name == "Five-Paradigm Parallel Debugging"
    assert len(tactic.steps) == 6
    assert any(ref.id == "DIRECTIVE_040" for ref in tactic.references)


def test_directive_040_loads(service: DoctrineService) -> None:
    directive = service.directives.get("DIRECTIVE_040")

    assert directive is not None
    assert directive.schema_version == "1.0"
    assert directive.title == "Recurring-Bug Structural-Intervention Discipline"
    assert str(getattr(directive.enforcement, "value", directive.enforcement)) == "required"
    assert any("five-paradigm" in procedure for procedure in directive.procedures)


def test_debugger_debbie_skill_references_exist() -> None:
    skill_root = SHIPPED_ROOT / "skills" / "debugger-debbie"
    skill_path = skill_root / "SKILL.md"

    assert skill_path.is_file()
    body = skill_path.read_text(encoding="utf-8")
    for reference in [
        "references/paradigm-prompts.md",
        "references/orthogonality-matrix.md",
    ]:
        assert reference in body
        assert (skill_root / reference).is_file()


def test_debugger_debbie_graph_nodes_and_edges_exist() -> None:
    graph = load_graph(SHIPPED_ROOT / "graph.yaml")
    nodes = graph.node_urns()

    assert "directive:DIRECTIVE_040" in nodes
    assert "tactic:five-paradigm-parallel-debugging" in nodes
    assert "agent_profile:debugger-debbie" in nodes

    edges = {(edge.source, edge.target, str(edge.relation)) for edge in graph.edges}
    assert (
        "directive:DIRECTIVE_040",
        "tactic:five-paradigm-parallel-debugging",
        "requires",
    ) in edges
    assert (
        "agent_profile:debugger-debbie",
        "tactic:five-paradigm-parallel-debugging",
        "requires",
    ) in edges
