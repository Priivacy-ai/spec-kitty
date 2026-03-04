"""ATDD acceptance tests for the human-in-charge sentinel profile (WP05)."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.agent_profiles.repository import AgentProfileRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

_PROPOSED_DIR = Path(__file__).parents[2] / "src" / "doctrine" / "agent_profiles" / "_proposed"
_SHIPPED_DIR = Path(__file__).parents[2] / "src" / "doctrine" / "agent_profiles" / "shipped"


def test_human_in_charge_exists_in_proposed() -> None:
    """AgentProfileRepository.get('human-in-charge') returns a non-None profile."""
    repo = AgentProfileRepository(shipped_dir=_SHIPPED_DIR, project_dir=_PROPOSED_DIR)

    profile = repo.get("human-in-charge")

    assert profile is not None, "human-in-charge profile not found in _proposed/"
    assert profile.profile_id == "human-in-charge"


def test_human_in_charge_sentinel_true() -> None:
    """profile.sentinel is True for the human-in-charge profile."""
    repo = AgentProfileRepository(shipped_dir=_SHIPPED_DIR, project_dir=_PROPOSED_DIR)

    profile = repo.get("human-in-charge")

    assert profile is not None
    assert profile.sentinel is True, f"Expected sentinel=True, got sentinel={profile.sentinel}"


def test_human_in_charge_not_in_shipped() -> None:
    """human-in-charge YAML must NOT exist in shipped/."""
    shipped_yaml = _SHIPPED_DIR / "human-in-charge.agent.yaml"

    assert not shipped_yaml.exists(), (
        "human-in-charge.agent.yaml found in shipped/ — it must remain in _proposed/ only"
    )


def test_kanban_shows_hic_marker(tmp_path: Path) -> None:
    """Kanban status renders 👤 marker for WPs with agent_profile: human-in-charge.

    Covers both the lazy (repo=None) and pre-built repo paths.
    """
    # repo_root is 4 levels up from _PROPOSED_DIR:
    # _proposed/ → agent_profiles/ → doctrine/ → src/ → repo_root
    repo_root = _PROPOSED_DIR.parents[3]

    from specify_cli.cli.commands.agent.tasks import _get_hic_marker

    # --- lazy path: repo=None, resolved internally ---
    marker = _get_hic_marker("human-in-charge", repo_root)
    assert "👤" in marker, f"Expected '👤' marker for human-in-charge (lazy), got: {repr(marker)}"

    # --- pre-built repo path ---
    pre_built = AgentProfileRepository(shipped_dir=_SHIPPED_DIR, project_dir=_PROPOSED_DIR)
    marker_prebuilt = _get_hic_marker("human-in-charge", repo_root, repo=pre_built)
    assert "👤" in marker_prebuilt, f"Expected '👤' marker for human-in-charge (pre-built), got: {repr(marker_prebuilt)}"

    # Non-sentinel profiles should return empty string (both paths)
    assert _get_hic_marker("generic-agent", repo_root) == ""
    assert _get_hic_marker("generic-agent", repo_root, repo=pre_built) == ""

    # Unknown/None profiles should return empty string gracefully
    assert _get_hic_marker(None, tmp_path) == ""
    assert _get_hic_marker("nonexistent-profile", tmp_path) == ""
