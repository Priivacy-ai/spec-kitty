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

        # 5. Emit events (WP08 - event emission adapters)
        # For now, just log (events module not implemented yet)
        # When WP08 is done, this will call:
        # from .events import emit_term_candidate_observed
        # for term in extracted:
        #     emit_term_candidate_observed(term, context)

        return context

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
