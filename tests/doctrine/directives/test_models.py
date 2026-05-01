"""Unit tests for Directive model and typed references."""

import pytest
from pydantic import ValidationError

from doctrine.artifact_kinds import ArtifactKind
from doctrine.directives.models import Directive, Enforcement
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# Alias kept for readability in test assertions
DirectiveReferenceType = ArtifactKind


class TestEnforcement:
    def test_required_value(self) -> None:
        assert Enforcement.REQUIRED == "required"

    def test_lenient_adherence_value(self) -> None:
        assert Enforcement.LENIENT_ADHERENCE == "lenient-adherence"

    def test_advisory_value(self) -> None:
        assert Enforcement.ADVISORY == "advisory"


class TestDirectiveReferenceType:
    def test_toolguide_value(self) -> None:
        assert DirectiveReferenceType.TOOLGUIDE == "toolguide"

    def test_template_value(self) -> None:
        assert DirectiveReferenceType.TEMPLATE == "template"


class TestDirective:
    def test_minimal_construction(self, sample_directive_data: dict) -> None:
        directive = Directive.model_validate(sample_directive_data)
        assert directive.id == "DIRECTIVE_999"
        assert directive.title == "Test Directive"
        assert directive.enforcement == Enforcement.REQUIRED
        # Post-WP02: inline `tactic_refs` has been excised from the Directive
        # model; cross-artifact relationships live in src/doctrine/graph.yaml.
        assert not hasattr(directive, "tactic_refs")
        assert directive.scope is None
        assert directive.procedures == []
        assert directive.references == []
        assert directive.integrity_rules == []
        assert directive.validation_criteria == []
        assert directive.explicit_allowances == []

    def test_enriched_construction(self, enriched_directive_data: dict) -> None:
        directive = Directive.model_validate(enriched_directive_data)
        assert directive.scope == "Applies to all test scenarios."
        assert len(directive.procedures) == 2
        assert len(directive.references) == 1
        assert directive.references[0].type == DirectiveReferenceType.TOOLGUIDE
        assert directive.references[0].id == "git-agent-commit-signing"
        assert len(directive.integrity_rules) == 1
        assert len(directive.validation_criteria) == 1
        assert len(directive.explicit_allowances) == 1
        # Post-WP02: inline `tactic_refs` is no longer a Directive attribute.
        assert not hasattr(directive, "tactic_refs")

    def test_frozen_model(self, sample_directive_data: dict) -> None:
        directive = Directive.model_validate(sample_directive_data)
        with pytest.raises(ValidationError):
            directive.title = "changed"  # type: ignore[misc]

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Directive.model_validate({"id": "DIRECTIVE_001", "title": "Test"})

    def test_invalid_enforcement_raises(self, sample_directive_data: dict) -> None:
        sample_directive_data["enforcement"] = "invalid"
        with pytest.raises(ValidationError):
            Directive.model_validate(sample_directive_data)

    def test_lenient_adherence_requires_explicit_allowances(self, sample_directive_data: dict) -> None:
        sample_directive_data["enforcement"] = "lenient-adherence"
        with pytest.raises(ValidationError):
            Directive.model_validate(sample_directive_data)

    def test_invalid_reference_type_raises(self, enriched_directive_data: dict) -> None:
        enriched_directive_data["references"] = [{"type": "unknown", "id": "whatever"}]
        with pytest.raises(ValidationError):
            Directive.model_validate(enriched_directive_data)
