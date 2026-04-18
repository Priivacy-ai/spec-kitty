"""Tests for DoctrineService lazy aggregation behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.models import Relation
from doctrine.service import DoctrineService

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

SHIPPED_GRAPH = Path(__file__).resolve().parents[2] / "src" / "doctrine" / "graph.yaml"


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(data, handle)


def test_service_loads_all_repositories_from_shipped_defaults(tmp_path: Path) -> None:
    shipped_root = tmp_path / "shipped-root"

    _write_yaml(
        shipped_root / "directives" / "shipped" / "001-test.directive.yaml",
        {"schema_version": "1.0", "id": "DIRECTIVE_001", "title": "Test",
         "intent": "Test intent.", "enforcement": "required"},
    )
    _write_yaml(
        shipped_root / "tactics" / "shipped" / "test-tactic.tactic.yaml",
        {"schema_version": "1.0", "id": "test-tactic", "name": "Test Tactic",
         "steps": [{"title": "Step 1"}]},
    )
    _write_yaml(
        shipped_root / "styleguides" / "shipped" / "test-style.styleguide.yaml",
        {"schema_version": "1.0", "id": "test-style", "title": "Test Style",
         "scope": "code", "principles": ["Be clear"]},
    )
    _write_yaml(
        shipped_root / "toolguides" / "shipped" / "test-tool.toolguide.yaml",
        {"schema_version": "1.0", "id": "test-tool", "tool": "bash",
         "title": "Test Tool", "guide_path": "src/doctrine/test-tool.md", "summary": "Test."},
    )
    _write_yaml(
        shipped_root / "paradigms" / "shipped" / "test-paradigm.paradigm.yaml",
        {"schema_version": "1.0", "id": "test-paradigm", "name": "Test Paradigm",
         "summary": "Test."},
    )
    _write_yaml(
        shipped_root / "procedures" / "shipped" / "test-proc.procedure.yaml",
        {"schema_version": "1.0", "id": "test-proc", "name": "Test Procedure",
         "purpose": "Test.", "entry_condition": "Always.",
         "exit_condition": "Done.", "steps": [{"title": "Step 1"}]},
    )
    _write_yaml(
        shipped_root / "agent_profiles" / "shipped" / "test.agent.yaml",
        {"profile-id": "test-agent", "name": "Test Agent", "role": "implementer",
         "personality-traits": ["diligent"], "directive-references": [],
         "purpose": "Test agent for unit tests.",
         "specialization": {
             "primary-focus": "testing",
             "secondary-awareness": "testing",
             "avoidance-boundary": "none",
             "success-definition": "tests pass",
         }},
    )

    service = DoctrineService(shipped_root=shipped_root)

    assert len(service.directives.list_all()) == 1
    assert service.tactics.get("test-tactic") is not None
    assert service.styleguides.get("test-style") is not None
    assert service.toolguides.get("test-tool") is not None
    assert service.paradigms.get("test-paradigm") is not None
    assert service.procedures.get("test-proc") is not None
    assert service.agent_profiles.get("test-agent") is not None


def test_service_repositories_are_lazily_cached() -> None:
    service = DoctrineService()
    assert service._cache == {}

    first_directives = service.directives
    assert "directives" in service._cache
    assert "tactics" not in service._cache

    second_directives = service.directives
    assert first_directives is second_directives

    _ = service.tactics
    assert "tactics" in service._cache


def test_service_honors_custom_shipped_and_project_roots(tmp_path: Path) -> None:
    shipped_root = tmp_path / "shipped-root"
    project_root = tmp_path / "project-root"

    shipped_directive = {
        "schema_version": "1.0",
        "id": "DIRECTIVE_CUSTOM",
        "title": "Base Directive",
        "intent": "Base intent.",
        "enforcement": "required",
    }
    project_override = {
        "schema_version": "1.0",
        "id": "DIRECTIVE_CUSTOM",
        "title": "Overridden Directive",
        "intent": "Overridden intent.",
        "enforcement": "advisory",
    }

    _write_yaml(
        shipped_root / "directives" / "shipped" / "001-custom.directive.yaml",
        shipped_directive,
    )
    _write_yaml(
        project_root / "directives" / "custom.directive.yaml",
        project_override,
    )

    service = DoctrineService(shipped_root=shipped_root, project_root=project_root)
    directive = service.directives.get("DIRECTIVE_CUSTOM")
    assert directive is not None
    assert directive.title == "Overridden Directive"
    assert directive.enforcement.value == "advisory"


# NOTE: `test_service_resolves_directive_tactic_refs_across_repositories`
# has been removed as part of WP02 of the
# ``excise-doctrine-curation-and-inline-references-01KP54J6`` mission.
# The Directive model no longer carries inline ``tactic_refs``; cross-artifact
# relationships are expressed exclusively via edges in
# ``src/doctrine/graph.yaml`` and are validated by the DRG cycle/shape tests.


def test_service_filters_language_scoped_artifacts_when_active_languages_do_not_match(
    tmp_path: Path,
) -> None:
    shipped_root = tmp_path / "shipped-root"

    _write_yaml(
        shipped_root / "styleguides" / "shipped" / "python.styleguide.yaml",
        {
            "schema_version": "1.0",
            "id": "python-style",
            "title": "Python Style",
            "scope": "code",
            "applies_to_languages": ["python"],
            "principles": ["Use Python idioms"],
        },
    )
    _write_yaml(
        shipped_root / "styleguides" / "shipped" / "generic.styleguide.yaml",
        {
            "schema_version": "1.0",
            "id": "generic-style",
            "title": "Generic Style",
            "scope": "code",
            "principles": ["Be clear"],
        },
    )
    _write_yaml(
        shipped_root / "toolguides" / "shipped" / "python.toolguide.yaml",
        {
            "schema_version": "1.0",
            "id": "python-tool",
            "tool": "pytest",
            "title": "Python Tool",
            "guide_path": "src/doctrine/toolguides/shipped/python.md",
            "summary": "Python tool",
            "applies_to_languages": ["python"],
        },
    )
    _write_yaml(
        shipped_root / "toolguides" / "shipped" / "generic.toolguide.yaml",
        {
            "schema_version": "1.0",
            "id": "generic-tool",
            "tool": "git",
            "title": "Generic Tool",
            "guide_path": "src/doctrine/toolguides/shipped/generic.md",
            "summary": "Generic tool",
        },
    )
    _write_yaml(
        shipped_root / "agent_profiles" / "shipped" / "python.agent.yaml",
        {
            "profile-id": "python-implementer",
            "name": "Python Implementer",
            "role": "implementer",
            "purpose": "Python specialist",
            "applies_to_languages": ["python"],
            "specialization": {
                "primary-focus": "python",
                "secondary-awareness": "testing",
                "avoidance-boundary": "other stacks",
                "success-definition": "ship Python changes safely",
            },
        },
    )
    _write_yaml(
        shipped_root / "agent_profiles" / "shipped" / "generic.agent.yaml",
        {
            "profile-id": "generic-implementer",
            "name": "Generic Implementer",
            "role": "implementer",
            "purpose": "General specialist",
            "specialization": {
                "primary-focus": "general implementation",
                "secondary-awareness": "quality",
                "avoidance-boundary": "none",
                "success-definition": "ship changes safely",
            },
        },
    )

    service = DoctrineService(shipped_root=shipped_root, active_languages=["typescript"])

    assert service.styleguides.get("generic-style") is not None
    assert service.styleguides.get("python-style") is None
    assert service.toolguides.get("generic-tool") is not None
    assert service.toolguides.get("python-tool") is None
    assert service.agent_profiles.get("generic-implementer") is not None
    assert service.agent_profiles.get("python-implementer") is None


def test_service_keeps_language_scoped_artifacts_when_active_languages_are_unset(
    tmp_path: Path,
) -> None:
    shipped_root = tmp_path / "shipped-root"

    _write_yaml(
        shipped_root / "styleguides" / "shipped" / "python.styleguide.yaml",
        {
            "schema_version": "1.0",
            "id": "python-style",
            "title": "Python Style",
            "scope": "code",
            "applies_to_languages": ["python"],
            "principles": ["Use Python idioms"],
        },
    )
    _write_yaml(
        shipped_root / "toolguides" / "shipped" / "python.toolguide.yaml",
        {
            "schema_version": "1.0",
            "id": "python-tool",
            "tool": "pytest",
            "title": "Python Tool",
            "guide_path": "src/doctrine/toolguides/shipped/python.md",
            "summary": "Python tool",
            "applies_to_languages": ["python"],
        },
    )
    _write_yaml(
        shipped_root / "agent_profiles" / "shipped" / "python.agent.yaml",
        {
            "profile-id": "python-implementer",
            "name": "Python Implementer",
            "role": "implementer",
            "purpose": "Python specialist",
            "applies_to_languages": ["python"],
            "specialization": {
                "primary-focus": "python",
                "secondary-awareness": "testing",
                "avoidance-boundary": "other stacks",
                "success-definition": "ship Python changes safely",
            },
        },
    )

    service = DoctrineService(shipped_root=shipped_root)

    assert service.styleguides.get("python-style") is not None
    assert service.toolguides.get("python-tool") is not None
    assert service.agent_profiles.get("python-implementer") is not None


def test_service_exposes_specification_by_example_artifacts() -> None:
    service = DoctrineService()
    graph = merge_layers(load_graph(SHIPPED_GRAPH), None)

    paradigm = service.paradigms.get("specification-by-example")
    assert paradigm is not None
    assert "DIRECTIVE_037" in paradigm.directive_refs

    directive = service.directives.get("DIRECTIVE_037")
    assert directive is not None

    tactic = service.tactics.get("usage-examples-sync")
    assert tactic is not None
    assert any(ref.id == "DIRECTIVE_010" for ref in tactic.references)

    procedure = service.procedures.get("example-mapping-workshop")
    assert procedure is not None

    paradigm_edges = {(edge.target, edge.relation) for edge in graph.edges_from("paradigm:specification-by-example")}
    assert ("directive:DIRECTIVE_037", Relation.REQUIRES) in paradigm_edges
    assert ("tactic:usage-examples-sync", Relation.REQUIRES) in paradigm_edges

    directive_edges = {(edge.target, edge.relation) for edge in graph.edges_from("directive:DIRECTIVE_037")}
    assert ("tactic:usage-examples-sync", Relation.REQUIRES) in directive_edges

    procedure_edges = {(edge.target, edge.relation) for edge in graph.edges_from("procedure:example-mapping-workshop")}
    assert ("tactic:usage-examples-sync", Relation.REQUIRES) in procedure_edges
