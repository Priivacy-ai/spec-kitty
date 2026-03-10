"""CSV schema validation for research mission artifacts.

This module provides reusable utilities to validate that CSV files match
their expected schemas. Used by upgrade migrations to detect schema
mismatches and by validators to ensure data integrity.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CSVSchemaValidation:
    """Result of CSV schema validation.

    Attributes:
        file_path: Path to the CSV file being validated
        expected_columns: List of column names in expected order
        actual_columns: List of column names found in file (None if file missing/unreadable)
        schema_valid: True if actual columns match expected exactly
        error_message: Error message if validation failed (None if valid)
    """

    file_path: Path
    expected_columns: list[str]
    actual_columns: list[str] | None
    schema_valid: bool
    error_message: str | None

    def format_mismatch_report(self, csv_name: str) -> str:
        """Format user-friendly schema mismatch report.

        Args:
            csv_name: Display name for the CSV file (e.g., "evidence-log.csv")

        Returns:
            Formatted multi-line string with schema comparison and migration tips
        """
        if self.schema_valid:
            return f"✅ {csv_name} schema is correct"

        lines = [
            f"⚠️  Schema mismatch: {csv_name}",
            "",
            f"Expected: {','.join(self.expected_columns)}",
            f"Actual:   {','.join(self.actual_columns or ['<missing>'])}",
            "",
            "To fix this schema mismatch:",
            "1. Read canonical schema in .claude/commands/spec-kitty.implement.md",
            "2. Create new CSV with correct headers",
            "3. Map old data → new schema (LLM agents can help)",
            "4. Replace old file",
            "",
            "📖 See 'Research CSV Schemas' section in implement.md for details",
        ]
        return "\n".join(lines)


def validate_csv_schema(csv_path: Path, expected_columns: list[str]) -> CSVSchemaValidation:
    """Validate CSV headers match expected schema exactly.

    Checks that:
    - File exists and is readable
    - CSV has headers (first row)
    - Column names match expected list exactly
    - Column order matches expected order

    Args:
        csv_path: Path to CSV file to validate
        expected_columns: List of required column names in expected order

    Returns:
        CSVSchemaValidation with validation results
    """
    if not csv_path.exists():
        return CSVSchemaValidation(
            file_path=csv_path,
            expected_columns=expected_columns,
            actual_columns=None,
            schema_valid=False,
            error_message="File does not exist",
        )

    try:
        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            actual_columns = next(reader, None)

            # Strip whitespace and filter out comments
            if actual_columns:
                actual_columns = [
                    col.strip() for col in actual_columns if col.strip() and not col.strip().startswith("#")
                ]

            # Validate exact match (names and order)
            schema_valid = actual_columns is not None and actual_columns == expected_columns

            return CSVSchemaValidation(
                file_path=csv_path,
                expected_columns=expected_columns,
                actual_columns=actual_columns,
                schema_valid=schema_valid,
                error_message=None if schema_valid else "Schema mismatch",
            )
    except Exception as exc:
        return CSVSchemaValidation(
            file_path=csv_path,
            expected_columns=expected_columns,
            actual_columns=None,
            schema_valid=False,
            error_message=f"Error reading CSV: {exc}",
        )


__all__ = [
    "CSVSchemaValidation",
    "validate_csv_schema",
]
