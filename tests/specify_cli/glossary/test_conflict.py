"""Tests for conflict detection and severity scoring (WP04 T017, T018)."""

import pytest
from datetime import datetime

from specify_cli.glossary.models import (
    TermSurface, TermSense, Provenance, SenseStatus, ConflictType, Severity
)
from specify_cli.glossary.extraction import ExtractedTerm
from specify_cli.glossary.conflict import (
    classify_conflict, score_severity, create_conflict, make_sense_ref
)


@pytest.fixture
def sample_term() -> ExtractedTerm:
    """Sample extracted term."""
    return ExtractedTerm(
        surface="workspace",
        source="quoted_phrase",
        confidence=0.8,
        original="workspace",
    )


@pytest.fixture
def sample_senses() -> list[TermSense]:
    """Sample term senses."""
    provenance = Provenance(
        actor_id="user:alice",
        timestamp=datetime(2026, 2, 16, 12, 0, 0),
        source="user_clarification",
    )

    return [
        TermSense(
            surface=TermSurface("workspace"),
            scope="mission_local",
            definition="Git worktree directory",
            provenance=provenance,
            confidence=1.0,
            status=SenseStatus.ACTIVE,
        ),
        TermSense(
            surface=TermSurface("workspace"),
            scope="team_domain",
            definition="VS Code workspace file",
            provenance=provenance,
            confidence=0.9,
            status=SenseStatus.ACTIVE,
        ),
    ]


# ============================================================================
# T017: Conflict Classification Tests
# ============================================================================


def test_classify_conflict_unknown(sample_term: ExtractedTerm) -> None:
    """Test UNKNOWN conflict classification (no matches)."""
    conflict_type = classify_conflict(sample_term, [])

    assert conflict_type == ConflictType.UNKNOWN


def test_classify_conflict_ambiguous(
    sample_term: ExtractedTerm,
    sample_senses: list[TermSense],
) -> None:
    """Test AMBIGUOUS conflict classification (multiple matches)."""
    conflict_type = classify_conflict(sample_term, sample_senses)

    assert conflict_type == ConflictType.AMBIGUOUS


def test_classify_conflict_no_conflict(
    sample_term: ExtractedTerm,
    sample_senses: list[TermSense],
) -> None:
    """Test no conflict when single match exists."""
    single_sense = [sample_senses[0]]
    conflict_type = classify_conflict(sample_term, single_sense)

    assert conflict_type is None


def test_classify_conflict_empty_term() -> None:
    """Test classification with empty extracted term."""
    empty_term = ExtractedTerm(
        surface="",
        source="test",
        confidence=0.5,
        original="",
    )

    # Unknown term (no matches)
    conflict_type = classify_conflict(empty_term, [])
    assert conflict_type == ConflictType.UNKNOWN


# ============================================================================
# T018: Severity Scoring Tests
# ============================================================================


def test_score_severity_ambiguous_critical() -> None:
    """Test HIGH severity for ambiguous conflict in critical step."""
    severity = score_severity(ConflictType.AMBIGUOUS, 0.5, is_critical_step=True)

    assert severity == Severity.HIGH


def test_score_severity_ambiguous_non_critical() -> None:
    """Test MEDIUM severity for ambiguous conflict in non-critical step."""
    severity = score_severity(ConflictType.AMBIGUOUS, 0.5, is_critical_step=False)

    assert severity == Severity.MEDIUM


def test_score_severity_unknown_high_confidence() -> None:
    """Test LOW severity for unknown term with high confidence."""
    severity = score_severity(ConflictType.UNKNOWN, 0.9, is_critical_step=False)

    assert severity == Severity.LOW


def test_score_severity_unknown_medium_confidence() -> None:
    """Test MEDIUM severity for unknown term with medium confidence."""
    severity = score_severity(ConflictType.UNKNOWN, 0.5, is_critical_step=False)

    assert severity == Severity.MEDIUM


def test_score_severity_unknown_low_confidence_critical() -> None:
    """Test HIGH severity for unknown term with low confidence in critical step."""
    severity = score_severity(ConflictType.UNKNOWN, 0.3, is_critical_step=True)

    assert severity == Severity.HIGH


def test_score_severity_unknown_low_confidence_non_critical() -> None:
    """Test MEDIUM severity for unknown term with low confidence in non-critical step."""
    severity = score_severity(ConflictType.UNKNOWN, 0.3, is_critical_step=False)

    assert severity == Severity.MEDIUM


def test_score_severity_inconsistent() -> None:
    """Test LOW severity for inconsistent usage (informational)."""
    severity = score_severity(ConflictType.INCONSISTENT, 0.8, is_critical_step=True)

    assert severity == Severity.LOW


def test_score_severity_unresolved_critical() -> None:
    """Test HIGH severity for unresolved critical term."""
    severity = score_severity(
        ConflictType.UNRESOLVED_CRITICAL, 0.3, is_critical_step=True
    )

    assert severity == Severity.HIGH


def test_score_severity_edge_cases() -> None:
    """Test severity scoring edge cases."""
    # Confidence exactly 0.8 (boundary)
    severity = score_severity(ConflictType.UNKNOWN, 0.8, is_critical_step=False)
    assert severity == Severity.LOW

    # Confidence exactly 0.5 (boundary)
    severity = score_severity(ConflictType.UNKNOWN, 0.5, is_critical_step=False)
    assert severity == Severity.MEDIUM

    # Confidence below 0.5
    severity = score_severity(ConflictType.UNKNOWN, 0.49, is_critical_step=False)
    assert severity == Severity.MEDIUM


# ============================================================================
# Conflict Creation Tests
# ============================================================================


def test_make_sense_ref(sample_senses: list[TermSense]) -> None:
    """Test converting TermSense to SenseRef."""
    sense_ref = make_sense_ref(sample_senses[0])

    assert sense_ref.surface == "workspace"
    assert sense_ref.scope == "mission_local"
    assert sense_ref.definition == "Git worktree directory"
    assert sense_ref.confidence == 1.0


def test_create_conflict_ambiguous(
    sample_term: ExtractedTerm,
    sample_senses: list[TermSense],
) -> None:
    """Test creating an ambiguous conflict."""
    conflict = create_conflict(
        term=sample_term,
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        candidate_senses=sample_senses,
        context="step input: description",
    )

    assert conflict.term.surface_text == "workspace"
    assert conflict.conflict_type == ConflictType.AMBIGUOUS
    assert conflict.severity == Severity.HIGH
    assert conflict.confidence == 0.8
    assert len(conflict.candidate_senses) == 2
    assert conflict.context == "step input: description"


def test_create_conflict_unknown(sample_term: ExtractedTerm) -> None:
    """Test creating an unknown conflict."""
    conflict = create_conflict(
        term=sample_term,
        conflict_type=ConflictType.UNKNOWN,
        severity=Severity.LOW,
        candidate_senses=[],
        context="source: quoted_phrase",
    )

    assert conflict.term.surface_text == "workspace"
    assert conflict.conflict_type == ConflictType.UNKNOWN
    assert conflict.severity == Severity.LOW
    assert len(conflict.candidate_senses) == 0


def test_create_conflict_with_candidates(
    sample_term: ExtractedTerm,
    sample_senses: list[TermSense],
) -> None:
    """Test that candidate_senses are properly converted to SenseRef."""
    conflict = create_conflict(
        term=sample_term,
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        candidate_senses=sample_senses,
    )

    # Verify all candidates are SenseRef objects
    assert all(hasattr(c, "surface") for c in conflict.candidate_senses)
    assert all(hasattr(c, "scope") for c in conflict.candidate_senses)
    assert all(hasattr(c, "definition") for c in conflict.candidate_senses)

    # Verify data is preserved
    assert conflict.candidate_senses[0].surface == "workspace"
    assert conflict.candidate_senses[0].scope == "mission_local"
    assert conflict.candidate_senses[1].scope == "team_domain"


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_classification_workflow_unknown(sample_term: ExtractedTerm) -> None:
    """Test full workflow: classify UNKNOWN → score severity → create conflict."""
    # 1. Classify
    conflict_type = classify_conflict(sample_term, [])
    assert conflict_type == ConflictType.UNKNOWN

    # 2. Score severity
    severity = score_severity(conflict_type, sample_term.confidence, False)
    assert severity == Severity.LOW

    # 3. Create conflict
    conflict = create_conflict(sample_term, conflict_type, severity, [])
    assert conflict.conflict_type == ConflictType.UNKNOWN
    assert conflict.severity == Severity.LOW


def test_full_classification_workflow_ambiguous(
    sample_term: ExtractedTerm,
    sample_senses: list[TermSense],
) -> None:
    """Test full workflow: classify AMBIGUOUS → score severity → create conflict."""
    # 1. Classify
    conflict_type = classify_conflict(sample_term, sample_senses)
    assert conflict_type == ConflictType.AMBIGUOUS

    # 2. Score severity
    severity = score_severity(conflict_type, sample_term.confidence, True)
    assert severity == Severity.HIGH

    # 3. Create conflict
    conflict = create_conflict(sample_term, conflict_type, severity, sample_senses)
    assert conflict.conflict_type == ConflictType.AMBIGUOUS
    assert conflict.severity == Severity.HIGH
    assert len(conflict.candidate_senses) == 2
