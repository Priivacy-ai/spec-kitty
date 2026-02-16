"""Glossary extraction middleware (WP03) and clarification middleware (WP06).

This module implements middleware that extracts glossary term candidates from
primitive execution context (step inputs/outputs), detects semantic conflicts,
and provides interactive clarification for conflict resolution.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

from rich.console import Console

from .extraction import ExtractedTerm, extract_all_terms

if TYPE_CHECKING:
    from . import models, scope, store

_logger = logging.getLogger(__name__)


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

            # Emit event BEFORE raising exception (ensure observability).
            # Guard: if emission fails, log the error but ALWAYS proceed
            # to raise BlockedByConflict -- blocking must never be bypassed.
            try:
                emit_generation_blocked_event(
                    step_id=step_id,
                    mission_id=mission_id,
                    conflicts=conflicts,
                    strictness_mode=effective_strictness,
                )
            except Exception as emit_err:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(
                    "Failed to emit generation-blocked event (blocking proceeds): %s",
                    emit_err,
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


class ClarificationMiddleware:
    """Interactive conflict resolution middleware (WP06/T028).

    This middleware orchestrates conflict rendering, user prompting,
    glossary updates, and event emission for the full clarification workflow.

    Pipeline position: Layer 4 (after generation gate raises BlockedByConflict)

    Usage:
        middleware = ClarificationMiddleware(console=Console(), max_questions=3)
        context = middleware.process(context)
    """

    def __init__(
        self,
        console: Console | None = None,
        max_questions: int = 3,
    ) -> None:
        """Initialize clarification middleware.

        Args:
            console: Rich console instance (creates default if None)
            max_questions: Max conflicts to prompt per burst (default 3)
        """
        self.console = console or Console()
        self.max_questions = max_questions

    def process(
        self,
        context: PrimitiveExecutionContext,
    ) -> PrimitiveExecutionContext:
        """Process conflicts and prompt user for resolution.

        Pipeline position: Layer 4 (after generation gate raises BlockedByConflict)

        This middleware is called when generation is blocked. It:
        1. Renders conflicts with Rich formatting
        2. Prompts user for each conflict (select/custom/defer)
        3. Emits events for each resolution
        4. Updates glossary state in context
        5. Returns updated context for resume

        Args:
            context: Primitive execution context with conflicts

        Returns:
            Updated context with resolved conflicts (if interactive)
            or deferred conflicts (if non-interactive)
        """
        from .rendering import render_conflict_batch
        from .prompts import prompt_conflict_resolution_safe, PromptChoice

        conflicts = getattr(context, "conflicts", [])
        if not conflicts:
            return context

        # Render conflicts (capped at max_questions)
        to_prompt = render_conflict_batch(
            self.console,
            conflicts,
            max_questions=self.max_questions,
        )

        # Emit deferred events for conflicts beyond max_questions
        deferred_conflicts = [c for c in conflicts if c not in to_prompt]
        for conflict in deferred_conflicts:
            self._emit_deferred(context, conflict)

        # Process each prompted conflict interactively
        resolved_count = 0
        for conflict in to_prompt:
            # Sort candidates by scope precedence then descending confidence
            # so the prompt numbering matches the rendered table order
            from .rendering import sort_candidates
            ranked_candidates = sort_candidates(conflict.candidate_senses)

            choice, value = prompt_conflict_resolution_safe(conflict)

            if choice == PromptChoice.SELECT_CANDIDATE:
                candidate_idx = value
                selected_sense = ranked_candidates[candidate_idx]
                self._handle_candidate_selection(
                    context, conflict, selected_sense
                )
                resolved_count += 1

            elif choice == PromptChoice.CUSTOM_SENSE:
                custom_definition = value
                self._handle_custom_sense(
                    context, conflict, custom_definition
                )
                resolved_count += 1

            elif choice == PromptChoice.DEFER:
                self._emit_deferred(context, conflict)

        # Update context with resolution stats
        context.resolved_conflicts_count = resolved_count
        context.deferred_conflicts_count = len(conflicts) - resolved_count

        # If all resolved, clear conflicts (allows generation to proceed)
        if resolved_count == len(conflicts):
            context.conflicts = []

        return context

    def _handle_candidate_selection(
        self,
        context: PrimitiveExecutionContext,
        conflict: "models.SemanticConflict",
        selected_sense: "models.SenseRef",
    ) -> None:
        """Handle user selection of a candidate sense.

        Args:
            context: Execution context
            conflict: The conflict being resolved
            selected_sense: The SenseRef selected by the user
        """
        from .events import emit_clarification_resolved
        from .models import Provenance, SenseStatus, TermSense

        conflict_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        actor_id = getattr(context, "actor_id", "user:unknown")

        # Create a TermSense from the selected SenseRef for event emission
        resolved_sense = TermSense(
            surface=conflict.term,
            scope=selected_sense.scope,
            definition=selected_sense.definition,
            provenance=Provenance(
                actor_id=actor_id,
                timestamp=now,
                source="candidate_selection",
            ),
            confidence=selected_sense.confidence,
            status=SenseStatus.ACTIVE,
        )

        # Emit resolution event
        try:
            emit_clarification_resolved(
                conflict_id=conflict_id,
                term_surface=conflict.term.surface_text,
                selected_sense=resolved_sense,
                actor_id=actor_id,
                timestamp=now,
                resolution_mode="interactive",
            )
        except Exception as err:
            _logger.error("Failed to emit clarification resolved event: %s", err)

        # Update glossary in context
        self._update_glossary(context, resolved_sense)

        self.console.print(
            f"[green]Resolved:[/green] {conflict.term.surface_text} = "
            f"{selected_sense.definition}"
        )

    def _handle_custom_sense(
        self,
        context: PrimitiveExecutionContext,
        conflict: "models.SemanticConflict",
        custom_definition: str,
    ) -> None:
        """Handle user-provided custom sense definition.

        Args:
            context: Execution context
            conflict: The conflict being resolved
            custom_definition: User-provided definition text
        """
        from .events import emit_sense_updated
        from .models import Provenance, SenseStatus, TermSense
        from .scope import GlossaryScope

        now = datetime.now(timezone.utc)
        actor_id = getattr(context, "actor_id", "user:unknown")

        # Create new sense with user definition
        new_sense = TermSense(
            surface=conflict.term,
            scope=GlossaryScope.TEAM_DOMAIN.value,
            definition=custom_definition,
            provenance=Provenance(
                actor_id=actor_id,
                timestamp=now,
                source="user_clarification",
            ),
            confidence=1.0,  # User-provided = high confidence
            status=SenseStatus.ACTIVE,
        )

        # Emit sense updated event
        try:
            emit_sense_updated(
                term_surface=conflict.term.surface_text,
                scope=GlossaryScope.TEAM_DOMAIN.value,
                new_sense=new_sense,
                actor_id=actor_id,
                timestamp=now,
                update_type="create",
            )
        except Exception as err:
            _logger.error("Failed to emit sense updated event: %s", err)

        # Update glossary in context
        self._update_glossary(context, new_sense)

        self.console.print(
            f"[green]Added custom sense:[/green] "
            f"{conflict.term.surface_text} = {custom_definition}"
        )

    def _emit_deferred(
        self,
        context: PrimitiveExecutionContext,
        conflict: "models.SemanticConflict",
    ) -> None:
        """Emit clarification requested event for deferred conflict.

        Args:
            context: Execution context
            conflict: The conflict being deferred
        """
        from .events import emit_clarification_requested
        from .rendering import sort_candidates

        conflict_id = str(uuid.uuid4())

        # Build ranked options list (sorted by scope precedence, descending confidence)
        ranked_candidates = sort_candidates(conflict.candidate_senses)
        options = [sense.definition for sense in ranked_candidates]

        try:
            emit_clarification_requested(
                conflict_id=conflict_id,
                question=(
                    f"What does '{conflict.term.surface_text}' "
                    f"mean in this context?"
                ),
                term=conflict.term.surface_text,
                options=options,
                urgency=conflict.severity.value,
                step_id=getattr(context, "step_id", "unknown"),
                mission_id=getattr(context, "mission_id", "unknown"),
                run_id=getattr(context, "run_id", "unknown"),
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as err:
            _logger.error(
                "Failed to emit clarification requested event: %s", err
            )

    def _update_glossary(
        self,
        context: PrimitiveExecutionContext,
        sense: "models.TermSense",
    ) -> None:
        """Update glossary state in context with new/updated sense.

        Args:
            context: Execution context
            sense: The resolved TermSense to add
        """
        if not hasattr(context, "resolved_senses"):
            context.resolved_senses = []

        context.resolved_senses.append(sense)
