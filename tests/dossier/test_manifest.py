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
from typing import Optional
from pydantic import ValidationError
from ruamel.yaml import YAML

from specify_cli.dossier.manifest import (
    ArtifactClassEnum,
    ExpectedArtifactSpec,
    ExpectedArtifactManifest,
    ManifestRegistry,
)


pytestmark = [pytest.mark.unit, pytest.mark.fast]

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
        assert frozenset(m.name for m in ArtifactClassEnum) == frozenset(
            {"INPUT", "WORKFLOW", "OUTPUT", "EVIDENCE", "POLICY", "RUNTIME"}
        )


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
        assert [s.artifact_key for s in manifest.required_always] == ["input.spec.main"]
        assert [s.artifact_key for s in manifest.optional_always] == ["evidence.research"]

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
        assert [b.artifact_key for b in blocking] == ["key1"]

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

    def test_software_dev_implement_requires_analysis_report(self):
        """software-dev manifest requires analysis-report.md before implement."""
        manifest = ManifestRegistry.load_manifest("software-dev")
        assert manifest is not None
        specs = ManifestRegistry.get_required_artifacts(manifest, "implement")
        report = [s for s in specs if s.artifact_key == "evidence.analysis-report"]
        assert len(report) > 0
        assert report[0].blocking is True
        assert report[0].path_pattern == "analysis-report.md"

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
            / "packs"
            / "built-in"
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
            / "packs"
            / "built-in"
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
            / "packs"
            / "built-in"
            / "missions"
            / "documentation"
            / "expected-artifacts.yaml"
        )
        assert yaml_path.exists(), f"Manifest file not found: {yaml_path}"
        manifest = ExpectedArtifactManifest.from_yaml_file(yaml_path)
        assert manifest.mission_type == "documentation"


# ---------------------------------------------------------------------------
# T027 (WP05, FR-008 + cache-key fix): `ManifestRegistry.load_manifest`
# org-tier override, and the `(mission_type, org_roots)` cache-key regression
# that closes the process-global-cache-shadows-across-projects defect.
# ---------------------------------------------------------------------------


def _write_org_pack_config(repo_root: Path, *, packs: list[tuple[str, Path]]) -> None:
    """Write ``<repo_root>/.kittify/config.yaml`` with a ``doctrine.org.packs``
    registry only -- no mission-type-activation block, since
    ``ManifestRegistry.load_manifest`` reads org packs directly via
    ``resolve_org_roots``/``resolve_org_expected_artifacts``, not through the
    `existing_mission_types()` activation gate `_resolve_expected_artifacts_slot`
    (charter side) goes through.
    """
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if packs:
        lines += ["doctrine:", "  org:", "    packs:"]
        for name, local_path in packs:
            lines.append(f"      - name: {name}")
            lines.append(f"        local_path: {local_path}")
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_org_manifest(org_root: Path, mission_type: str, data: dict) -> None:
    """Write ``<org_root>/<mission_type>/expected-artifacts.yaml`` (raw-root
    shape, C-4 -- see ``test_org_expected_artifacts.py``'s module docstring).
    """
    target_dir = org_root / mission_type
    target_dir.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with (target_dir / "expected-artifacts.yaml").open("w") as fh:
        yaml.dump(data, fh)


class TestManifestRegistryOrgTier:
    """T027: org-tier override through `ManifestRegistry.load_manifest`, plus
    the SC-005 byte-identical-no-override proof and the cache-key regression
    this WP's fix exists to close.
    """

    def setup_method(self):
        """Clear cache before each test."""
        ManifestRegistry.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        ManifestRegistry.clear_cache()

    def test_org_override_delta_through_load_manifest(self, tmp_path: Path) -> None:
        """Mirrors T026's shape but through `ManifestRegistry.load_manifest`
        with a `repo_root` argument: a delta in `required_always`, not
        merely "no exception."
        """
        before = ManifestRegistry.load_manifest("software-dev")
        assert before is not None
        before_count = len(before.required_always)

        project_root = tmp_path / "project"
        project_root.mkdir()
        org_root = tmp_path / "org-pack"
        _write_org_manifest(
            org_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "org-1",
                "required_always": [
                    {
                        "artifact_key": "policy.org-required",
                        "artifact_class": "policy",
                        "path_pattern": "org-policy.md",
                        "blocking": True,
                    }
                ],
            },
        )
        _write_org_pack_config(project_root, packs=[("acme", org_root)])

        after = ManifestRegistry.load_manifest("software-dev", repo_root=project_root)

        assert after is not None
        assert len(after.required_always) == before_count + 1
        assert after.manifest_version == "org-1"
        assert any(
            spec.artifact_key == "policy.org-required" for spec in after.required_always
        )

    def test_no_repo_root_is_byte_identical_to_pre_wp_behavior(
        self, tmp_path: Path
    ) -> None:
        """SC-005 Given #2: `load_manifest(mission_type)` with no `repo_root`
        (and with `repo_root=None` explicitly) produces output identical to
        pre-this-WP behavior -- proving the new optional parameter did not
        silently change the default call shape that
        `specify_cli.sync.namespace.resolve_manifest_version` depends on.
        """
        no_arg_result = ManifestRegistry.load_manifest("software-dev")
        ManifestRegistry.clear_cache()
        explicit_none_result = ManifestRegistry.load_manifest(
            "software-dev", repo_root=None
        )

        assert no_arg_result is not None
        assert explicit_none_result is not None
        assert no_arg_result.model_dump() == explicit_none_result.model_dump()

    def test_cache_key_does_not_shadow_across_different_repo_roots(
        self, tmp_path: Path
    ) -> None:
        """Cache-key regression (T023's fix): two different `repo_root`s
        resolving the SAME mission_type in the same process must not
        silently share a cached result -- this is exactly the defect this
        WP's cache-key fix exists to close. The cache is deliberately NOT
        cleared between the two calls below, since proving
        no-shadowing-without-clearing is the point.
        """
        project_a = tmp_path / "project-a"
        project_a.mkdir()
        org_root = tmp_path / "org-pack"
        _write_org_manifest(
            org_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "project-a-org",
            },
        )
        _write_org_pack_config(project_a, packs=[("acme", org_root)])

        project_b = tmp_path / "project-b"
        project_b.mkdir()
        # No org pack configured for project_b -- built-in tree only.

        result_a = ManifestRegistry.load_manifest("software-dev", repo_root=project_a)
        result_b = ManifestRegistry.load_manifest("software-dev", repo_root=project_b)

        assert result_a is not None
        assert result_b is not None
        assert result_a.manifest_version == "project-a-org"
        # The defect this fix closes: without the cache-key fix, project_b's
        # call would silently return project_a's cached (org-overridden)
        # result instead of resolving its own (built-in-only) manifest.
        assert result_b.manifest_version != "project-a-org"
        assert result_b.manifest_version == "1"

    def test_cache_key_preserves_declaration_order_for_same_root_set(
        self, tmp_path: Path
    ) -> None:
        """Same SET of org roots, declared in different order across two
        `repo_root`s, must not collide on one cache key. Per NFR-003 /
        C-4 ("last-EXISTING-match wins"), reversing declaration order
        flips which org root's manifest wins -- so a cache key built from
        a *sorted* tuple of root strings (order-blind) would map both
        projects to the same key, and the second project would silently
        receive the first project's cached, order-wrong manifest. This is
        distinct from `test_cache_key_does_not_shadow_across_different_repo_roots`,
        which only covers *different* root sets.
        """
        org_x = tmp_path / "org-x"
        org_y = tmp_path / "org-y"
        _write_org_manifest(
            org_x,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "x-wins",
            },
        )
        _write_org_manifest(
            org_y,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "y-wins",
            },
        )

        project_xy = tmp_path / "project-xy"
        project_xy.mkdir()
        _write_org_pack_config(project_xy, packs=[("x", org_x), ("y", org_y)])

        project_yx = tmp_path / "project-yx"
        project_yx.mkdir()
        _write_org_pack_config(project_yx, packs=[("y", org_y), ("x", org_x)])

        # Cache deliberately not cleared between calls -- proving the two
        # differently-ordered-but-same-set projects don't collide is the
        # point, same as the different-root-sets regression test above.
        result_xy = ManifestRegistry.load_manifest("software-dev", repo_root=project_xy)
        result_yx = ManifestRegistry.load_manifest("software-dev", repo_root=project_yx)

        assert result_xy is not None
        assert result_yx is not None
        # project_xy declared [x, y] -> last-match-wins is y.
        assert result_xy.manifest_version == "y-wins"
        # project_yx declared [y, x] -> last-match-wins is x.
        assert result_yx.manifest_version == "x-wins"

    def test_org_file_failing_model_validation_returns_none_and_caches_none(
        self, tmp_path: Path
    ) -> None:
        """A parseable org YAML mapping that fails `ExpectedArtifactManifest`
        validation (e.g. missing the required `mission_type` field) hits the
        new org-branch's `except` clause: logged, cached as `None` under
        that call's cache key, and returned as `None` -- not raised, and not
        silently falling back to the built-in file (the org file's presence
        is still authoritative, per whole-file precedence).
        """
        project_root = tmp_path / "project"
        project_root.mkdir()
        org_root = tmp_path / "org-pack"
        _write_org_manifest(
            org_root,
            "software-dev",
            # Missing required `mission_type` field -> pydantic ValidationError.
            {"schema_version": "1.0", "manifest_version": "broken"},
        )
        _write_org_pack_config(project_root, packs=[("acme", org_root)])

        result = ManifestRegistry.load_manifest("software-dev", repo_root=project_root)

        assert result is None
        org_roots = (str(org_root),)
        cache_key = ("software-dev", org_roots)
        assert ManifestRegistry._cache[cache_key] is None

    def test_cache_key_shape_is_tuple_of_mission_type_and_org_roots(self) -> None:
        """Every cached key is a `(mission_type, tuple[str, ...])` 2-tuple —
        durable proof the cache-key fix's shape (not just its behavior) is
        what's actually stored, so a future refactor that silently reverts
        to a bare `mission_type` key would fail this test even before any
        cross-project shadowing test caught it.
        """
        ManifestRegistry.load_manifest("software-dev")
        # Pins the whole cache -- exactly one entry, keyed by the
        # `(mission_type, org_roots)` 2-tuple shape. `==` against a `list`
        # of one `tuple` literal fails on a bare `"software-dev"` key (the
        # regression this test guards against), a differently-shaped key,
        # an extra entry, or a non-tuple `org_roots` part (e.g. a `list`)
        # just as surely as the old count-plus-isinstance-poke sequence did.
        assert list(ManifestRegistry._cache.keys()) == [("software-dev", ())]
