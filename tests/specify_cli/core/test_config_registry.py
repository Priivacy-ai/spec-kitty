"""Registry invariant tests for WP04 (T022).

Asserts that after the WP04 edits:
- ``vibe``, ``pi``, and ``letta`` are present in AI_CHOICES,
  AGENT_TOOL_REQUIREMENTS, AGENT_SKILL_CONFIG.
- ``codex`` is NOT in AGENT_COMMAND_CONFIG.
- ``vibe``, ``pi``, and ``letta`` are NOT in AGENT_COMMAND_CONFIG.
- Command-skill agents have class SKILL_CLASS_SHARED with .agents/skills/ as root.
- The twelve non-migrated command-layer agents are still present in AGENT_COMMAND_CONFIG.
"""

from __future__ import annotations


from specify_cli.agent_utils.directories import AGENT_DIRS, AGENT_DIR_TO_KEY
from specify_cli.core.config import (
    AI_CHOICES,
    AGENT_COMMAND_CONFIG,
    AGENT_SKILL_CONFIG,
    AGENT_TOOL_REQUIREMENTS,
    SKILL_CLASS_SHARED,
)

# ---------------------------------------------------------------------------
# AI_CHOICES
# ---------------------------------------------------------------------------


import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]
def test_vibe_in_ai_choices() -> None:
    assert "vibe" in AI_CHOICES
    assert AI_CHOICES["vibe"] == "Mistral Vibe"


def test_pi_and_letta_in_ai_choices() -> None:
    assert AI_CHOICES["pi"] == "Pi"
    assert AI_CHOICES["letta"] == "Letta Code"


# ---------------------------------------------------------------------------
# AGENT_TOOL_REQUIREMENTS
# ---------------------------------------------------------------------------


def test_vibe_tool_requirement() -> None:
    assert "vibe" in AGENT_TOOL_REQUIREMENTS
    assert AGENT_TOOL_REQUIREMENTS["vibe"][0] == "vibe"


def test_pi_and_letta_tool_requirements() -> None:
    assert AGENT_TOOL_REQUIREMENTS["pi"][0] == "pi"
    assert AGENT_TOOL_REQUIREMENTS["letta"][0] == "letta"


# ---------------------------------------------------------------------------
# AGENT_COMMAND_CONFIG
# ---------------------------------------------------------------------------


def test_codex_not_in_command_config() -> None:
    assert "codex" not in AGENT_COMMAND_CONFIG


def test_vibe_not_in_command_config() -> None:
    assert "vibe" not in AGENT_COMMAND_CONFIG


def test_pi_and_letta_not_in_command_config() -> None:
    assert "pi" not in AGENT_COMMAND_CONFIG
    assert "letta" not in AGENT_COMMAND_CONFIG


def test_eleven_agents_still_in_command_config() -> None:
    """NFR-005 smoke test: the eleven command-layer agents are present.

    "roo" was removed — Roo Code shut down on 2026-05-15 (C-007).
    """
    expected = {
        "claude",
        "copilot",
        "gemini",
        "cursor",
        "qwen",
        "opencode",
        "windsurf",
        "kilocode",
        "auggie",
        # "roo" removed — Roo Code shut down on 2026-05-15 (C-007)
        "q",
        "antigravity",
    }
    missing = expected - set(AGENT_COMMAND_CONFIG.keys())
    assert not missing, f"Missing from AGENT_COMMAND_CONFIG: {missing}"


def test_command_agent_directory_registry_is_consistent() -> None:
    """Command-layer directory roots, keys, and config rows must stay aligned."""
    agent_dir_roots = {root for root, _ in AGENT_DIRS}
    command_config_roots = {
        config["dir"].split("/", 1)[0]
        for config in AGENT_COMMAND_CONFIG.values()
    }

    assert agent_dir_roots == set(AGENT_DIR_TO_KEY)
    assert set(AGENT_DIR_TO_KEY.values()) == set(AGENT_COMMAND_CONFIG)
    assert command_config_roots == set(AGENT_DIR_TO_KEY)


# ---------------------------------------------------------------------------
# AGENT_SKILL_CONFIG
# ---------------------------------------------------------------------------


def test_command_skill_agents_are_shared_skill_roots() -> None:
    for key in ("codex", "vibe", "pi", "letta"):
        assert key in AGENT_SKILL_CONFIG, f"{key!r} missing from AGENT_SKILL_CONFIG"
        entry = AGENT_SKILL_CONFIG[key]
        assert entry["class"] == SKILL_CLASS_SHARED, (
            f"{key!r} should have class SKILL_CLASS_SHARED, got {entry['class']!r}"
        )
        roots: list[str] = entry["skill_roots"]
        assert ".agents/skills/" in roots, (
            f"{key!r} skill_roots should contain '.agents/skills/', got {roots!r}"
        )
