"""Scope: config unit tests — no real git or subprocesses."""

import pytest
from specify_cli.core import (
    AI_CHOICES,
    AGENT_COMMAND_CONFIG,
    AGENT_TOOL_REQUIREMENTS,
    BANNER,
    DEFAULT_MISSION_KEY,
    DEFAULT_TEMPLATE_REPO,
    MISSION_CHOICES,
    SCRIPT_TYPE_CHOICES,
)

pytestmark = pytest.mark.fast


def test_ai_choices_contains_known_agents():
    """AI_CHOICES dict includes claude and q entries."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    claude_name = AI_CHOICES.get("claude")
    q_present = "q" in AI_CHOICES

    # Assert
    assert claude_name == "Claude Code"
    assert q_present


def test_agent_command_config_shapes():
    """AGENT_COMMAND_CONFIG entry for claude has expected dir, ext, and arg_format."""
    # Arrange
    # (no precondition)

    # Assumption check
    assert "claude" in AGENT_COMMAND_CONFIG, "claude must be a registered agent"

    # Act
    config = AGENT_COMMAND_CONFIG["claude"]

    # Assert
    assert config["dir"].startswith(".claude")
    assert config["ext"] == "md"
    assert config["arg_format"] == "$ARGUMENTS"


def test_defaults_and_banner_present():
    """Default mission key, template repo, and banner are all non-empty strings."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act / Assert
    assert DEFAULT_MISSION_KEY in MISSION_CHOICES
    assert isinstance(DEFAULT_TEMPLATE_REPO, str) and DEFAULT_TEMPLATE_REPO
    assert isinstance(BANNER, str) and BANNER.strip()


def test_script_type_choices_are_human_readable():
    """SCRIPT_TYPE_CHOICES contains sh and ps with human-readable labels."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act / Assert
    assert set(SCRIPT_TYPE_CHOICES.keys()) == {"sh", "ps"}
    assert "POSIX" in SCRIPT_TYPE_CHOICES["sh"]


def test_agent_tool_requirements_urls():
    """AGENT_TOOL_REQUIREMENTS entry for claude provides CLI name and install URL."""
    # Arrange
    # (no precondition)

    # Assumption check
    assert "claude" in AGENT_TOOL_REQUIREMENTS, "claude must have tool requirements"

    # Act
    claude_tool = AGENT_TOOL_REQUIREMENTS["claude"]

    # Assert
    assert claude_tool[0] == "claude"
    assert claude_tool[1].startswith("https://")
