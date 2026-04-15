"""
Test suite for AgentProfileRepository.

Follows ATDD approach with ZOMBIES ordering:
- Zero: Empty repository
- One: Single profile
- Many: Multiple profiles from shipped + project
- Boundary: Edge cases (routing_priority 0/100, missing dirs)
- Interface: Field-level merge, YAML round-trip
- Exceptions: Invalid YAML, cycles, orphans
- Simple: Query methods, hierarchy traversal, matching
"""

from pathlib import Path

import pytest

from doctrine.agent_profiles.profile import AgentProfile, Role, TaskContext
from doctrine.agent_profiles.repository import AgentProfileRepository
pytestmark = [pytest.mark.fast, pytest.mark.doctrine]



@pytest.fixture
def minimal_profile_yaml() -> str:
    """Minimal valid agent profile YAML."""
    return """profile-id: test-profile
name: Test Profile
purpose: Testing purpose
role: implementer
specialization:
  primary-focus: Testing
"""


@pytest.fixture
def shipped_profiles_dir(tmp_path: Path) -> Path:
    """Create temporary shipped profiles directory with test fixtures."""
    shipped = tmp_path / "shipped"
    shipped.mkdir()

    # Parent profile: architect
    (shipped / "architect-alphonso.agent.yaml").write_text("""profile-id: architect-alphonso
name: Architect Alphonso
purpose: System design and architecture
role: architect
routing-priority: 80
specialization:
  primary-focus: Architecture and design
  domain-keywords:
    - architecture
    - design
    - system
specialization-context:
  languages:
    - python
    - typescript
  frameworks:
    - django
  file-patterns:
    - "architecture/**/*.md"
  domain-keywords:
    - design patterns
    - system architecture
""")

    # Child profile: python-implementer (specializes from generic implementer)
    (shipped / "python-pedro.agent.yaml").write_text("""profile-id: python-pedro
name: Python Pedro
purpose: Python implementation specialist
role: implementer
routing-priority: 90
specializes-from: generic-implementer
specialization:
  primary-focus: Python development
  domain-keywords:
    - python
    - django
    - pytest
specialization-context:
  languages:
    - python
  frameworks:
    - django
    - pytest
  file-patterns:
    - "**/*.py"
  domain-keywords:
    - python
    - backend
""")

    # Generic implementer (root)
    (shipped / "generic-implementer.agent.yaml").write_text("""profile-id: generic-implementer
name: Generic Implementer
purpose: General-purpose implementation
role: implementer
routing-priority: 50
specialization:
  primary-focus: General implementation
""")

    return shipped


@pytest.fixture
def project_profiles_dir(tmp_path: Path) -> Path:
    """Create temporary project profiles directory."""
    project = tmp_path / "project"
    project.mkdir()

    # Override python-pedro with higher priority
    (project / "python-pedro.agent.yaml").write_text("""profile-id: python-pedro
routing-priority: 95
specialization:
  primary-focus: Custom Python development
""")

    # New custom profile
    (project / "custom-reviewer.agent.yaml").write_text("""profile-id: custom-reviewer
name: Custom Reviewer
purpose: Code review specialist
role: reviewer
routing-priority: 70
specialization:
  primary-focus: Code review
""")

    return project


class TestAgentProfileRepositoryZero:
    """Test zero/empty cases."""

    def test_empty_repository_no_dirs(self):
        """Empty repository with no shipped or project dirs returns empty list."""
        repo = AgentProfileRepository(shipped_dir=Path("/nonexistent"), project_dir=None)
        assert repo.list_all() == []

    def test_get_nonexistent_profile_returns_none(self, shipped_profiles_dir: Path):
        """Getting nonexistent profile returns None."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        assert repo.get("nonexistent") is None


class TestAgentProfileRepositoryOne:
    """Test single profile cases."""

    def test_load_single_shipped_profile(self, shipped_profiles_dir: Path):
        """Single shipped profile loads correctly."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        profiles = repo.list_all()
        assert len(profiles) == 3  # We have 3 shipped profiles

        alphonso = repo.get("architect-alphonso")
        assert alphonso is not None
        assert alphonso.name == "Architect Alphonso"
        assert alphonso.role == Role.ARCHITECT
        assert alphonso.routing_priority == 80

    def test_get_existing_profile(self, shipped_profiles_dir: Path):
        """Get returns correct profile by ID."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        profile = repo.get("python-pedro")
        assert profile is not None
        assert profile.profile_id == "python-pedro"
        assert profile.name == "Python Pedro"


class TestAgentProfileRepositoryMany:
    """Test multiple profiles."""

    def test_load_multiple_shipped_profiles(self, shipped_profiles_dir: Path):
        """Multiple shipped profiles load correctly."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        profiles = repo.list_all()
        assert len(profiles) == 3
        profile_ids = {p.profile_id for p in profiles}
        assert profile_ids == {"architect-alphonso", "python-pedro", "generic-implementer"}

    def test_load_shipped_and_project_profiles(
        self, shipped_profiles_dir: Path, project_profiles_dir: Path
    ):
        """Both shipped and project profiles load correctly."""
        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir
        )
        profiles = repo.list_all()
        # 3 shipped + 1 new project - 1 override = 4 total
        assert len(profiles) == 4
        profile_ids = {p.profile_id for p in profiles}
        assert profile_ids == {
            "architect-alphonso",
            "python-pedro",
            "generic-implementer",
            "custom-reviewer",
        }

    def test_filters_language_scoped_profiles_when_active_languages_do_not_match(
        self, tmp_path: Path
    ) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()

        (shipped / "python-only.agent.yaml").write_text(
            """profile-id: python-only
name: Python Only
purpose: Python specialist
role: implementer
applies_to_languages:
  - python
specialization:
  primary-focus: Python implementation
""",
            encoding="utf-8",
        )
        (shipped / "generic.agent.yaml").write_text(
            """profile-id: generic
name: Generic
purpose: Generic specialist
role: implementer
specialization:
  primary-focus: General implementation
""",
            encoding="utf-8",
        )

        repo = AgentProfileRepository(shipped_dir=shipped, active_languages=["typescript"])
        profile_ids = {profile.profile_id for profile in repo.list_all()}

        assert "generic" in profile_ids
        assert "python-only" not in profile_ids

    def test_keeps_language_scoped_profiles_when_active_languages_are_unset(
        self, tmp_path: Path
    ) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()

        (shipped / "python-only.agent.yaml").write_text(
            """profile-id: python-only
name: Python Only
purpose: Python specialist
role: implementer
applies_to_languages:
  - python
specialization:
  primary-focus: Python implementation
""",
            encoding="utf-8",
        )
        (shipped / "generic.agent.yaml").write_text(
            """profile-id: generic
name: Generic
purpose: Generic specialist
role: implementer
specialization:
  primary-focus: General implementation
""",
            encoding="utf-8",
        )

        repo = AgentProfileRepository(shipped_dir=shipped)
        profile_ids = {profile.profile_id for profile in repo.list_all()}

        assert "generic" in profile_ids
        assert "python-only" in profile_ids

    def test_skips_project_profiles_when_language_scope_does_not_match(
        self, shipped_profiles_dir: Path, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "python-pedro.agent.yaml").write_text(
            """profile-id: python-pedro
applies_to_languages:
  - python
routing-priority: 99
""",
            encoding="utf-8",
        )
        (project / "typescript-reviewer.agent.yaml").write_text(
            """profile-id: typescript-reviewer
name: TypeScript Reviewer
purpose: Review TypeScript changes
role: reviewer
applies_to_languages:
  - typescript
specialization:
  primary-focus: TypeScript review
""",
            encoding="utf-8",
        )

        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir,
            project_dir=project,
            active_languages=["go"],
        )

        python_pedro = repo.get("python-pedro")
        assert python_pedro is not None
        assert python_pedro.routing_priority == 90
        assert repo.get("typescript-reviewer") is None


class TestAgentProfileRepositoryBoundaries:
    """Test boundary conditions."""

    def test_routing_priority_boundaries(self, shipped_profiles_dir: Path):
        """Profiles with routing_priority 0 and 100 are valid."""
        shipped = shipped_profiles_dir
        (shipped / "min-priority.agent.yaml").write_text("""profile-id: min-priority
name: Min Priority
purpose: Test
role: planner
routing-priority: 0
specialization:
  primary-focus: Testing
""")
        (shipped / "max-priority.agent.yaml").write_text("""profile-id: max-priority
name: Max Priority
purpose: Test
role: planner
routing-priority: 100
specialization:
  primary-focus: Testing
""")

        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        min_prof = repo.get("min-priority")
        max_prof = repo.get("max-priority")
        assert min_prof.routing_priority == 0
        assert max_prof.routing_priority == 100


class TestAgentProfileRepositoryInterface:
    """Test interface contracts and field-level merge."""

    def test_field_level_merge_overrides_some_fields(
        self, shipped_profiles_dir: Path, project_profiles_dir: Path
    ):
        """Project profile overrides specific fields, retains others from shipped."""
        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir
        )
        pedro = repo.get("python-pedro")

        # Overridden fields from project
        assert pedro.routing_priority == 95  # From project override
        assert pedro.specialization.primary_focus == "Custom Python development"  # From project

        # Retained fields from shipped
        assert pedro.name == "Python Pedro"  # Not overridden, from shipped
        assert pedro.role == Role.IMPLEMENTER  # Not overridden, from shipped
        assert pedro.purpose == "Python implementation specialist"  # From shipped

    def test_project_only_profile_loads(
        self, shipped_profiles_dir: Path, project_profiles_dir: Path
    ):
        """Project-only profile (not in shipped) loads correctly."""
        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir
        )
        custom = repo.get("custom-reviewer")
        assert custom is not None
        assert custom.profile_id == "custom-reviewer"
        assert custom.role == Role.REVIEWER


class TestAgentProfileRepositoryExceptions:
    """Test exception handling and validation."""

    def test_invalid_yaml_skipped_with_warning(
        self, shipped_profiles_dir: Path, caplog: pytest.LogCaptureFixture
    ):
        """Invalid YAML file is skipped and warning is logged."""
        (shipped_profiles_dir / "invalid.agent.yaml").write_text("invalid: yaml: {")

        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        # Should load valid profiles, skip invalid
        assert len(repo.list_all()) == 3  # Only the 3 valid profiles

    def test_cycle_detection(self, tmp_path: Path):
        """Validate hierarchy detects cycles."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()

        # Create cycle: A → B → C → A
        (shipped / "a.agent.yaml").write_text("""profile-id: profile-a
name: Profile A
purpose: Test
role: implementer
specializes-from: profile-c
specialization:
  primary-focus: Testing
""")
        (shipped / "b.agent.yaml").write_text("""profile-id: profile-b
name: Profile B
purpose: Test
role: implementer
specializes-from: profile-a
specialization:
  primary-focus: Testing
""")
        (shipped / "c.agent.yaml").write_text("""profile-id: profile-c
name: Profile C
purpose: Test
role: implementer
specializes-from: profile-b
specialization:
  primary-focus: Testing
""")

        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        errors = repo.validate_hierarchy()
        assert len(errors) > 0
        assert any("cycle" in err.lower() for err in errors)

    def test_orphaned_reference_warning(self, tmp_path: Path):
        """Validate hierarchy detects orphaned references."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()

        (shipped / "orphan.agent.yaml").write_text("""profile-id: orphan-child
name: Orphan Child
purpose: Test
role: implementer
specializes-from: nonexistent-parent
specialization:
  primary-focus: Testing
""")

        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        errors = repo.validate_hierarchy()
        assert len(errors) > 0
        assert any("orphan" in err.lower() or "nonexistent" in err.lower() for err in errors)


class TestAgentProfileRepositorySimple:
    """Test simple query operations."""

    def test_find_by_role_enum(self, shipped_profiles_dir: Path):
        """Find profiles by role enum."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        implementers = repo.find_by_role(Role.IMPLEMENTER)
        assert len(implementers) == 2  # python-pedro and generic-implementer
        ids = {p.profile_id for p in implementers}
        assert ids == {"python-pedro", "generic-implementer"}

    def test_find_by_role_string(self, shipped_profiles_dir: Path):
        """Find profiles by role string."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        implementers = repo.find_by_role("implementer")
        assert len(implementers) == 2

    def test_find_by_role_returns_empty_for_nonexistent(self, shipped_profiles_dir: Path):
        """Find by role returns empty list for nonexistent role."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        assert repo.find_by_role("nonexistent") == []


class TestAgentProfileRepositoryHierarchy:
    """Test hierarchy traversal."""

    def test_get_children(self, shipped_profiles_dir: Path):
        """Get children returns direct descendants."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        children = repo.get_children("generic-implementer")
        assert len(children) == 1
        assert children[0].profile_id == "python-pedro"

    def test_get_children_of_leaf_returns_empty(self, shipped_profiles_dir: Path):
        """Get children of leaf profile returns empty list."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        assert repo.get_children("python-pedro") == []

    def test_get_ancestors(self, shipped_profiles_dir: Path):
        """Get ancestors returns parent chain."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        ancestors = repo.get_ancestors("python-pedro")
        assert ancestors == ["generic-implementer"]

    def test_get_ancestors_of_root_returns_empty(self, shipped_profiles_dir: Path):
        """Get ancestors of root profile returns empty list."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        assert repo.get_ancestors("generic-implementer") == []

    def test_get_hierarchy_tree(self, shipped_profiles_dir: Path):
        """Get hierarchy tree returns nested structure."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        tree = repo.get_hierarchy_tree()

        # Should have 2 roots: architect-alphonso and generic-implementer
        assert "architect-alphonso" in tree
        assert "generic-implementer" in tree

        # generic-implementer should have python-pedro as child
        assert "python-pedro" in tree["generic-implementer"]["children"]


class TestAgentProfileRepositoryMatching:
    """Test context-based profile matching."""

    def test_find_best_match_with_language(self, shipped_profiles_dir: Path):
        """Find best match returns specialist for matching language."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        context = TaskContext(
            task_type="implement",
            language="python",
            complexity="medium",
        )
        match = repo.find_best_match(context)
        assert match is not None
        assert match.profile_id == "python-pedro"  # Specialist with higher priority

    def test_find_best_match_no_context_returns_highest_priority(
        self, shipped_profiles_dir: Path
    ):
        """Find best match with no context returns highest routing_priority."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        context = TaskContext(task_type="implement", complexity="medium")
        match = repo.find_best_match(context)
        assert match is not None
        # python-pedro has routing_priority 90, highest among all
        assert match.profile_id == "python-pedro"

    def test_find_best_match_with_workload_penalty(self, shipped_profiles_dir: Path):
        """Workload penalty reduces score for busy profiles."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        context = TaskContext(
            task_type="implement",
            language="python",
            complexity="medium",
            current_workload=5,  # 5+ tasks = 0.70 penalty
        )
        match = repo.find_best_match(context)
        # Should still match python-pedro despite penalty
        assert match is not None

    def test_find_best_match_returns_none_for_zero_profiles(self):
        """Find best match returns None when repository is empty."""
        repo = AgentProfileRepository(shipped_dir=Path("/nonexistent"), project_dir=None)
        context = TaskContext(task_type="implement", complexity="medium")
        assert repo.find_best_match(context) is None


class TestAgentProfileRepositorySaveDelete:
    """Test save and delete operations."""

    def test_save_creates_yaml_file(
        self, shipped_profiles_dir: Path, tmp_path: Path
    ):
        """Save writes profile as YAML to project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir, project_dir=project_dir
        )

        new_profile = AgentProfile(
            profile_id="new-tester",
            name="New Tester",
            purpose="Testing",
            role=Role.REVIEWER,
            specialization={"primary_focus": "Test review"},
        )

        repo.save(new_profile)

        # Verify file exists
        yaml_file = project_dir / "new-tester.agent.yaml"
        assert yaml_file.exists()

        # Verify profile is in repository
        assert repo.get("new-tester") is not None

    def test_save_without_project_dir_raises_error(self, shipped_profiles_dir: Path):
        """Save without project_dir raises ValueError."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)
        profile = AgentProfile(
            profile_id="test",
            name="Test",
            purpose="Test",
            role=Role.PLANNER,
            specialization={"primary_focus": "Testing"},
        )

        with pytest.raises(ValueError, match="project_dir"):
            repo.save(profile)

    def test_delete_removes_project_only_profile(
        self, shipped_profiles_dir: Path, project_profiles_dir: Path
    ):
        """Delete removes project-only profile."""
        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir
        )

        # custom-reviewer is project-only
        assert repo.get("custom-reviewer") is not None
        result = repo.delete("custom-reviewer")
        assert result is True
        assert repo.get("custom-reviewer") is None

    def test_delete_reverts_merged_profile_to_shipped(
        self, shipped_profiles_dir: Path, project_profiles_dir: Path
    ):
        """Delete on merged profile reverts to shipped version."""
        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir
        )

        # python-pedro is merged (project overrides shipped)
        pedro_before = repo.get("python-pedro")
        assert pedro_before.routing_priority == 95  # Project override

        result = repo.delete("python-pedro")
        assert result is True

        # Should revert to shipped version
        pedro_after = repo.get("python-pedro")
        assert pedro_after is not None
        assert pedro_after.routing_priority == 90  # Back to shipped value

    def test_delete_nonexistent_returns_false(
        self, shipped_profiles_dir: Path, tmp_path: Path
    ):
        """Delete nonexistent profile returns False."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        repo = AgentProfileRepository(
            shipped_dir=shipped_profiles_dir, project_dir=project_dir
        )
        result = repo.delete("nonexistent")
        assert result is False

    def test_delete_without_project_dir_raises_error(self, shipped_profiles_dir: Path):
        """Delete without project_dir raises ValueError."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)

        with pytest.raises(ValueError, match="project_dir"):
            repo.delete("anything")
