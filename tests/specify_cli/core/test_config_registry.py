"""Registry invariant tests for WP04 (T022).

Asserts that after the WP04 edits:
- ``vibe`` is present in AI_CHOICES, AGENT_TOOL_REQUIREMENTS, AGENT_SKILL_CONFIG.
- ``codex`` is NOT in AGENT_COMMAND_CONFIG.
- ``vibe`` is NOT in AGENT_COMMAND_CONFIG.
- Both codex and vibe have class SKILL_CLASS_SHARED with .agents/skills/ as root.
- The twelve non-migrated command-layer agents are still present in AGENT_COMMAND_CONFIG.
"""

from __future__ import annotations


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


def test_vibe_in_ai_choices() -> None:
    assert "vibe" in AI_CHOICES
    assert AI_CHOICES["vibe"] == "Mistral Vibe"


# ---------------------------------------------------------------------------
# AGENT_TOOL_REQUIREMENTS
# ---------------------------------------------------------------------------


def test_vibe_tool_requirement() -> None:
    assert "vibe" in AGENT_TOOL_REQUIREMENTS
    assert AGENT_TOOL_REQUIREMENTS["vibe"][0] == "vibe"


# ---------------------------------------------------------------------------
# AGENT_COMMAND_CONFIG
# ---------------------------------------------------------------------------


def test_codex_not_in_command_config() -> None:
    assert "codex" not in AGENT_COMMAND_CONFIG


def test_vibe_not_in_command_config() -> None:
    assert "vibe" not in AGENT_COMMAND_CONFIG


def test_twelve_agents_still_in_command_config() -> None:
    """NFR-005 smoke test: the twelve non-migrated command-layer agents are present."""
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
        "roo",
        "q",
        "antigravity",
    }
    missing = expected - set(AGENT_COMMAND_CONFIG.keys())
    assert not missing, f"Missing from AGENT_COMMAND_CONFIG: {missing}"


# ---------------------------------------------------------------------------
# AGENT_SKILL_CONFIG
# ---------------------------------------------------------------------------


def test_codex_and_vibe_are_shared_skill_roots() -> None:
    for key in ("codex", "vibe"):
        assert key in AGENT_SKILL_CONFIG, f"{key!r} missing from AGENT_SKILL_CONFIG"
        entry = AGENT_SKILL_CONFIG[key]
        assert entry["class"] == SKILL_CLASS_SHARED, (
            f"{key!r} should have class SKILL_CLASS_SHARED, got {entry['class']!r}"
        )
        roots: list[str] = entry["skill_roots"]  # type: ignore[assignment]
        assert ".agents/skills/" in roots, (
            f"{key!r} skill_roots should contain '.agents/skills/', got {roots!r}"
        )
