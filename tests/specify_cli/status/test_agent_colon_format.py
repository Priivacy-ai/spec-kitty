"""Tests for --agent colon-split format and template/skill flag documentation.

These tests are EXPECTED TO FAIL in their current state:

1. resolved_agent() does not split colon-separated strings — the full string
   "claude:opus-4-7:reviewer:reviewer" is used as the tool name verbatim
   instead of being parsed into (tool, model, profile_id, role).

2. The command templates and skill files only document ``--agent <name>``
   and do not mention the decomposed flags ``--profile``, ``--tool``,
   ``--profile-id``, or ``--role``.

Observed in the wild: every WP in the latest mission carries
  agent: "claude:opus-4-7:reviewer:reviewer"
which is already in the intended colon-split format, but the production
code silently discards the model/profile/role parts.

Fix targets:
  src/specify_cli/status/wp_metadata.py  — _resolve_agent_from_string()
  src/specify_cli/missions/software-dev/command-templates/implement.md
  src/specify_cli/missions/software-dev/command-templates/review.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.status.models import AgentAssignment
from specify_cli.status.wp_metadata import WPMetadata

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).parents[3]
_IMPLEMENT_TEMPLATE = _REPO_ROOT / "src/specify_cli/missions/software-dev/command-templates/implement.md"
_REVIEW_TEMPLATE = _REPO_ROOT / "src/specify_cli/missions/software-dev/command-templates/review.md"
_SKILL_IMPLEMENT = _REPO_ROOT / ".agents/skills/spec-kitty.implement/SKILL.md"
_SKILL_REVIEW = _REPO_ROOT / ".agents/skills/spec-kitty.review/SKILL.md"


# ─────────────────────────────────────────────────────────────
# Part 1: resolved_agent() colon-split parsing
# ─────────────────────────────────────────────────────────────


class TestResolvedAgentColonSplit:
    """--agent colon-separated string must be split into AgentAssignment parts.

    Expected wire format:  <tool>:<model>:<profile_id>:<role>
    All parts after <tool> are optional (trailing omission only).

    Regression: every WP in stability-and-hygiene-hardening-2026-04-01KQ4ARB
    stores  agent: "claude:opus-4-7:reviewer:reviewer"  — the production code
    currently returns tool="claude:opus-4-7:reviewer:reviewer" (the unsplit
    string) which is incorrect.
    """

    def test_four_parts_map_to_all_assignment_fields(self) -> None:
        meta = WPMetadata(work_package_id="WP01", agent="claude:opus-4-7:reviewer:reviewer")

        result = meta.resolved_agent()

        assert result.tool == "claude"
        assert result.model == "opus-4-7"
        assert result.profile_id == "reviewer"
        assert result.role == "reviewer"

    def test_three_parts_leave_role_as_none(self) -> None:
        meta = WPMetadata(work_package_id="WP01", agent="claude:opus-4-7:python-pedro")

        result = meta.resolved_agent()

        assert result.tool == "claude"
        assert result.model == "opus-4-7"
        assert result.profile_id == "python-pedro"
        assert result.role is None

    def test_two_parts_default_profile_to_generic_agent(self) -> None:
        """When profile is omitted from the agent string, profile_id defaults to 'generic-agent'."""
        meta = WPMetadata(work_package_id="WP01", agent="claude:opus-4-7")

        result = meta.resolved_agent()

        assert result.tool == "claude"
        assert result.model == "opus-4-7"
        assert result.profile_id == "generic-agent"
        assert result.role is None

    def test_single_part_defaults_profile_to_generic_agent(self) -> None:
        """Backward-compat: a bare tool name (no colon) still defaults profile to 'generic-agent'."""
        meta = WPMetadata(work_package_id="WP01", agent="claude", model="opus-4-7")

        result = meta.resolved_agent()

        assert result.tool == "claude"
        assert result.model == "opus-4-7"
        assert result.profile_id == "generic-agent"

    def test_tool_field_contains_no_colons_after_split(self) -> None:
        """Splitting must strip the model/profile/role from the tool name."""
        meta = WPMetadata(work_package_id="WP01", agent="claude:opus-4-7:reviewer:reviewer")

        result = meta.resolved_agent()

        assert ":" not in result.tool

    def test_result_is_agent_assignment_instance(self) -> None:
        meta = WPMetadata(work_package_id="WP01", agent="claude:opus-4-7:reviewer:reviewer")

        result = meta.resolved_agent()

        assert isinstance(result, AgentAssignment)

    def test_latest_mission_wp_format_roundtrips_correctly(self) -> None:
        """Regression for the exact agent string observed in the latest mission WPs.

        All WPs in stability-and-hygiene-hardening-2026-04-01KQ4ARB carry:
          agent: "claude:opus-4-7:reviewer:reviewer"
        """
        meta = WPMetadata(work_package_id="WP07", agent="claude:opus-4-7:reviewer:reviewer")

        result = meta.resolved_agent()

        assert result == AgentAssignment(
            tool="claude",
            model="opus-4-7",
            profile_id="reviewer",
            role="reviewer",
        )

    def test_colon_split_model_takes_precedence_over_standalone_model_field(self) -> None:
        """Model encoded in the agent string wins over the separate model field."""
        meta = WPMetadata(
            work_package_id="WP01",
            agent="claude:sonnet-4-6:python-pedro:implementer",
            model="haiku",  # should be overridden by the split model
        )

        result = meta.resolved_agent()

        assert result.model == "sonnet-4-6"

    def test_four_parts_with_profile_and_no_role_variant(self) -> None:
        meta = WPMetadata(work_package_id="WP01", agent="codex:o1:implementer-ivan:implementer")

        result = meta.resolved_agent()

        assert result.tool == "codex"
        assert result.model == "o1"
        assert result.profile_id == "implementer-ivan"
        assert result.role == "implementer"


# ─────────────────────────────────────────────────────────────
# Part 2: Source templates document the decomposed flags
# ─────────────────────────────────────────────────────────────

_DECOMPOSED_FLAGS = ["--profile", "--tool", "--profile-id", "--role"]


class TestImplementTemplateDocumentsDecomposedFlags:
    """Source implement template must instruct agents to use specific flags.

    Currently the template only documents ``--agent <name>``.  It should
    also document ``--profile``, ``--tool``, ``--profile-id``, and ``--role``
    so agents know how to populate all AgentAssignment fields.
    """

    @pytest.mark.parametrize("flag", _DECOMPOSED_FLAGS)
    def test_implement_template_mentions_flag(self, flag: str) -> None:
        content = _IMPLEMENT_TEMPLATE.read_text(encoding="utf-8")
        assert flag in content, (
            f"implement.md does not document {flag!r} — agents cannot populate "
            f"AgentAssignment.{flag.lstrip('-').replace('-', '_')}"
        )


class TestReviewTemplateDocumentsDecomposedFlags:
    """Source review template must instruct agents to use specific flags."""

    @pytest.mark.parametrize("flag", _DECOMPOSED_FLAGS)
    def test_review_template_mentions_flag(self, flag: str) -> None:
        content = _REVIEW_TEMPLATE.read_text(encoding="utf-8")
        assert flag in content, (
            f"review.md does not document {flag!r} — agents cannot populate "
            f"AgentAssignment.{flag.lstrip('-').replace('-', '_')}"
        )


# ─────────────────────────────────────────────────────────────
# Part 3: Generated Skill files document the decomposed flags
# ─────────────────────────────────────────────────────────────


class TestImplementSkillDocumentsDecomposedFlags:
    """Generated spec-kitty.implement SKILL.md must mention specific flags."""

    @pytest.mark.parametrize("flag", _DECOMPOSED_FLAGS)
    def test_implement_skill_mentions_flag(self, flag: str) -> None:
        content = _SKILL_IMPLEMENT.read_text(encoding="utf-8")
        assert flag in content, (
            f"spec-kitty.implement/SKILL.md does not document {flag!r}"
        )


class TestReviewSkillDocumentsDecomposedFlags:
    """Generated spec-kitty.review SKILL.md must mention specific flags."""

    @pytest.mark.parametrize("flag", _DECOMPOSED_FLAGS)
    def test_review_skill_mentions_flag(self, flag: str) -> None:
        content = _SKILL_REVIEW.read_text(encoding="utf-8")
        assert flag in content, (
            f"spec-kitty.review/SKILL.md does not document {flag!r}"
        )
