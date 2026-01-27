"""Unit tests for CSV schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.validators.csv_schema import CSVSchemaValidation, validate_csv_schema


@pytest.fixture
def correct_schema_csv(tmp_path: Path) -> Path:
    """CSV file with correct schema."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        "2025-01-25T10:00:00,journal,Citation text,Finding,high,Notes\n",
        encoding="utf-8",
    )
    return csv_file


@pytest.fixture
def wrong_column_names_csv(tmp_path: Path) -> Path:
    """CSV file with wrong column names."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "timestamp,type,ref,finding,confidence,notes\n"
        "2025-01-25T10:00:00,journal,Citation,Finding,high,Notes\n",
        encoding="utf-8",
    )
    return csv_file


@pytest.fixture
def wrong_column_order_csv(tmp_path: Path) -> Path:
    """CSV file with correct columns but wrong order."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "source_type,timestamp,citation,key_finding,confidence,notes\n"
        "journal,2025-01-25T10:00:00,Citation,Finding,high,Notes\n",
        encoding="utf-8",
    )
    return csv_file


@pytest.fixture
def missing_columns_csv(tmp_path: Path) -> Path:
    """CSV file with missing columns."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "timestamp,citation,key_finding\n" "2025-01-25T10:00:00,Citation,Finding\n", encoding="utf-8"
    )
    return csv_file


@pytest.fixture
def extra_columns_csv(tmp_path: Path) -> Path:
    """CSV file with extra columns."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes,extra\n"
        "2025-01-25T10:00:00,journal,Citation,Finding,high,Notes,Extra data\n",
        encoding="utf-8",
    )
    return csv_file


@pytest.fixture
def empty_csv(tmp_path: Path) -> Path:
    """Empty CSV file."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("", encoding="utf-8")
    return csv_file


@pytest.fixture
def csv_with_comments(tmp_path: Path) -> Path:
    """CSV file with comment headers."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "# This is a comment\n"
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        "2025-01-25T10:00:00,journal,Citation,Finding,high,Notes\n",
        encoding="utf-8",
    )
    return csv_file


EXPECTED_COLUMNS = ["timestamp", "source_type", "citation", "key_finding", "confidence", "notes"]


def test_validate_correct_schema(correct_schema_csv):
    """Test validation passes for correct schema."""
    result = validate_csv_schema(correct_schema_csv, EXPECTED_COLUMNS)

    assert result.schema_valid is True
    assert result.error_message is None
    assert result.actual_columns == EXPECTED_COLUMNS
    assert result.expected_columns == EXPECTED_COLUMNS


def test_validate_wrong_column_names(wrong_column_names_csv):
    """Test validation fails for wrong column names."""
    result = validate_csv_schema(wrong_column_names_csv, EXPECTED_COLUMNS)

    assert result.schema_valid is False
    assert result.error_message == "Schema mismatch"
    assert result.actual_columns != EXPECTED_COLUMNS
    assert "type" in result.actual_columns  # Wrong name
    assert "source_type" not in result.actual_columns  # Missing correct name


def test_validate_wrong_column_order(wrong_column_order_csv):
    """Test validation fails for wrong column order."""
    result = validate_csv_schema(wrong_column_order_csv, EXPECTED_COLUMNS)

    assert result.schema_valid is False
    assert result.error_message == "Schema mismatch"
    # All columns present but wrong order
    assert set(result.actual_columns) == set(EXPECTED_COLUMNS)
    assert result.actual_columns != EXPECTED_COLUMNS


def test_validate_missing_columns(missing_columns_csv):
    """Test validation fails for missing columns."""
    result = validate_csv_schema(missing_columns_csv, EXPECTED_COLUMNS)

    assert result.schema_valid is False
    assert result.error_message == "Schema mismatch"
    assert len(result.actual_columns) < len(EXPECTED_COLUMNS)


def test_validate_extra_columns(extra_columns_csv):
    """Test validation fails for extra columns."""
    result = validate_csv_schema(extra_columns_csv, EXPECTED_COLUMNS)

    assert result.schema_valid is False
    assert result.error_message == "Schema mismatch"
    assert len(result.actual_columns) > len(EXPECTED_COLUMNS)
    assert "extra" in result.actual_columns


def test_validate_file_not_found(tmp_path):
    """Test validation fails gracefully for missing file."""
    nonexistent = tmp_path / "nonexistent.csv"
    result = validate_csv_schema(nonexistent, EXPECTED_COLUMNS)

    assert result.schema_valid is False
    assert result.error_message == "File does not exist"
    assert result.actual_columns is None


def test_validate_empty_csv(empty_csv):
    """Test validation fails for empty CSV."""
    result = validate_csv_schema(empty_csv, EXPECTED_COLUMNS)

    assert result.schema_valid is False
    assert result.error_message == "Schema mismatch"
    # Empty file has no headers
    assert result.actual_columns is None or result.actual_columns == []


def test_validate_csv_with_comment_headers(csv_with_comments):
    """Test CSV with comment line (not headers) fails validation."""
    result = validate_csv_schema(csv_with_comments, EXPECTED_COLUMNS)

    # First line is a comment, second line has headers
    # CSV reader will treat first line as headers
    assert result.schema_valid is False
    assert result.actual_columns != EXPECTED_COLUMNS


def test_format_mismatch_report_correct_schema(correct_schema_csv):
    """Test mismatch report for correct schema."""
    result = validate_csv_schema(correct_schema_csv, EXPECTED_COLUMNS)
    report = result.format_mismatch_report("test.csv")

    assert "✅" in report
    assert "correct" in report.lower()


def test_format_mismatch_report_wrong_schema(wrong_column_names_csv):
    """Test mismatch report for wrong schema."""
    result = validate_csv_schema(wrong_column_names_csv, EXPECTED_COLUMNS)
    report = result.format_mismatch_report("test.csv")

    assert "⚠️" in report
    assert "Schema mismatch" in report
    assert "Expected:" in report
    assert "Actual:" in report
    assert "To fix" in report
    assert "implement.md" in report


def test_format_mismatch_report_missing_file(tmp_path):
    """Test mismatch report for missing file."""
    nonexistent = tmp_path / "nonexistent.csv"
    result = validate_csv_schema(nonexistent, EXPECTED_COLUMNS)
    report = result.format_mismatch_report("nonexistent.csv")

    assert "⚠️" in report
    assert "<missing>" in report


def test_csv_schema_validation_dataclass():
    """Test CSVSchemaValidation dataclass creation."""
    validation = CSVSchemaValidation(
        file_path=Path("/test/path.csv"),
        expected_columns=["a", "b", "c"],
        actual_columns=["a", "b", "c"],
        schema_valid=True,
        error_message=None,
    )

    assert validation.file_path == Path("/test/path.csv")
    assert validation.expected_columns == ["a", "b", "c"]
    assert validation.actual_columns == ["a", "b", "c"]
    assert validation.schema_valid is True
    assert validation.error_message is None


def test_whitespace_handling(tmp_path):
    """Test that whitespace in headers is stripped."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        " timestamp , source_type , citation , key_finding , confidence , notes \n"
        "2025-01-25T10:00:00,journal,Citation,Finding,high,Notes\n",
        encoding="utf-8",
    )

    result = validate_csv_schema(csv_file, EXPECTED_COLUMNS)

    # Whitespace should be stripped, schema should match
    assert result.schema_valid is True
    assert result.actual_columns == EXPECTED_COLUMNS
