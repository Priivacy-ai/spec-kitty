"""Pytest fixtures for glossary tests."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from typing import List
from specify_cli.glossary.models import (
    TermSurface,
    TermSense,
    Provenance,
    SenseStatus,
    SemanticConflict,
    ConflictType,
    Severity,
    SenseRef,
)


@pytest.fixture
def sample_term_surface():
    """Sample TermSurface for testing."""
    return TermSurface("workspace")


@pytest.fixture
def sample_provenance():
    """Sample Provenance for testing."""
    return Provenance(
        actor_id="user:alice",
        timestamp=datetime(2026, 2, 16, 12, 0, 0),
        source="user_clarification",
    )


@pytest.fixture
def sample_term_sense(sample_term_surface, sample_provenance):
    """Sample TermSense for testing."""
    return TermSense(
        surface=sample_term_surface,
        scope="team_domain",
        definition="Git worktree directory for a work package",
        provenance=sample_provenance,
        confidence=0.9,
        status=SenseStatus.ACTIVE,
    )


@pytest.fixture
def mock_primitive_context():
    """Mock PrimitiveExecutionContext for testing."""
    context = MagicMock()
    context.inputs = {"description": "The workspace contains files"}
    context.metadata = {
        "glossary_check": "enabled",
        "glossary_watch_terms": ["workspace", "mission"],
    }
    context.strictness = "medium"
    context.extracted_terms = []
    context.conflicts = []
    return context


@pytest.fixture
def mock_event_log(tmp_path):
    """Mock event log directory for testing."""
    event_log_path = tmp_path / "events"
    event_log_path.mkdir()
    return event_log_path


@pytest.fixture
def sample_seed_file(tmp_path):
    """Sample team_domain.yaml seed file for testing."""
    glossaries_path = tmp_path / ".kittify" / "glossaries"
    glossaries_path.mkdir(parents=True)

    seed_content = """terms:
  - surface: workspace
    definition: Git worktree directory for a work package
    confidence: 1.0
    status: active

  - surface: mission
    definition: Purpose-specific workflow machine
    confidence: 1.0
    status: active
"""
    seed_file = glossaries_path / "team_domain.yaml"
    seed_file.write_text(seed_content)
    return seed_file


def make_conflict(
    surface_text: str,
    conflict_type: ConflictType = ConflictType.AMBIGUOUS,
    severity: Severity = Severity.HIGH,
    candidates: List[SenseRef] = None,
) -> SemanticConflict:
    """Helper to create SemanticConflict for testing."""
    if candidates is None and conflict_type == ConflictType.AMBIGUOUS:
        # Default candidates for ambiguous conflicts
        candidates = [
            SenseRef(surface_text, "team_domain", f"Definition 1 of {surface_text}", 0.9),
            SenseRef(surface_text, "team_domain", f"Definition 2 of {surface_text}", 0.7),
        ]

    return SemanticConflict(
        term=TermSurface(surface_text),
        conflict_type=conflict_type,
        severity=severity,
        confidence=0.9,
        candidate_senses=candidates or [],
        context="test context",
    )
