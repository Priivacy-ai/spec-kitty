"""Smoke tests for the Paula Patterns doctrine artifacts."""

from __future__ import annotations

import pytest

from doctrine.drg.loader import load_graph
from doctrine.service import DoctrineService
from specify_cli.skills.registry import SkillRegistry

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


def test_paula_patterns_skill_references_exist() -> None:
    skill_root = BUILT_IN_ROOT / "skills" / "paula-patterns"
    skill_path = skill_root / "SKILL.md"

    assert skill_path.is_file()
    body = skill_path.read_text(encoding="utf-8")
    for scout in [
        "Layered Architecture Scout",
        "Bounded Context / DDD Scout",
        "Event-Driven Architecture Scout",
        "Hexagonal / Ports-and-Adapters Scout",
        "Consumer Compatibility / Contract Scout",
    ]:
        assert scout in body
    assert "Release fix" in body
    assert "Long-term architecture fix" in body
    assert "#1343 / #1359" in body
    assert "Do not inline-modify those prompts" in body
    for reference in [
        "references/scout-prompts.md",
        "references/synthesis-matrix.md",
    ]:
        assert reference in body
        assert (skill_root / reference).is_file()

    prompts = (skill_root / "references" / "scout-prompts.md").read_text(
        encoding="utf-8"
    )
    for scout in [
        "You are the Layered Architecture Scout",
        "You are the Bounded Context / DDD Scout",
        "You are the Event-Driven Architecture Scout",
        "You are the Hexagonal / Ports-and-Adapters Scout",
        "You are the Consumer Compatibility / Contract Scout",
    ]:
        assert scout in prompts


def test_paula_patterns_skill_is_discoverable() -> None:
    registry = SkillRegistry(BUILT_IN_ROOT / "skills")
    skill = registry.get_skill("paula-patterns")

    assert skill is not None
    assert skill.skill_md.is_file()
    assert {path.name for path in skill.references} == {
        "scout-prompts.md",
        "synthesis-matrix.md",
    }


def test_paula_patterns_graph_node_and_edges_exist() -> None:
    graph = load_graph(BUILT_IN_ROOT / "graph.yaml")
    nodes = graph.node_urns()

    assert "tactic:paula-patterns-architecture-scout-review" in nodes

    edges = {(edge.source, edge.target, str(edge.relation)) for edge in graph.edges}
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
