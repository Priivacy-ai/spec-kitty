"""Tests for ownership.validation — overlap, authoritative surface, mode consistency."""

from __future__ import annotations

import pytest

from pathlib import Path

from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import (
    ValidationResult,
    validate_all,
    validate_authoritative_surface,
    validate_execution_mode_consistency,
    validate_glob_matches,
    validate_no_overlap,
    validate_ownership,
)


def _manifest(
    mode: ExecutionMode = ExecutionMode.CODE_CHANGE,
    owned: tuple[str, ...] = ("src/foo/**",),
    surface: str = "src/foo/",
) -> OwnershipManifest:
    return OwnershipManifest(execution_mode=mode, owned_files=owned, authoritative_surface=surface)


# ---------------------------------------------------------------------------
# validate_no_overlap
# ---------------------------------------------------------------------------


class TestValidateNoOverlap:
    def test_no_overlap_returns_empty(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/foo/**",), surface="src/foo/"),
            "WP02": _manifest(owned=("src/bar/**",), surface="src/bar/"),
        }
        errors = validate_no_overlap(manifests)
        assert errors == []

    def test_identical_globs_overlap(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/foo/**",), surface="src/foo/"),
            "WP02": _manifest(owned=("src/foo/**",), surface="src/foo/"),
        }
        errors = validate_no_overlap(manifests)
        assert len(errors) == 1
        assert "WP01" in errors[0] and "WP02" in errors[0]

    def test_nested_glob_overlap(self) -> None:
        """src/** overlaps with src/context/** — parent captures child."""
        manifests = {
            "WP01": _manifest(owned=("src/**",), surface="src/"),
            "WP02": _manifest(owned=("src/context/**",), surface="src/context/"),
        }
        errors = validate_no_overlap(manifests)
        assert len(errors) >= 1

    def test_disjoint_paths_no_overlap(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/alpha/**",), surface="src/alpha/"),
            "WP02": _manifest(owned=("src/beta/**",), surface="src/beta/"),
            "WP03": _manifest(owned=("tests/alpha/**",), surface="tests/alpha/"),
        }
        errors = validate_no_overlap(manifests)
        assert errors == []

    def test_single_wp_no_overlap(self) -> None:
        manifests = {"WP01": _manifest()}
        errors = validate_no_overlap(manifests)
        assert errors == []

    def test_empty_manifests_no_overlap(self) -> None:
        errors = validate_no_overlap({})
        assert errors == []


# ---------------------------------------------------------------------------
# validate_authoritative_surface
# ---------------------------------------------------------------------------


class TestValidateAuthoritativeSurface:
    def test_valid_prefix(self) -> None:
        m = _manifest(owned=("src/foo/**",), surface="src/foo/")
        errors = validate_authoritative_surface(m)
        assert errors == []

    def test_exact_match_valid(self) -> None:
        m = _manifest(owned=("src/foo",), surface="src/foo")
        errors = validate_authoritative_surface(m)
        assert errors == []

    def test_surface_not_a_prefix_returns_error(self) -> None:
        m = _manifest(owned=("src/bar/**",), surface="src/foo/")
        errors = validate_authoritative_surface(m)
        assert len(errors) == 1
        assert "prefix" in errors[0].lower() or "authoritative_surface" in errors[0]

    def test_empty_surface_returns_error(self) -> None:
        m = _manifest(owned=("src/foo/**",), surface="")
        errors = validate_authoritative_surface(m)
        assert len(errors) == 1
        assert "empty" in errors[0].lower()

    def test_no_owned_files_but_surface_present(self) -> None:
        m = _manifest(owned=(), surface="src/foo/")
        errors = validate_authoritative_surface(m)
        # No files to prefix → surface is not a prefix of any file
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# validate_execution_mode_consistency
# ---------------------------------------------------------------------------


class TestValidateExecutionModeConsistency:
    def test_code_change_with_src_files_no_warning(self) -> None:
        m = _manifest(mode=ExecutionMode.CODE_CHANGE, owned=("src/foo/**",), surface="src/foo/")
        warnings = validate_execution_mode_consistency(m)
        assert warnings == []

    def test_code_change_with_tests_files_no_warning(self) -> None:
        m = _manifest(
            mode=ExecutionMode.CODE_CHANGE,
            owned=("tests/specify_cli/**",),
            surface="tests/specify_cli/",
        )
        warnings = validate_execution_mode_consistency(m)
        assert warnings == []

    def test_code_change_with_only_kitty_specs_warns(self) -> None:
        m = _manifest(
            mode=ExecutionMode.CODE_CHANGE,
            owned=("kitty-specs/001-feature/**",),
            surface="kitty-specs/001-feature/",
        )
        warnings = validate_execution_mode_consistency(m)
        assert len(warnings) == 1

    def test_planning_artifact_with_kitty_specs_no_warning(self) -> None:
        m = _manifest(
            mode=ExecutionMode.PLANNING_ARTIFACT,
            owned=("kitty-specs/001-feature/**",),
            surface="kitty-specs/001-feature/",
        )
        warnings = validate_execution_mode_consistency(m)
        assert warnings == []

    def test_planning_artifact_with_docs_no_warning(self) -> None:
        m = _manifest(
            mode=ExecutionMode.PLANNING_ARTIFACT,
            owned=("docs/features/**",),
            surface="docs/features/",
        )
        warnings = validate_execution_mode_consistency(m)
        assert warnings == []

    def test_planning_artifact_with_src_warns(self) -> None:
        m = _manifest(
            mode=ExecutionMode.PLANNING_ARTIFACT,
            owned=("src/specify_cli/ownership/**",),
            surface="src/specify_cli/ownership/",
        )
        warnings = validate_execution_mode_consistency(m)
        assert len(warnings) == 1

    def test_empty_owned_files_no_warning(self) -> None:
        m = _manifest(mode=ExecutionMode.CODE_CHANGE, owned=(), surface="src/")
        warnings = validate_execution_mode_consistency(m)
        # Empty owned_files → no inconsistency to detect
        assert warnings == []


# ---------------------------------------------------------------------------
# validate_all / validate_ownership
# ---------------------------------------------------------------------------


class TestValidateAll:
    def test_valid_manifests_pass(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/alpha/**",), surface="src/alpha/"),
            "WP02": _manifest(owned=("src/beta/**",), surface="src/beta/"),
        }
        result = validate_all(manifests)
        assert result.passed

    def test_overlap_fails(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/**",), surface="src/"),
            "WP02": _manifest(owned=("src/foo/**",), surface="src/foo/"),
        }
        result = validate_all(manifests)
        assert not result.passed
        assert any("WP01" in e or "WP02" in e for e in result.errors)

    def test_bad_surface_fails(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/bar/**",), surface="src/foo/"),
        }
        result = validate_all(manifests)
        assert not result.passed

    def test_mode_inconsistency_is_warning_not_error(self) -> None:
        # planning_artifact owns src/ → warning only
        manifests = {
            "WP01": _manifest(
                mode=ExecutionMode.PLANNING_ARTIFACT,
                owned=("src/foo/**",),
                surface="src/foo/",
            ),
        }
        result = validate_all(manifests)
        # Surface check will fail (src/ is not a planning path) — that is an error
        # but mode inconsistency itself is a warning
        assert any("WP01" in w for w in result.warnings)

    def test_validate_ownership_alias(self) -> None:
        """validate_ownership must be an alias for validate_all."""
        manifests = {
            "WP01": _manifest(owned=("src/foo/**",), surface="src/foo/"),
        }
        r1 = validate_all(manifests)
        r2 = validate_ownership(manifests)
        assert r1.passed == r2.passed
        assert r1.errors == r2.errors

    def test_validation_result_is_dataclass(self) -> None:
        result = ValidationResult()
        assert result.passed
        result.errors.append("some error")
        assert not result.passed


# ---------------------------------------------------------------------------
# T013: validate_glob_matches — warns when globs match zero files
# ---------------------------------------------------------------------------


class TestValidateGlobMatches:
    def test_nonexistent_glob_emits_warning(self, tmp_path: Path) -> None:
        """A glob that matches no files must produce a warning."""
        manifests = {
            "WP01": _manifest(
                owned=("nonexistent_dir/**",),
                surface="nonexistent_dir/",
            ),
        }
        warnings = validate_glob_matches(manifests, tmp_path)
        assert len(warnings) == 1
        assert "WP01" in warnings[0]
        assert "nonexistent_dir/**" in warnings[0]

    def test_existing_glob_no_warning(self, tmp_path: Path) -> None:
        """A glob that matches at least one file must produce no warning."""
        # Create a file so the glob matches
        src_dir = tmp_path / "src" / "module"
        src_dir.mkdir(parents=True)
        (src_dir / "foo.py").write_text("# hello")

        manifests = {
            "WP01": _manifest(owned=("src/**",), surface="src/"),
        }
        warnings = validate_glob_matches(manifests, tmp_path)
        assert warnings == []

    def test_multiple_globs_one_missing_warns(self, tmp_path: Path) -> None:
        """Only the missing glob gets a warning; existing one is fine."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "present.py").write_text("# present")

        manifests = {
            "WP01": OwnershipManifest(
                execution_mode=ExecutionMode.CODE_CHANGE,
                owned_files=("src/**", "missing_path/**"),
                authoritative_surface="src/",
            ),
        }
        warnings = validate_glob_matches(manifests, tmp_path)
        assert len(warnings) == 1
        assert "missing_path/**" in warnings[0]

    def test_empty_manifests_no_warnings(self, tmp_path: Path) -> None:
        warnings = validate_glob_matches({}, tmp_path)
        assert warnings == []

    def test_warnings_sorted_by_wp_id(self, tmp_path: Path) -> None:
        """Warnings are emitted in sorted WP ID order."""
        manifests = {
            "WP02": _manifest(owned=("miss_b/**",), surface="miss_b/"),
            "WP01": _manifest(owned=("miss_a/**",), surface="miss_a/"),
        }
        warnings = validate_glob_matches(manifests, tmp_path)
        assert len(warnings) == 2
        assert warnings[0].startswith("WP01")
        assert warnings[1].startswith("WP02")
