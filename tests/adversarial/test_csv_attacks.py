"""
CSV Schema Attack Tests

Tests for CSV validation to ensure:
- Formula injection payloads don't execute
- Invalid encodings produce clear errors
- Duplicate columns are detected
- Empty/malformed files are handled gracefully

Target: src/specify_cli/validators/csv_schema.py
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.validators.csv_schema import validate_csv_schema

pytestmark = [pytest.mark.adversarial]

# Expected columns for evidence-log.csv (from ADR 8)
EVIDENCE_COLUMNS = ["timestamp", "source_type", "citation", "key_finding", "confidence", "notes"]
SOURCE_COLUMNS = ["source_id", "citation", "url", "accessed_date", "relevance", "status"]


class TestFormulaInjection:
    """Test formula injection attack handling.

    CSV formula injection occurs when cells start with =, +, -, @
    When opened in Excel/LibreOffice, these can execute code.

    Python's csv module doesn't execute formulas, but we should:
    1. Not crash on these inputs
    2. Ideally warn about potential injection
    """

    @pytest.mark.parametrize(
        "formula,description",
        [
            ("=cmd|'/c calc'!A1", "Excel DDE attack"),
            ("=1+1", "Simple formula"),
            ("+1+1", "Plus formula"),
            ("-1+1", "Minus formula"),
            ("@SUM(A1:A10)", "At-sign function"),
            ("=HYPERLINK(\"http://evil.com\",\"Click\")", "Hyperlink injection"),
        ],
    )
    def test_formula_in_cell_handled(self, tmp_path: Path, formula: str, description: str):
        """CSV with formula injection should be validated without execution."""
        csv_path = tmp_path / "test.csv"
        content = (
            f"{','.join(EVIDENCE_COLUMNS)}\n"
            f"2025-01-25T10:00:00,journal,\"{formula}\",Finding,high,Notes\n"
        )
        csv_path.write_text(content, encoding="utf-8")

        # Should not raise exception
        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Validation should complete (schema is correct)
        assert result is not None, "Should return validation result"
        # The formula is just data - schema validation should pass

    def test_formula_in_header_rejected(self, tmp_path: Path):
        """Formula in column header should cause schema mismatch."""
        csv_path = tmp_path / "test.csv"
        content = "=timestamp,source_type,citation,key_finding,confidence,notes\n"
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Schema should not match (column name wrong)
        assert not result.schema_valid, "Formula in header should cause mismatch"


class TestEncodingAttacks:
    """Test encoding attack handling."""

    def test_invalid_utf8_clear_error(self, tmp_path: Path):
        """Invalid UTF-8 should produce clear error, not cryptic exception."""
        csv_path = tmp_path / "test.csv"
        # Invalid UTF-8 byte sequence
        csv_path.write_bytes(b"\xff\xfe\x00\x01invalid")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Should not crash, should report error
        assert not result.schema_valid, "Invalid UTF-8 should fail validation"
        assert result.error_message, "Should have error message"
        # Error should mention encoding, not raw exception
        assert "exception" not in result.error_message.lower() or "encoding" in result.error_message.lower()

    def test_latin1_encoding_handled(self, tmp_path: Path):
        """Latin-1 encoded file should be handled gracefully."""
        csv_path = tmp_path / "test.csv"
        # cafe encoded in Latin-1 (not UTF-8)
        content = "timestamp,source_type,citation,key_finding,confidence,notes\n"
        content += "2025-01-25T10:00:00,journal,caf\xe9,Finding,high,Notes\n"
        csv_path.write_bytes(content.encode("latin-1"))

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Should handle gracefully (may fail validation, but with clear error)
        assert result is not None

    def test_utf8_bom_handled(self, tmp_path: Path):
        """UTF-8 with BOM should be handled correctly."""
        csv_path = tmp_path / "test.csv"
        # UTF-8 BOM + valid content
        content = f"{','.join(EVIDENCE_COLUMNS)}\n"
        csv_path.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # UTF-8 BOM should be stripped, validation should pass
        # (or at least not crash)
        assert result is not None

    def test_null_bytes_in_content(self, tmp_path: Path):
        """Null bytes in CSV content should be handled."""
        csv_path = tmp_path / "test.csv"
        content = f"{','.join(EVIDENCE_COLUMNS)}\n"
        content += "2025-01-25T10:00:00,journal,cita\x00tion,Finding,high,Notes\n"
        csv_path.write_bytes(content.encode("utf-8"))

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Should handle without crash
        assert result is not None


class TestSchemaViolations:
    """Test schema violation detection."""

    def test_duplicate_columns_detected(self, tmp_path: Path):
        """Duplicate column names should be detected."""
        csv_path = tmp_path / "test.csv"
        # Duplicate 'citation' column
        content = "timestamp,source_type,citation,citation,confidence,notes\n"
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Should detect duplicate
        assert not result.schema_valid, "Duplicate columns should fail validation"
        # Ideally error mentions duplicate
        # If this fails, it's a bug to fix

    def test_extra_columns_rejected(self, tmp_path: Path):
        """Extra columns beyond schema should be rejected."""
        csv_path = tmp_path / "test.csv"
        content = "timestamp,source_type,citation,key_finding,confidence,notes,extra_col\n"
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        assert not result.schema_valid, "Extra columns should fail validation"

    def test_missing_columns_rejected(self, tmp_path: Path):
        """Missing required columns should be rejected."""
        csv_path = tmp_path / "test.csv"
        content = "timestamp,source_type,citation\n"  # Missing 3 columns
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        assert not result.schema_valid, "Missing columns should fail validation"
        assert result.error_message, "Should explain which columns are missing"

    def test_wrong_column_order_rejected(self, tmp_path: Path):
        """Columns in wrong order should be rejected (schema is positional)."""
        csv_path = tmp_path / "test.csv"
        # Swap first two columns
        content = "source_type,timestamp,citation,key_finding,confidence,notes\n"
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        assert not result.schema_valid, "Wrong column order should fail validation"

    def test_whitespace_in_column_names(self, tmp_path: Path):
        """Whitespace in column names should be normalized."""
        csv_path = tmp_path / "test.csv"
        content = " timestamp , source_type , citation , key_finding , confidence , notes \n"
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Should either strip whitespace and pass, or fail with clear error
        # Current implementation strips - verify behavior
        assert result.schema_valid


class TestEmptyAndMalformed:
    """Test empty and malformed file handling."""

    def test_empty_file_clear_error(self, tmp_path: Path):
        """Empty CSV should have distinct error from schema mismatch."""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("", encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        assert not result.schema_valid, "Empty file should fail validation"
        # Error should indicate empty, not just "schema mismatch"
        # This is a UX improvement if currently unclear

    def test_headers_only_handled(self, tmp_path: Path):
        """CSV with headers but no data rows should be handled."""
        csv_path = tmp_path / "test.csv"
        content = f"{','.join(EVIDENCE_COLUMNS)}\n"
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Headers-only file should pass schema validation (schema is correct)
        assert result.schema_valid, "Headers-only file should pass schema check"

    def test_mixed_line_endings_handled(self, tmp_path: Path):
        """Mixed line endings (CRLF/LF/CR) should be handled."""
        csv_path = tmp_path / "test.csv"
        # Mix of CRLF, LF, and CR
        content = f"{','.join(EVIDENCE_COLUMNS)}\r\n"
        content += "2025-01-25T10:00:00,journal,cite1,find1,high,note1\n"
        content += "2025-01-25T11:00:00,journal,cite2,find2,high,note2\r"
        csv_path.write_text(content, encoding="utf-8")

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        # Should handle without crash
        assert result is not None

    def test_file_not_found_error(self, tmp_path: Path):
        """Non-existent file should produce clear error."""
        csv_path = tmp_path / "nonexistent.csv"

        result = validate_csv_schema(csv_path, EVIDENCE_COLUMNS)

        assert not result.schema_valid
        assert result.error_message
        assert "not found" in result.error_message.lower() or "does not exist" in result.error_message.lower()

    def test_directory_instead_of_file(self, tmp_path: Path):
        """Directory path instead of file should produce clear error."""
        dir_path = tmp_path / "not_a_file"
        dir_path.mkdir()

        result = validate_csv_schema(dir_path, EVIDENCE_COLUMNS)

        assert not result.schema_valid
        assert result.error_message


def test_malformed_csv_factory(malformed_csv_factory, tmp_path: Path):
    """Verify factory creates files correctly."""
    from tests.adversarial.conftest import AttackVector

    vector = AttackVector("test", "content", "csv", "handle", "test")
    path = malformed_csv_factory(vector, "test.csv")

    assert path.exists()
    assert path.read_text(encoding="utf-8") == "content"
