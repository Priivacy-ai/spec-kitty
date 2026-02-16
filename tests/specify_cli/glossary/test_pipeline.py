"""Tests for GlossaryMiddlewarePipeline (T041)."""

import pytest
from unittest.mock import MagicMock

from specify_cli.glossary.exceptions import (
    AbortResume,
    BlockedByConflict,
    DeferredToAsync,
)
from specify_cli.glossary.models import (
    ConflictType,
    SemanticConflict,
    Severity,
    TermSurface,
)
from specify_cli.glossary.pipeline import (
    GlossaryMiddlewarePipeline,
    create_standard_pipeline,
)
from specify_cli.glossary.strictness import Strictness
from specify_cli.missions.primitives import PrimitiveExecutionContext


def _make_context(**overrides):
    """Helper to create a PrimitiveExecutionContext with defaults."""
    defaults = dict(
        step_id="test-001",
        mission_id="test-mission",
        run_id="run-001",
        inputs={"description": "test input"},
        metadata={},
        config={},
    )
    defaults.update(overrides)
    return PrimitiveExecutionContext(**defaults)


class _MockMiddleware:
    """Mock middleware that records calls and optionally transforms context."""

    def __init__(self, name: str, side_effect=None):
        self.name = name
        self.call_count = 0
        self.last_context = None
        self._side_effect = side_effect

    def process(self, context):
        self.call_count += 1
        self.last_context = context
        if self._side_effect:
            return self._side_effect(context)
        return context


class _FailingMiddleware:
    """Middleware that raises an unexpected exception."""

    def process(self, context):
        raise ValueError("unexpected error in middleware")


class _NoneReturningMiddleware:
    """Middleware that returns None."""

    def process(self, context):
        return None


class TestPipelineExecution:
    """Test basic pipeline execution."""

    def test_empty_middleware_returns_context_unchanged(self):
        pipeline = GlossaryMiddlewarePipeline(middleware=[])
        ctx = _make_context()
        result = pipeline.process(ctx)
        assert result is ctx

    def test_single_middleware_called(self):
        mw = _MockMiddleware("mw1")
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw])
        ctx = _make_context()

        result = pipeline.process(ctx)

        assert mw.call_count == 1
        assert result is ctx

    def test_middleware_executed_in_order(self):
        call_order = []

        def make_side_effect(name):
            def side_effect(ctx):
                call_order.append(name)
                return ctx
            return side_effect

        mw1 = _MockMiddleware("mw1", side_effect=make_side_effect("mw1"))
        mw2 = _MockMiddleware("mw2", side_effect=make_side_effect("mw2"))
        mw3 = _MockMiddleware("mw3", side_effect=make_side_effect("mw3"))

        pipeline = GlossaryMiddlewarePipeline(middleware=[mw1, mw2, mw3])
        ctx = _make_context()
        pipeline.process(ctx)

        assert call_order == ["mw1", "mw2", "mw3"]

    def test_context_flows_between_layers(self):
        """Each middleware receives the output of the previous one."""

        def add_term(ctx):
            ctx.extracted_terms.append("term_from_mw1")
            return ctx

        def check_term(ctx):
            assert "term_from_mw1" in ctx.extracted_terms
            return ctx

        mw1 = _MockMiddleware("extractor", side_effect=add_term)
        mw2 = _MockMiddleware("checker", side_effect=check_term)

        pipeline = GlossaryMiddlewarePipeline(middleware=[mw1, mw2])
        ctx = _make_context()
        result = pipeline.process(ctx)

        assert "term_from_mw1" in result.extracted_terms


class TestPipelineSkipOnDisabled:
    """Test pipeline skipping when glossary is disabled."""

    def test_skips_when_glossary_disabled(self):
        mw = _MockMiddleware("mw1")
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw], skip_on_disabled=True)
        ctx = _make_context(metadata={"glossary_check": "disabled"})

        result = pipeline.process(ctx)

        assert mw.call_count == 0
        assert result is ctx

    def test_executes_when_glossary_enabled(self):
        mw = _MockMiddleware("mw1")
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw], skip_on_disabled=True)
        ctx = _make_context(metadata={"glossary_check": "enabled"})

        pipeline.process(ctx)

        assert mw.call_count == 1

    def test_executes_when_skip_disabled_false(self):
        mw = _MockMiddleware("mw1")
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw], skip_on_disabled=False)
        ctx = _make_context(metadata={"glossary_check": "disabled"})

        pipeline.process(ctx)

        assert mw.call_count == 1

    def test_executes_when_default_enabled(self):
        mw = _MockMiddleware("mw1")
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw], skip_on_disabled=True)
        ctx = _make_context()  # Default: enabled

        pipeline.process(ctx)

        assert mw.call_count == 1


class TestPipelineExceptionPropagation:
    """Test that expected exceptions propagate correctly."""

    def test_blocked_by_conflict_propagates(self):
        conflict = SemanticConflict(
            term=TermSurface("workspace"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.HIGH,
            confidence=0.9,
            candidate_senses=[
                MagicMock(surface="workspace", scope="team_domain",
                          definition="def1", confidence=0.9),
                MagicMock(surface="workspace", scope="team_domain",
                          definition="def2", confidence=0.7),
            ],
        )

        def raise_blocked(ctx):
            raise BlockedByConflict(conflicts=[conflict])

        mw = _MockMiddleware("gate", side_effect=raise_blocked)
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw])
        ctx = _make_context()

        with pytest.raises(BlockedByConflict) as exc_info:
            pipeline.process(ctx)

        assert len(exc_info.value.conflicts) == 1

    def test_deferred_to_async_propagates(self):
        def raise_deferred(ctx):
            raise DeferredToAsync(conflict_id="abc-123")

        mw = _MockMiddleware("clarify", side_effect=raise_deferred)
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw])
        ctx = _make_context()

        with pytest.raises(DeferredToAsync) as exc_info:
            pipeline.process(ctx)

        assert exc_info.value.conflict_id == "abc-123"

    def test_abort_resume_propagates(self):
        def raise_abort(ctx):
            raise AbortResume(reason="user declined")

        mw = _MockMiddleware("resume", side_effect=raise_abort)
        pipeline = GlossaryMiddlewarePipeline(middleware=[mw])
        ctx = _make_context()

        with pytest.raises(AbortResume) as exc_info:
            pipeline.process(ctx)

        assert "user declined" in str(exc_info.value)

    def test_subsequent_middleware_not_called_after_exception(self):
        def raise_blocked(ctx):
            raise BlockedByConflict(conflicts=[])

        mw1 = _MockMiddleware("gate", side_effect=raise_blocked)
        mw2 = _MockMiddleware("clarify")

        pipeline = GlossaryMiddlewarePipeline(middleware=[mw1, mw2])
        ctx = _make_context()

        with pytest.raises(BlockedByConflict):
            pipeline.process(ctx)

        assert mw2.call_count == 0


class TestPipelineErrorHandling:
    """Test error handling for unexpected conditions."""

    def test_none_context_raises_value_error(self):
        pipeline = GlossaryMiddlewarePipeline(middleware=[])

        with pytest.raises(ValueError, match="must not be None"):
            pipeline.process(None)

    def test_unexpected_exception_wrapped_in_runtime_error(self):
        pipeline = GlossaryMiddlewarePipeline(middleware=[_FailingMiddleware()])
        ctx = _make_context()

        with pytest.raises(RuntimeError, match="_FailingMiddleware failed"):
            pipeline.process(ctx)

    def test_wrapped_exception_preserves_traceback(self):
        pipeline = GlossaryMiddlewarePipeline(middleware=[_FailingMiddleware()])
        ctx = _make_context()

        with pytest.raises(RuntimeError) as exc_info:
            pipeline.process(ctx)

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_middleware_returning_none_raises_runtime_error(self):
        pipeline = GlossaryMiddlewarePipeline(middleware=[_NoneReturningMiddleware()])
        ctx = _make_context()

        with pytest.raises(RuntimeError, match="returned None"):
            pipeline.process(ctx)


class TestCreateStandardPipeline:
    """Test the create_standard_pipeline factory."""

    def test_creates_pipeline_with_5_middleware(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        pipeline = create_standard_pipeline(tmp_path)

        assert isinstance(pipeline, GlossaryMiddlewarePipeline)
        assert len(pipeline.middleware) == 5

    def test_middleware_order_is_correct(self, tmp_path):
        """Verify correct order: extraction, check, gate, clarification, resume."""
        from specify_cli.glossary.clarification import ClarificationMiddleware
        from specify_cli.glossary.middleware import (
            GlossaryCandidateExtractionMiddleware,
            GenerationGateMiddleware,
            ResumeMiddleware,
            SemanticCheckMiddleware,
        )

        (tmp_path / ".kittify").mkdir()
        pipeline = create_standard_pipeline(tmp_path)

        assert isinstance(pipeline.middleware[0], GlossaryCandidateExtractionMiddleware)
        assert isinstance(pipeline.middleware[1], SemanticCheckMiddleware)
        assert isinstance(pipeline.middleware[2], GenerationGateMiddleware)
        assert isinstance(pipeline.middleware[3], ClarificationMiddleware)
        assert isinstance(pipeline.middleware[4], ResumeMiddleware)

    def test_runtime_strictness_passed_to_gate(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        pipeline = create_standard_pipeline(
            tmp_path, runtime_strictness=Strictness.OFF
        )

        gate = pipeline.middleware[2]
        assert gate.runtime_override == Strictness.OFF

    def test_creates_events_directory(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        create_standard_pipeline(tmp_path)

        events_dir = tmp_path / ".kittify" / "events" / "glossary"
        assert events_dir.exists()

    def test_loads_seed_files_into_store(self, tmp_path):
        """When seed files exist, they are loaded into the glossary store."""
        (tmp_path / ".kittify").mkdir()
        glossaries = tmp_path / ".kittify" / "glossaries"
        glossaries.mkdir()
        (glossaries / "team_domain.yaml").write_text(
            "terms:\n"
            "  - surface: workspace\n"
            "    definition: A git worktree\n"
            "    confidence: 1.0\n"
            "    status: active\n"
        )

        pipeline = create_standard_pipeline(tmp_path)

        # The SemanticCheckMiddleware should have a store with the loaded term
        check_mw = pipeline.middleware[1]
        results = check_mw.glossary_store.lookup(
            "workspace", ("team_domain",)
        )
        assert len(results) >= 1
        assert results[0].definition == "A git worktree"
