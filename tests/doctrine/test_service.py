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


def test_service_loads_all_repositories_from_built_in_defaults(tmp_path: Path) -> None:
    built_in_root = tmp_path / "shipped-root"

    _write_yaml(
        built_in_root / "directives" / "built-in" / "001-test.directive.yaml",
        {"schema_version": "1.0", "id": "DIRECTIVE_001", "title": "Test",
         "intent": "Test intent.", "enforcement": "required"},
    )
    _write_yaml(
        built_in_root / "tactics" / "built-in" / "test-tactic.tactic.yaml",
        {"schema_version": "1.0", "id": "test-tactic", "name": "Test Tactic",
         "steps": [{"title": "Step 1"}]},
    )
    _write_yaml(
        built_in_root / "styleguides" / "built-in" / "test-style.styleguide.yaml",
        {"schema_version": "1.0", "id": "test-style", "title": "Test Style",
         "scope": "code", "principles": ["Be clear"]},
    )
    _write_yaml(
        built_in_root / "toolguides" / "built-in" / "test-tool.toolguide.yaml",
        {"schema_version": "1.0", "id": "test-tool", "tool": "bash",
         "title": "Test Tool", "guide_path": "src/doctrine/test-tool.md", "summary": "Test."},
    )
    _write_yaml(
        built_in_root / "paradigms" / "built-in" / "test-paradigm.paradigm.yaml",
        {"schema_version": "1.0", "id": "test-paradigm", "name": "Test Paradigm",
         "summary": "Test."},
    )
    _write_yaml(
        built_in_root / "procedures" / "built-in" / "test-proc.procedure.yaml",
        {"schema_version": "1.0", "id": "test-proc", "name": "Test Procedure",
         "purpose": "Test.", "entry_condition": "Always.",
         "exit_condition": "Done.", "steps": [{"title": "Step 1"}]},
    )
    _write_yaml(
        built_in_root / "agent_profiles" / "built-in" / "test.agent.yaml",
        {"profile-id": "test-agent", "name": "Test Agent", "roles": ["implementer"],
         "personality-traits": ["diligent"], "directive-references": [],
         "purpose": "Test agent for unit tests.",
         "specialization": {
             "primary-focus": "testing",
             "secondary-awareness": "testing",
             "avoidance-boundary": "none",
             "success-definition": "tests pass",
         }},
    )

    service = DoctrineService(built_in_root=built_in_root)

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


def test_service_honors_custom_built_in_and_project_roots(tmp_path: Path) -> None:
    built_in_root = tmp_path / "shipped-root"
    project_root = tmp_path / "project-root"

    built_in_directive = {
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
        built_in_root / "directives" / "built-in" / "001-custom.directive.yaml",
        built_in_directive,
    )
    _write_yaml(
        project_root / "directives" / "custom.directive.yaml",
        project_override,
    )

    service = DoctrineService(built_in_root=built_in_root, project_root=project_root)
    directive = service.directives.get("DIRECTIVE_CUSTOM")
    assert directive is not None
    assert directive.title == "Overridden Directive"
    assert directive.enforcement.value == "advisory"


def test_service_loads_synthesized_project_root_singular_kind_dirs(tmp_path: Path) -> None:
    project_root = tmp_path / ".kittify" / "doctrine"

    _write_yaml(
        project_root / "directive" / "001-project.directive.yaml",
        {
            "schema_version": "1.0",
            "id": "PROJECT_001",
            "title": "Project Directive",
            "intent": "Project intent.",
            "enforcement": "required",
        },
    )
    _write_yaml(
        project_root / "tactic" / "project-tactic.tactic.yaml",
        {
            "schema_version": "1.0",
            "id": "project-tactic",
            "name": "Project Tactic",
            "steps": [{"title": "Step 1"}],
        },
    )
    _write_yaml(
        project_root / "styleguide" / "project-style.styleguide.yaml",
        {
            "schema_version": "1.0",
            "id": "project-style",
            "title": "Project Style",
            "scope": "code",
            "principles": ["Be clear"],
        },
    )

    service = DoctrineService(built_in_root=tmp_path / "shipped-root", project_root=project_root)

    assert service.directives.get("PROJECT_001") is not None
    assert service.tactics.get("project-tactic") is not None
    assert service.styleguides.get("project-style") is not None


def test_service_ignores_legacy_plural_dirs_for_synthesized_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / ".kittify" / "doctrine"

    _write_yaml(
        project_root / "directives" / "001-legacy.directive.yaml",
        {
            "schema_version": "1.0",
            "id": "PROJECT_LEGACY",
            "title": "Legacy Directive",
            "intent": "Legacy intent.",
            "enforcement": "required",
        },
    )
    _write_yaml(
        project_root / "tactics" / "legacy-tactic.tactic.yaml",
        {
            "schema_version": "1.0",
            "id": "legacy-tactic",
            "name": "Legacy Tactic",
            "steps": [{"title": "Step 1"}],
        },
    )
    _write_yaml(
        project_root / "styleguides" / "legacy-style.styleguide.yaml",
        {
            "schema_version": "1.0",
            "id": "legacy-style",
            "title": "Legacy Style",
            "scope": "code",
            "principles": ["Be clear"],
        },
    )

    service = DoctrineService(built_in_root=tmp_path / "shipped-root", project_root=project_root)

    assert service.directives.get("PROJECT_LEGACY") is None
    assert service.tactics.get("legacy-tactic") is None
    assert service.styleguides.get("legacy-style") is None


# NOTE: `test_service_resolves_directive_tactic_refs_across_repositories`
# has been removed as part of WP02 of the
# ``excise-doctrine-curation-and-inline-references-01KP54J6`` mission.
# The Directive model no longer carries inline ``tactic_refs``; cross-artifact
# relationships are expressed exclusively via edges in
# ``src/doctrine/graph.yaml`` and are validated by the DRG cycle/shape tests.


def test_service_filters_language_scoped_artifacts_when_active_languages_do_not_match(
    tmp_path: Path,
) -> None:
    built_in_root = tmp_path / "shipped-root"

    _write_yaml(
        built_in_root / "styleguides" / "built-in" / "python.styleguide.yaml",
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
        built_in_root / "styleguides" / "built-in" / "generic.styleguide.yaml",
        {
            "schema_version": "1.0",
            "id": "generic-style",
            "title": "Generic Style",
            "scope": "code",
            "principles": ["Be clear"],
        },
    )
    _write_yaml(
        built_in_root / "toolguides" / "built-in" / "python.toolguide.yaml",
        {
            "schema_version": "1.0",
            "id": "python-tool",
            "tool": "pytest",
            "title": "Python Tool",
            "guide_path": "src/doctrine/toolguides/built-in/python.md",
            "summary": "Python tool",
            "applies_to_languages": ["python"],
        },
    )
    _write_yaml(
        built_in_root / "toolguides" / "built-in" / "generic.toolguide.yaml",
        {
            "schema_version": "1.0",
            "id": "generic-tool",
            "tool": "git",
            "title": "Generic Tool",
            "guide_path": "src/doctrine/toolguides/built-in/generic.md",
            "summary": "Generic tool",
        },
    )
    _write_yaml(
        built_in_root / "agent_profiles" / "built-in" / "python.agent.yaml",
        {
            "profile-id": "python-pedro",
            "name": "Python Pedro",
            "roles": ["implementer"],
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
        built_in_root / "agent_profiles" / "built-in" / "generic.agent.yaml",
        {
            "profile-id": "generic-implementer",
            "name": "Generic Implementer",
            "roles": ["implementer"],
            "purpose": "General specialist",
            "specialization": {
                "primary-focus": "general implementation",
                "secondary-awareness": "quality",
                "avoidance-boundary": "none",
                "success-definition": "ship changes safely",
            },
        },
    )

    service = DoctrineService(built_in_root=built_in_root, active_languages=["typescript"])

    assert service.styleguides.get("generic-style") is not None
    assert service.styleguides.get("python-style") is None
    assert service.toolguides.get("generic-tool") is not None
    assert service.toolguides.get("python-tool") is None
    assert service.agent_profiles.get("generic-implementer") is not None
    assert service.agent_profiles.get("python-pedro") is None


def test_service_keeps_language_scoped_artifacts_when_active_languages_are_unset(
    tmp_path: Path,
) -> None:
    built_in_root = tmp_path / "shipped-root"

    _write_yaml(
        built_in_root / "styleguides" / "built-in" / "python.styleguide.yaml",
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
        built_in_root / "toolguides" / "built-in" / "python.toolguide.yaml",
        {
            "schema_version": "1.0",
            "id": "python-tool",
            "tool": "pytest",
            "title": "Python Tool",
            "guide_path": "src/doctrine/toolguides/built-in/python.md",
            "summary": "Python tool",
            "applies_to_languages": ["python"],
        },
    )
    _write_yaml(
        built_in_root / "agent_profiles" / "built-in" / "python.agent.yaml",
        {
            "profile-id": "python-pedro",
            "name": "Python Pedro",
            "roles": ["implementer"],
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

    service = DoctrineService(built_in_root=built_in_root)

    assert service.styleguides.get("python-style") is not None
    assert service.toolguides.get("python-tool") is not None
    assert service.agent_profiles.get("python-pedro") is not None


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
