"""Tests for glossary pipeline attachment (T042)."""


from specify_cli.glossary.attachment import (
    attach_glossary_pipeline,
    glossary_enabled,
    read_glossary_check_metadata,
    run_with_glossary,
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


class TestAttachGlossaryPipeline:
    """Test attach_glossary_pipeline factory function."""

    def test_returns_callable(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        processor = attach_glossary_pipeline(repo_root=tmp_path)
        assert callable(processor)

    def test_callable_processes_context(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        processor = attach_glossary_pipeline(repo_root=tmp_path)

        ctx = _make_context()
        result = processor(ctx)

        # Should return a context (same or modified)
        assert result is not None
        assert hasattr(result, "step_id")

    def test_skips_when_glossary_disabled(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        processor = attach_glossary_pipeline(repo_root=tmp_path)

        ctx = _make_context(metadata={"glossary_check": "disabled"})
        result = processor(ctx)

        # Context returned unchanged (no extraction)
        assert result.extracted_terms == []
        assert result.conflicts == []
        assert result.effective_strictness is None

    def test_runtime_strictness_override(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        processor = attach_glossary_pipeline(
            repo_root=tmp_path,
            runtime_strictness=Strictness.OFF,
        )

        ctx = _make_context()
        result = processor(ctx)

        # With OFF strictness and no conflicts, pipeline completes
        assert result.effective_strictness == Strictness.OFF

    def test_non_interactive_mode(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        processor = attach_glossary_pipeline(
            repo_root=tmp_path,
            interaction_mode="non-interactive",
        )

        ctx = _make_context()
        result = processor(ctx)
        assert result is not None


class TestReadGlossaryCheckMetadata:
    """Test read_glossary_check_metadata function."""

    def test_default_when_key_missing(self):
        assert read_glossary_check_metadata({}) is True

    def test_explicit_enabled_string(self):
        assert read_glossary_check_metadata({"glossary_check": "enabled"}) is True

    def test_explicit_disabled_string(self):
        assert read_glossary_check_metadata({"glossary_check": "disabled"}) is False

    def test_explicit_enabled_bool_true(self):
        assert read_glossary_check_metadata({"glossary_check": True}) is True

    def test_explicit_disabled_bool_false(self):
        assert read_glossary_check_metadata({"glossary_check": False}) is False

    def test_none_value_defaults_to_true(self):
        assert read_glossary_check_metadata({"glossary_check": None}) is True

    def test_case_insensitive_disabled(self):
        assert read_glossary_check_metadata({"glossary_check": "Disabled"}) is False

    def test_case_insensitive_enabled(self):
        assert read_glossary_check_metadata({"glossary_check": "Enabled"}) is True

    def test_unknown_string_value_defaults_to_true(self):
        assert read_glossary_check_metadata({"glossary_check": "something"}) is True

    def test_other_metadata_keys_ignored(self):
        metadata = {
            "some_other_key": "value",
            "another_key": 42,
        }
        assert read_glossary_check_metadata(metadata) is True


# ---------------------------------------------------------------------------
# Regression: Issue 1 -- run_with_glossary() wrapper
# ---------------------------------------------------------------------------


class TestRunWithGlossary:
    """Test run_with_glossary() direct wrapper for mission primitives."""

    def test_processes_context_successfully(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        ctx = _make_context()
        result = run_with_glossary(context=ctx, repo_root=tmp_path)
        assert result is not None
        assert hasattr(result, "step_id")
        assert result.effective_strictness == Strictness.MEDIUM

    def test_skips_when_disabled(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        ctx = _make_context(metadata={"glossary_check": False})
        result = run_with_glossary(context=ctx, repo_root=tmp_path)
        assert result.effective_strictness is None
        assert result.extracted_terms == []

    def test_passes_runtime_strictness(self, tmp_path):
        (tmp_path / ".kittify").mkdir()
        ctx = _make_context()
        result = run_with_glossary(
            context=ctx,
            repo_root=tmp_path,
            runtime_strictness=Strictness.OFF,
        )
        assert result.effective_strictness == Strictness.OFF


# ---------------------------------------------------------------------------
# Regression: Issue 1 -- glossary_enabled() decorator
# ---------------------------------------------------------------------------


class TestGlossaryEnabledDecorator:
    """Test glossary_enabled() decorator for mission primitives."""

    def test_decorator_processes_context_before_function(self, tmp_path):
        (tmp_path / ".kittify").mkdir()

        @glossary_enabled(repo_root=tmp_path)
        def my_primitive(context):
            # By the time we get here, effective_strictness should be set
            return context.effective_strictness

        ctx = _make_context()
        result = my_primitive(ctx)
        assert result == Strictness.MEDIUM

    def test_decorator_skips_when_disabled(self, tmp_path):
        (tmp_path / ".kittify").mkdir()

        @glossary_enabled(repo_root=tmp_path)
        def my_primitive(context):
            return context.effective_strictness

        ctx = _make_context(metadata={"glossary_check": False})
        result = my_primitive(ctx)
        assert result is None  # Pipeline was skipped, strictness not set

    def test_decorator_preserves_function_name(self, tmp_path):
        (tmp_path / ".kittify").mkdir()

        @glossary_enabled(repo_root=tmp_path)
        def my_named_primitive(context):
            return context

        assert my_named_primitive.__name__ == "my_named_primitive"

    def test_decorator_passes_extra_args(self, tmp_path):
        (tmp_path / ".kittify").mkdir()

        @glossary_enabled(repo_root=tmp_path)
        def my_primitive(context, extra_arg, kwarg_val=None):
            return (context.effective_strictness, extra_arg, kwarg_val)

        ctx = _make_context()
        result = my_primitive(ctx, "hello", kwarg_val=42)
        assert result == (Strictness.MEDIUM, "hello", 42)

    def test_decorator_with_runtime_strictness(self, tmp_path):
        (tmp_path / ".kittify").mkdir()

        @glossary_enabled(repo_root=tmp_path, runtime_strictness=Strictness.MAX)
        def my_primitive(context):
            return context.effective_strictness

        ctx = _make_context()
        result = my_primitive(ctx)
        assert result == Strictness.MAX


# ---------------------------------------------------------------------------
# Regression: Issue 1 -- GlossaryAwarePrimitiveRunner
# ---------------------------------------------------------------------------


class TestGlossaryAwarePrimitiveRunner:
    """Test GlossaryAwarePrimitiveRunner class (production call site)."""

    def test_runner_creates_successfully(self, tmp_path):
        from specify_cli.glossary.attachment import GlossaryAwarePrimitiveRunner
        (tmp_path / ".kittify").mkdir()
        runner = GlossaryAwarePrimitiveRunner(repo_root=tmp_path)
        assert runner is not None

    def test_runner_execute_calls_pipeline_then_primitive(self, tmp_path):
        from specify_cli.glossary.attachment import GlossaryAwarePrimitiveRunner
        (tmp_path / ".kittify").mkdir()

        runner = GlossaryAwarePrimitiveRunner(repo_root=tmp_path)
        call_log = []

        def my_primitive(context):
            call_log.append("primitive_ran")
            return {"strictness": context.effective_strictness}

        ctx = _make_context()
        result = runner.execute(my_primitive, ctx)

        assert call_log == ["primitive_ran"]
        assert result["strictness"] == Strictness.MEDIUM

    def test_runner_passes_extra_args_to_primitive(self, tmp_path):
        from specify_cli.glossary.attachment import GlossaryAwarePrimitiveRunner
        (tmp_path / ".kittify").mkdir()

        runner = GlossaryAwarePrimitiveRunner(
            repo_root=tmp_path,
            runtime_strictness=Strictness.OFF,
        )

        def my_primitive(context, extra, key=None):
            return (context.effective_strictness, extra, key)

        ctx = _make_context()
        result = runner.execute(my_primitive, ctx, "hello", key="world")

        assert result == (Strictness.OFF, "hello", "world")

    def test_runner_is_importable_from_glossary_package(self):
        """GlossaryAwarePrimitiveRunner is exported from glossary package."""
        from specify_cli.glossary import GlossaryAwarePrimitiveRunner
        assert GlossaryAwarePrimitiveRunner is not None
