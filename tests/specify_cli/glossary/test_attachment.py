"""Tests for glossary pipeline attachment (T042)."""

import pytest

from specify_cli.glossary.attachment import (
    attach_glossary_pipeline,
    read_glossary_check_metadata,
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
