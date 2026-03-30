"""Tests for DoctrineService lazy aggregation behavior."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from doctrine.service import DoctrineService
import pytest
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]



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


def test_service_resolves_directive_tactic_refs_across_repositories(
    tmp_path: Path,
) -> None:
    shipped_root = tmp_path / "shipped-root"

    _write_yaml(
        shipped_root / "directives" / "shipped" / "001-test.directive.yaml",
        {
            "schema_version": "1.0",
            "id": "DIRECTIVE_TEST",
            "title": "Test Directive",
            "intent": "Test intent.",
            "enforcement": "required",
            "tactic_refs": ["test-tactic"],
        },
    )
    _write_yaml(
        shipped_root / "tactics" / "shipped" / "test-tactic.tactic.yaml",
        {
            "schema_version": "1.0",
            "id": "test-tactic",
            "name": "Test Tactic",
            "steps": [{"title": "Step 1"}],
        },
    )

    service = DoctrineService(shipped_root=shipped_root)
    directive = service.directives.get("DIRECTIVE_TEST")
    assert directive is not None
    assert directive.tactic_refs

    for ref in directive.tactic_refs:
        assert service.tactics.get(ref) is not None

