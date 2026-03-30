"""Tests for Procedure domain model."""

import pytest
from pydantic import ValidationError

from doctrine.artifact_kinds import ArtifactKind
from doctrine.procedures.models import (
    ActorRole,
    Procedure,
    ProcedureStep,
)
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# Alias kept for readability in test assertions
ProcedureReferenceType = ArtifactKind


class TestProcedureModel:
    """Procedure Pydantic model tests."""

    def test_valid_procedure(self, sample_procedure_data: dict) -> None:
        p = Procedure.model_validate(sample_procedure_data)
        assert p.id == "curation-interview"
        assert p.name == "Doctrine Curation Interview"
        assert len(p.steps) == 3
        assert p.entry_condition.startswith("At least one")

    def test_enriched_procedure(self, enriched_procedure_data: dict) -> None:
        p = Procedure.model_validate(enriched_procedure_data)
        assert p.id == "mission-merge-ceremony"
        assert p.steps[0].on_failure is not None
        assert p.steps[0].tactic_refs == ["adr-drafting-workflow"]
        assert len(p.references) == 2
        assert p.references[0].type == ProcedureReferenceType.DIRECTIVE
        assert p.references[1].type == ProcedureReferenceType.TEMPLATE

    def test_step_actor_defaults_to_agent(self) -> None:
        step = ProcedureStep(title="test step")
        assert step.actor == ActorRole.AGENT

    def test_all_actor_roles(self) -> None:
        for role in ("human", "agent", "system"):
            step = ProcedureStep(title="test", actor=role)
            assert step.actor == role

    def test_missing_required_fields_raises(self) -> None:
        with pytest.raises(ValidationError):
            Procedure.model_validate({"schema_version": "1.0", "id": "x"})

    def test_empty_steps_raises(self) -> None:
        with pytest.raises(ValidationError):
            Procedure.model_validate(
                {
                    "schema_version": "1.0",
                    "id": "empty",
                    "name": "Empty",
                    "purpose": "Nothing",
                    "entry_condition": "Never",
                    "exit_condition": "Never",
                    "steps": [],
                }
            )

    def test_invalid_id_pattern_raises(self) -> None:
        with pytest.raises(ValidationError):
            Procedure.model_validate(
                {
                    "schema_version": "1.0",
                    "id": "UPPER_CASE",
                    "name": "Bad",
                    "purpose": "Test",
                    "entry_condition": "x",
                    "exit_condition": "x",
                    "steps": [{"title": "s"}],
                }
            )

    def test_frozen_model(self, sample_procedure_data: dict) -> None:
        p = Procedure.model_validate(sample_procedure_data)
        with pytest.raises(ValidationError):
            p.name = "changed"
