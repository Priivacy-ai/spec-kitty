"""Tests for the bulk_edit inference keyword scanning module."""

from __future__ import annotations

from pathlib import Path

from specify_cli.bulk_edit.inference import (
    INFERENCE_THRESHOLD,
    scan_spec_file,
    score_spec_for_bulk_edit,
)

# ---------------------------------------------------------------------------
# score_spec_for_bulk_edit
# ---------------------------------------------------------------------------


class TestScoreSpecForBulkEdit:
    def test_empty_content_scores_zero(self) -> None:
        result = score_spec_for_bulk_edit("")
        assert result.score == 0
        assert result.triggered is False
        assert result.matched_phrases == []
        assert result.threshold == INFERENCE_THRESHOLD

    def test_single_high_phrase_scores_3(self) -> None:
        result = score_spec_for_bulk_edit("We need to run a codemod on the entire project.")
        assert result.score == 3
        assert ("codemod", 3) in result.matched_phrases
        assert result.triggered is False  # 3 < 4

    def test_single_medium_keyword_scores_2(self) -> None:
        result = score_spec_for_bulk_edit("Rename the function to something better.")
        assert result.score == 2
        assert ("rename", 2) in result.matched_phrases
        assert result.triggered is False

    def test_single_low_keyword_scores_1(self) -> None:
        result = score_spec_for_bulk_edit("Update the module configuration.")
        assert result.score == 1
        assert ("update", 1) in result.matched_phrases
        assert result.triggered is False

    def test_threshold_reached_with_mixed(self) -> None:
        result = score_spec_for_bulk_edit("Rename all occurrences across the codebase.")
        # "rename all occurrences" = 3 (high)
        # "across the codebase" = 2 (medium)
        # "rename" would be skipped (substring of "rename all occurrences")
        assert result.triggered is True
        assert result.score >= INFERENCE_THRESHOLD

    def test_threshold_not_reached_low_only(self) -> None:
        result = score_spec_for_bulk_edit("Update and change the config file.")
        # "update" = 1, "change" = 1 => total = 2
        assert result.score == 2
        assert result.triggered is False

    def test_no_double_counting(self) -> None:
        result = score_spec_for_bulk_edit("Rename across the code to fix naming.")
        # "rename across" = 3 (high)
        # "rename" should NOT also count as medium (2) since it's a substring
        # of "rename across"
        high_matches = [p for p, w in result.matched_phrases if w == 3]
        medium_matches = [p for p, w in result.matched_phrases if w == 2]
        assert "rename across" in high_matches
        assert "rename" not in medium_matches
        assert result.score == 3  # only the high phrase

    def test_case_insensitive(self) -> None:
        lower = score_spec_for_bulk_edit("bulk edit all the things")
        upper = score_spec_for_bulk_edit("BULK EDIT all the things")
        mixed = score_spec_for_bulk_edit("Bulk Edit all the things")
        assert lower.score == upper.score == mixed.score
        assert lower.score == 3

    def test_realistic_positive(self) -> None:
        spec = (
            "This mission performs a codebase-wide rename of the term "
            "'constitution' to 'charter'. We will use a find-and-replace "
            "approach to rename all occurrences across the codebase, including "
            "code symbols, import paths, and user-facing strings. "
            "The change should be applied globally."
        )
        result = score_spec_for_bulk_edit(spec)
        assert result.triggered is True
        assert result.score >= INFERENCE_THRESHOLD
        # Should have multiple matches
        assert len(result.matched_phrases) >= 2

    def test_realistic_negative(self) -> None:
        spec = (
            "Add an authentication endpoint that validates JWT tokens. "
            "The endpoint should accept POST requests with a token in the "
            "Authorization header and return user profile data."
        )
        result = score_spec_for_bulk_edit(spec)
        assert result.triggered is False
        assert result.score < INFERENCE_THRESHOLD

    def test_medium_multi_word_keyword_matches(self) -> None:
        result = score_spec_for_bulk_edit("Apply the change across the codebase in all modules.")
        assert ("across the codebase", 2) in result.matched_phrases
        assert ("change", 1) in result.matched_phrases

    def test_word_boundary_prevents_partial_match(self) -> None:
        # "update" should not match inside "updated_at" due to word boundary
        result = score_spec_for_bulk_edit("The updated_at column stores timestamps.")
        # "update" won't match because of word boundary regex
        assert result.score == 0
        assert result.triggered is False


# ---------------------------------------------------------------------------
# scan_spec_file
# ---------------------------------------------------------------------------


class TestScanSpecFile:
    def test_scan_missing_spec_returns_not_triggered(self, tmp_path: Path) -> None:
        result = scan_spec_file(tmp_path)
        assert result.triggered is False
        assert result.score == 0
        assert result.threshold == INFERENCE_THRESHOLD

    def test_scan_existing_spec_returns_result(self, tmp_path: Path) -> None:
        spec_content = "Rename across the entire codebase. Apply find-and-replace to update all references globally."
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content, encoding="utf-8")

        result = scan_spec_file(tmp_path)

        assert result.triggered is True
        assert result.score >= INFERENCE_THRESHOLD
        assert len(result.matched_phrases) >= 2

    def test_scan_empty_spec_returns_zero(self, tmp_path: Path) -> None:
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("", encoding="utf-8")

        result = scan_spec_file(tmp_path)

        assert result.score == 0
        assert result.triggered is False
