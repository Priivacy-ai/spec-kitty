"""Tests for PrimitiveExecutionContext (T040)."""

import pytest

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


class TestPrimitiveExecutionContextDefaults:
    """Test that glossary fields have correct defaults."""

    def test_extracted_terms_defaults_to_empty_list(self):
        ctx = _make_context()
        assert ctx.extracted_terms == []

    def test_conflicts_defaults_to_empty_list(self):
        ctx = _make_context()
        assert ctx.conflicts == []

    def test_effective_strictness_defaults_to_none(self):
        ctx = _make_context()
        assert ctx.effective_strictness is None

    def test_checkpoint_token_defaults_to_none(self):
        ctx = _make_context()
        assert ctx.checkpoint_token is None

    def test_scope_refs_defaults_to_empty_list(self):
        ctx = _make_context()
        assert ctx.scope_refs == []

    def test_step_input_populated_from_inputs(self):
        ctx = _make_context(inputs={"description": "hello"})
        assert ctx.step_input == {"description": "hello"}

    def test_step_output_defaults_to_empty_dict(self):
        ctx = _make_context()
        assert ctx.step_output == {}


class TestMissionStrictness:
    """Test mission_strictness property."""

    def test_returns_none_when_config_empty(self):
        ctx = _make_context(config={})
        assert ctx.mission_strictness is None

    def test_returns_none_when_no_glossary_section(self):
        ctx = _make_context(config={"other": "value"})
        assert ctx.mission_strictness is None

    def test_returns_none_when_no_strictness_in_glossary(self):
        ctx = _make_context(config={"glossary": {"enabled": True}})
        assert ctx.mission_strictness is None

    def test_returns_strictness_off(self):
        ctx = _make_context(config={"glossary": {"strictness": "off"}})
        assert ctx.mission_strictness == Strictness.OFF

    def test_returns_strictness_medium(self):
        ctx = _make_context(config={"glossary": {"strictness": "medium"}})
        assert ctx.mission_strictness == Strictness.MEDIUM

    def test_returns_strictness_max(self):
        ctx = _make_context(config={"glossary": {"strictness": "max"}})
        assert ctx.mission_strictness == Strictness.MAX

    def test_returns_none_on_invalid_value(self):
        ctx = _make_context(config={"glossary": {"strictness": "invalid"}})
        assert ctx.mission_strictness is None


class TestStepStrictness:
    """Test step_strictness property."""

    def test_returns_none_when_metadata_empty(self):
        ctx = _make_context(metadata={})
        assert ctx.step_strictness is None

    def test_returns_none_when_key_missing(self):
        ctx = _make_context(metadata={"other": "value"})
        assert ctx.step_strictness is None

    def test_returns_strictness_off(self):
        ctx = _make_context(metadata={"glossary_check_strictness": "off"})
        assert ctx.step_strictness == Strictness.OFF

    def test_returns_strictness_medium(self):
        ctx = _make_context(metadata={"glossary_check_strictness": "medium"})
        assert ctx.step_strictness == Strictness.MEDIUM

    def test_returns_strictness_max(self):
        ctx = _make_context(metadata={"glossary_check_strictness": "max"})
        assert ctx.step_strictness == Strictness.MAX

    def test_returns_none_on_invalid_value(self):
        ctx = _make_context(metadata={"glossary_check_strictness": "bogus"})
        assert ctx.step_strictness is None

    def test_returns_none_when_value_is_null(self):
        ctx = _make_context(metadata={"glossary_check_strictness": None})
        assert ctx.step_strictness is None


class TestIsGlossaryEnabled:
    """Test is_glossary_enabled() method."""

    def test_default_is_true(self):
        ctx = _make_context()
        assert ctx.is_glossary_enabled() is True

    def test_explicit_enabled(self):
        ctx = _make_context(metadata={"glossary_check": "enabled"})
        assert ctx.is_glossary_enabled() is True

    def test_explicit_disabled(self):
        ctx = _make_context(metadata={"glossary_check": "disabled"})
        assert ctx.is_glossary_enabled() is False

    def test_null_metadata_falls_through_to_default(self):
        ctx = _make_context(metadata={"glossary_check": None})
        assert ctx.is_glossary_enabled() is True

    def test_null_metadata_falls_through_to_mission_config_false(self):
        ctx = _make_context(
            metadata={"glossary_check": None},
            config={"glossary": {"enabled": False}},
        )
        assert ctx.is_glossary_enabled() is False

    def test_mission_config_enabled_false(self):
        ctx = _make_context(config={"glossary": {"enabled": False}})
        assert ctx.is_glossary_enabled() is False

    def test_mission_config_enabled_true(self):
        ctx = _make_context(config={"glossary": {"enabled": True}})
        assert ctx.is_glossary_enabled() is True

    def test_step_metadata_overrides_mission_config(self):
        """Step metadata has higher precedence than mission config."""
        ctx = _make_context(
            metadata={"glossary_check": "enabled"},
            config={"glossary": {"enabled": False}},
        )
        assert ctx.is_glossary_enabled() is True

    def test_step_disabled_overrides_mission_enabled(self):
        ctx = _make_context(
            metadata={"glossary_check": "disabled"},
            config={"glossary": {"enabled": True}},
        )
        assert ctx.is_glossary_enabled() is False

    def test_unknown_metadata_value_treated_as_enabled(self):
        ctx = _make_context(metadata={"glossary_check": "something_else"})
        assert ctx.is_glossary_enabled() is True

    def test_empty_config_and_metadata(self):
        ctx = _make_context(config={}, metadata={})
        assert ctx.is_glossary_enabled() is True

    def test_both_mission_and_step_strictness_coexist(self):
        """Both properties should return their respective values."""
        ctx = _make_context(
            metadata={"glossary_check_strictness": "off"},
            config={"glossary": {"strictness": "max"}},
        )
        assert ctx.mission_strictness == Strictness.MAX
        assert ctx.step_strictness == Strictness.OFF
