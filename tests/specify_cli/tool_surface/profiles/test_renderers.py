"""Unit tests for ``tool_surface.profiles.renderers``."""

from __future__ import annotations

from pathlib import Path

from doctrine.agent_profiles.profile import AgentProfile
from specify_cli.tool_surface.profiles.renderers import (
    ClaudeCodeProfileRenderer,
    CopilotProfileRenderer,
    ProfileRenderer,
    get_renderer,
    native_name_violation,
)

import pytest

pytestmark = [pytest.mark.unit]


def make_test_profile(slug: str = "architect-alphonso") -> AgentProfile:
    """Build a minimal valid :class:`AgentProfile` for renderer tests."""
    return AgentProfile.model_validate(
        {
            "profile-id": slug,
            "name": slug.replace("-", " ").title(),
            "description": "A test profile: with a colon.",
            "roles": ["architect"],
            "purpose": "Test purpose line.",
            "specialization": {
                "primary-focus": "testing renderers",
                "avoidance-boundary": "anything else",
            },
        }
    )


def test_claude_code_renderer_satisfies_protocol() -> None:
    assert isinstance(ClaudeCodeProfileRenderer(), ProfileRenderer)


def test_claude_code_renderer_output_path() -> None:
    profile = make_test_profile(slug="architect-alphonso")
    renderer = ClaudeCodeProfileRenderer()
    path = renderer.output_path("claude", profile, Path("/project"))
    assert path == Path("/project/.claude/agents/architect-alphonso.md")


def test_claude_code_renderer_can_render() -> None:
    renderer = ClaudeCodeProfileRenderer()
    assert renderer.can_render("claude") is True
    assert renderer.can_render("copilot") is False


def test_claude_code_renderer_produces_yaml_frontmatter() -> None:
    profile = make_test_profile()
    body = ClaudeCodeProfileRenderer().render(profile)
    lines = body.splitlines()
    assert lines[0] == "---"
    assert "name: architect-alphonso" in lines
    assert lines.index("---", 1) > 0  # closing frontmatter delimiter present
    # Free-text description with a colon is quoted so YAML stays valid.
    assert 'description: "A test profile: with a colon."' in lines
    assert "roles: [architect]" in lines


def test_copilot_renderer_output_path() -> None:
    profile = make_test_profile(slug="researcher-robbie")
    renderer = CopilotProfileRenderer()
    path = renderer.output_path("copilot", profile, Path("/project"))
    assert path == Path("/project/.github/agents/researcher-robbie.agent.md")


def test_copilot_renderer_handles_vscode() -> None:
    renderer = CopilotProfileRenderer()
    assert renderer.can_render("copilot") is True
    assert renderer.can_render("vscode") is True
    assert renderer.can_render("claude") is False


def test_copilot_renderer_produces_agent_md_frontmatter() -> None:
    profile = make_test_profile(slug="researcher-robbie")
    body = CopilotProfileRenderer().render(profile)
    assert body.startswith("---\n")
    assert "name: researcher-robbie" in body
    assert profile.purpose in body


def test_get_renderer_returns_claude_for_claude() -> None:
    renderer = get_renderer("claude")
    assert isinstance(renderer, ClaudeCodeProfileRenderer)


def test_get_renderer_returns_copilot_for_copilot_and_vscode() -> None:
    assert isinstance(get_renderer("copilot"), CopilotProfileRenderer)
    assert isinstance(get_renderer("vscode"), CopilotProfileRenderer)


def test_get_renderer_returns_none_for_codex() -> None:
    assert get_renderer("codex") is None  # Codex yields research-gap-surface


def test_get_renderer_returns_none_for_unknown_tool() -> None:
    assert get_renderer("unknown_tool") is None


# --- #1940 native-name validity (drives the profile-name-invalid condition) ---


def test_native_name_violation_accepts_clean_id() -> None:
    """A canonical kebab-case id is legal for the native filename."""
    assert native_name_violation("architect-alphonso") is None


@pytest.mark.parametrize(
    "bad_id",
    [
        "bad/slash",  # path separator escapes the agents dir
        "bad\\back",  # Windows separator
        "..",  # path traversal
        "with space",  # whitespace is illegal in the native filename
        "tab\tchar",  # control char
        "",  # empty id has no filename stem
    ],
)
def test_native_name_violation_flags_illegal_ids(bad_id: str) -> None:
    """Ids illegal for ``.claude/agents/<id>.md`` return a violation reason."""
    reason = native_name_violation(bad_id)
    assert reason is not None
    assert isinstance(reason, str) and reason
