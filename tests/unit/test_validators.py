"""Unit tests for research citation validators."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.validators.research import (
    CitationIssue,
    CitationValidationResult,
    CitationFormat,
    detect_citation_format,
    is_apa_format,
    is_bibtex_format,
    is_simple_format,
    validate_citations,
    validate_source_register,
)


@pytest.fixture
def valid_evidence_log(tmp_path: Path) -> Path:
    csv_file = tmp_path / "evidence-log.csv"
    csv_file.write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        '2025-01-15T10:00:00,journal,"Smith, J. (2024). Title. Journal.",Finding text,high,Notes here\n'
        '2025-01-15T11:00:00,conference,"@inproceedings{jones2024,author={Jones}}",Another finding,medium,\n',
        encoding="utf-8",
    )
    return csv_file


@pytest.fixture
def invalid_evidence_log(tmp_path: Path) -> Path:
    csv_file = tmp_path / "evidence-log.csv"
    csv_file.write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        "2025-01-15T10:00:00,invalid,,Empty citation,high,\n"
        "2025-01-15T11:00:00,journal,Not a real citation,Finding,wrong,\n",
        encoding="utf-8",
    )
    return csv_file


@pytest.fixture
def valid_source_register(tmp_path: Path) -> Path:
    csv_file = tmp_path / "source-register.csv"
    csv_file.write_text(
        "source_id,citation,url,accessed_date,relevance,status\n"
        'smith2024,"Smith, J. (2024). Title. Journal.",https://doi.org/10.0/abc,2025-01-15,high,reviewed\n'
        'jones2024,"@inproceedings{jones2024,author={Jones}}",https://dl.acm.org/xyz,2025-01-16,medium,pending\n',
        encoding="utf-8",
    )
    return csv_file


@pytest.fixture
def invalid_source_register(tmp_path: Path) -> Path:
    csv_file = tmp_path / "source-register.csv"
    csv_file.write_text(
        "source_id,citation,url,accessed_date,relevance,status\n"
        ",,,2025-01-15,invalid,done\n"
        "dup,Duplicate citation,,2025-01-16,high,reviewed\n"
        "dup,Duplicate citation,,2025-01-17,high,reviewed\n",
        encoding="utf-8",
    )
    return csv_file


def test_bibtex_format_detection() -> None:
    assert is_bibtex_format("@article{smith2024, title={Title}}")
    assert not is_bibtex_format("Smith, J. (2024). Title.")


def test_apa_format_detection() -> None:
    assert is_apa_format("Smith, J. (2024). Title. Journal, 10(2), 123-145.")
    assert not is_apa_format("@article{smith2024, title={Title}}")


def test_simple_format_detection() -> None:
    assert is_simple_format("Smith (2024). Title. Source.")
    assert not is_simple_format("No year or punctuation")


def test_citation_format_detection() -> None:
    assert detect_citation_format("@article{smith2024,") is CitationFormat.BIBTEX
    assert detect_citation_format("Smith, J. (2024). Title.") is CitationFormat.APA
    assert detect_citation_format("Smith (2024). Title. Source.") is CitationFormat.SIMPLE
    assert detect_citation_format("invalid citation") is CitationFormat.UNKNOWN


def test_validate_citations_valid_file(valid_evidence_log: Path) -> None:
    result = validate_citations(valid_evidence_log)
    assert result.total_entries == 2
    assert result.error_count == 0
    # warnings allowed for certain rows
    assert result.valid_entries == 2


def test_validate_citations_invalid_file(invalid_evidence_log: Path) -> None:
    result = validate_citations(invalid_evidence_log)
    assert result.has_errors
    assert result.error_count >= 2
    assert result.total_entries == 2


def test_validate_citations_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    result = validate_citations(missing)
    assert result.has_errors
    assert "not found" in result.issues[0].message.lower()


def test_validate_source_register_valid_file(valid_source_register: Path) -> None:
    result = validate_source_register(valid_source_register)
    assert result.total_entries == 2
    assert result.error_count == 0
    assert result.valid_entries == 2


def test_validate_source_register_invalid_file(invalid_source_register: Path) -> None:
    result = validate_source_register(invalid_source_register)
    assert result.has_errors
    assert result.error_count >= 3  # empty id, duplicate id, invalid enums


def test_validate_source_register_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    result = validate_source_register(missing)
    assert result.has_errors
    assert "not found" in result.issues[0].message.lower()


def test_validation_result_format_report() -> None:
    result = CitationValidationResult(
        file_path=Path("test.csv"),
        total_entries=3,
        valid_entries=1,
        issues=[
            CitationIssue(2, "citation", "error", "Citation empty"),
            CitationIssue(3, "source_type", "warning", "Format warning"),
        ],
    )
    report = result.format_report()
    assert "ERRORS" in report
    assert "WARNINGS" in report
    assert "Line 2" in report
