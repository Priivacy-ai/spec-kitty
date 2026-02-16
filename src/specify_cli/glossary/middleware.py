"""Glossary extraction middleware (WP03).

This module implements middleware that extracts glossary term candidates from
primitive execution context (step inputs/outputs) and emits events.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

from .extraction import ExtractedTerm, extract_all_terms

if TYPE_CHECKING:
    from . import models, scope, store


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

        # Get LLM output text for INCONSISTENT detection (if available)
        llm_output_text: Optional[str] = None
        if hasattr(context, "step_output") and context.step_output:
            # Extract text from output fields for contradiction detection
            output_parts: List[str] = []
            for value in context.step_output.values():
                if isinstance(value, str):
                    output_parts.append(value)
            if output_parts:
                llm_output_text = "\n".join(output_parts)

        # Resolve each extracted term
        for extracted_term in context.extracted_terms:
            # 1. Resolve against scope hierarchy
            senses = resolve_term(
                extracted_term.surface,
                self.scope_order,
                self.glossary_store,
            )

            # 2. Classify conflict (with all 4 types)
            conflict_type = classify_conflict(
                extracted_term,
                senses,
                is_critical_step=is_critical_step,
                llm_output_text=llm_output_text,
            )

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


class GenerationGateMiddleware:
    """Generation gate that blocks LLM calls on unresolved conflicts.

    This middleware:
    1. Resolves effective strictness from precedence chain
    2. Evaluates whether to block based on strictness policy
    3. Emits GenerationBlockedBySemanticConflict event if blocking
    4. Raises BlockedByConflict exception to halt pipeline

    Pipeline position: Layer 3 (after extraction and semantic check)

    Usage:
        gate = GenerationGateMiddleware(
            repo_root=Path("."),
            runtime_override=Strictness.MEDIUM,
        )
        context = gate.process(context)
    """

    def __init__(
        self,
        repo_root: Path | None = None,
        runtime_override: "Strictness" | None = None,  # type: ignore[name-defined]
    ) -> None:
        """Initialize gate with optional runtime override.

        Args:
            repo_root: Path to repository root (for loading config)
            runtime_override: CLI --strictness flag value (highest precedence)
        """
        self.repo_root = repo_root
        self.runtime_override = runtime_override

    def process(
        self,
        context: PrimitiveExecutionContext,
    ) -> PrimitiveExecutionContext:
        """Evaluate conflicts and block if necessary.

        Args:
            context: Execution context (must have conflicts populated by SemanticCheckMiddleware)

        Returns:
            Unmodified context if generation is allowed to proceed

        Raises:
            BlockedByConflict: When strictness policy requires blocking

        Side effects:
            - Stores effective_strictness in context
            - Emits GenerationBlockedBySemanticConflict event (if blocking)
        """
        from pathlib import Path
        from typing import cast, Any
        from .strictness import (
            resolve_strictness,
            should_block,
            Strictness,
            load_global_strictness,
        )
        from .exceptions import BlockedByConflict
        from .events import emit_generation_blocked_event
        from .models import Severity

        # Get conflicts from context (populated by SemanticCheckMiddleware)
        conflicts = getattr(context, "conflicts", [])

        # Resolve effective strictness
        global_default = Strictness.MEDIUM
        if self.repo_root:
            global_default = load_global_strictness(self.repo_root)

        # Get mission and step overrides from context
        mission_strictness = getattr(context, "mission_strictness", None)
        step_strictness = getattr(context, "step_strictness", None)

        effective_strictness = resolve_strictness(
            global_default=global_default,
            mission_override=mission_strictness,
            step_override=step_strictness,
            runtime_override=self.runtime_override,
        )

        # Store effective strictness in context for observability
        setattr(context, "effective_strictness", effective_strictness)

        # Evaluate blocking decision
        if should_block(effective_strictness, conflicts):
            # Get step and mission IDs from context
            step_id = getattr(context, "step_id", "unknown")
            mission_id = getattr(context, "mission_id", "unknown")

            # Emit event BEFORE raising exception (ensure observability)
            emit_generation_blocked_event(
                step_id=step_id,
                mission_id=mission_id,
                conflicts=conflicts,
                strictness_mode=effective_strictness,
            )

            # Block generation by raising exception
            raise BlockedByConflict(
                conflicts=conflicts,
                strictness=effective_strictness,
                message=self._format_block_message(conflicts),
            )

        # Generation allowed - return context unchanged
        return context

    def _format_block_message(
        self,
        conflicts: List["models.SemanticConflict"],
    ) -> str:
        """Format user-facing error message for blocked generation.

        Args:
            conflicts: List of conflicts that caused blocking

        Returns:
            Formatted error message with conflict count and severity breakdown
        """
        from . import models

        high_severity = [c for c in conflicts if c.severity == models.Severity.HIGH]
        conflict_count = len(conflicts)
        high_count = len(high_severity)

        if high_count > 0:
            return (
                f"Generation blocked: {high_count} high-severity "
                f"semantic conflict(s) detected (out of {conflict_count} total). "
                f"Resolve conflicts before proceeding."
            )
        else:
            return (
                f"Generation blocked: {conflict_count} unresolved "
                f"semantic conflict(s) detected. Resolve conflicts before proceeding."
            )
