"""Behavior tests for AgentAssignment dataclass and WPMetadata.resolved_agent().

Covers all coercion scenarios:
- String agent
- Dict agent (full and partial)
- None/missing agent
- Empty string agent
- AgentAssignment passthrough
- Fallback to model, agent_profile, role fields
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import AgentAssignment
from specify_cli.status.wp_metadata import WPMetadata

pytestmark = pytest.mark.fast


# ── AgentAssignment dataclass tests ───────────────────────────────────────────


def test_agent_assignment_is_frozen() -> None:
    """AgentAssignment must be immutable (frozen=True)."""
    a = AgentAssignment(tool="claude", model="claude-opus-4-6")
    with pytest.raises((AttributeError, TypeError)):
        a.tool = "other"  # type: ignore[misc]


def test_agent_assignment_fields() -> None:
    """AgentAssignment has correct field types and defaults."""
    a = AgentAssignment(tool="claude", model="claude-opus-4-6")
    assert a.tool == "claude"
    assert a.model == "claude-opus-4-6"
    assert a.profile_id is None
    assert a.role is None


def test_agent_assignment_with_all_fields() -> None:
    """AgentAssignment stores all four fields correctly."""
    a = AgentAssignment(
        tool="copilot",
        model="gpt-4-turbo",
        profile_id="p1",
        role="reviewer",
    )
    assert a.tool == "copilot"
    assert a.model == "gpt-4-turbo"
    assert a.profile_id == "p1"
    assert a.role == "reviewer"


def test_agent_assignment_equality() -> None:
    """AgentAssignment supports value equality (frozen dataclass)."""
    a1 = AgentAssignment(tool="claude", model="claude-opus-4-6")
    a2 = AgentAssignment(tool="claude", model="claude-opus-4-6")
    assert a1 == a2


# ── Helper factory ────────────────────────────────────────────────────────────


def make_wp(
    agent=None,
    model=None,
    agent_profile=None,
    role=None,
    work_package_id="WP01",
    title="Test WP",
) -> WPMetadata:
    """Construct a WPMetadata with the given agent-resolution fields."""
    return WPMetadata(
        work_package_id=work_package_id,
        title=title,
        agent=agent,
        model=model,
        agent_profile=agent_profile,
        role=role,
    )


# ── resolved_agent() behavior tests ──────────────────────────────────────────


def test_resolved_agent_returns_agent_assignment() -> None:
    """resolved_agent() always returns an AgentAssignment instance."""
    wp = make_wp(agent="claude")
    result = wp.resolved_agent()
    assert isinstance(result, AgentAssignment)


class TestStringAgent:
    """String agent coercion scenarios."""

    def test_string_agent_with_model(self) -> None:
        """String agent field uses itself as tool; model field as model."""
        wp = make_wp(agent="claude", model="claude-opus-4-6")
        result = wp.resolved_agent()
        assert result.tool == "claude"
        assert result.model == "claude-opus-4-6"
        assert result.profile_id == "generic-agent"
        assert result.role is None

    def test_string_agent_no_model_falls_back_to_unknown_model(self) -> None:
        """String agent with no model field falls back to 'unknown-model'."""
        wp = make_wp(agent="claude", model=None)
        result = wp.resolved_agent()
        assert result.tool == "claude"
        assert result.model == "unknown-model"

    def test_string_agent_with_profile_and_role(self) -> None:
        """String agent inherits agent_profile and role from WP fields."""
        wp = make_wp(agent="gemini", model="gemini-pro", agent_profile="p2", role="implementer")
        result = wp.resolved_agent()
        assert result.tool == "gemini"
        assert result.model == "gemini-pro"
        assert result.profile_id == "p2"
        assert result.role == "implementer"


class TestDictAgent:
    """Dict agent coercion scenarios."""

    def test_dict_agent_with_all_fields(self) -> None:
        """Dict agent with all fields uses them directly."""
        wp = make_wp(
            agent={"tool": "copilot", "model": "gpt-4", "profile_id": "p1", "role": "reviewer"},
            model="ignored",
            agent_profile="ignored",
            role="ignored",
        )
        result = wp.resolved_agent()
        assert result.tool == "copilot"
        assert result.model == "gpt-4"
        assert result.profile_id == "p1"
        assert result.role == "reviewer"

    def test_dict_agent_partial_fields_fall_back_to_wp_fields(self) -> None:
        """Dict agent with partial fields falls back to WP-level model/profile/role."""
        wp = make_wp(
            agent={"tool": "gemini"},
            model="default-model",
            agent_profile="p2",
            role="implementer",
        )
        result = wp.resolved_agent()
        assert result.tool == "gemini"
        assert result.model == "default-model"
        assert result.profile_id == "p2"
        assert result.role == "implementer"

    def test_dict_agent_empty_dict_falls_back_to_unknown(self) -> None:
        """Empty dict agent falls back to 'unknown'/'unknown-model'."""
        wp = make_wp(agent={}, model=None)
        result = wp.resolved_agent()
        assert result.tool == "unknown"
        assert result.model == "unknown-model"

    def test_dict_agent_empty_dict_uses_wp_model(self) -> None:
        """Empty dict agent uses WP-level model when available."""
        wp = make_wp(agent={}, model="my-model")
        result = wp.resolved_agent()
        assert result.tool == "unknown"
        assert result.model == "my-model"


class TestNoneAgent:
    """None/missing agent coercion scenarios."""

    def test_none_agent_with_model_and_profile(self) -> None:
        """None agent falls back to 'unknown' tool and uses WP-level fields."""
        wp = make_wp(agent=None, model="default-model", agent_profile="p3", role="reviewer")
        result = wp.resolved_agent()
        assert result.tool == "unknown"
        assert result.model == "default-model"
        assert result.profile_id == "p3"
        assert result.role == "reviewer"

    def test_none_agent_no_model_falls_back_to_unknown_model(self) -> None:
        """None agent with no model falls back to 'unknown-model'."""
        wp = make_wp(agent=None, model=None)
        result = wp.resolved_agent()
        assert result.tool == "unknown"
        assert result.model == "unknown-model"
        assert result.profile_id == "generic-agent"
        assert result.role is None


class TestEmptyStringAgent:
    """Empty string agent is treated as missing (falsy)."""

    def test_empty_string_agent_treated_as_none(self) -> None:
        """Empty string agent treated as missing → tool='unknown'."""
        wp = make_wp(agent="", model="model-x")
        result = wp.resolved_agent()
        assert result.tool == "unknown"
        assert result.model == "model-x"

    def test_empty_string_agent_no_model(self) -> None:
        """Empty string agent with no model → 'unknown'/'unknown-model'."""
        wp = make_wp(agent="", model=None)
        result = wp.resolved_agent()
        assert result.tool == "unknown"
        assert result.model == "unknown-model"


class TestAgentAssignmentPassthrough:
    """AgentAssignment in agent field is returned as-is (passthrough)."""

    def test_agent_assignment_passthrough(self) -> None:
        """If agent field is already AgentAssignment, return it directly."""
        existing = AgentAssignment(tool="claude", model="claude-opus-4-6")
        wp = make_wp(agent=existing, model="ignored", agent_profile="ignored", role="ignored")
        result = wp.resolved_agent()
        assert result is existing

    def test_agent_assignment_passthrough_with_profile_and_role(self) -> None:
        """AgentAssignment passthrough preserves its own profile_id and role."""
        existing = AgentAssignment(
            tool="cursor", model="cursor-fast", profile_id="my-profile", role="reviewer"
        )
        wp = make_wp(agent=existing)
        result = wp.resolved_agent()
        assert result.tool == "cursor"
        assert result.model == "cursor-fast"
        assert result.profile_id == "my-profile"
        assert result.role == "reviewer"


class TestFallbackOrder:
    """Verify the deterministic fallback order documented in resolved_agent()."""

    def test_dict_model_takes_precedence_over_wp_model(self) -> None:
        """Dict agent model field takes precedence over WP-level model field."""
        wp = make_wp(
            agent={"tool": "copilot", "model": "gpt-4-turbo"},
            model="wp-level-model",
        )
        result = wp.resolved_agent()
        assert result.model == "gpt-4-turbo"

    def test_dict_profile_takes_precedence_over_agent_profile_field(self) -> None:
        """Dict agent profile_id takes precedence over WP-level agent_profile."""
        wp = make_wp(
            agent={"tool": "copilot", "profile_id": "dict-profile"},
            agent_profile="wp-level-profile",
        )
        result = wp.resolved_agent()
        assert result.profile_id == "dict-profile"

    def test_dict_role_takes_precedence_over_role_field(self) -> None:
        """Dict agent role takes precedence over WP-level role field."""
        wp = make_wp(
            agent={"tool": "copilot", "role": "dict-role"},
            role="wp-level-role",
        )
        result = wp.resolved_agent()
        assert result.role == "dict-role"

    def test_model_fallback_chain_for_none_agent(self) -> None:
        """None agent uses WP-level model, not 'unknown-model', when model is set."""
        wp = make_wp(agent=None, model="specific-model")
        result = wp.resolved_agent()
        assert result.model == "specific-model"


class TestImmutabilityOfResult:
    """Returned AgentAssignment must be frozen (immutable)."""

    def test_resolved_agent_result_is_frozen(self) -> None:
        """Result of resolved_agent() cannot be mutated."""
        wp = make_wp(agent="claude", model="claude-opus-4-6")
        result = wp.resolved_agent()
        with pytest.raises((AttributeError, TypeError)):
            result.tool = "other"  # type: ignore[misc]


# ── Import verification: AgentAssignment must be importable from status package ──


def test_agent_assignment_importable_from_status_package() -> None:
    """AgentAssignment must be importable from the top-level status package."""
    from specify_cli.status import AgentAssignment as _AgentAssignment

    assert _AgentAssignment is AgentAssignment


def test_resolved_agent_importable_via_status_package() -> None:
    """WPMetadata.resolved_agent() must be callable via status package import."""
    from specify_cli.status import WPMetadata as _WPMetadata

    wp = _WPMetadata(work_package_id="WP01", title="Test", agent="claude")
    result = wp.resolved_agent()
    assert isinstance(result, AgentAssignment)
    assert result.tool == "claude"
