"""
Integration tests for shipped reference profiles.

Verifies that all shipped reference profiles:
- Load via AgentProfileRepository
- Pass schema validation
- Have no hierarchy errors
- Have no duplicate profile_ids
- Have non-empty purpose and specialization.primary_focus
"""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.agent_profiles.profile import AgentProfile, Role
from doctrine.agent_profiles.repository import AgentProfileRepository
from doctrine.agent_profiles.validation import validate_agent_profile_yaml

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

SHIPPED_DIR = Path(__file__).parent.parent.parent / "src" / "doctrine" / "agent_profiles" / "shipped"

EXPECTED_PROFILE_IDS = {
    "architect",
    "designer",
    "generic-agent",
    "human-in-charge",
    "implementer",
    "planner",
    "python-implementer",
    "researcher",
    "reviewer",
    "curator",
}

# Sentinel profiles are workflow markers, not real agents.  They intentionally
# have empty context sources and directive references.
_SENTINEL_PROFILES = {"human-in-charge"}
_AGENT_PROFILE_IDS = EXPECTED_PROFILE_IDS - _SENTINEL_PROFILES


@pytest.fixture(scope="module")
def repo() -> AgentProfileRepository:
    """Load repository from the actual shipped profiles directory."""
    return AgentProfileRepository(shipped_dir=SHIPPED_DIR, project_dir=None)


@pytest.fixture(scope="module")
def all_profiles(repo: AgentProfileRepository) -> list[AgentProfile]:
    """All loaded profiles from shipped directory."""
    return repo.list_all()


class TestShippedProfilesLoad:
    """Verify all shipped profiles load correctly."""

    def test_shipped_dir_exists(self):
        """Shipped profiles directory exists."""
        assert SHIPPED_DIR.exists(), f"Shipped directory not found: {SHIPPED_DIR}"
        assert SHIPPED_DIR.is_dir()

    def test_all_profiles_load(self, all_profiles: list[AgentProfile]):
        """All expected profiles are loaded."""
        assert len(all_profiles) == len(EXPECTED_PROFILE_IDS), (
            f"Expected {len(EXPECTED_PROFILE_IDS)} profiles, got {len(all_profiles)}: "
            f"{[p.profile_id for p in all_profiles]}"
        )

    def test_expected_profile_ids_present(self, all_profiles: list[AgentProfile]):
        """All expected profile IDs are present."""
        loaded_ids = {p.profile_id for p in all_profiles}
        assert loaded_ids == EXPECTED_PROFILE_IDS, (
            f"Missing: {EXPECTED_PROFILE_IDS - loaded_ids}, Extra: {loaded_ids - EXPECTED_PROFILE_IDS}"
        )

    def test_no_duplicate_profile_ids(self, all_profiles: list[AgentProfile]):
        """No duplicate profile IDs exist."""
        ids = [p.profile_id for p in all_profiles]
        assert len(ids) == len(set(ids)), f"Duplicate profile IDs found: {ids}"

    @pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILE_IDS))
    def test_each_profile_accessible_by_id(self, repo: AgentProfileRepository, profile_id: str):
        """Each shipped profile is accessible via repo.get()."""
        profile = repo.get(profile_id)
        assert profile is not None, f"Profile '{profile_id}' not found in repository"
        assert profile.profile_id == profile_id


class TestShippedProfilesRoles:
    """Verify profiles have correct roles."""

    @pytest.mark.parametrize(
        "profile_id,expected_role",
        [
            ("architect", Role.ARCHITECT),
            ("designer", Role.DESIGNER),
            ("generic-agent", Role.IMPLEMENTER),
            ("implementer", Role.IMPLEMENTER),
            ("python-implementer", Role.IMPLEMENTER),
            ("reviewer", Role.REVIEWER),
            ("planner", Role.PLANNER),
            ("researcher", Role.RESEARCHER),
            ("curator", Role.CURATOR),
        ],
    )
    def test_profile_has_correct_role(
        self,
        repo: AgentProfileRepository,
        profile_id: str,
        expected_role: Role,
    ):
        """Each profile has the correct role enum value."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert profile.role == expected_role, (
            f"Profile '{profile_id}' has role={profile.role!r}, expected {expected_role!r}"
        )


class TestShippedProfilesContent:
    """Verify profiles have non-empty required content."""

    @pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILE_IDS))
    def test_purpose_is_non_empty(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile has a non-empty purpose."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert profile.purpose.strip(), f"Profile '{profile_id}' has empty purpose"

    @pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILE_IDS))
    def test_primary_focus_is_non_empty(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile has a non-empty specialization.primary_focus."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert profile.specialization.primary_focus.strip(), (
            f"Profile '{profile_id}' has empty specialization.primary_focus"
        )

    @pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILE_IDS))
    def test_name_is_non_empty(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile has a non-empty name."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert profile.name.strip(), f"Profile '{profile_id}' has empty name"

    @pytest.mark.parametrize(
        "profile_id,expected_priority",
        [
            ("architect", 50),
            ("designer", 50),
            ("generic-agent", 10),
            ("implementer", 50),
            ("python-implementer", 80),
            ("reviewer", 50),
            ("planner", 50),
            ("researcher", 40),
            ("curator", 40),
        ],
    )
    def test_routing_priority(
        self,
        repo: AgentProfileRepository,
        profile_id: str,
        expected_priority: int,
    ):
        """Each profile has the expected routing priority."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert profile.routing_priority == expected_priority, (
            f"Profile '{profile_id}' has routing_priority={profile.routing_priority}, expected {expected_priority}"
        )

    @pytest.mark.parametrize(
        "profile_id,expected_max",
        [
            ("architect", 3),
            ("designer", 4),
            ("generic-agent", 5),
            ("implementer", 5),
            ("python-implementer", 5),
            ("reviewer", 8),
            ("planner", 3),
            ("researcher", 4),
            ("curator", 6),
        ],
    )
    def test_max_concurrent_tasks(
        self,
        repo: AgentProfileRepository,
        profile_id: str,
        expected_max: int,
    ):
        """Each profile has the expected max_concurrent_tasks."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert profile.max_concurrent_tasks == expected_max, (
            f"Profile '{profile_id}' has max_concurrent_tasks={profile.max_concurrent_tasks}, expected {expected_max}"
        )


class TestShippedProfilesSchemaValidation:
    """Verify all profiles pass YAML schema validation."""

    @pytest.mark.parametrize("profile_id", sorted(EXPECTED_PROFILE_IDS))
    def test_profile_passes_schema_validation(self, profile_id: str):
        """Each shipped profile passes the agent-profile JSON schema validation."""
        yaml_file = SHIPPED_DIR / f"{profile_id}.agent.yaml"
        assert yaml_file.exists(), f"Profile file not found: {yaml_file}"

        yaml = YAML(typ="safe")
        with yaml_file.open() as f:
            data = yaml.load(f)

        errors = validate_agent_profile_yaml(data)
        assert errors == [], f"Schema validation failed for '{profile_id}':\n" + "\n".join(f"  - {e}" for e in errors)


class TestShippedProfilesHierarchy:
    """Verify hierarchy validation returns no errors."""

    def test_validate_hierarchy_returns_no_errors(self, repo: AgentProfileRepository):
        """Shipped profiles have valid hierarchy (no cycles, no orphans)."""
        errors = repo.validate_hierarchy()
        assert errors == [], "Hierarchy validation failed:\n" + "\n".join(f"  - {e}" for e in errors)

    def test_specializes_from_targets_exist(self, all_profiles: list[AgentProfile]):
        """Any shipped profile that specializes from another must reference an existing shipped profile."""
        shipped_ids = {p.profile_id for p in all_profiles}
        for profile in all_profiles:
            if profile.specializes_from is not None:
                assert profile.specializes_from in shipped_ids, (
                    f"Shipped profile '{profile.profile_id}' specializes from "
                    f"'{profile.specializes_from}', which is not a shipped profile"
                )


class TestShippedProfilesCollaboration:
    """Verify collaboration contracts have required fields."""

    @pytest.mark.parametrize("profile_id", sorted(_AGENT_PROFILE_IDS))
    def test_collaboration_has_canonical_verbs(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile has at least one canonical verb."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert len(profile.collaboration.canonical_verbs) > 0, f"Profile '{profile_id}' has no canonical verbs"

    @pytest.mark.parametrize("profile_id", sorted(_AGENT_PROFILE_IDS))
    def test_collaboration_has_output_artifacts(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile defines at least one output artifact."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert len(profile.collaboration.output_artifacts) > 0, f"Profile '{profile_id}' has no output artifacts"

    @pytest.mark.parametrize("profile_id", sorted(_AGENT_PROFILE_IDS))
    def test_mode_defaults_are_non_empty(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile has at least one mode default."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert len(profile.mode_defaults) > 0, f"Profile '{profile_id}' has no mode defaults"

    @pytest.mark.parametrize("profile_id", sorted(_AGENT_PROFILE_IDS))
    def test_mode_defaults_have_use_case(self, repo: AgentProfileRepository, profile_id: str):
        """Each mode default has a non-empty use_case."""
        profile = repo.get(profile_id)
        assert profile is not None
        for mode in profile.mode_defaults:
            assert mode.use_case.strip(), f"Profile '{profile_id}' mode '{mode.mode}' has empty use_case"


class TestShippedProfilesContextSources:
    """Verify context sources are defined."""

    @pytest.mark.parametrize("profile_id", sorted(_AGENT_PROFILE_IDS))
    def test_context_sources_has_doctrine_layers(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile has at least one doctrine layer configured."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert len(profile.context_sources.doctrine_layers) > 0, (
            f"Profile '{profile_id}' has no doctrine layers in context_sources"
        )

    @pytest.mark.parametrize("profile_id", sorted(_AGENT_PROFILE_IDS))
    def test_directive_references_are_defined(self, repo: AgentProfileRepository, profile_id: str):
        """Each profile has at least one directive reference."""
        profile = repo.get(profile_id)
        assert profile is not None
        assert len(profile.directive_references) > 0, f"Profile '{profile_id}' has no directive references"
