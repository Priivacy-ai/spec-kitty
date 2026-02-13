"""Tests for documentation mission validation in acceptance/validation flows.

These tests verify:
1. Missing documentation_state in meta.json causes validation failure
2. Missing gap-analysis.md causes validation failure
3. Stale last_audit_date (older than created_at) causes failure
4. Fresh artifacts and state pass validation
5. Non-doc missions skip doc-specific checks entirely
6. Integration with acceptance summary (collect_feature_summary)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.validators.documentation import (
    validate_documentation_mission,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def doc_feature_dir(tmp_path: Path) -> Path:
    """Create a minimal documentation mission feature directory."""
    feature_dir = tmp_path / "kitty-specs" / "050-docs-feature"
    feature_dir.mkdir(parents=True)

    # Create meta.json with documentation mission
    meta = {
        "feature_number": "050",
        "mission": "documentation",
        "created_at": "2026-01-10T00:00:00Z",
        "documentation_state": {
            "iteration_mode": "gap_filling",
            "divio_types_selected": ["tutorial", "reference"],
            "generators_configured": [],
            "target_audience": "developers",
            "last_audit_date": "2026-01-15T00:00:00Z",
            "coverage_percentage": 0.5,
        },
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Create gap-analysis.md
    (feature_dir / "gap-analysis.md").write_text(
        "# Gap Analysis\n\nCoverage matrix here.\n"
    )

    # Create standard artifacts
    (feature_dir / "spec.md").write_text("Spec content")
    (feature_dir / "plan.md").write_text("Plan content")
    (feature_dir / "tasks.md").write_text("- [x] Task 1")
    (feature_dir / "tasks").mkdir()

    return feature_dir


@pytest.fixture()
def software_dev_feature_dir(tmp_path: Path) -> Path:
    """Create a minimal software-dev mission feature directory."""
    feature_dir = tmp_path / "kitty-specs" / "051-sw-feature"
    feature_dir.mkdir(parents=True)

    meta = {
        "feature_number": "051",
        "mission": "software-dev",
        "created_at": "2026-01-10T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    (feature_dir / "spec.md").write_text("Spec content")
    (feature_dir / "plan.md").write_text("Plan content")
    (feature_dir / "tasks.md").write_text("- [x] Task 1")
    (feature_dir / "tasks").mkdir()

    return feature_dir


# ============================================================================
# Test: Non-doc mission skips all checks (T019)
# ============================================================================


class TestNonDocMissionSkipped:
    """Verify non-documentation missions are not affected by doc checks."""

    def test_software_dev_mission_skips_doc_validation(
        self, software_dev_feature_dir: Path
    ) -> None:
        result = validate_documentation_mission(software_dev_feature_dir)
        assert not result.is_documentation_mission
        assert result.passed
        assert result.issues == []

    def test_missing_meta_json_skips_doc_validation(self, tmp_path: Path) -> None:
        """Feature without meta.json should not be treated as doc mission."""
        feature_dir = tmp_path / "kitty-specs" / "052-no-meta"
        feature_dir.mkdir(parents=True)
        result = validate_documentation_mission(feature_dir)
        assert not result.is_documentation_mission
        assert result.passed

    def test_invalid_meta_json_skips_doc_validation(self, tmp_path: Path) -> None:
        """Feature with invalid JSON in meta.json should not crash."""
        feature_dir = tmp_path / "kitty-specs" / "053-bad-meta"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text("not valid json {{{")
        result = validate_documentation_mission(feature_dir)
        assert not result.is_documentation_mission
        assert result.passed

    def test_research_mission_skips_doc_validation(self, tmp_path: Path) -> None:
        """Research mission should not trigger doc checks."""
        feature_dir = tmp_path / "kitty-specs" / "054-research"
        feature_dir.mkdir(parents=True)
        meta = {"mission": "research", "created_at": "2026-01-10T00:00:00Z"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))
        result = validate_documentation_mission(feature_dir)
        assert not result.is_documentation_mission
        assert result.passed


# ============================================================================
# Test: documentation_state missing (T019)
# ============================================================================


class TestDocumentationStateMissing:
    """Verify validation fails when documentation_state is absent."""

    def test_missing_documentation_state_is_error(
        self, doc_feature_dir: Path
    ) -> None:
        # Remove documentation_state from meta.json
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        del meta["documentation_state"]
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission
        assert result.has_errors
        assert not result.passed

        # Should have at least the documentation_state_exists error
        state_errors = [
            i for i in result.issues if i.check == "documentation_state_exists"
        ]
        assert len(state_errors) == 1
        assert state_errors[0].issue_type == "error"
        assert "documentation_state is missing" in state_errors[0].message
        assert "remediation" in state_errors[0].remediation.lower() or len(state_errors[0].remediation) > 0

    def test_missing_state_error_message_includes_remediation(
        self, doc_feature_dir: Path
    ) -> None:
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        del meta["documentation_state"]
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        report = result.format_report()
        assert "Remediation" in report


# ============================================================================
# Test: gap-analysis.md missing (T019)
# ============================================================================


class TestGapAnalysisMissing:
    """Verify validation fails when gap-analysis.md is absent."""

    def test_missing_gap_analysis_is_error(
        self, doc_feature_dir: Path
    ) -> None:
        # Remove gap-analysis.md
        (doc_feature_dir / "gap-analysis.md").unlink()

        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission
        assert result.has_errors
        assert not result.passed

        gap_errors = [
            i for i in result.issues if i.check == "gap_analysis_exists"
        ]
        assert len(gap_errors) == 1
        assert gap_errors[0].issue_type == "error"
        assert "gap-analysis.md" in gap_errors[0].message

    def test_gap_analysis_error_has_remediation(
        self, doc_feature_dir: Path
    ) -> None:
        (doc_feature_dir / "gap-analysis.md").unlink()
        result = validate_documentation_mission(doc_feature_dir)
        gap_errors = [
            i for i in result.issues if i.check == "gap_analysis_exists"
        ]
        assert gap_errors[0].remediation
        assert "gap-analysis.md" in gap_errors[0].remediation or "plan" in gap_errors[0].remediation.lower()


# ============================================================================
# Test: Stale audit date (T019)
# ============================================================================


class TestStaleAuditDate:
    """Verify validation fails when last_audit_date < created_at."""

    def test_stale_audit_date_is_error(self, doc_feature_dir: Path) -> None:
        # Set last_audit_date before created_at
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta["created_at"] = "2026-02-01T00:00:00Z"
        meta["documentation_state"]["last_audit_date"] = "2026-01-01T00:00:00Z"
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission
        assert result.has_errors

        recency_errors = [
            i for i in result.issues if i.check == "audit_recency"
        ]
        assert len(recency_errors) == 1
        assert recency_errors[0].issue_type == "error"
        assert "stale" in recency_errors[0].message.lower() or "older" in recency_errors[0].message.lower()

    def test_null_audit_date_is_error(self, doc_feature_dir: Path) -> None:
        # Set last_audit_date to null
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta["documentation_state"]["last_audit_date"] = None
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission
        assert result.has_errors

        recency_errors = [
            i for i in result.issues if i.check == "audit_recency"
        ]
        assert len(recency_errors) == 1
        assert recency_errors[0].issue_type == "error"
        assert "null" in recency_errors[0].message.lower()

    def test_audit_date_equal_to_created_at_passes(
        self, doc_feature_dir: Path
    ) -> None:
        """Audit on the same date as creation should be acceptable."""
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        same_date = "2026-01-15T00:00:00Z"
        meta["created_at"] = same_date
        meta["documentation_state"]["last_audit_date"] = same_date
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        recency_errors = [
            i for i in result.issues if i.check == "audit_recency"
        ]
        assert len(recency_errors) == 0

    def test_audit_date_after_created_at_passes(
        self, doc_feature_dir: Path
    ) -> None:
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta["created_at"] = "2026-01-10T00:00:00Z"
        meta["documentation_state"]["last_audit_date"] = "2026-02-01T00:00:00Z"
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        recency_errors = [
            i for i in result.issues if i.check == "audit_recency"
        ]
        assert len(recency_errors) == 0


# ============================================================================
# Test: All checks pass with valid artifacts (T019)
# ============================================================================


class TestValidDocumentationFeature:
    """Verify validation passes with all artifacts present and fresh."""

    def test_valid_feature_passes_all_checks(
        self, doc_feature_dir: Path
    ) -> None:
        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission
        assert result.passed
        assert not result.has_errors
        assert result.error_count == 0
        assert result.issues == []

    def test_valid_feature_report_says_passed(
        self, doc_feature_dir: Path
    ) -> None:
        result = validate_documentation_mission(doc_feature_dir)
        report = result.format_report()
        assert "passed" in report.lower()

    def test_error_messages_empty_when_valid(
        self, doc_feature_dir: Path
    ) -> None:
        result = validate_documentation_mission(doc_feature_dir)
        assert result.error_messages() == []


# ============================================================================
# Test: Multiple errors combine correctly
# ============================================================================


class TestMultipleErrors:
    """Verify multiple doc validation errors are all reported."""

    def test_missing_state_and_gap_analysis(
        self, doc_feature_dir: Path
    ) -> None:
        # Remove both documentation_state and gap-analysis.md
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        del meta["documentation_state"]
        meta_file.write_text(json.dumps(meta, indent=2))
        (doc_feature_dir / "gap-analysis.md").unlink()

        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission
        assert result.has_errors
        assert result.error_count >= 2

        check_names = {i.check for i in result.issues}
        assert "documentation_state_exists" in check_names
        assert "gap_analysis_exists" in check_names

    def test_all_three_errors_reported(self, doc_feature_dir: Path) -> None:
        """Remove state, gap analysis, and set stale audit - all should fail.
        
        Note: When documentation_state is missing, audit_recency cannot be
        checked (no state to check against), so we test a variant where state
        exists but has stale date and gap-analysis is missing.
        """
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta["created_at"] = "2026-02-01T00:00:00Z"
        meta["documentation_state"]["last_audit_date"] = "2026-01-01T00:00:00Z"
        meta_file.write_text(json.dumps(meta, indent=2))
        (doc_feature_dir / "gap-analysis.md").unlink()

        result = validate_documentation_mission(doc_feature_dir)
        assert result.has_errors
        assert result.error_count >= 2

        check_names = {i.check for i in result.issues}
        assert "gap_analysis_exists" in check_names
        assert "audit_recency" in check_names


# ============================================================================
# Test: DocValidationResult helpers
# ============================================================================


class TestDocValidationResultHelpers:
    """Verify result helper methods work correctly."""

    def test_error_messages_format(self, doc_feature_dir: Path) -> None:
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        del meta["documentation_state"]
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        messages = result.error_messages()
        assert all(msg.startswith("[doc-validation]") for msg in messages)

    def test_format_report_non_doc_mission(
        self, software_dev_feature_dir: Path
    ) -> None:
        result = validate_documentation_mission(software_dev_feature_dir)
        report = result.format_report()
        assert "Skipped" in report

    def test_format_report_with_errors(self, doc_feature_dir: Path) -> None:
        (doc_feature_dir / "gap-analysis.md").unlink()
        result = validate_documentation_mission(doc_feature_dir)
        report = result.format_report()
        assert "ERRORS" in report
        assert "gap-analysis.md" in report

    def test_passed_property_true_when_no_errors(
        self, doc_feature_dir: Path
    ) -> None:
        result = validate_documentation_mission(doc_feature_dir)
        assert result.passed is True

    def test_passed_property_false_when_errors(
        self, doc_feature_dir: Path
    ) -> None:
        (doc_feature_dir / "gap-analysis.md").unlink()
        result = validate_documentation_mission(doc_feature_dir)
        assert result.passed is False


# ============================================================================
# Test: Edge cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases in documentation validation."""

    def test_no_created_at_in_meta(self, doc_feature_dir: Path) -> None:
        """Missing created_at should not crash (recency check skipped)."""
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta.pop("created_at", None)
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        # Should not crash; audit_recency check requires both dates
        assert result.is_documentation_mission

    def test_malformed_audit_date(self, doc_feature_dir: Path) -> None:
        """Malformed date string should not crash."""
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta["documentation_state"]["last_audit_date"] = "not-a-date"
        meta_file.write_text(json.dumps(meta, indent=2))

        # Should not raise an exception
        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission

    def test_malformed_created_at(self, doc_feature_dir: Path) -> None:
        """Malformed created_at should not crash."""
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta["created_at"] = "not-a-date"
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        assert result.is_documentation_mission

    def test_empty_gap_analysis_file_passes(
        self, doc_feature_dir: Path
    ) -> None:
        """An empty gap-analysis.md file should still pass the existence check."""
        (doc_feature_dir / "gap-analysis.md").write_text("")
        result = validate_documentation_mission(doc_feature_dir)
        gap_errors = [
            i for i in result.issues if i.check == "gap_analysis_exists"
        ]
        assert len(gap_errors) == 0

    def test_timezone_aware_dates_compared_correctly(
        self, doc_feature_dir: Path
    ) -> None:
        """Dates with timezone info should compare correctly."""
        meta_file = doc_feature_dir / "meta.json"
        meta = json.loads(meta_file.read_text())
        meta["created_at"] = "2026-01-10T00:00:00+00:00"
        meta["documentation_state"]["last_audit_date"] = "2026-01-15T00:00:00+05:00"
        meta_file.write_text(json.dumps(meta, indent=2))

        result = validate_documentation_mission(doc_feature_dir)
        recency_errors = [
            i for i in result.issues if i.check == "audit_recency"
        ]
        assert len(recency_errors) == 0
