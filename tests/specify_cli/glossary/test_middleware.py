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
