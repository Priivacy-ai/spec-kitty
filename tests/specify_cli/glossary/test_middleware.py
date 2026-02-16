"""Tests for glossary extraction middleware (WP03)."""

import pytest
from specify_cli.glossary.middleware import (
    GlossaryCandidateExtractionMiddleware,
    MockContext,
)
from specify_cli.glossary.extraction import ExtractedTerm


class TestMiddlewareBasics:
    """Basic middleware functionality tests."""

    def test_middleware_initialization_default_fields(self):
        """Middleware initializes with default glossary fields."""
        middleware = GlossaryCandidateExtractionMiddleware()

        assert middleware.glossary_fields == ["description", "prompt", "output"]

    def test_middleware_initialization_custom_fields(self):
        """Middleware initializes with custom glossary fields."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["input", "result"]
        )

        assert middleware.glossary_fields == ["input", "result"]

    def test_scan_fields_extracts_text(self):
        """scan_fields extracts text from configured fields."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description", "prompt"]
        )

        data = {
            "description": "First field",
            "prompt": "Second field",
            "other": "Ignored field",
        }

        text = middleware.scan_fields(data)

        assert "First field" in text
        assert "Second field" in text
        assert "Ignored field" not in text

    def test_scan_fields_ignores_non_string(self):
        """scan_fields ignores non-string values."""
        middleware = GlossaryCandidateExtractionMiddleware()

        data = {
            "description": "Valid text",
            "prompt": 123,  # Integer
            "output": ["list", "items"],  # List
        }

        text = middleware.scan_fields(data)

        assert "Valid text" in text
        assert "123" not in text


class TestMiddlewareProcess:
    """Tests for middleware process() method (T014)."""

    def test_process_extracts_from_step_input(self):
        """Middleware extracts terms from step_input."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description"]
        )

        context = MockContext(
            step_input={"description": 'The "workspace" is a term.'},
            metadata={},
        )

        result = middleware.process(context)

        # Should extract "workspace" from quoted phrase
        assert len(result.extracted_terms) > 0
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces

    def test_process_extracts_from_step_output(self):
        """Middleware extracts terms from step_output."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["output"]
        )

        context = MockContext(
            step_output={"output": "The API is an acronym."},
            metadata={},
        )

        result = middleware.process(context)

        # Should extract "api" from acronym pattern
        assert len(result.extracted_terms) > 0
        surfaces = {t.surface for t in result.extracted_terms}
        assert "api" in surfaces

    def test_process_combines_input_and_output(self):
        """Middleware combines step_input and step_output."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description", "output"]
        )

        context = MockContext(
            step_input={"description": 'The "workspace" is here.'},
            step_output={"output": "The API result."},
            metadata={},
        )

        result = middleware.process(context)

        # Should extract from both
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces
        assert "api" in surfaces

    def test_process_with_metadata_hints(self):
        """Middleware uses metadata hints (highest confidence)."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={"description": "Some text"},
            metadata={"glossary_watch_terms": ["mission", "primitive"]},
        )

        result = middleware.process(context)

        # Should extract metadata hints
        metadata_terms = [t for t in result.extracted_terms if t.source == "metadata_hint"]
        assert len(metadata_terms) == 2
        surfaces = {t.surface for t in metadata_terms}
        assert surfaces == {"mission", "primitive"}

    def test_process_deduplicates_terms(self):
        """Middleware deduplicates terms from multiple sources."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description"]
        )

        context = MockContext(
            step_input={"description": 'The "workspace" is a work_space.'},
            metadata={"glossary_watch_terms": ["workspace"]},
        )

        result = middleware.process(context)

        # "workspace" appears in metadata, quoted phrase, and casing pattern
        # Should only appear once (metadata takes precedence)
        workspace_terms = [t for t in result.extracted_terms if t.surface == "workspace"]
        assert len(workspace_terms) == 1
        assert workspace_terms[0].source == "metadata_hint"

    def test_process_excludes_filtered_terms(self):
        """Middleware excludes terms in glossary_exclude_terms from metadata hints."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={"description": "Some generic text about workspace"},
            metadata={
                "glossary_watch_terms": ["test", "workspace"],
                "glossary_exclude_terms": ["test"],
            },
        )

        result = middleware.process(context)

        # "test" should be excluded from metadata hints
        # (it might still be extracted from text if it appears there, but it doesn't)
        metadata_surfaces = {
            t.surface for t in result.extracted_terms if t.source == "metadata_hint"
        }
        assert "test" not in metadata_surfaces
        assert "workspace" in metadata_surfaces

    def test_process_empty_context(self):
        """Middleware handles empty context gracefully."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext()

        result = middleware.process(context)

        # Should not crash, returns empty
        assert len(result.extracted_terms) == 0

    def test_process_respects_configured_fields(self):
        """Middleware only scans configured fields."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description"]  # Only scan description
        )

        context = MockContext(
            step_input={
                "description": 'The "workspace" is here.',
                "prompt": 'The "mission" is ignored.',
            },
            metadata={},
        )

        result = middleware.process(context)

        # Should only extract from description
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces
        assert "mission" not in surfaces


class TestMiddlewareIntegration:
    """Integration tests for full middleware pipeline."""

    def test_full_extraction_pipeline(self):
        """Full pipeline: metadata hints + heuristics + normalization + scoring."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={
                "description": """
                The "workspace" contains a mission primitive.
                Each WP has a work_package configuration.
                The workspace workspace workspace appears often.
                """
            },
            metadata={
                "glossary_watch_terms": ["primitive"],
                "glossary_aliases": {"WP": "work package"},
            },
        )

        result = middleware.process(context)

        # Should extract:
        # - primitive (metadata_hint, confidence 1.0)
        # - work package (metadata alias, confidence 1.0)
        # - workspace (quoted_phrase, confidence 0.8)
        # - wp (acronym, confidence 0.8)
        # - work_package (casing_pattern, confidence 0.8)
        # - workspace (repeated_noun, confidence 0.5) - deduped with quoted

        assert len(result.extracted_terms) > 0

        # Check metadata hints present
        metadata_terms = [t for t in result.extracted_terms if t.source == "metadata_hint"]
        surfaces = {t.surface for t in metadata_terms}
        assert "primitive" in surfaces
        assert "work package" in surfaces

        # Check confidence ordering (metadata hints first)
        confidences = [t.confidence for t in result.extracted_terms]
        assert confidences[0] == 1.0  # Highest confidence first

    def test_performance_within_budget(self):
        """Middleware completes within performance budget (<100ms)."""
        import time

        middleware = GlossaryCandidateExtractionMiddleware()

        # Typical step input (500 words)
        context = MockContext(
            step_input={
                "description": " ".join(
                    [
                        "The workspace contains a mission primitive.",
                        "Each WP has a work_package configuration.",
                        'The "semantic integrity" is validated.',
                    ]
                    * 50  # ~500 words
                ),
            },
            metadata={
                "glossary_watch_terms": ["workspace", "mission"],
            },
        )

        start = time.perf_counter()
        result = middleware.process(context)
        elapsed = time.perf_counter() - start

        # Should complete in <100ms
        assert elapsed < 0.1, f"Middleware took {elapsed:.3f}s (expected <0.1s)"

        # Should extract some terms
        assert len(result.extracted_terms) > 0

    def test_adds_to_existing_extracted_terms(self):
        """Middleware appends to existing extracted_terms list."""
        middleware = GlossaryCandidateExtractionMiddleware()

        # Pre-populate extracted_terms
        existing_term = ExtractedTerm(
            surface="existing",
            source="manual",
            confidence=1.0,
            original="existing",
        )

        context = MockContext(
            step_input={"description": 'The "workspace" is a term.'},
            metadata={},
        )
        context.extracted_terms.append(existing_term)

        result = middleware.process(context)

        # Should preserve existing term and add new ones
        assert len(result.extracted_terms) > 1
        surfaces = {t.surface for t in result.extracted_terms}
        assert "existing" in surfaces
        assert "workspace" in surfaces


class TestMiddlewareEdgeCases:
    """Edge case tests for middleware."""

    def test_missing_configured_fields(self):
        """Middleware handles missing configured fields gracefully."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description", "prompt"]
        )

        context = MockContext(
            step_input={"other": "Only other field present"},
            metadata={},
        )

        result = middleware.process(context)

        # Should not crash, returns empty
        assert len(result.extracted_terms) == 0

    def test_none_metadata(self):
        """Middleware handles None metadata gracefully."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={"description": 'The "workspace" is here.'},
            metadata=None,  # type: ignore
        )

        result = middleware.process(context)

        # Should extract from text (no metadata hints)
        assert len(result.extracted_terms) > 0
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces

    def test_malformed_metadata(self):
        """Middleware handles malformed metadata gracefully."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={"description": "Some text"},
            metadata={
                "glossary_watch_terms": "not_a_list",  # Should be list
            },
        )

        # Should not crash (extract_metadata_hints handles gracefully)
        # May log warning in production
        result = middleware.process(context)

        # Should still process text (just no metadata hints)
        assert len(result.extracted_terms) >= 0


class TestMetadataDrivenFieldSelection:
    """Regression tests for metadata.glossary_fields runtime override (cycle 3 fix)."""

    def test_metadata_glossary_fields_overrides_constructor(self):
        """metadata.glossary_fields overrides constructor default at runtime."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description", "prompt"]  # Constructor default
        )

        context = MockContext(
            step_input={
                "description": 'The "workspace" is in description.',
                "prompt": 'The "mission" is in prompt.',
                "custom_field": 'The "primitive" is in custom_field.',
            },
            metadata={
                "glossary_fields": ["custom_field"]  # Runtime override
            },
        )

        result = middleware.process(context)

        # Should only scan custom_field (metadata override)
        surfaces = {t.surface for t in result.extracted_terms}
        assert "primitive" in surfaces  # From custom_field
        assert "workspace" not in surfaces  # description ignored
        assert "mission" not in surfaces  # prompt ignored

    def test_metadata_glossary_fields_empty_list(self):
        """metadata.glossary_fields=[] scans no fields."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={
                "description": 'The "workspace" is here.',
            },
            metadata={
                "glossary_fields": []  # Empty list = scan nothing
            },
        )

        result = middleware.process(context)

        # Should extract no terms from text (but may have metadata hints)
        text_terms = [t for t in result.extracted_terms if t.source != "metadata_hint"]
        assert len(text_terms) == 0

    def test_metadata_glossary_fields_invalid_type_ignored(self):
        """Invalid metadata.glossary_fields (not list) falls back to constructor."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description"]
        )

        context = MockContext(
            step_input={
                "description": 'The "workspace" is here.',
                "other": 'The "mission" is ignored.',
            },
            metadata={
                "glossary_fields": "not_a_list"  # Invalid type
            },
        )

        result = middleware.process(context)

        # Should fall back to constructor fields (description only)
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces  # From description
        assert "mission" not in surfaces  # other field ignored

    def test_metadata_glossary_fields_invalid_elements_ignored(self):
        """metadata.glossary_fields with non-string elements falls back to constructor."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description"]
        )

        context = MockContext(
            step_input={
                "description": 'The "workspace" is here.',
            },
            metadata={
                "glossary_fields": ["description", 123, None]  # Invalid elements
            },
        )

        result = middleware.process(context)

        # Should fall back to constructor fields (invalid list ignored)
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces

    def test_metadata_glossary_fields_multiple_fields(self):
        """metadata.glossary_fields with multiple fields scans all of them."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description"]  # Constructor default
        )

        context = MockContext(
            step_input={
                "field1": 'The "workspace" is in field1.',
                "field2": 'The "mission" is in field2.',
                "field3": 'The "primitive" is in field3.',
                "ignored": 'The "term" is ignored.',
            },
            metadata={
                "glossary_fields": ["field1", "field2", "field3"]  # Runtime override
            },
        )

        result = middleware.process(context)

        # Should scan all three metadata-specified fields
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces  # field1
        assert "mission" in surfaces  # field2
        assert "primitive" in surfaces  # field3
        assert "term" not in surfaces  # ignored field not scanned

    def test_metadata_glossary_fields_with_step_output(self):
        """metadata.glossary_fields applies to both step_input and step_output."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={
                "custom_input": 'The "workspace" is in input.',
            },
            step_output={
                "custom_output": 'The "mission" is in output.',
            },
            metadata={
                "glossary_fields": ["custom_input", "custom_output"]
            },
        )

        result = middleware.process(context)

        # Should scan both input and output fields
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces  # From step_input
        assert "mission" in surfaces  # From step_output

    def test_metadata_glossary_fields_no_metadata(self):
        """No metadata.glossary_fields uses constructor default."""
        middleware = GlossaryCandidateExtractionMiddleware(
            glossary_fields=["description"]
        )

        context = MockContext(
            step_input={
                "description": 'The "workspace" is here.',
                "other": 'The "mission" is ignored.',
            },
            metadata={},  # No glossary_fields
        )

        result = middleware.process(context)

        # Should use constructor default (description only)
        surfaces = {t.surface for t in result.extracted_terms}
        assert "workspace" in surfaces
        assert "mission" not in surfaces

    def test_metadata_glossary_fields_combined_with_watch_terms(self):
        """metadata.glossary_fields works alongside glossary_watch_terms."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={
                "custom_field": 'The "workspace" is in custom_field.',
                "ignored_field": 'The "mission" is ignored.',
            },
            metadata={
                "glossary_fields": ["custom_field"],  # Only scan custom_field
                "glossary_watch_terms": ["primitive"],  # Metadata hints
            },
        )

        result = middleware.process(context)

        # Should have metadata hint + text extraction from custom_field only
        surfaces = {t.surface for t in result.extracted_terms}
        assert "primitive" in surfaces  # From glossary_watch_terms
        assert "workspace" in surfaces  # From custom_field text
        assert "mission" not in surfaces  # ignored_field not scanned


class TestEventEmission:
    """Tests for T014: Event emission (stub implementation for WP08).

    These tests verify that the event emission interface is properly defined
    and called for all extracted terms, even though the actual event infrastructure
    is deferred to WP08.
    """

    def test_emit_called_for_each_term(self):
        """_emit_term_candidate_observed is called once per extracted term."""
        middleware = GlossaryCandidateExtractionMiddleware()

        # Track emission calls
        emission_calls = []

        # Monkey-patch the emission method to track calls
        original_emit = middleware._emit_term_candidate_observed

        def track_emit(term, context):
            emission_calls.append((term.surface, term.confidence, term.source))
            return original_emit(term, context)

        middleware._emit_term_candidate_observed = track_emit

        context = MockContext(
            step_input={
                "description": 'The "workspace" and "mission" are quoted terms.',
            },
            metadata={
                "glossary_watch_terms": ["primitive"],  # Metadata hint
            },
        )

        middleware.process(context)

        # Should have emitted events for all extracted terms
        assert len(emission_calls) > 0

        # Verify metadata hint was emitted (confidence 1.0)
        metadata_emissions = [
            (surf, conf, src)
            for surf, conf, src in emission_calls
            if src == "metadata_hint"
        ]
        assert len(metadata_emissions) == 1
        assert metadata_emissions[0][0] == "primitive"
        assert metadata_emissions[0][1] == 1.0

        # Verify quoted phrases were emitted (confidence 0.8)
        quoted_emissions = [
            (surf, conf, src)
            for surf, conf, src in emission_calls
            if src == "quoted_phrase"
        ]
        assert len(quoted_emissions) >= 2
        surfaces = {surf for surf, _, _ in quoted_emissions}
        assert "workspace" in surfaces
        assert "mission" in surfaces

    def test_emit_stub_is_noop(self):
        """_emit_term_candidate_observed stub is safe to call (no-op until WP08)."""
        middleware = GlossaryCandidateExtractionMiddleware()

        context = MockContext(
            step_input={"description": 'The "workspace" is here.'},
        )

        # Should not raise exception (stub is safe)
        result = middleware.process(context)

        # Terms should still be added to context
        assert len(result.extracted_terms) > 0

    def test_emit_interface_contract(self):
        """Event emission method signature matches WP08 contract."""
        from inspect import signature

        middleware = GlossaryCandidateExtractionMiddleware()

        # Check method exists
        assert hasattr(middleware, "_emit_term_candidate_observed")

        # Check signature: (self, term: ExtractedTerm, context: PrimitiveExecutionContext)
        sig = signature(middleware._emit_term_candidate_observed)
        params = list(sig.parameters.keys())

        assert "term" in params, "Expected 'term' parameter"
        assert "context" in params, "Expected 'context' parameter"
        assert len(params) == 2, f"Expected 2 parameters, got {len(params)}"
