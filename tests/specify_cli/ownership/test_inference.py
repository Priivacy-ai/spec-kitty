"""Tests for ownership.inference — execution mode and owned_files inference."""

from __future__ import annotations

import pytest

from specify_cli.ownership.inference import (
    infer_authoritative_surface,
    infer_execution_mode,
    infer_owned_files,
    infer_ownership,
)
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest


# ---------------------------------------------------------------------------
# infer_execution_mode
# ---------------------------------------------------------------------------


class TestInferExecutionMode:
    def test_code_change_default_no_signals(self) -> None:
        """When content has no discernible signals, default to code_change."""
        mode = infer_execution_mode("Create a new feature.", [])
        assert mode == ExecutionMode.CODE_CHANGE

    def test_src_path_implies_code_change(self) -> None:
        content = "Create src/specify_cli/ownership/__init__.py with public exports."
        mode = infer_execution_mode(content, [])
        assert mode == ExecutionMode.CODE_CHANGE

    def test_test_path_implies_code_change(self) -> None:
        content = "Add tests/specify_cli/ownership/test_models.py covering all branches."
        mode = infer_execution_mode(content, [])
        assert mode == ExecutionMode.CODE_CHANGE

    def test_kitty_specs_only_implies_planning_artifact(self) -> None:
        content = (
            "Update kitty-specs/057-feature/spec.md with FR-004 and FR-005. "
            "Also update kitty-specs/057-feature/plan.md."
        )
        mode = infer_execution_mode(content, [])
        assert mode == ExecutionMode.PLANNING_ARTIFACT

    def test_spec_md_implies_planning_artifact(self) -> None:
        content = "Write spec.md and plan.md for the new feature."
        mode = infer_execution_mode(content, [])
        assert mode == ExecutionMode.PLANNING_ARTIFACT

    def test_tasks_md_implies_planning_artifact(self) -> None:
        content = "Generate tasks.md with work packages."
        mode = infer_execution_mode(content, [])
        assert mode == ExecutionMode.PLANNING_ARTIFACT

    def test_data_model_md_implies_planning_artifact(self) -> None:
        content = "Write data-model.md describing the entity relationships."
        mode = infer_execution_mode(content, [])
        assert mode == ExecutionMode.PLANNING_ARTIFACT

    def test_mixed_content_code_change_wins(self) -> None:
        """When both code and planning signals are present, code_change wins."""
        content = "Update kitty-specs/001/spec.md and implement src/specify_cli/foo.py."
        mode = infer_execution_mode(content, [])
        assert mode == ExecutionMode.CODE_CHANGE

    def test_wp_files_list_contributes(self) -> None:
        content = "Do some work."
        wp_files = ["src/specify_cli/new_module.py"]
        mode = infer_execution_mode(content, wp_files)
        assert mode == ExecutionMode.CODE_CHANGE


# ---------------------------------------------------------------------------
# infer_owned_files
# ---------------------------------------------------------------------------


class TestInferOwnedFiles:
    def test_planning_artifact_defaults_to_feature_glob(self) -> None:
        content = "Update kitty-specs/057-feature/spec.md and plan.md."
        globs = infer_owned_files(content, "057-my-feature")
        assert "kitty-specs/057-my-feature/**" in globs

    def test_code_change_extracts_src_paths(self) -> None:
        content = (
            "Create src/specify_cli/ownership/__init__.py\n"
            "Create src/specify_cli/ownership/models.py\n"
        )
        globs = infer_owned_files(content, "057-feature")
        assert any("src/" in g for g in globs)

    def test_code_change_extracts_tests_paths(self) -> None:
        content = "Add tests/specify_cli/ownership/test_models.py"
        globs = infer_owned_files(content, "057-feature")
        assert any("tests" in g for g in globs)

    def test_fallback_when_no_paths_found(self) -> None:
        """When no path tokens are found in a code_change WP, return src/**."""
        content = "Implement the new feature logic."
        globs = infer_owned_files(content, "057-feature")
        assert globs == ["src/**"]

    def test_deduplicates_results(self) -> None:
        content = (
            "Create src/specify_cli/foo.py\n"
            "Create src/specify_cli/bar.py\n"
        )
        globs = infer_owned_files(content, "057-feature")
        assert len(globs) == len(set(globs))


# ---------------------------------------------------------------------------
# infer_authoritative_surface
# ---------------------------------------------------------------------------


class TestInferAuthoritativeSurface:
    def test_single_pattern_returns_prefix(self) -> None:
        surface = infer_authoritative_surface(["src/specify_cli/ownership/**"])
        assert surface == "src/specify_cli/ownership/"

    def test_common_prefix_shared_paths(self) -> None:
        surface = infer_authoritative_surface([
            "src/specify_cli/ownership/**",
            "src/specify_cli/ownership/models.py",
        ])
        assert "src/specify_cli/ownership" in surface

    def test_divergent_paths_shorter_common(self) -> None:
        surface = infer_authoritative_surface([
            "src/specify_cli/alpha/**",
            "src/specify_cli/beta/**",
        ])
        assert surface.startswith("src/specify_cli/")

    def test_empty_list_returns_empty_string(self) -> None:
        surface = infer_authoritative_surface([])
        assert surface == ""

    def test_planning_artifact_path(self) -> None:
        surface = infer_authoritative_surface(["kitty-specs/057-feature/**"])
        assert surface == "kitty-specs/057-feature/"


# ---------------------------------------------------------------------------
# infer_ownership (convenience wrapper)
# ---------------------------------------------------------------------------


class TestInferOwnership:
    def test_returns_ownership_manifest(self) -> None:
        content = "Create src/specify_cli/ownership/__init__.py"
        manifest = infer_ownership(content, "057-feature")
        assert isinstance(manifest, OwnershipManifest)
        assert manifest.execution_mode == ExecutionMode.CODE_CHANGE
        assert len(manifest.owned_files) > 0
        assert manifest.authoritative_surface != ""

    def test_planning_artifact_manifest(self) -> None:
        content = "Update kitty-specs/057-feature/spec.md and plan.md."
        manifest = infer_ownership(content, "057-feature")
        assert manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT
        assert any("kitty-specs/057-feature" in f for f in manifest.owned_files)

    def test_wp_files_override_contributes(self) -> None:
        content = "Do something."
        manifest = infer_ownership(content, "057-feature", wp_files=["src/foo.py"])
        assert manifest.execution_mode == ExecutionMode.CODE_CHANGE
