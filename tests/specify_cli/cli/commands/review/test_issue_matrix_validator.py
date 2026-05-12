"""Tests for the issue-matrix validator (T019, FR-028-032).

NFR-007: Vocabulary constants are imported directly from _issue_matrix.py;
no duplication.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands.review._diagnostics import MissionReviewDiagnostic
from specify_cli.cli.commands.review._issue_matrix import (
    COLUMN_ALIASES,
    MANDATORY_COLUMNS,
    NAMED_OPTIONAL_COLUMNS,
    IssueMatrixVerdict,
    validate_issue_matrix,
)

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_matrix(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "issue-matrix.md"
    p.write_text(content, encoding="utf-8")
    return p


_VALID_HEADER = "| issue | verdict | evidence_ref |\n|-------|---------|--------------|"
_VALID_ROW = "| #123 | fixed | commit abc123 |"
_VALID_MATRIX = f"# Issue Matrix\n\n{_VALID_HEADER}\n{_VALID_ROW}\n"


# ---------------------------------------------------------------------------
# Vocabulary constants (NFR-007 single-source test)
# ---------------------------------------------------------------------------


class TestVocabularyConstants:
    def test_mandatory_columns_are_tuple(self) -> None:
        assert isinstance(MANDATORY_COLUMNS, tuple)

    def test_mandatory_columns_content(self) -> None:
        assert MANDATORY_COLUMNS == ("issue", "verdict", "evidence_ref")

    def test_named_optional_columns_are_tuple(self) -> None:
        assert isinstance(NAMED_OPTIONAL_COLUMNS, tuple)

    def test_named_optional_contains_repo(self) -> None:
        assert "repo" in NAMED_OPTIONAL_COLUMNS

    def test_column_aliases_are_dict(self) -> None:
        assert isinstance(COLUMN_ALIASES, dict)

    def test_alias_evidence_ref(self) -> None:
        assert COLUMN_ALIASES["evidence ref"] == "evidence_ref"

    def test_alias_wp_id(self) -> None:
        assert COLUMN_ALIASES["wp_id"] == "wp"

    def test_alias_fr_s(self) -> None:
        assert COLUMN_ALIASES["fr(s)"] == "fr"

    def test_alias_nfr_s(self) -> None:
        assert COLUMN_ALIASES["nfr(s)"] == "nfr"

    def test_alias_theme(self) -> None:
        assert COLUMN_ALIASES["theme"] == "scope"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidateHappyPath:
    def test_minimal_valid_matrix_passes(self, tmp_path: Path) -> None:
        p = _write_matrix(tmp_path, _VALID_MATRIX)
        result = validate_issue_matrix(p)
        assert result.passed
        assert len(result.diagnostics) == 0

    def test_parsed_row_issue(self, tmp_path: Path) -> None:
        p = _write_matrix(tmp_path, _VALID_MATRIX)
        result = validate_issue_matrix(p)
        assert result.rows[0].issue == "#123"

    def test_parsed_row_verdict(self, tmp_path: Path) -> None:
        p = _write_matrix(tmp_path, _VALID_MATRIX)
        result = validate_issue_matrix(p)
        assert result.rows[0].verdict == IssueMatrixVerdict.FIXED

    def test_parsed_row_evidence_ref(self, tmp_path: Path) -> None:
        p = _write_matrix(tmp_path, _VALID_MATRIX)
        result = validate_issue_matrix(p)
        assert "abc123" in result.rows[0].evidence_ref

    def test_backtick_verdict_accepted(self, tmp_path: Path) -> None:
        content = f"# Matrix\n\n{_VALID_HEADER}\n| #1 | `fixed` | some_ref |\n"
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.passed
        assert result.rows[0].verdict == IssueMatrixVerdict.FIXED

    def test_linkified_issue_normalized(self, tmp_path: Path) -> None:
        content = (
            f"# Matrix\n\n{_VALID_HEADER}\n"
            "| [#456](https://github.com/Priivacy-ai/spec-kitty/issues/456) | fixed | ref |\n"
        )
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.rows[0].issue == "#456"

    def test_deferred_with_followup_valid_handle(self, tmp_path: Path) -> None:
        content = (
            f"# Matrix\n\n{_VALID_HEADER}\n"
            "| #10 | deferred-with-followup | Follow-up: #999 deferred |\n"
        )
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.passed

    def test_case_insensitive_headers(self, tmp_path: Path) -> None:
        header = "| Issue | Verdict | evidence_ref |"
        sep = "|-------|---------|--------------|"
        content = f"# Matrix\n\n{header}\n{sep}\n| #1 | fixed | ref |\n"
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.passed

    def test_alias_header_normalized(self, tmp_path: Path) -> None:
        header = "| issue | verdict | Evidence ref |"
        sep = "|-------|---------|---------------|"
        content = f"# Matrix\n\n{header}\n{sep}\n| #1 | fixed | ref |\n"
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.passed

    def test_optional_columns_included(self, tmp_path: Path) -> None:
        header = "| issue | title | verdict | evidence_ref |"
        sep = "|-------|-------|---------|--------------|"
        content = f"# Matrix\n\n{header}\n{sep}\n| #1 | My title | fixed | ref |\n"
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.passed
        assert result.rows[0].title == "My title"


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------


class TestMissingFile:
    def test_missing_file_produces_diagnostic(self, tmp_path: Path) -> None:
        p = tmp_path / "issue-matrix.md"
        result = validate_issue_matrix(p)
        assert not result.passed
        codes = [d["diagnostic_code"] for d in result.diagnostics]
        assert str(MissionReviewDiagnostic.ISSUE_MATRIX_MISSING) in codes


# ---------------------------------------------------------------------------
# Multi-table rule
# ---------------------------------------------------------------------------


class TestMultiTableRule:
    def test_two_tables_fires_multi_table(self, tmp_path: Path) -> None:
        content = (
            "# Matrix\n\n"
            f"{_VALID_HEADER}\n{_VALID_ROW}\n\n"
            "## Summary\n\n"
            "| verdict | count |\n|---------|-------|\n| fixed | 1 |\n"
        )
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert not result.passed
        codes = [d["diagnostic_code"] for d in result.diagnostics]
        assert str(MissionReviewDiagnostic.ISSUE_MATRIX_MULTI_TABLE) in codes


# ---------------------------------------------------------------------------
# Schema drift: unknown column
# ---------------------------------------------------------------------------


class TestSchemaDriftUnknownColumn:
    def test_unknown_column_fires_schema_drift(self, tmp_path: Path) -> None:
        header = "| issue | verdict | evidence_ref | Severity |"
        sep = "|-------|---------|--------------|----------|"
        content = f"# Matrix\n\n{header}\n{sep}\n| #1 | fixed | ref | high |\n"
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert not result.passed
        codes = [d["diagnostic_code"] for d in result.diagnostics]
        assert str(MissionReviewDiagnostic.ISSUE_MATRIX_SCHEMA_DRIFT) in codes

    def test_unknown_column_name_in_diagnostic(self, tmp_path: Path) -> None:
        header = "| issue | verdict | evidence_ref | Severity |"
        sep = "|-------|---------|--------------|----------|"
        content = f"# Matrix\n\n{header}\n{sep}\n| #1 | fixed | ref | high |\n"
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        messages = " ".join(d.get("message", "") for d in result.diagnostics)
        assert "severity" in messages.lower()


# ---------------------------------------------------------------------------
# Verdict unknown
# ---------------------------------------------------------------------------


class TestVerdictUnknown:
    def test_invalid_verdict_fires_diagnostic(self, tmp_path: Path) -> None:
        content = (
            f"# Matrix\n\n{_VALID_HEADER}\n"
            "| #2 | deferred | some_ref |\n"
        )
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert not result.passed
        codes = [d["diagnostic_code"] for d in result.diagnostics]
        assert str(MissionReviewDiagnostic.ISSUE_MATRIX_VERDICT_UNKNOWN) in codes


# ---------------------------------------------------------------------------
# Evidence ref empty
# ---------------------------------------------------------------------------


class TestEvidenceRefEmpty:
    def test_empty_evidence_ref_fires_diagnostic(self, tmp_path: Path) -> None:
        content = f"# Matrix\n\n{_VALID_HEADER}\n| #3 | fixed |  |\n"
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert not result.passed
        codes = [d["diagnostic_code"] for d in result.diagnostics]
        assert str(MissionReviewDiagnostic.ISSUE_MATRIX_EVIDENCE_REF_EMPTY) in codes


# ---------------------------------------------------------------------------
# Deferred without handle
# ---------------------------------------------------------------------------


class TestDeferredWithoutHandle:
    def test_deferred_tbd_fires_diagnostic(self, tmp_path: Path) -> None:
        content = (
            f"# Matrix\n\n{_VALID_HEADER}\n"
            "| #4 | deferred-with-followup | TBD |\n"
        )
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert not result.passed
        codes = [d["diagnostic_code"] for d in result.diagnostics]
        assert (
            str(MissionReviewDiagnostic.ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE) in codes
        )

    def test_deferred_with_hash_passes(self, tmp_path: Path) -> None:
        content = (
            f"# Matrix\n\n{_VALID_HEADER}\n"
            "| #5 | deferred-with-followup | see #888 |\n"
        )
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.passed

    def test_deferred_with_followup_colon_passes(self, tmp_path: Path) -> None:
        content = (
            f"# Matrix\n\n{_VALID_HEADER}\n"
            "| #6 | deferred-with-followup | Follow-up: file issue later |\n"
        )
        p = _write_matrix(tmp_path, content)
        result = validate_issue_matrix(p)
        assert result.passed
