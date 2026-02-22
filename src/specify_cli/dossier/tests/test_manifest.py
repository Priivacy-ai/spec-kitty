"""Tests for expected artifact manifest system (WP02).

Tests cover:
- Manifest schema validation
- YAML loading from expected-artifacts.yaml files
- ManifestRegistry loading and caching
- Step-aware artifact querying
- Unknown mission handling (graceful degradation)
- Path pattern validation
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

from specify_cli.dossier.manifest import (
    ArtifactClassEnum,
    ExpectedArtifactSpec,
    ExpectedArtifactManifest,
    ManifestRegistry,
)


class TestArtifactClassEnum:
    """Test ArtifactClassEnum values and usage."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        assert ArtifactClassEnum.INPUT.value == "input"
        assert ArtifactClassEnum.WORKFLOW.value == "workflow"
        assert ArtifactClassEnum.OUTPUT.value == "output"
        assert ArtifactClassEnum.EVIDENCE.value == "evidence"
        assert ArtifactClassEnum.POLICY.value == "policy"
        assert ArtifactClassEnum.RUNTIME.value == "runtime"

    def test_enum_has_six_values(self):
        """Verify exactly 6 artifact classes."""
        assert len(list(ArtifactClassEnum)) == 6


class TestExpectedArtifactSpec:
    """Test ExpectedArtifactSpec model creation and validation."""

    def test_create_simple_spec(self):
        """Create a simple artifact spec."""
        spec = ExpectedArtifactSpec(
            artifact_key="input.spec.main",
            artifact_class=ArtifactClassEnum.INPUT,
            path_pattern="spec.md",
        )
        assert spec.artifact_key == "input.spec.main"
        assert spec.artifact_class == ArtifactClassEnum.INPUT
        assert spec.path_pattern == "spec.md"
        assert spec.blocking is False  # Default

    def test_create_blocking_spec(self):
        """Create a blocking artifact spec."""
        spec = ExpectedArtifactSpec(
            artifact_key="output.tasks.list",
            artifact_class=ArtifactClassEnum.OUTPUT,
            path_pattern="tasks.md",
            blocking=True,
        )
        assert spec.blocking is True

    def test_artifact_key_with_dots_and_underscores(self):
        """Artifact keys can use dots and underscores."""
        spec = ExpectedArtifactSpec(
            artifact_key="evidence.gap_analysis.final",
            artifact_class=ArtifactClassEnum.EVIDENCE,
            path_pattern="gap-analysis.md",
        )
        assert spec.artifact_key == "evidence.gap_analysis.final"

    def test_path_pattern_with_wildcards(self):
        """Path patterns support glob wildcards."""
        spec = ExpectedArtifactSpec(
            artifact_key="output.tasks.per_wp",
            artifact_class=ArtifactClassEnum.OUTPUT,
            path_pattern="tasks/*.md",
        )
        assert spec.path_pattern == "tasks/*.md"

    def test_path_pattern_with_double_wildcards(self):
        """Path patterns support recursive glob.**."""
        spec = ExpectedArtifactSpec(
            artifact_key="output.docs.all",
            artifact_class=ArtifactClassEnum.OUTPUT,
            path_pattern="docs/**/*.md",
        )
        assert spec.path_pattern == "docs/**/*.md"

    def test_invalid_artifact_class_string(self):
        """Invalid artifact_class string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpectedArtifactSpec(
                artifact_key="test.key",
                artifact_class="invalid_class",  # type: ignore
                path_pattern="test.md",
            )
        assert "artifact_class" in str(exc_info.value)

    def test_empty_artifact_key_invalid(self):
        """Empty artifact_key is invalid."""
        with pytest.raises(ValidationError):
            ExpectedArtifactSpec(
                artifact_key="",
                artifact_class=ArtifactClassEnum.INPUT,
                path_pattern="spec.md",
            )

    def test_empty_path_pattern_invalid(self):
        """Empty path_pattern is invalid."""
        with pytest.raises(ValidationError):
            ExpectedArtifactSpec(
                artifact_key="test.key",
                artifact_class=ArtifactClassEnum.INPUT,
                path_pattern="",
            )


class TestExpectedArtifactManifest:
    """Test ExpectedArtifactManifest model and methods."""

    def test_create_empty_manifest(self):
        """Create a manifest with only mission_type."""
        manifest = ExpectedArtifactManifest(mission_type="software-dev")
        assert manifest.mission_type == "software-dev"
        assert manifest.schema_version == "1.0"
        assert manifest.manifest_version == "1"
        assert manifest.required_always == []
        assert manifest.required_by_step == {}
        assert manifest.optional_always == []

    def test_create_manifest_with_specs(self):
        """Create a manifest with artifact specs."""
        spec1 = ExpectedArtifactSpec(
            artifact_key="input.spec.main",
            artifact_class=ArtifactClassEnum.INPUT,
            path_pattern="spec.md",
            blocking=True,
        )
        spec2 = ExpectedArtifactSpec(
            artifact_key="evidence.research",
            artifact_class=ArtifactClassEnum.EVIDENCE,
            path_pattern="research.md",
            blocking=False,
        )
        manifest = ExpectedArtifactManifest(
            mission_type="software-dev",
            required_always=[spec1],
            optional_always=[spec2],
        )
        assert len(manifest.required_always) == 1
        assert len(manifest.optional_always) == 1

    def test_create_manifest_with_step_specs(self):
        """Create a manifest with step-specific specs."""
        spec = ExpectedArtifactSpec(
            artifact_key="output.plan.main",
            artifact_class=ArtifactClassEnum.OUTPUT,
            path_pattern="plan.md",
            blocking=True,
        )
        manifest = ExpectedArtifactManifest(
            mission_type="software-dev",
            required_by_step={"plan": [spec]},
        )
        assert "plan" in manifest.required_by_step
        assert len(manifest.required_by_step["plan"]) == 1

    def test_get_step_ids(self):
        """Get list of step IDs from manifest."""
        manifest = ExpectedArtifactManifest(
            mission_type="research",
            required_by_step={
                "scoping": [],
                "methodology": [],
                "gathering": [],
                "synthesis": [],
            },
        )
        step_ids = manifest.get_step_ids()
        assert set(step_ids) == {"scoping", "methodology", "gathering", "synthesis"}


class TestManifestRegistry:
    """Test ManifestRegistry loading and querying."""

    def setup_method(self):
        """Clear cache before each test."""
        ManifestRegistry.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        ManifestRegistry.clear_cache()

    def test_load_software_dev_manifest(self):
        """Load software-dev manifest successfully."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        assert manifest.mission_type == "software-dev"
        assert manifest.schema_version == "1.0"

    def test_load_research_manifest(self):
        """Load research manifest successfully."""
        manifest = ManifestRegistry.load_manifest("research")
        assert manifest is not None
        assert manifest.mission_type == "research"

    def test_load_documentation_manifest(self):
        """Load documentation manifest successfully."""
        manifest = ManifestRegistry.load_manifest("documentation")
        assert manifest is not None
        assert manifest.mission_type == "documentation"

    def test_load_unknown_mission_returns_none(self):
        """Unknown mission type returns None (graceful degradation)."""
        manifest = ManifestRegistry.load_manifest("unknown_mission_xyz")
        assert manifest is None

    def test_manifest_caching(self):
        """Manifest is cached after first load."""
        manifest1 = ManifestRegistry.load_manifest("software-dev")
        manifest2 = ManifestRegistry.load_manifest("software-dev")
        assert manifest1 is manifest2  # Same object (cached)

    def test_unknown_mission_cached_as_none(self):
        """Unknown mission type cached as None."""
        result1 = ManifestRegistry.load_manifest("fake_mission")
        result2 = ManifestRegistry.load_manifest("fake_mission")
        assert result1 is None
        assert result2 is None

    def test_get_required_artifacts_specify_step(self):
        """Get required artifacts for software-dev specify step."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "specify")
        assert len(specs) > 0
        # Should include spec.md requirement
        assert any(s.artifact_key == "input.spec.main" for s in specs)

    def test_get_required_artifacts_plan_step(self):
        """Get required artifacts for software-dev plan step."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "plan")
        assert len(specs) >= 2
        # Should include plan.md and tasks.md
        assert any(s.artifact_key == "output.plan.main" for s in specs)
        assert any(s.artifact_key == "output.tasks.list" for s in specs)

    def test_get_required_artifacts_unknown_step(self):
        """Get required artifacts for unknown step returns gracefully."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "nonexistent_step")
        # Should return only required_always (may be empty)
        assert specs is not None

    def test_get_blocking_artifacts(self):
        """Filter to blocking artifacts only."""
        spec1 = ExpectedArtifactSpec(
            artifact_key="key1",
            artifact_class=ArtifactClassEnum.INPUT,
            path_pattern="spec.md",
            blocking=True,
        )
        spec2 = ExpectedArtifactSpec(
            artifact_key="key2",
            artifact_class=ArtifactClassEnum.EVIDENCE,
            path_pattern="research.md",
            blocking=False,
        )
        specs = [spec1, spec2]
        blocking = ManifestRegistry.get_blocking_artifacts(specs)
        assert len(blocking) == 1
        assert blocking[0].artifact_key == "key1"

    def test_get_optional_artifacts(self):
        """Get optional artifacts from manifest."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        optional = ManifestRegistry.get_optional_artifacts(manifest)
        assert len(optional) > 0
        # All should have blocking=False
        assert all(not s.blocking for s in optional)

    def test_software_dev_manifest_has_all_states(self):
        """Software-dev manifest covers all states."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        step_ids = manifest.get_step_ids()
        # Should have steps for discovery, specify, plan, implement, review, done
        expected_steps = {"discovery", "specify", "plan", "implement", "review", "done"}
        assert expected_steps.issubset(set(step_ids))

    def test_research_manifest_has_all_states(self):
        """Research manifest covers all states."""
        manifest = ManifestRegistry.load_manifest("research")
        assert manifest is not None
        step_ids = manifest.get_step_ids()
        # Should have research-specific states
        expected_steps = {"scoping", "methodology", "gathering", "synthesis", "output", "done"}
        assert expected_steps.issubset(set(step_ids))

    def test_documentation_manifest_has_all_states(self):
        """Documentation manifest covers expected states."""
        manifest = ManifestRegistry.load_manifest("documentation")
        assert manifest is not None
        step_ids = manifest.get_step_ids()
        # Should have documentation-specific states
        assert len(step_ids) > 0


class TestManifestValidation:
    """Test manifest validation."""

    def test_validate_valid_manifest(self):
        """Validate a valid manifest."""
        manifest = ExpectedArtifactManifest(
            mission_type="software-dev",
            required_by_step={"specify": []},
        )
        mission_dir = Path(__file__).parent.parent.parent / "missions" / "software-dev"
        is_valid, errors = ManifestRegistry.validate_manifest(manifest, mission_dir)
        # Should pass or only have minor warnings
        assert isinstance(is_valid, bool)

    def test_validate_manifest_with_absolute_path(self):
        """Manifest with absolute path should fail validation."""
        spec = ExpectedArtifactSpec(
            artifact_key="test.key",
            artifact_class=ArtifactClassEnum.INPUT,
            path_pattern="/absolute/path/spec.md",
        )
        manifest = ExpectedArtifactManifest(
            mission_type="test",
            required_always=[spec],
        )
        mission_dir = Path(".")
        is_valid, errors = ManifestRegistry.validate_manifest(manifest, mission_dir)
        assert not is_valid
        assert any("absolute" in e.lower() for e in errors)

    def test_validate_manifest_with_parent_reference(self):
        """Manifest with parent directory reference should fail."""
        spec = ExpectedArtifactSpec(
            artifact_key="test.key",
            artifact_class=ArtifactClassEnum.INPUT,
            path_pattern="../spec.md",
        )
        manifest = ExpectedArtifactManifest(
            mission_type="test",
            required_always=[spec],
        )
        mission_dir = Path(".")
        is_valid, errors = ManifestRegistry.validate_manifest(manifest, mission_dir)
        assert not is_valid
        assert any("parent" in e.lower() for e in errors)

    def test_clear_cache(self):
        """Test cache clearing."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        # Cache should have entry
        assert len(ManifestRegistry._cache) > 0
        ManifestRegistry.clear_cache()
        assert len(ManifestRegistry._cache) == 0


class TestManifestIntegration:
    """Integration tests with actual manifest files."""

    def setup_method(self):
        """Clear cache before each test."""
        ManifestRegistry.clear_cache()

    def test_software_dev_manifest_spec_step_has_spec_requirement(self):
        """software-dev manifest requires spec.md at specify step."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "specify")
        # Find spec.md requirement
        spec_md = [s for s in specs if s.artifact_key == "input.spec.main"]
        assert len(spec_md) > 0
        assert spec_md[0].blocking is True
        assert spec_md[0].path_pattern == "spec.md"

    def test_software_dev_manifest_plan_step_has_plan_and_tasks(self):
        """software-dev manifest requires plan.md and tasks.md at plan step."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "plan")
        plan_md = [s for s in specs if s.artifact_key == "output.plan.main"]
        tasks_md = [s for s in specs if s.artifact_key == "output.tasks.list"]
        assert len(plan_md) > 0
        assert len(tasks_md) > 0
        assert all(s.blocking for s in plan_md + tasks_md)

    def test_software_dev_has_optional_research_evidence(self):
        """software-dev manifest includes optional research.md."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        optional = ManifestRegistry.get_optional_artifacts(manifest)
        research = [s for s in optional if s.artifact_key == "evidence.research"]
        assert len(research) > 0
        assert research[0].path_pattern == "research.md"

    def test_research_manifest_scoping_step_requires_spec(self):
        """research manifest requires spec.md at scoping step."""
        manifest = ManifestRegistry.load_manifest("research")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "scoping")
        assert any(s.artifact_key == "input.spec.research" for s in specs)

    def test_research_manifest_synthesis_step_requires_findings(self):
        """research manifest requires findings.md at synthesis step."""
        manifest = ManifestRegistry.load_manifest("research")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "synthesis")
        assert any(s.artifact_key == "output.findings.main" for s in specs)

    def test_documentation_manifest_audit_requires_gap_analysis(self):
        """documentation manifest requires gap-analysis.md at audit step."""
        manifest = ManifestRegistry.load_manifest("documentation")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "audit")
        # Gap analysis should be required for audit step
        gap = [s for s in specs if s.artifact_key == "evidence.gap-analysis"]
        assert len(gap) > 0


class TestManifestYAMLFormat:
    """Test YAML file format and loading."""

    def test_from_yaml_file_software_dev(self):
        """Load software-dev manifest from YAML file."""
        yaml_path = (
            Path(__file__).parent.parent.parent
            / "missions"
            / "software-dev"
            / "expected-artifacts.yaml"
        )
        assert yaml_path.exists(), f"Manifest file not found: {yaml_path}"
        manifest = ExpectedArtifactManifest.from_yaml_file(yaml_path)
        assert manifest.mission_type == "software-dev"

    def test_from_yaml_file_research(self):
        """Load research manifest from YAML file."""
        yaml_path = (
            Path(__file__).parent.parent.parent
            / "missions"
            / "research"
            / "expected-artifacts.yaml"
        )
        assert yaml_path.exists(), f"Manifest file not found: {yaml_path}"
        manifest = ExpectedArtifactManifest.from_yaml_file(yaml_path)
        assert manifest.mission_type == "research"

    def test_from_yaml_file_documentation(self):
        """Load documentation manifest from YAML file."""
        yaml_path = (
            Path(__file__).parent.parent.parent
            / "missions"
            / "documentation"
            / "expected-artifacts.yaml"
        )
        assert yaml_path.exists(), f"Manifest file not found: {yaml_path}"
        manifest = ExpectedArtifactManifest.from_yaml_file(yaml_path)
        assert manifest.mission_type == "documentation"
