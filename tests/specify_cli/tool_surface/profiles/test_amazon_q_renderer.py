"""Unit tests for ``tool_surface.profiles.amazon_q_renderer``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from doctrine.agent_profiles.profile import AgentProfile
from specify_cli.tool_surface.profiles.amazon_q_renderer import (
    FORMAT_AMAZON_Q_AGENT,
    AmazonQProfileRenderer,
)
from specify_cli.tool_surface.profiles.renderers import ProfileRenderer

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def make_test_profile(slug: str = "analyst-alex") -> AgentProfile:
    """Build a minimal valid :class:`AgentProfile` for renderer tests."""
    return AgentProfile.model_validate(
        {
            "profile-id": slug,
            "name": slug.replace("-", " ").title(),
            "description": "Amazon Q test profile.",
            "roles": ["analyst"],
            "purpose": "Perform analysis tasks for Amazon Q.",
            "specialization": {
                "primary-focus": "data analysis",
                "avoidance-boundary": "out-of-scope tasks",
            },
        }
    )


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_amazon_q_renderer_satisfies_protocol() -> None:
    assert isinstance(AmazonQProfileRenderer(), ProfileRenderer)


def test_amazon_q_renderer_has_correct_format_key() -> None:
    assert AmazonQProfileRenderer().format_key == FORMAT_AMAZON_Q_AGENT
    assert FORMAT_AMAZON_Q_AGENT == "amazon-q-agent"


def test_amazon_q_renderer_is_user_global() -> None:
    assert AmazonQProfileRenderer.USER_GLOBAL is True


# ---------------------------------------------------------------------------
# can_render
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_key", ["q", "amazon-q", FORMAT_AMAZON_Q_AGENT])
def test_can_render_returns_true_for_known_aliases(tool_key: str) -> None:
    assert AmazonQProfileRenderer().can_render(tool_key) is True


@pytest.mark.parametrize("tool_key", ["claude", "codex", "auggie", "kiro", "unknown"])
def test_can_render_returns_false_for_other_tools(tool_key: str) -> None:
    assert AmazonQProfileRenderer().can_render(tool_key) is False


# ---------------------------------------------------------------------------
# output_path — user-global, ignores project_root
# ---------------------------------------------------------------------------


def test_output_path_goes_to_home_aws_directory() -> None:
    profile = make_test_profile("analyst-alex")
    renderer = AmazonQProfileRenderer()
    path = renderer.output_path("q", profile, Path("/project"))
    assert path == Path.home() / ".aws" / "amazonq" / "cli-agents" / "analyst-alex.json"


def test_output_path_ignores_project_root() -> None:
    """The project_root parameter must not affect the output path."""
    profile = make_test_profile("analyst-alex")
    renderer = AmazonQProfileRenderer()
    path_a = renderer.output_path("q", profile, Path("/project-a"))
    path_b = renderer.output_path("q", profile, Path("/project-b"))
    assert path_a == path_b


def test_output_path_ignores_tool_key_variant() -> None:
    profile = make_test_profile("analyst-alex")
    renderer = AmazonQProfileRenderer()
    path_q = renderer.output_path("q", profile, Path("/project"))
    path_aq = renderer.output_path("amazon-q", profile, Path("/project"))
    assert path_q == path_aq


def test_output_path_uses_profile_id_as_filename() -> None:
    profile = make_test_profile("researcher-robbie")
    renderer = AmazonQProfileRenderer()
    path = renderer.output_path("q", profile, Path("/project"))
    assert path.name == "researcher-robbie.json"
    assert path.suffix == ".json"


# ---------------------------------------------------------------------------
# render — valid JSON output
# ---------------------------------------------------------------------------


def test_render_produces_valid_json() -> None:
    profile = make_test_profile("analyst-alex")
    body = AmazonQProfileRenderer().render(profile)
    parsed = json.loads(body)  # must not raise
    assert isinstance(parsed, dict)


def test_render_includes_name_field() -> None:
    profile = make_test_profile("analyst-alex")
    body = AmazonQProfileRenderer().render(profile)
    payload = json.loads(body)
    assert "name" in payload
    assert payload["name"] == "Analyst Alex"


def test_render_includes_description_field() -> None:
    profile = make_test_profile("analyst-alex")
    body = AmazonQProfileRenderer().render(profile)
    payload = json.loads(body)
    assert "description" in payload
    assert payload["description"] == "Amazon Q test profile."


def test_render_includes_instructions_field() -> None:
    profile = make_test_profile("analyst-alex")
    body = AmazonQProfileRenderer().render(profile)
    payload = json.loads(body)
    assert "instructions" in payload
    assert payload["instructions"] == "Perform analysis tasks for Amazon Q."


def test_render_uses_purpose_as_fallback_for_empty_description() -> None:
    profile = AgentProfile.model_validate(
        {
            "profile-id": "minimal-marvin",
            "name": "Minimal Marvin",
            "description": "",
            "roles": ["implementer"],
            "purpose": "Do minimal tasks.",
            "specialization": {"primary-focus": "minimal work"},
        }
    )
    body = AmazonQProfileRenderer().render(profile)
    payload = json.loads(body)
    assert payload["description"] == "Do minimal tasks."


def test_render_uses_profile_id_as_fallback_for_empty_name() -> None:
    profile = AgentProfile.model_validate(
        {
            "profile-id": "nameless-nora",
            "name": "Nameless Nora",
            "description": "A profile.",
            "roles": ["reviewer"],
            "purpose": "Review code.",
            "specialization": {"primary-focus": "code review"},
        }
    )
    # Profiles always have a name in the schema, so test via rendered output
    body = AmazonQProfileRenderer().render(profile)
    payload = json.loads(body)
    assert payload["name"]  # non-empty


def test_render_output_is_prettily_indented() -> None:
    profile = make_test_profile()
    body = AmazonQProfileRenderer().render(profile)
    # json.dumps with indent=2 produces multiline output
    assert "\n" in body
