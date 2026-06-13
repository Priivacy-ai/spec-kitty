"""Tests for ownership warning routing in validate_glob_matches (WP04 / FR-006).

Covers:
- T015: is_glob_pattern helper
- T015/T016: literal vs glob classification in validate_glob_matches
- T016: literal zero-match → hard error with nearest-match suggestion
- T017: create_intent suppresses hard error for planned-new-file paths
- T018: GlobValidationResult separates errors from warnings
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import (
    GlobValidationResult,
    is_glob_pattern,
    validate_glob_matches,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# T015 — is_glob_pattern helper
# ---------------------------------------------------------------------------


class TestIsGlobPattern:
    def test_glob_star(self) -> None:
        assert is_glob_pattern("src/foo/*.py") is True

    def test_glob_double_star(self) -> None:
        assert is_glob_pattern("src/**/*.py") is True

    def test_glob_question_mark(self) -> None:
        assert is_glob_pattern("src/foo/ba?.py") is True

    def test_glob_bracket(self) -> None:
        assert is_glob_pattern("src/[abc]oo.py") is True

    def test_glob_brace(self) -> None:
        assert is_glob_pattern("src/{foo,bar}.py") is True

    def test_literal_py_file(self) -> None:
        assert is_glob_pattern("src/foo/bar.py") is False

    def test_literal_directory_path(self) -> None:
        assert is_glob_pattern("src/specify_cli/ownership/") is False

    def test_empty_string(self) -> None:
        assert is_glob_pattern("") is False

    def test_plain_filename(self) -> None:
        assert is_glob_pattern("README.md") is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(patterns: list[str]) -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode.CODE_CHANGE,
        owned_files=tuple(patterns),
        authoritative_surface="src/",
    )


# ---------------------------------------------------------------------------
# T015/T016 — literal vs glob classification
# ---------------------------------------------------------------------------


class TestValidateGlobMatchesClassification:
    def test_glob_zero_match_is_warning_not_error(self, tmp_path: Path) -> None:
        """A zero-match glob pattern should produce a warning, not a hard error."""
        manifests = {"WP01": _make_manifest(["src/*.py"])}
        result = validate_glob_matches(manifests, tmp_path)

        assert isinstance(result, GlobValidationResult)
        assert result.passed, f"Should pass (no hard errors), got errors: {result.errors}"
        assert len(result.warnings) == 1
        assert "WP01" in result.warnings[0]
        assert "src/*.py" in result.warnings[0]

    def test_literal_zero_match_is_hard_error(self, tmp_path: Path) -> None:
        """A zero-match literal path should produce a hard error."""
        manifests = {"WP01": _make_manifest(["src/foo/bar.py"])}
        result = validate_glob_matches(manifests, tmp_path)

        assert not result.passed
        assert len(result.errors) == 1
        assert "WP01" in result.errors[0]
        assert "src/foo/bar.py" in result.errors[0]
        assert len(result.warnings) == 0

    def test_literal_existing_file_no_error(self, tmp_path: Path) -> None:
        """A literal path that exists should produce no error or warning."""
        target = tmp_path / "src" / "foo" / "bar.py"
        target.parent.mkdir(parents=True)
        target.write_text("# file\n")

        manifests = {"WP01": _make_manifest(["src/foo/bar.py"])}
        result = validate_glob_matches(manifests, tmp_path)

        assert result.passed
        assert result.errors == []
        assert result.warnings == []

    def test_glob_existing_matches_no_warning(self, tmp_path: Path) -> None:
        """A glob pattern with at least one match should produce no warning."""
        target = tmp_path / "src" / "foo.py"
        target.parent.mkdir(parents=True)
        target.write_text("# file\n")

        manifests = {"WP01": _make_manifest(["src/*.py"])}
        result = validate_glob_matches(manifests, tmp_path)

        assert result.passed
        assert result.errors == []
        assert result.warnings == []

    def test_mixed_entries_separated_correctly(self, tmp_path: Path) -> None:
        """Mixed literal+glob entries in one WP should be classified independently."""
        # Create one real file for the glob to match
        existing = tmp_path / "src" / "real.py"
        existing.parent.mkdir(parents=True)
        existing.write_text("# real\n")

        manifests = {
            "WP01": _make_manifest([
                "src/*.py",           # glob — matches (no warning)
                "src/missing.py",     # literal — no match (hard error)
                "tests/**/*.py",      # glob — no match (warning)
            ])
        }
        result = validate_glob_matches(manifests, tmp_path)

        assert not result.passed
        assert len(result.errors) == 1
        assert "src/missing.py" in result.errors[0]
        assert len(result.warnings) == 1
        assert "tests/**/*.py" in result.warnings[0]


# ---------------------------------------------------------------------------
# T016 — nearest-match suggestion
# ---------------------------------------------------------------------------


class TestNearestMatchSuggestion:
    def test_nearest_match_included_in_error(self, tmp_path: Path) -> None:
        """When a sibling file is close in name, the error should suggest it."""
        sibling = tmp_path / "src" / "foo" / "barr.py"
        sibling.parent.mkdir(parents=True)
        sibling.write_text("# sibling\n")

        manifests = {"WP01": _make_manifest(["src/foo/bar.py"])}
        result = validate_glob_matches(manifests, tmp_path)

        assert not result.passed
        # Should contain "Did you mean" hint
        assert "barr.py" in result.errors[0] or "Did you mean" in result.errors[0]

    def test_no_suggestion_when_parent_missing(self, tmp_path: Path) -> None:
        """When the parent directory doesn't exist, no suggestion is added."""
        manifests = {"WP01": _make_manifest(["src/nonexistent_dir/foo.py"])}
        result = validate_glob_matches(manifests, tmp_path)

        assert not result.passed
        # Error message should still mention create_intent as remedy
        assert "create_intent" in result.errors[0]


# ---------------------------------------------------------------------------
# T017 — create_intent suppression
# ---------------------------------------------------------------------------


class TestCreateIntentSuppression:
    def test_create_intent_suppresses_hard_error(self, tmp_path: Path) -> None:
        """A literal zero-match path in create_intent must not produce a hard error."""
        manifests = {"WP01": _make_manifest(["src/new_module.py"])}
        create_intent = {"WP01": ["src/new_module.py"]}

        result = validate_glob_matches(manifests, tmp_path, create_intent=create_intent)

        assert result.passed, f"Should pass, got errors: {result.errors}"
        assert result.errors == []
        assert result.warnings == []

    def test_create_intent_emits_info_note(self, tmp_path: Path) -> None:
        """Suppressed path should appear in info notes, not errors."""
        manifests = {"WP01": _make_manifest(["src/new_module.py"])}
        create_intent = {"WP01": ["src/new_module.py"]}

        result = validate_glob_matches(manifests, tmp_path, create_intent=create_intent)

        assert len(result.info) == 1
        assert "src/new_module.py" in result.info[0]
        assert "create_intent" in result.info[0]

    def test_create_intent_partial_suppression(self, tmp_path: Path) -> None:
        """Only the exact paths in create_intent are suppressed; others still error."""
        manifests = {
            "WP01": _make_manifest([
                "src/new_module.py",    # suppressed
                "src/other_module.py",  # not suppressed → hard error
            ])
        }
        create_intent = {"WP01": ["src/new_module.py"]}

        result = validate_glob_matches(manifests, tmp_path, create_intent=create_intent)

        assert not result.passed
        assert len(result.errors) == 1
        assert "src/other_module.py" in result.errors[0]
        assert len(result.info) == 1
        assert "src/new_module.py" in result.info[0]

    def test_create_intent_only_applies_to_correct_wp(self, tmp_path: Path) -> None:
        """create_intent for WP02 must not suppress a zero-match in WP01."""
        manifests = {
            "WP01": _make_manifest(["src/new_module.py"]),
            "WP02": _make_manifest(["src/other_module.py"]),
        }
        # create_intent only covers WP02
        create_intent = {"WP02": ["src/other_module.py"]}

        result = validate_glob_matches(manifests, tmp_path, create_intent=create_intent)

        assert not result.passed
        # WP01 literal path should still be a hard error
        assert any("WP01" in e for e in result.errors)
        # WP02 path should be suppressed to info
        assert any("src/other_module.py" in note for note in result.info)

    def test_create_intent_does_not_suppress_glob_warnings(self, tmp_path: Path) -> None:
        """create_intent does not affect glob patterns — glob zero-match stays a warning."""
        manifests = {"WP01": _make_manifest(["src/*.py"])}
        create_intent = {"WP01": ["src/*.py"]}  # glob in create_intent (unusual)

        result = validate_glob_matches(manifests, tmp_path, create_intent=create_intent)

        # Glob patterns take the warning path regardless of create_intent
        assert result.passed  # warnings don't fail passed
        assert len(result.warnings) == 1
        assert result.errors == []

    def test_create_intent_none_behaves_like_empty(self, tmp_path: Path) -> None:
        """Passing create_intent=None should behave identically to create_intent={}."""
        manifests = {"WP01": _make_manifest(["src/missing.py"])}

        result_none = validate_glob_matches(manifests, tmp_path, create_intent=None)
        result_empty = validate_glob_matches(manifests, tmp_path, create_intent={})

        assert result_none.errors == result_empty.errors
        assert result_none.warnings == result_empty.warnings
        assert result_none.info == result_empty.info


# ---------------------------------------------------------------------------
# T018 — GlobValidationResult structure
# ---------------------------------------------------------------------------


class TestGlobValidationResult:
    def test_passed_is_true_when_no_errors(self) -> None:
        r = GlobValidationResult(warnings=["some warning"])
        assert r.passed is True

    def test_passed_is_false_when_errors_present(self) -> None:
        r = GlobValidationResult(errors=["hard error"])
        assert r.passed is False

    def test_empty_result_passes(self) -> None:
        r = GlobValidationResult()
        assert r.passed is True
        assert r.errors == []
        assert r.warnings == []
        assert r.info == []

    def test_return_type_is_glob_validation_result(self, tmp_path: Path) -> None:
        """validate_glob_matches must return a GlobValidationResult, not a list."""
        manifests: dict[str, OwnershipManifest] = {}
        result = validate_glob_matches(manifests, tmp_path)
        assert isinstance(result, GlobValidationResult)

    def test_empty_manifests_returns_clean_result(self, tmp_path: Path) -> None:
        """Empty manifests should return a clean (passed) result."""
        result = validate_glob_matches({}, tmp_path)
        assert result.passed
        assert result.errors == []
        assert result.warnings == []


# ---------------------------------------------------------------------------
# T018 — Multiple WPs interaction
# ---------------------------------------------------------------------------


class TestMultipleWPs:
    def test_multiple_wps_errors_collected(self, tmp_path: Path) -> None:
        """Hard errors from multiple WPs must all be collected in result.errors."""
        manifests = {
            "WP01": _make_manifest(["src/missing_a.py"]),
            "WP02": _make_manifest(["src/missing_b.py"]),
        }
        result = validate_glob_matches(manifests, tmp_path)

        assert not result.passed
        assert len(result.errors) == 2
        wp_ids_in_errors = {e.split(":")[0] for e in result.errors}
        assert "WP01" in wp_ids_in_errors
        assert "WP02" in wp_ids_in_errors

    def test_multiple_wps_warnings_collected(self, tmp_path: Path) -> None:
        """Glob warnings from multiple WPs must all be collected in result.warnings."""
        manifests = {
            "WP01": _make_manifest(["src/foo/**/*.py"]),
            "WP02": _make_manifest(["tests/**/*.py"]),
        }
        result = validate_glob_matches(manifests, tmp_path)

        assert result.passed  # warnings only
        assert len(result.warnings) == 2
