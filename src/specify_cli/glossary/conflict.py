"""Conflict detection logic (WP04).

This module implements conflict classification and severity scoring for
semantic conflicts detected during term resolution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from .extraction import ExtractedTerm
from .models import ConflictType, Severity, TermSense, TermSurface, SenseRef, SenseStatus

if TYPE_CHECKING:
    from . import models


def classify_conflict(
    term: ExtractedTerm,
    resolution_results: List[TermSense],
    is_critical_step: bool = False,
    llm_output_text: Optional[str] = None,
) -> Optional[ConflictType]:
    """Classify conflict type based on resolution results.

    Args:
        term: Extracted term with confidence score
        resolution_results: List of TermSense from scope resolution
        is_critical_step: Whether the step is marked as critical (for UNRESOLVED_CRITICAL)
        llm_output_text: LLM output text to check for contradictions (for INCONSISTENT)

    Returns:
        ConflictType if a conflict exists, None otherwise

    Conflict types:
        - UNKNOWN: No match in any scope
        - AMBIGUOUS: 2+ active senses, unqualified usage
        - INCONSISTENT: LLM output contradicts active glossary
        - UNRESOLVED_CRITICAL: Critical term, low confidence, unresolved

    Note:
        INCONSISTENT detection requires llm_output_text parameter.
        UNRESOLVED_CRITICAL requires is_critical_step=True.
    """
    # UNKNOWN: No match in any scope
    if not resolution_results:
        # Check if this is a critical step with low confidence (UNRESOLVED_CRITICAL)
        if is_critical_step and term.confidence < 0.5:
            return ConflictType.UNRESOLVED_CRITICAL
        return ConflictType.UNKNOWN

    # AMBIGUOUS: 2+ active senses (filter out deprecated/draft)
    active_senses = [s for s in resolution_results if s.status == SenseStatus.ACTIVE]
    if len(active_senses) > 1:
        return ConflictType.AMBIGUOUS

    # Single match - check for INCONSISTENT
    if llm_output_text is not None and len(resolution_results) == 1:
        sense = resolution_results[0]
        # Simple contradiction check: if LLM output uses the term but with
        # a different meaning than the glossary definition (heuristic)
        # This is a basic implementation - WP06 may enhance with semantic analysis
        if _detect_inconsistent_usage(term.surface, sense.definition, llm_output_text):
            return ConflictType.INCONSISTENT

    # Single match - no conflict
    return None


def _detect_inconsistent_usage(
    term_surface: str,
    glossary_definition: str,
    llm_output: str,
) -> bool:
    """Detect if LLM output uses term inconsistently with glossary.

    This is a heuristic-based implementation. Uses simple keyword matching
    to detect if the term appears in output with contradictory context.

    Args:
        term_surface: The term being checked
        glossary_definition: The authoritative definition from glossary
        llm_output: The LLM-generated text to analyze

    Returns:
        True if inconsistent usage detected

    Implementation:
        Uses keyword-based contradiction detection:
        1. Extract key concepts from glossary definition (nouns)
        2. Search for term usage context in LLM output
        3. Check if context contradicts key concepts

        Contradiction indicators:
        - Negation words near term ("not a", "isn't a", "unlike")
        - Alternative definitions ("refers to", "means", "is a")
        - Context missing key concepts from definition

    Note:
        This is a basic heuristic implementation. WP06 may enhance with:
        - Semantic similarity models
        - Context window analysis
        - LLM-based contradiction detection
    """
    # Normalize inputs
    term_lower = term_surface.lower()
    definition_lower = glossary_definition.lower()
    output_lower = llm_output.lower()

    # Quick exit: term not in output
    if term_lower not in output_lower:
        return False

    # Extract key concepts from definition (simple noun extraction)
    # Split definition into words, filter stop words
    stop_words = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "of",
        "for",
        "to",
        "in",
        "on",
        "at",
        "by",
        "with",
        "from",
        "as",
        "and",
        "or",
        "but",
    }
    definition_words = set(
        word.strip(".,;:!?") for word in definition_lower.split() if len(word) > 3 and word not in stop_words
    )

    # Find term occurrences in output with context window
    import re

    # Pattern: capture 50 chars before and after term
    pattern = rf"(.{{0,50}})\b{re.escape(term_lower)}\b(.{{0,50}})"
    matches = list(re.finditer(pattern, output_lower))

    for match in matches:
        before_context = match.group(1)
        after_context = match.group(2)
        context = before_context + " " + term_lower + " " + after_context

        # Check for direct negation of definition key concepts
        # Example: definition has "unit of work", output says "not a unit of work"
        for def_word in definition_words:
            # Pattern: "is not a {def_word}", "isn't a {def_word}", "{term} not a {def_word}"
            negation_of_concept = rf"\b(is\s+not|isn['']t|not\s+a|not\s+an)\s+({def_word}|[a-z]+\s+{def_word})"
            if re.search(negation_of_concept, context):
                return True  # Negation of key concept = contradiction

        # Check for broader negation patterns
        negation_patterns = [
            rf"\b{re.escape(term_lower)}\s+is\s+not\s+a?\b",
            rf"\b{re.escape(term_lower)}\s+isn['']t\s+a?\b",
            rf"\bnot\s+a\s+{re.escape(term_lower)}\b",
            rf"\bunlike\s+{re.escape(term_lower)}\b",
            rf"\bcontrary\s+to\s+{re.escape(term_lower)}\b",
        ]

        for neg_pattern in negation_patterns:
            if re.search(neg_pattern, context):
                return True  # Negation found = contradiction

        # Check for alternative definitions
        alternative_patterns = [
            rf"\b{re.escape(term_lower)}\s+(refers\s+to|means|is\s+a|is\s+an)\b",
        ]

        for alt_pattern in alternative_patterns:
            if re.search(alt_pattern, context):
                # Check if the alternative definition contradicts key concepts
                context_words = set(
                    word.strip(".,;:!?") for word in context.split() if len(word) > 3 and word not in stop_words
                )

                # If less than 30% overlap with definition key concepts, flag inconsistency
                if definition_words:
                    overlap = len(definition_words & context_words)
                    overlap_ratio = overlap / len(definition_words)
                    if overlap_ratio < 0.3:
                        return True  # Low overlap = likely contradiction

    return False


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
