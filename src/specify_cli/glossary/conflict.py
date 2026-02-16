"""Conflict detection logic (WP04).

This module implements conflict classification and severity scoring for
semantic conflicts detected during term resolution.
"""

from typing import List, Optional

from .extraction import ExtractedTerm
from .models import ConflictType, Severity, TermSense, TermSurface, SenseRef


def classify_conflict(
    term: ExtractedTerm,
    resolution_results: List[TermSense],
) -> Optional[ConflictType]:
    """Classify conflict type based on resolution results.

    Args:
        term: Extracted term with confidence score
        resolution_results: List of TermSense from scope resolution

    Returns:
        ConflictType if a conflict exists, None otherwise

    Conflict types:
        - UNKNOWN: No match in any scope
        - AMBIGUOUS: 2+ active senses, unqualified usage
        - INCONSISTENT: LLM output contradicts active glossary (deferred to WP06)
        - UNRESOLVED_CRITICAL: Critical term, low confidence (deferred to WP06)

    Note:
        INCONSISTENT and UNRESOLVED_CRITICAL require additional context
        (LLM output analysis, step criticality) which will be implemented in WP06.
        This function handles UNKNOWN and AMBIGUOUS classification only.
    """
    if not resolution_results:
        return ConflictType.UNKNOWN
    elif len(resolution_results) > 1:
        return ConflictType.AMBIGUOUS
    # Single match - no conflict
    return None


def score_severity(
    conflict_type: ConflictType,
    confidence: float,
    is_critical_step: bool = False,
) -> Severity:
    """Score severity based on conflict type, confidence, and step criticality.

    Args:
        conflict_type: Type of conflict detected
        confidence: Extraction confidence (0.0-1.0)
        is_critical_step: Whether the step is marked critical

    Returns:
        Severity level (LOW, MEDIUM, HIGH)

    Scoring matrix:
        - HIGH: (critical step + low confidence) OR ambiguous conflict
        - MEDIUM: (non-critical + ambiguous) OR (unknown + medium confidence)
        - LOW: (inconsistent) OR (unknown + high confidence)

    Examples:
        >>> score_severity(ConflictType.AMBIGUOUS, 0.5, True)
        Severity.HIGH
        >>> score_severity(ConflictType.UNKNOWN, 0.9, False)
        Severity.LOW
        >>> score_severity(ConflictType.UNKNOWN, 0.5, False)
        Severity.MEDIUM
    """
    # Ambiguous conflicts are always high severity if critical step
    if conflict_type == ConflictType.AMBIGUOUS:
        if is_critical_step:
            return Severity.HIGH
        else:
            return Severity.MEDIUM

    # Unknown terms scored by confidence
    elif conflict_type == ConflictType.UNKNOWN:
        if confidence >= 0.8:
            return Severity.LOW  # High confidence unknown (likely safe)
        elif confidence >= 0.5:
            return Severity.MEDIUM  # Medium confidence unknown
        else:
            if is_critical_step:
                return Severity.HIGH  # Low confidence in critical step
            else:
                return Severity.MEDIUM

    # Inconsistent usage (WP06)
    elif conflict_type == ConflictType.INCONSISTENT:
        return Severity.LOW  # Non-blocking, informational

    # Unresolved critical (WP06)
    elif conflict_type == ConflictType.UNRESOLVED_CRITICAL:
        return Severity.HIGH  # Always high severity

    # Default fallback
    return Severity.MEDIUM


def make_sense_ref(sense: TermSense) -> SenseRef:
    """Convert TermSense to SenseRef for conflict reporting.

    Args:
        sense: TermSense to convert

    Returns:
        SenseRef with essential fields (surface, scope, definition, confidence)
    """
    return SenseRef(
        surface=sense.surface.surface_text,
        scope=sense.scope,
        definition=sense.definition,
        confidence=sense.confidence,
    )


def create_conflict(
    term: ExtractedTerm,
    conflict_type: ConflictType,
    severity: Severity,
    candidate_senses: List[TermSense],
    context: str = "",
) -> "models.SemanticConflict":
    """Create a SemanticConflict from classification results.

    Args:
        term: Extracted term that has a conflict
        conflict_type: Type of conflict detected
        severity: Severity score
        candidate_senses: List of matching TermSense objects
        context: Usage context (e.g., "step input: description field")

    Returns:
        SemanticConflict with all fields populated
    """
    from . import models

    return models.SemanticConflict(
        term=TermSurface(term.surface),
        conflict_type=conflict_type,
        severity=severity,
        confidence=term.confidence,
        candidate_senses=[make_sense_ref(s) for s in candidate_senses],
        context=context,
    )
