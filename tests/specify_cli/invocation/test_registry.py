"""Tests for ProfileRegistry."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.invocation.errors import ProfileNotFoundError
from specify_cli.invocation.registry import ProfileRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "profiles"


def _make_registry_with_fixtures(tmp_path: Path) -> ProfileRegistry:
    """Create a registry pointing at the test fixture profiles directory."""
    # Copy fixture files to a simulated project .kittify/profiles/ directory.
    project_profiles = tmp_path / ".kittify" / "profiles"
    project_profiles.mkdir(parents=True)
    import shutil

    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, project_profiles / yaml_file.name)
    return ProfileRegistry(tmp_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegistryListsShippedProfiles:
    def test_list_all_returns_profiles(self, tmp_path: Path) -> None:
        """list_all() returns at least one profile (shipped profiles always available)."""
        # Use a directory with no .kittify/profiles/ — falls back to shipped
        registry = ProfileRegistry(tmp_path)
        profiles = registry.list_all()
        # Shipped profiles always include at least 'implementer'
        assert len(profiles) >= 1

    def test_list_all_with_fixtures_returns_fixture_profiles(self, tmp_path: Path) -> None:
        registry = _make_registry_with_fixtures(tmp_path)
        profile_ids = [p.profile_id for p in registry.list_all()]
        assert "implementer-fixture" in profile_ids
        assert "reviewer-fixture" in profile_ids


class TestRegistryGet:
    def test_get_existing_profile_returns_agent_profile(self, tmp_path: Path) -> None:
        registry = _make_registry_with_fixtures(tmp_path)
        profile = registry.get("implementer-fixture")
        assert profile is not None
        assert profile.profile_id == "implementer-fixture"
        assert profile.name == "Implementer (fixture)"

    def test_get_missing_profile_returns_none(self, tmp_path: Path) -> None:
        registry = ProfileRegistry(tmp_path)
        result = registry.get("does-not-exist")
        assert result is None


class TestRegistryResolve:
    def test_resolve_missing_raises_profile_not_found_error(self, tmp_path: Path) -> None:
        registry = ProfileRegistry(tmp_path)
        with pytest.raises(ProfileNotFoundError) as exc_info:
            registry.resolve("no-such-profile")
        assert "no-such-profile" in str(exc_info.value)
        assert isinstance(exc_info.value.available, list)

    def test_resolve_existing_returns_profile(self, tmp_path: Path) -> None:
        registry = _make_registry_with_fixtures(tmp_path)
        profile = registry.resolve("reviewer-fixture")
        assert profile.profile_id == "reviewer-fixture"


class TestRegistryFallbackNoProjectDir:
    def test_no_kittify_profiles_dir_does_not_raise(self, tmp_path: Path) -> None:
        """When .kittify/profiles/ does not exist, ProfileRegistry should not raise."""
        assert not (tmp_path / ".kittify" / "profiles").exists()
        registry = ProfileRegistry(tmp_path)
        # Should fall back to shipped profiles gracefully
        assert isinstance(registry.list_all(), list)

    def test_has_profiles_returns_true_with_shipped(self, tmp_path: Path) -> None:
        registry = ProfileRegistry(tmp_path)
        # Shipped profiles always present — has_profiles() should return True
        assert registry.has_profiles() is True
