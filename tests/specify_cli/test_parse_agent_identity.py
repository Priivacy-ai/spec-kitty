"""Tests for parse_agent_identity() – T014 (WP03).

Covers mutual exclusion, individual flags, compound format, and identity round-trip.
"""

from __future__ import annotations

import pytest
import typer

from specify_cli.identity import ActorIdentity, parse_agent_identity

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Mutual exclusion tests
# ---------------------------------------------------------------------------


def test_mutual_exclusion_agent_and_tool_raises():
    with pytest.raises(typer.BadParameter):
        parse_agent_identity(agent="claude", tool="claude")


def test_mutual_exclusion_agent_and_model_raises():
    with pytest.raises(typer.BadParameter):
        parse_agent_identity(agent="claude:opus", model="opus")


def test_mutual_exclusion_agent_and_profile_raises():
    with pytest.raises(typer.BadParameter):
        parse_agent_identity(agent="claude", profile="impl")


def test_mutual_exclusion_agent_and_role_raises():
    with pytest.raises(typer.BadParameter):
        parse_agent_identity(agent="claude", role="implementer")


# ---------------------------------------------------------------------------
# No arguments → None
# ---------------------------------------------------------------------------


def test_all_none_returns_none():
    assert parse_agent_identity() is None


def test_empty_agent_string_returns_unknown_identity():
    # Empty agent string is passed through from_legacy which produces tool='unknown'
    result = parse_agent_identity(agent="", tool=None, model=None, profile=None, role=None)
    assert isinstance(result, ActorIdentity)
    assert result.tool == "unknown"


# ---------------------------------------------------------------------------
# Legacy --agent string
# ---------------------------------------------------------------------------


def test_agent_bare_string_returns_actor_identity():
    result = parse_agent_identity(agent="claude")
    assert isinstance(result, ActorIdentity)
    assert result.tool == "claude"
    assert result.model == "unknown"
    assert result.profile == "unknown"
    assert result.role == "unknown"


def test_agent_compact_string_returns_full_identity():
    result = parse_agent_identity(agent="claude:opus-4:impl:impl")
    assert result == ActorIdentity(tool="claude", model="opus-4", profile="impl", role="impl")


# ---------------------------------------------------------------------------
# Individual --tool/--model/--profile/--role flags
# ---------------------------------------------------------------------------


def test_tool_only_returns_actor_identity():
    result = parse_agent_identity(tool="copilot")
    assert isinstance(result, ActorIdentity)
    assert result.tool == "copilot"
    assert result.model == "unknown"


def test_all_individual_flags_return_full_identity():
    result = parse_agent_identity(tool="claude", model="opus-4-6", profile="reviewer", role="reviewer")
    assert result == ActorIdentity(tool="claude", model="opus-4-6", profile="reviewer", role="reviewer")


def test_tool_and_model_partial_flags():
    result = parse_agent_identity(tool="gemini", model="pro")
    assert result is not None
    assert result.tool == "gemini"
    assert result.model == "pro"
    assert result.profile == "unknown"


# ---------------------------------------------------------------------------
# str() compatibility
# ---------------------------------------------------------------------------


def test_str_returns_tool_name():
    result = parse_agent_identity(agent="claude")
    assert str(result) == "claude"


def test_str_with_compound_returns_tool_name():
    result = parse_agent_identity(agent="codex:gpt4o:reviewer:reviewer")
    assert str(result) == "codex"
