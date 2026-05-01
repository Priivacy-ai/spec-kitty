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
roles:
  - implementer
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
roles:
  - architect
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

    # Child profile: python-pedro (specializes from generic implementer)
    (shipped / "python-pedro.agent.yaml").write_text("""profile-id: python-pedro
name: Python Pedro
purpose: Python implementation specialist
roles:
  - implementer
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
roles:
  - implementer
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
roles:
  - reviewer
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

    def test_load_shipped_and_project_profiles(self, shipped_profiles_dir: Path, project_profiles_dir: Path):
        """Both shipped and project profiles load correctly."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir)
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

    def test_filters_language_scoped_profiles_when_active_languages_do_not_match(self, tmp_path: Path) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()

        (shipped / "python-only.agent.yaml").write_text(
            """profile-id: python-only
name: Python Only
purpose: Python specialist
roles:
  - implementer
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
roles:
  - implementer
specialization:
  primary-focus: General implementation
""",
            encoding="utf-8",
        )

        repo = AgentProfileRepository(shipped_dir=shipped, active_languages=["typescript"])
        profile_ids = {profile.profile_id for profile in repo.list_all()}

        assert "generic" in profile_ids
        assert "python-only" not in profile_ids

    def test_keeps_language_scoped_profiles_when_active_languages_are_unset(self, tmp_path: Path) -> None:
        shipped = tmp_path / "shipped"
        shipped.mkdir()

        (shipped / "python-only.agent.yaml").write_text(
            """profile-id: python-only
name: Python Only
purpose: Python specialist
roles:
  - implementer
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
roles:
  - implementer
specialization:
  primary-focus: General implementation
""",
            encoding="utf-8",
        )

        repo = AgentProfileRepository(shipped_dir=shipped)
        profile_ids = {profile.profile_id for profile in repo.list_all()}

        assert "generic" in profile_ids
        assert "python-only" in profile_ids

    def test_skips_project_profiles_when_language_scope_does_not_match(self, shipped_profiles_dir: Path, tmp_path: Path) -> None:
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
roles:
  - reviewer
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
roles:
  - planner
routing-priority: 0
specialization:
  primary-focus: Testing
""")
        (shipped / "max-priority.agent.yaml").write_text("""profile-id: max-priority
name: Max Priority
purpose: Test
roles:
  - planner
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

    def test_field_level_merge_overrides_some_fields(self, shipped_profiles_dir: Path, project_profiles_dir: Path):
        """Project profile overrides specific fields, retains others from shipped."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir)
        pedro = repo.get("python-pedro")

        # Overridden fields from project
        assert pedro.routing_priority == 95  # From project override
        assert pedro.specialization.primary_focus == "Custom Python development"  # From project

        # Retained fields from shipped
        assert pedro.name == "Python Pedro"  # Not overridden, from shipped
        assert pedro.role == Role.IMPLEMENTER  # Not overridden, from shipped
        assert pedro.purpose == "Python implementation specialist"  # From shipped

    def test_project_only_profile_loads(self, shipped_profiles_dir: Path, project_profiles_dir: Path):
        """Project-only profile (not in shipped) loads correctly."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir)
        custom = repo.get("custom-reviewer")
        assert custom is not None
        assert custom.profile_id == "custom-reviewer"
        assert custom.role == Role.REVIEWER


class TestAgentProfileRepositoryExceptions:
    """Test exception handling and validation."""

    def test_invalid_yaml_skipped_with_warning(self, shipped_profiles_dir: Path, caplog: pytest.LogCaptureFixture):
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
roles:
  - implementer
specializes-from: profile-c
specialization:
  primary-focus: Testing
""")
        (shipped / "b.agent.yaml").write_text("""profile-id: profile-b
name: Profile B
purpose: Test
roles:
  - implementer
specializes-from: profile-a
specialization:
  primary-focus: Testing
""")
        (shipped / "c.agent.yaml").write_text("""profile-id: profile-c
name: Profile C
purpose: Test
roles:
  - implementer
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
roles:
  - implementer
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

    def test_find_best_match_no_context_returns_highest_priority(self, shipped_profiles_dir: Path):
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

    def test_save_creates_yaml_file(self, shipped_profiles_dir: Path, tmp_path: Path):
        """Save writes profile as YAML to project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project_dir)

        new_profile = AgentProfile(
            profile_id="new-tester",
            name="New Tester",
            purpose="Testing",
            roles=[Role.REVIEWER],
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
            roles=[Role.PLANNER],
            specialization={"primary_focus": "Testing"},
        )

        with pytest.raises(ValueError, match="project_dir"):
            repo.save(profile)

    def test_delete_removes_project_only_profile(self, shipped_profiles_dir: Path, project_profiles_dir: Path):
        """Delete removes project-only profile."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir)

        # custom-reviewer is project-only
        assert repo.get("custom-reviewer") is not None
        result = repo.delete("custom-reviewer")
        assert result is True
        assert repo.get("custom-reviewer") is None

    def test_delete_reverts_merged_profile_to_shipped(self, shipped_profiles_dir: Path, project_profiles_dir: Path):
        """Delete on merged profile reverts to shipped version."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project_profiles_dir)

        # python-pedro is merged (project overrides shipped)
        pedro_before = repo.get("python-pedro")
        assert pedro_before.routing_priority == 95  # Project override

        result = repo.delete("python-pedro")
        assert result is True

        # Should revert to shipped version
        pedro_after = repo.get("python-pedro")
        assert pedro_after is not None
        assert pedro_after.routing_priority == 90  # Back to shipped value

    def test_delete_nonexistent_returns_false(self, shipped_profiles_dir: Path, tmp_path: Path):
        """Delete nonexistent profile returns False."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project_dir)
        result = repo.delete("nonexistent")
        assert result is False

    def test_delete_without_project_dir_raises_error(self, shipped_profiles_dir: Path):
        """Delete without project_dir raises ValueError."""
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=None)

        with pytest.raises(ValueError, match="project_dir"):
            repo.delete("anything")


# ── Loader boundary tests ──────────────────────────────────────────────────


class TestAgentProfileRepositoryLoader:
    """Loader boundary: glob patterns, None data, missing profile-id, rglob depth."""

    def test_shipped_rglob_finds_profiles_in_subdirectory(self, tmp_path: Path):
        """Shipped loader uses rglob and finds profiles nested in subdirectories."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        sub = shipped / "sub"
        sub.mkdir()
        (sub / "nested.agent.yaml").write_text(
            "profile-id: nested\nname: Nested\npurpose: Test\nroles:\n  - implementer\nspecialization:\n  primary-focus: Testing\n"
        )
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        assert repo.get("nested") is not None

    def test_project_glob_does_not_find_profiles_in_subdirectory(self, shipped_profiles_dir: Path, tmp_path: Path):
        """Project loader uses glob (not rglob) and ignores nested profiles."""
        project = tmp_path / "project"
        sub = project / "sub"
        sub.mkdir(parents=True)
        (sub / "deep.agent.yaml").write_text("profile-id: deep\nname: Deep\npurpose: Test\nroles:\n  - implementer\nspecialization:\n  primary-focus: Testing\n")
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project)
        assert repo.get("deep") is None

    def test_non_agent_yaml_files_are_ignored(self, tmp_path: Path):
        """Files not matching *.agent.yaml pattern are silently ignored."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "notes.yaml").write_text("note: not a profile\n")
        (shipped / "profile.agent.yml").write_text("profile-id: wrong-ext\n")
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        assert repo.list_all() == []

    def test_empty_yaml_file_is_silently_skipped(self, tmp_path: Path):
        """Empty YAML (data is None) is skipped without raising."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "empty.agent.yaml").write_text("")
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        assert repo.list_all() == []

    def test_project_profile_missing_profile_id_emits_warning(self, shipped_profiles_dir: Path, tmp_path: Path):
        """Project YAML with no profile-id key emits UserWarning and is skipped."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "no-id.agent.yaml").write_text("name: No ID Profile\npurpose: Test\nroles:\n  - implementer\nspecialization:\n  primary-focus: Testing\n")
        with pytest.warns(UserWarning, match="no profile-id"):
            repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project)
        ids = {p.profile_id for p in repo.list_all()}
        assert "no-id" not in ids

    def test_invalid_shipped_yaml_emits_warning(self, tmp_path: Path):
        """Shipped YAML with parse error emits UserWarning and loads other profiles."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "good.agent.yaml").write_text(
            "profile-id: good\nname: Good\npurpose: Test\nroles:\n  - implementer\nspecialization:\n  primary-focus: Testing\n"
        )
        (shipped / "bad.agent.yaml").write_text("invalid: yaml: {")
        with pytest.warns(UserWarning):
            repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        assert repo.get("good") is not None
        assert repo.get("bad") is None

    def test_warning_fires_once_per_invalid_shipped_file(self, tmp_path: Path):
        """A single invalid shipped file produces exactly one UserWarning on load."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "bad.agent.yaml").write_text("invalid: yaml: {")
        with pytest.warns(UserWarning) as record:
            AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        user_warnings = [w for w in record if issubclass(w.category, UserWarning)]
        assert len(user_warnings) == 1

    def test_invalid_project_yaml_emits_warning(self, shipped_profiles_dir: Path, tmp_path: Path):
        """Project YAML with parse error emits UserWarning for that file."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "broken.agent.yaml").write_text("broken: yaml: {")
        with pytest.warns(UserWarning):
            AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project)


# ── _apply_excluding tests ─────────────────────────────────────────────────


class TestResolveProfileWithExcluding:
    """resolve_profile applies excluding from the leaf profile after union merge."""

    def _make_shipped_dir(self, tmp_path: Path) -> Path:
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "base.agent.yaml").write_text(
            "profile-id: base\nname: Base\npurpose: Base profile\n"
            "roles:\n  - implementer\nrouting-priority: 50\n"
            "capabilities:\n  - read\n  - write\n  - edit\n"
            "specialization:\n  primary-focus: Base implementation\n"
        )
        (shipped / "child.agent.yaml").write_text(
            "profile-id: child\nname: Child\npurpose: Child profile\n"
            "roles:\n  - implementer\nrouting-priority: 60\n"
            "specializes-from: base\n"
            "specialization:\n  primary-focus: Child implementation\n"
            "excluding:\n  capabilities:\n    - edit\n"
        )
        return shipped

    def test_excluding_dict_removes_specific_list_values(self, tmp_path: Path):
        """Child's excluding dict removes named values from parent list fields."""
        shipped = self._make_shipped_dir(tmp_path)
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        child = repo.resolve_profile("child")
        assert "edit" not in child.capabilities
        assert "read" in child.capabilities
        assert "write" in child.capabilities

    def test_excluding_list_removes_entire_field(self, tmp_path: Path):
        """Child's excluding list removes the entire named field."""
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "base2.agent.yaml").write_text(
            "profile-id: base2\nname: Base2\npurpose: Base2 profile\n"
            "roles:\n  - implementer\nrouting-priority: 50\n"
            "capabilities:\n  - read\n  - write\n"
            "specialization:\n  primary-focus: Base2 implementation\n"
        )
        (shipped / "child2.agent.yaml").write_text(
            "profile-id: child2\nname: Child2\npurpose: Child2 profile\n"
            "roles:\n  - implementer\nspecializes-from: base2\n"
            "specialization:\n  primary-focus: Child2 implementation\n"
            "excluding:\n  - capabilities\n"
        )
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        child = repo.resolve_profile("child2")
        assert child.capabilities == []


# ── Multi-field merge assertions ───────────────────────────────────────────


class TestFieldLevelMergeComplete:
    """Project override: verify every asserted field individually."""

    def test_project_override_preserves_all_non_overridden_shipped_fields(self, shipped_profiles_dir: Path, tmp_path: Path):
        """When project overrides only routing-priority, all other fields come from shipped."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "architect-alphonso.agent.yaml").write_text("profile-id: architect-alphonso\nrouting-priority: 99\n")
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project)
        profile = repo.get("architect-alphonso")
        assert profile.routing_priority == 99  # overridden
        assert profile.name == "Architect Alphonso"  # from shipped
        assert profile.role == Role.ARCHITECT  # from shipped
        assert profile.purpose == "System design and architecture"  # from shipped

    def test_project_new_profile_is_fully_independent(self, shipped_profiles_dir: Path, tmp_path: Path):
        """New project-only profile is completely independent; no shipped merge."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "standalone.agent.yaml").write_text(
            "profile-id: standalone\nname: Standalone\npurpose: Custom purpose\n"
            "roles:\n  - curator\nrouting-priority: 42\n"
            "specialization:\n  primary-focus: Standalone work\n"
        )
        repo = AgentProfileRepository(shipped_dir=shipped_profiles_dir, project_dir=project)
        profile = repo.get("standalone")
        assert profile is not None
        assert profile.profile_id == "standalone"
        assert profile.routing_priority == 42
        assert profile.role == Role.CURATOR


# ── Hierarchy ancestors multi-level ────────────────────────────────────────


class TestMultiLevelHierarchy:
    """Hierarchy traversal with chains longer than one level."""

    def _three_level_shipped(self, tmp_path: Path) -> Path:
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "root.agent.yaml").write_text("profile-id: root\nname: Root\npurpose: Root\nroles:\n  - implementer\nspecialization:\n  primary-focus: Root\n")
        (shipped / "mid.agent.yaml").write_text(
            "profile-id: mid\nname: Mid\npurpose: Mid\nroles:\n  - implementer\nspecializes-from: root\nspecialization:\n  primary-focus: Mid\n"
        )
        (shipped / "leaf.agent.yaml").write_text(
            "profile-id: leaf\nname: Leaf\npurpose: Leaf\nroles:\n  - implementer\nspecializes-from: mid\nspecialization:\n  primary-focus: Leaf\n"
        )
        return shipped

    def test_get_ancestors_returns_full_chain_nearest_first(self, tmp_path: Path):
        shipped = self._three_level_shipped(tmp_path)
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        ancestors = repo.get_ancestors("leaf")
        assert ancestors == ["mid", "root"]

    def test_get_children_returns_only_direct_children(self, tmp_path: Path):
        shipped = self._three_level_shipped(tmp_path)
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        root_children = repo.get_children("root")
        assert [p.profile_id for p in root_children] == ["mid"]
        # leaf is NOT a direct child of root
        assert "leaf" not in [p.profile_id for p in root_children]

    def test_resolve_profile_inherits_through_full_chain(self, tmp_path: Path):
        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "root.agent.yaml").write_text(
            "profile-id: root\nname: Root\npurpose: Root\nroles:\n  - implementer\n"
            "routing-priority: 10\ncapabilities:\n  - read\n"
            "specialization:\n  primary-focus: Root\n"
        )
        (shipped / "mid.agent.yaml").write_text(
            "profile-id: mid\nname: Mid\npurpose: Mid\nroles:\n  - implementer\n"
            "specializes-from: root\ncapabilities:\n  - write\n"
            "specialization:\n  primary-focus: Mid\n"
        )
        (shipped / "leaf.agent.yaml").write_text(
            "profile-id: leaf\nname: Leaf\npurpose: Leaf\nroles:\n  - implementer\n"
            "specializes-from: mid\ncapabilities:\n  - search\n"
            "routing-priority: 90\n"
            "specialization:\n  primary-focus: Leaf\n"
        )
        repo = AgentProfileRepository(shipped_dir=shipped, project_dir=None)
        resolved = repo.resolve_profile("leaf")
        # Leaf overrides root's routing-priority
        assert resolved.routing_priority == 90
        # Capabilities union: root=read, mid=write, leaf=search
        assert "read" in resolved.capabilities
        assert "write" in resolved.capabilities
        assert "search" in resolved.capabilities


# ── Multi-role routing ─────────────────────────────────────────────────────


from doctrine.agent_profiles.repository import _filter_candidates_by_role, _exact_id_signal  # noqa: E402


def _make_profile(profile_id: str, roles: list[str]) -> AgentProfile:
    return AgentProfile(
        **{
            "profile-id": profile_id,
            "name": f"Test {profile_id}",
            "purpose": "Test purpose",
            "roles": roles,
            "specialization": {"primary-focus": "Testing"},
        }
    )


class TestMultiRoleRouting:
    """Profiles with multiple roles — filter and signal behaviour."""

    def test_secondary_role_included_in_filter(self):
        """A profile with a secondary role passes the role filter for that role."""
        p = _make_profile("arch-alex", ["architect", "researcher"])
        assert p in _filter_candidates_by_role([p], "researcher")

    def test_primary_role_included_in_filter(self):
        p = _make_profile("arch-alex", ["architect", "researcher"])
        assert p in _filter_candidates_by_role([p], "architect")

    def test_unrelated_role_excluded_from_filter(self):
        p = _make_profile("arch-alex", ["architect", "researcher"])
        assert p not in _filter_candidates_by_role([p], "implementer")

    def test_primary_role_signal_is_1_0(self):
        p = _make_profile("arch-alex", ["architect", "researcher"])
        ctx = TaskContext(required_role=Role("architect"))
        assert _exact_id_signal(ctx, p) == 1.0

    def test_secondary_role_signal_is_0_5(self):
        p = _make_profile("arch-alex", ["architect", "researcher"])
        ctx = TaskContext(required_role=Role("researcher"))
        assert _exact_id_signal(ctx, p) == 0.5

    def test_no_match_signal_is_0_0(self):
        p = _make_profile("arch-alex", ["architect", "researcher"])
        ctx = TaskContext(required_role=Role("implementer"))
        assert _exact_id_signal(ctx, p) == 0.0

    def test_profile_id_match_signal_is_1_0(self):
        p = _make_profile("arch-alex", ["architect"])
        ctx = TaskContext(required_role=Role("arch-alex"))
        assert _exact_id_signal(ctx, p) == 1.0

    def test_no_required_role_signal_is_0_0(self):
        p = _make_profile("arch-alex", ["architect"])
        ctx = TaskContext(required_role=None)
        assert _exact_id_signal(ctx, p) == 0.0


class TestRoleLookup:
    """find_by_role checks all role positions; get() is keyed by profile_id."""

    def _repo_with(self, *profiles: AgentProfile) -> AgentProfileRepository:
        repo = AgentProfileRepository.__new__(AgentProfileRepository)
        repo._profiles = {p.profile_id: p for p in profiles}
        repo._hierarchy_index = None
        return repo

    def test_find_by_role_returns_primary_role_profile(self):
        p = _make_profile("arch-alex", ["architect"])
        repo = self._repo_with(p)
        assert p in repo.find_by_role("architect")

    def test_find_by_role_returns_secondary_role_profile(self):
        """find_by_role checks all roles, not just primary."""
        p = _make_profile("arch-bob", ["implementer", "architect"])
        repo = self._repo_with(p)
        assert p in repo.find_by_role("architect")

    def test_find_by_role_returns_multiple_profiles_sharing_a_role(self):
        """When several profiles list the same role, all are returned."""
        primary = _make_profile("arch-alex", ["architect"])
        secondary = _make_profile("arch-bob", ["implementer", "architect"])
        repo = self._repo_with(primary, secondary)

        result = repo.find_by_role("architect")
        assert len(result) == 2
        assert primary in result
        assert secondary in result

    def test_find_by_role_returns_empty_when_no_match(self):
        p = _make_profile("arch-alex", ["architect"])
        repo = self._repo_with(p)
        assert repo.find_by_role("implementer") == []

    def test_find_by_role_with_role_instance(self):
        """find_by_role accepts a Role instance."""
        p = _make_profile("impl-ivan", ["implementer"])
        repo = self._repo_with(p)
        assert p in repo.find_by_role(Role.IMPLEMENTER)

    def test_get_returns_profile_for_known_id(self):
        p = _make_profile("arch-alex", ["architect"])
        repo = self._repo_with(p)
        assert repo.get("arch-alex") is p

    def test_get_returns_none_for_unknown_id(self):
        repo = self._repo_with()
        assert repo.get("nonexistent") is None

    def test_get_is_unique_two_profiles_with_different_ids(self):
        """Different profile_ids never collide."""
        p1 = _make_profile("arch-alex", ["architect"])
        p2 = _make_profile("arch-bob", ["architect"])
        repo = self._repo_with(p1, p2)
        assert repo.get("arch-alex") is p1
        assert repo.get("arch-bob") is p2
        assert repo.get("arch-alex") is not p2
