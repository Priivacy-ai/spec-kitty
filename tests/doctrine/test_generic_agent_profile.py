"""US-5 acceptance tests for the generic-agent profile in _proposed/."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.agent_profiles.repository import AgentProfileRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

_PROPOSED_DIR = Path(__file__).parents[2] / "src" / "doctrine" / "agent_profiles" / "_proposed"
_SHIPPED_DIR = Path(__file__).parents[2] / "src" / "doctrine" / "agent_profiles" / "shipped"


def test_generic_agent_exists_in_proposed() -> None:
    """US-5 S1: AgentProfileRepository.get('generic-agent') returns a non-None profile."""
    repo = AgentProfileRepository(shipped_dir=_SHIPPED_DIR, project_dir=_PROPOSED_DIR)

    profile = repo.get("generic-agent")

    assert profile is not None, "generic-agent profile not found in _proposed/"
    assert profile.profile_id == "generic-agent"


def test_generic_agent_references_directive_028() -> None:
    """US-5 S2: resolved profile has exactly one directive reference to DIRECTIVE_028 (code='028')."""
    repo = AgentProfileRepository(shipped_dir=_SHIPPED_DIR, project_dir=_PROPOSED_DIR)

    profile = repo.get("generic-agent")
    assert profile is not None

    directive_codes = [ref.code for ref in profile.directive_references]
    assert "028" in directive_codes, f"Expected code '028' in directive_references, got: {directive_codes}"
    assert len(directive_codes) == 1, f"Expected exactly 1 directive reference, got: {directive_codes}"


def test_generic_agent_not_in_shipped() -> None:
    """US-5 S3: generic-agent YAML must NOT exist in shipped/."""
    shipped_yaml = _SHIPPED_DIR / "generic-agent.agent.yaml"

    assert not shipped_yaml.exists(), (
        "generic-agent.agent.yaml found in shipped/ — it must remain in _proposed/ only"
    )
