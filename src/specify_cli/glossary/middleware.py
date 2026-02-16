"""Glossary extraction middleware (WP03).

This module implements middleware that extracts glossary term candidates from
primitive execution context (step inputs/outputs) and emits events.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from .extraction import ExtractedTerm, extract_all_terms


class PrimitiveExecutionContext(Protocol):
    """Protocol for primitive execution context.

    This is a forward reference to the actual context that will be implemented
    in WP08 (orchestrator integration). For now, we define the minimal interface
    needed for extraction middleware.
    """

    metadata: Dict[str, Any]
    """Step metadata (may contain glossary_* fields)"""

    step_input: Dict[str, Any]
    """Step input data"""

    step_output: Dict[str, Any]
    """Step output data"""

    extracted_terms: List[ExtractedTerm]
    """List of extracted terms (populated by middleware)"""


@dataclass
class MockContext:
    """Mock context for testing middleware in isolation.

    This will be replaced by the actual PrimitiveExecutionContext in WP08.
    """

    metadata: Dict[str, Any] = field(default_factory=dict)
    step_input: Dict[str, Any] = field(default_factory=dict)
    step_output: Dict[str, Any] = field(default_factory=dict)
    extracted_terms: List[ExtractedTerm] = field(default_factory=list)


class GlossaryCandidateExtractionMiddleware:
    """Middleware that extracts glossary term candidates from execution context.

    This middleware:
    1. Extracts terms from metadata hints (glossary_watch_terms, etc.)
    2. Extracts terms from heuristics (quoted phrases, acronyms, casing patterns, repeated nouns)
    3. Normalizes all terms
    4. Scores confidence
    5. Emits TermCandidateObserved events (WP08)
    6. Adds extracted terms to context.extracted_terms

    Performance target: <100ms for typical step input (100-500 words).
    """

    def __init__(self, glossary_fields: List[str] | None = None) -> None:
        """Initialize middleware.

        Args:
            glossary_fields: List of field names to scan for terms.
                If None, scans all fields. Default: ["description", "prompt", "output"]
        """
        self.glossary_fields = glossary_fields or ["description", "prompt", "output"]

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """Process context and extract term candidates.

        Args:
            context: Execution context (must have metadata, step_input, step_output)

        Returns:
            Updated context with extracted_terms populated

        Side effects:
            - Emits TermCandidateObserved events (WP08)
        """
        # 1. Determine which fields to scan
        # Check if metadata specifies glossary_fields (runtime override)
        fields_to_scan = self.glossary_fields
        if context.metadata and "glossary_fields" in context.metadata:
            metadata_fields = context.metadata["glossary_fields"]
            # Validate it's a list of strings
            if isinstance(metadata_fields, list) and all(
                isinstance(f, str) for f in metadata_fields
            ):
                fields_to_scan = metadata_fields

        # 2. Collect text from glossary fields
        text_parts: List[str] = []

        # Scan configured fields in step_input
        for field_name in fields_to_scan:
            if field_name in context.step_input:
                value = context.step_input[field_name]
                if isinstance(value, str):
                    text_parts.append(value)

        # Scan configured fields in step_output
        for field_name in fields_to_scan:
            if field_name in context.step_output:
                value = context.step_output[field_name]
                if isinstance(value, str):
                    text_parts.append(value)

        # Combine all text
        combined_text = "\n".join(text_parts)

        # 3. Extract terms (metadata hints + heuristics)
        extracted = extract_all_terms(
            text=combined_text,
            metadata=context.metadata if context.metadata else None,
            limit_words=1000,
        )

        # 4. Add to context
        context.extracted_terms.extend(extracted)

        # 5. Emit events for each extracted term
        for term in extracted:
            self._emit_term_candidate_observed(term, context)

        return context

    def _emit_term_candidate_observed(
        self,
        term: ExtractedTerm,
        context: PrimitiveExecutionContext,
    ) -> None:
        """Emit TermCandidateObserved event (stub until WP08).

        Args:
            term: Extracted term to emit event for
            context: Execution context providing metadata

        Note:
            This is a stub implementation. The actual event emission infrastructure
            will be implemented in WP08 (orchestrator integration). When WP08 is
            complete, this method will be replaced with:

            from .events import emit_term_candidate_observed
            emit_term_candidate_observed(term, context)

            For now, this serves as:
            1. Documentation of the event emission contract
            2. Placeholder for testing middleware behavior
            3. Interface definition for WP08 integration
        """
        # Stub: Event emission deferred to WP08
        # When implemented, this will emit an event with:
        # - event_type: "TermCandidateObserved"
        # - term.surface: normalized term surface
        # - term.confidence: extraction confidence score
        # - term.source: extraction source (metadata_hint, quoted_phrase, etc.)
        # - context.metadata: step metadata for correlation
        pass

    def scan_fields(self, data: Dict[str, Any]) -> str:
        """Scan configured fields in a data dictionary.

        Args:
            data: Dictionary to scan

        Returns:
            Combined text from all matching fields
        """
        text_parts: List[str] = []

        for field_name in self.glossary_fields:
            if field_name in data:
                value = data[field_name]
                if isinstance(value, str):
                    text_parts.append(value)

        return "\n".join(text_parts)


class SemanticCheckMiddleware:
    """Middleware that resolves extracted terms and detects semantic conflicts.

    This middleware:
    1. Resolves extracted terms against scope hierarchy
    2. Classifies conflicts (UNKNOWN, AMBIGUOUS, INCONSISTENT, UNRESOLVED_CRITICAL)
    3. Scores severity based on step criticality + confidence
    4. Emits SemanticCheckEvaluated events (WP08)
    5. Adds conflicts to context.conflicts

    Usage:
        middleware = SemanticCheckMiddleware(glossary_store, scope_order)
        context = middleware.process(context)
    """

    def __init__(
        self,
        glossary_store: "store.GlossaryStore",
        scope_order: List["scope.GlossaryScope"] | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            glossary_store: GlossaryStore to query for term resolution
            scope_order: List of GlossaryScope in precedence order.
                If None, uses default SCOPE_RESOLUTION_ORDER.
        """
        from . import scope, store

        self.glossary_store: store.GlossaryStore = glossary_store
        self.scope_order = scope_order or scope.SCOPE_RESOLUTION_ORDER

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """Process context and detect semantic conflicts.

        Args:
            context: Execution context with extracted_terms populated

        Returns:
            Updated context with conflicts populated

        Side effects:
            - Emits SemanticCheckEvaluated event (WP08)
        """
        from typing import cast, Any
        from .conflict import classify_conflict, create_conflict, score_severity
        from . import models
        from .resolution import resolve_term

        conflicts: List[models.SemanticConflict] = []

        # Get step criticality flag from metadata (default: False)
        is_critical_step = False
        if hasattr(context, "metadata") and context.metadata:
            is_critical_step = context.metadata.get("critical_step", False)

        # Resolve each extracted term
        for extracted_term in context.extracted_terms:
            # 1. Resolve against scope hierarchy
            senses = resolve_term(
                extracted_term.surface,
                self.scope_order,
                self.glossary_store,
            )

            # 2. Classify conflict
            conflict_type = classify_conflict(extracted_term, senses)

            # 3. If conflict exists, score severity and create conflict
            if conflict_type is not None:
                severity = score_severity(
                    conflict_type,
                    extracted_term.confidence,
                    is_critical_step,
                )

                # Determine context string
                context_str = f"source: {extracted_term.source}"

                conflict = create_conflict(
                    term=extracted_term,
                    conflict_type=conflict_type,
                    severity=severity,
                    candidate_senses=senses,
                    context=context_str,
                )

                conflicts.append(conflict)

        # Add conflicts to context (using setattr to handle Protocol)
        if not hasattr(context, "conflicts"):
            setattr(context, "conflicts", [])
        cast(Any, context).conflicts.extend(conflicts)

        # Emit SemanticCheckEvaluated event
        self._emit_semantic_check_evaluated(context, conflicts)

        return context

    def _emit_semantic_check_evaluated(
        self,
        context: PrimitiveExecutionContext,
        conflicts: List["models.SemanticConflict"],
    ) -> None:
        """Emit SemanticCheckEvaluated event (stub until WP08).

        Args:
            context: Execution context
            conflicts: List of detected conflicts

        Note:
            This is a stub implementation. The actual event emission infrastructure
            will be implemented in WP08 (orchestrator integration). When WP08 is
            complete, this method will be replaced with:

            from .events import emit_semantic_check_evaluated
            emit_semantic_check_evaluated(context, conflicts)

            For now, this serves as:
            1. Documentation of the event emission contract
            2. Placeholder for testing middleware behavior
            3. Interface definition for WP08 integration
        """
        # Stub: Event emission deferred to WP08
        # When implemented, this will emit an event with:
        # - event_type: "SemanticCheckEvaluated"
        # - conflicts: List of SemanticConflict serialized to dict
        # - overall_severity: max(conflict.severity for conflict in conflicts)
        # - recommended_action: "block" | "warn" | "allow"
        # - context.metadata: step metadata for correlation
        pass
