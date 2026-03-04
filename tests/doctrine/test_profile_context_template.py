"""Tests for the profile-context command template.

Verifies that:
- The template file exists in the doctrine command-templates directory
- It has valid frontmatter with description
- It references $ARGUMENTS for profile selection
- It works with all 7 shipped profile IDs
- It contains key session behavior instructions
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.agent_profiles.repository import AgentProfileRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "src" / "doctrine" / "templates" / "command-templates"
TEMPLATE_PATH = TEMPLATE_DIR / "profile-context.md"
SHIPPED_DIR = Path(__file__).parent.parent.parent / "src" / "doctrine" / "agent_profiles" / "shipped"

EXPECTED_PROFILE_IDS = sorted([
    "architect",
    "curator",
    "designer",
    "implementer",
    "planner",
    "researcher",
    "reviewer",
])


@pytest.fixture(scope="module")
def template_content() -> str:
    """Read the profile-context template."""
    assert TEMPLATE_PATH.exists(), f"Template not found: {TEMPLATE_PATH}"
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def repo() -> AgentProfileRepository:
    return AgentProfileRepository(shipped_dir=SHIPPED_DIR, project_dir=None)


class TestTemplateExists:
    def test_template_file_exists(self):
        assert TEMPLATE_PATH.exists(), (
            f"profile-context.md not found in {TEMPLATE_DIR}"
        )

    def test_template_has_frontmatter(self, template_content: str):
        assert template_content.startswith("---"), "Template must start with YAML frontmatter"
        parts = template_content.split("---", 2)
        assert len(parts) >= 3, "Template must have opening and closing --- for frontmatter"

    def test_frontmatter_has_description(self, template_content: str):
        parts = template_content.split("---", 2)
        yaml = YAML(typ="safe")
        frontmatter = yaml.load(parts[1])
        assert "description" in frontmatter, "Frontmatter must have 'description' field"
        assert len(frontmatter["description"]) > 10, "Description should be meaningful"


class TestTemplateContent:
    def test_accepts_arguments(self, template_content: str):
        """Template must reference $ARGUMENTS to accept the profile name."""
        assert "$ARGUMENTS" in template_content, (
            "Template must use $ARGUMENTS to receive the profile name"
        )

    def test_instructs_profile_listing_via_cli(self, template_content: str):
        """Template must instruct agent to use CLI to list profiles, not hardcode them."""
        assert "spec-kitty agent profile list" in template_content, (
            "Template must instruct agent to run 'spec-kitty agent profile list'"
        )

    def test_instructs_profile_loading(self, template_content: str):
        """Template must instruct the agent to load profile data."""
        content_lower = template_content.lower()
        assert "spec-kitty agent profile show" in content_lower or "agent profile show" in content_lower, (
            "Template must instruct agent to run 'spec-kitty agent profile show'"
        )

    def test_advisory_session_boundary(self, template_content: str):
        """Template must state the session is advisory and doesn't advance mission state."""
        content_lower = template_content.lower()
        assert "advisory" in content_lower or "does not advance" in content_lower or "no mission state" in content_lower, (
            "Template must clarify advisory-only session boundaries"
        )

    def test_initialization_declaration_reference(self, template_content: str):
        """Template must instruct the agent to use the initialization declaration."""
        content_lower = template_content.lower()
        assert "initialization" in content_lower or "introduce" in content_lower, (
            "Template must reference the initialization declaration"
        )

    def test_no_unfilled_placeholders(self, template_content: str):
        """Template must not contain unfilled {{TOKEN}} placeholders."""
        placeholder_re = re.compile(r"\{\{[A-Z_]+\}\}")
        matches = placeholder_re.findall(template_content)
        assert not matches, f"Template has unfilled placeholders: {matches}"


class TestProfileCompatibility:
    """Verify the template workflow works for all shipped profiles."""

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILE_IDS)
    def test_profile_resolves_for_context_session(
        self, repo: AgentProfileRepository, profile_id: str
    ):
        """Each shipped profile can be resolved for a context session."""
        profile = repo.resolve_profile(profile_id)
        assert profile is not None
        assert profile.initialization_declaration.strip(), (
            f"Profile '{profile_id}' has no initialization declaration — "
            "profile-context sessions require one"
        )

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILE_IDS)
    def test_profile_has_mode_defaults(
        self, repo: AgentProfileRepository, profile_id: str
    ):
        """Each shipped profile has mode defaults for session context."""
        profile = repo.resolve_profile(profile_id)
        assert len(profile.mode_defaults) > 0, (
            f"Profile '{profile_id}' has no mode defaults — "
            "profile-context sessions use these for operating mode"
        )

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILE_IDS)
    def test_profile_has_specialization(
        self, repo: AgentProfileRepository, profile_id: str
    ):
        """Each shipped profile has specialization for session boundaries."""
        profile = repo.resolve_profile(profile_id)
        assert profile.specialization.primary_focus.strip(), (
            f"Profile '{profile_id}' has no primary focus"
        )

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILE_IDS)
    def test_profile_has_collaboration_contract(
        self, repo: AgentProfileRepository, profile_id: str
    ):
        """Each shipped profile has collaboration info for handoff suggestions."""
        profile = repo.resolve_profile(profile_id)
        assert len(profile.collaboration.canonical_verbs) > 0, (
            f"Profile '{profile_id}' has no canonical verbs"
        )
