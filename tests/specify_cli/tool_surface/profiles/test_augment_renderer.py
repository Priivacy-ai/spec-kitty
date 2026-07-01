"""Unit tests for ``tool_surface.profiles.augment_renderer``."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.agent_profiles.profile import AgentProfile
from specify_cli.tool_surface.profiles.augment_renderer import (
    FORMAT_AUGMENT_AGENT,
    AugmentProfileRenderer,
)
from specify_cli.tool_surface.profiles.renderers import ProfileRenderer

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def make_test_profile(slug: str = "implementer-ivan") -> AgentProfile:
    """Build a minimal valid :class:`AgentProfile` for renderer tests."""
    return AgentProfile.model_validate(
        {
            "profile-id": slug,
            "name": slug.replace("-", " ").title(),
            "description": "An Augment test profile.",
            "roles": ["implementer"],
            "purpose": "Implement features for Augment Code.",
            "specialization": {
                "primary-focus": "code implementation",
                "avoidance-boundary": "non-coding tasks",
            },
        }
    )


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_augment_renderer_satisfies_protocol() -> None:
    assert isinstance(AugmentProfileRenderer(), ProfileRenderer)


def test_augment_renderer_has_correct_format_key() -> None:
    assert AugmentProfileRenderer().format_key == FORMAT_AUGMENT_AGENT
    assert FORMAT_AUGMENT_AGENT == "augment-agent"


def test_augment_renderer_is_project_local() -> None:
    assert AugmentProfileRenderer.USER_GLOBAL is False


# ---------------------------------------------------------------------------
# can_render
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_key", ["auggie", "augment", FORMAT_AUGMENT_AGENT]
)
def test_can_render_returns_true_for_known_aliases(tool_key: str) -> None:
    assert AugmentProfileRenderer().can_render(tool_key) is True


@pytest.mark.parametrize(
    "tool_key", ["claude", "codex", "q", "copilot", "unknown"]
)
def test_can_render_returns_false_for_other_tools(tool_key: str) -> None:
    assert AugmentProfileRenderer().can_render(tool_key) is False


# ---------------------------------------------------------------------------
# output_path — project-local
# ---------------------------------------------------------------------------


def test_output_path_inside_augment_agents_dir() -> None:
    profile = make_test_profile("implementer-ivan")
    renderer = AugmentProfileRenderer()
    path = renderer.output_path("auggie", profile, Path("/project"))
    assert path == Path("/project/.augment/agents/implementer-ivan.md")


def test_output_path_uses_project_root() -> None:
    profile = make_test_profile("implementer-ivan")
    renderer = AugmentProfileRenderer()
    path_a = renderer.output_path("auggie", profile, Path("/project-a"))
    path_b = renderer.output_path("auggie", profile, Path("/project-b"))
    assert path_a != path_b
    assert str(path_a).startswith("/project-a")
    assert str(path_b).startswith("/project-b")


def test_output_path_ignores_tool_key_variant() -> None:
    profile = make_test_profile("implementer-ivan")
    renderer = AugmentProfileRenderer()
    path_auggie = renderer.output_path("auggie", profile, Path("/project"))
    path_augment = renderer.output_path("augment", profile, Path("/project"))
    assert path_auggie == path_augment


def test_output_path_has_md_suffix() -> None:
    profile = make_test_profile("implementer-ivan")
    path = AugmentProfileRenderer().output_path("auggie", profile, Path("/project"))
    assert path.suffix == ".md"
    assert path.name == "implementer-ivan.md"


# ---------------------------------------------------------------------------
# render — Markdown + YAML frontmatter
# ---------------------------------------------------------------------------


def test_render_starts_with_yaml_frontmatter_delimiter() -> None:
    profile = make_test_profile()
    body = AugmentProfileRenderer().render(profile)
    assert body.startswith("---\n")


def test_render_contains_closing_frontmatter_delimiter() -> None:
    profile = make_test_profile()
    body = AugmentProfileRenderer().render(profile)
    lines = body.splitlines()
    # First '---' is at index 0; there must be a second one closing it.
    assert lines.count("---") >= 2


def test_render_includes_profile_id_as_name() -> None:
    profile = make_test_profile("implementer-ivan")
    body = AugmentProfileRenderer().render(profile)
    assert "name: implementer-ivan" in body


def test_render_includes_quoted_description() -> None:
    profile = make_test_profile()
    body = AugmentProfileRenderer().render(profile)
    assert "description:" in body
    assert "An Augment test profile." in body


def test_render_includes_roles() -> None:
    profile = make_test_profile()
    body = AugmentProfileRenderer().render(profile)
    assert "roles: [implementer]" in body


def test_render_includes_purpose_in_body() -> None:
    profile = make_test_profile()
    body = AugmentProfileRenderer().render(profile)
    assert "Implement features for Augment Code." in body


def test_render_format_matches_claude_code_renderer() -> None:
    """Augment and Claude Code renderers share the same Markdown structure."""
    from specify_cli.tool_surface.profiles.renderers import ClaudeCodeProfileRenderer

    profile = make_test_profile("implementer-ivan")
    augment_body = AugmentProfileRenderer().render(profile)
    claude_body = ClaudeCodeProfileRenderer().render(profile)
    # Both use the same _render_markdown_agent helper — output must be identical.
    assert augment_body == claude_body


def test_render_includes_spec_kitty_provenance_footer() -> None:
    profile = make_test_profile()
    body = AugmentProfileRenderer().render(profile)
    assert "spec-kitty" in body.lower() or "Spec Kitty" in body
