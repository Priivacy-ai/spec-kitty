"""Citation and bibliography validation for the research mission.

This module keeps the research CSV artifacts (evidence log + source
register) healthy by catching missing citations, invalid enumerations,
and malformed entries. Validation follows a progressive approach:

* Level 1 (errors)   – Completeness issues that block the workflow.
* Level 2 (warnings) – Citation formatting issues (BibTeX / APA / Simple).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Literal

BIBTEX_PATTERN = r"@\w+\{[\w-]+,"
APA_PATTERN = r"^[\w\s\.,&]+?,\s?.+\(\d{4}\)\."
SIMPLE_PATTERN = r"^.+\(\d{4}\)\..+\."

VALID_SOURCE_TYPES = ["journal", "conference", "book", "web", "preprint"]
VALID_CONFIDENCE_LEVELS = ["high", "medium", "low"]
VALID_RELEVANCE_LEVELS = ["high", "medium", "low"]
VALID_SOURCE_STATUS = ["reviewed", "pending", "archived"]

EVIDENCE_REQUIRED_COLUMNS = [
    "timestamp",
    "source_type",
    "citation",
    "key_finding",
    "confidence",
    "notes",
]

SOURCE_REGISTER_REQUIRED_COLUMNS = [
    "source_id",
    "citation",
    "url",
    "accessed_date",
    "relevance",
    "status",
]


class ResearchValidationError(Exception):
    """Raised when research validation fails unexpectedly."""


class CitationFormat(str, Enum):
    """Supported citation formats."""

    BIBTEX = "bibtex"
    APA = "apa"
    SIMPLE = "simple"
    UNKNOWN = "unknown"


@dataclass
class CitationIssue:
    """Single citation validation issue."""

    line_number: int
    field: str
    issue_type: Literal["error", "warning"]
    message: str


@dataclass
class CitationValidationResult:
    """Result of citation validation."""

    file_path: Path
    total_entries: int
    valid_entries: int
    issues: List[CitationIssue]

    @property
    def has_errors(self) -> bool:
        """Return True if any issues are errors (blocking)."""

        return any(issue.issue_type == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.issue_type == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.issue_type == "warning")

    def format_report(self) -> str:
        """Format issues in a reviewer-friendly string."""

        output = [
            f"Citation Validation: {self.file_path.name}",
            f"Total entries: {self.total_entries}",
            f"Valid: {self.valid_entries}",
            f"Errors: {self.error_count}",
            f"Warnings: {self.warning_count}",
            "",
        ]

        if self.issues:
            errors = [i for i in self.issues if i.issue_type == "error"]
            warnings = [i for i in self.issues if i.issue_type == "warning"]

            if errors:
                output.append("ERRORS (must fix):")
                for issue in errors:
                    output.append(f"  Line {issue.line_number} ({issue.field}): {issue.message}")
                output.append("")

            if warnings:
                output.append("WARNINGS (recommended fixes):")
                for issue in warnings:
                    output.append(f"  Line {issue.line_number} ({issue.field}): {issue.message}")

        return "\n".join(output)


def _missing_columns(fieldnames: Iterable[str] | None, required: list[str]) -> list[str]:
    if not fieldnames:
        return required.copy()
    return [col for col in required if col not in fieldnames]


def is_bibtex_format(citation: str) -> bool:
    """Return True when the citation appears to use BibTeX syntax."""

    return bool(re.match(BIBTEX_PATTERN, citation.strip()))


def is_apa_format(citation: str) -> bool:
    """Return True when the citation appears to use APA style."""

    return bool(re.match(APA_PATTERN, citation.strip()))


def is_simple_format(citation: str) -> bool:
    """Return True when the citation matches the simplified fallback format."""

    return bool(re.match(SIMPLE_PATTERN, citation.strip()))


def detect_citation_format(citation: str) -> CitationFormat:
    """Detect the most likely citation format for the given string."""

    if is_bibtex_format(citation):
        return CitationFormat.BIBTEX
    if is_apa_format(citation):
        return CitationFormat.APA
    if is_simple_format(citation):
        return CitationFormat.SIMPLE
    return CitationFormat.UNKNOWN


def _missing_file_result(path: Path, kind: str) -> CitationValidationResult:
    return CitationValidationResult(
        file_path=path,
        total_entries=0,
        valid_entries=0,
        issues=[
            CitationIssue(
                line_number=0,
                field="file",
                issue_type="error",
                message=f"{kind} not found: {path}",
            )
        ],
    )


def validate_citations(evidence_log_path: Path) -> CitationValidationResult:
    """Validate research/evidence-log.csv."""

    if not evidence_log_path.exists():
        return _missing_file_result(evidence_log_path, "Evidence log")

    issues: list[CitationIssue] = []
    total = 0
    valid = 0

    try:
        with evidence_log_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing_columns = _missing_columns(reader.fieldnames, EVIDENCE_REQUIRED_COLUMNS)
            if missing_columns:
                issues.append(
                    CitationIssue(
                        line_number=1,
                        field="headers",
                        issue_type="error",
                        message=f"Missing required columns: {', '.join(missing_columns)}",
                    )
                )
                return CitationValidationResult(evidence_log_path, 0, 0, issues)

            for line_number, row in enumerate(reader, start=2):
                total += 1
                entry_valid = True

                citation = (row.get("citation") or "").strip()
                source_type = (row.get("source_type") or "").strip()
                confidence = (row.get("confidence") or "").strip()
                key_finding = (row.get("key_finding") or "").strip()

                if not citation:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="citation",
                            issue_type="error",
                            message="Citation is empty",
                        )
                    )
                    entry_valid = False

                if source_type not in VALID_SOURCE_TYPES:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="source_type",
                            issue_type="error",
                            message=(
                                f"Invalid source_type '{source_type}'. "
                                f"Must be one of: {', '.join(VALID_SOURCE_TYPES)}"
                            ),
                        )
                    )
                    entry_valid = False

                if confidence and confidence not in VALID_CONFIDENCE_LEVELS:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="confidence",
                            issue_type="error",
                            message=(
                                f"Invalid confidence '{confidence}'. "
                                f"Must be one of: {', '.join(VALID_CONFIDENCE_LEVELS)}"
                            ),
                        )
                    )
                    entry_valid = False

                if not key_finding:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="key_finding",
                            issue_type="warning",
                            message="Key finding is empty – document the main takeaway for traceability",
                        )
                    )

                if citation:
                    fmt = detect_citation_format(citation)
                    if fmt is CitationFormat.UNKNOWN:
                        issues.append(
                            CitationIssue(
                                line_number=line_number,
                                field="citation",
                                issue_type="warning",
                                message="Citation format not recognized. Prefer BibTeX or APA for consistency.",
                            )
                        )

                if entry_valid:
                    valid += 1

    except csv.Error as exc:
        issues.append(
            CitationIssue(
                line_number=0,
                field="file",
                issue_type="error",
                message=f"CSV parsing error: {exc}",
            )
        )

    return CitationValidationResult(evidence_log_path, total, valid, issues)


def validate_source_register(source_register_path: Path) -> CitationValidationResult:
    """Validate research/source-register.csv."""

    if not source_register_path.exists():
        return _missing_file_result(source_register_path, "Source register")

    issues: list[CitationIssue] = []
    total = 0
    valid = 0
    seen_ids: set[str] = set()

    try:
        with source_register_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing_columns = _missing_columns(reader.fieldnames, SOURCE_REGISTER_REQUIRED_COLUMNS)
            if missing_columns:
                issues.append(
                    CitationIssue(
                        line_number=1,
                        field="headers",
                        issue_type="error",
                        message=f"Missing required columns: {', '.join(missing_columns)}",
                    )
                )
                return CitationValidationResult(source_register_path, 0, 0, issues)

            for line_number, row in enumerate(reader, start=2):
                total += 1
                entry_valid = True

                source_id = (row.get("source_id") or "").strip()
                citation = (row.get("citation") or "").strip()
                relevance = (row.get("relevance") or "").strip()
                status = (row.get("status") or "").strip()

                if not source_id:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="source_id",
                            issue_type="error",
                            message="source_id is empty",
                        )
                    )
                    entry_valid = False
                elif source_id in seen_ids:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="source_id",
                            issue_type="error",
                            message=f"Duplicate source_id '{source_id}' (must be unique)",
                        )
                    )
                    entry_valid = False
                else:
                    seen_ids.add(source_id)

                if not citation:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="citation",
                            issue_type="error",
                            message="Citation is empty",
                        )
                    )
                    entry_valid = False
                else:
                    fmt = detect_citation_format(citation)
                    if fmt is CitationFormat.UNKNOWN:
                        issues.append(
                            CitationIssue(
                                line_number=line_number,
                                field="citation",
                                issue_type="warning",
                                message="Citation format not recognized. Prefer BibTeX or APA for consistency.",
                            )
                        )

                if relevance and relevance not in VALID_RELEVANCE_LEVELS:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="relevance",
                            issue_type="error",
                            message=(
                                f"Invalid relevance '{relevance}'. "
                                f"Must be: {', '.join(VALID_RELEVANCE_LEVELS)}"
                            ),
                        )
                    )
                    entry_valid = False

                if status and status not in VALID_SOURCE_STATUS:
                    issues.append(
                        CitationIssue(
                            line_number=line_number,
                            field="status",
                            issue_type="error",
                            message=(
                                f"Invalid status '{status}'. Must be: {', '.join(VALID_SOURCE_STATUS)}"
                            ),
                        )
                    )
                    entry_valid = False

                if entry_valid:
                    valid += 1

    except csv.Error as exc:
        issues.append(
            CitationIssue(
                line_number=0,
                field="file",
                issue_type="error",
                message=f"CSV parsing error: {exc}",
            )
        )

    return CitationValidationResult(source_register_path, total, valid, issues)


__all__ = [
    "APA_PATTERN",
    "BIBTEX_PATTERN",
    "CitationFormat",
    "CitationIssue",
    "CitationValidationResult",
    "ResearchValidationError",
    "SIMPLE_PATTERN",
    "VALID_CONFIDENCE_LEVELS",
    "VALID_RELEVANCE_LEVELS",
    "VALID_SOURCE_STATUS",
    "VALID_SOURCE_TYPES",
    "detect_citation_format",
    "is_apa_format",
    "is_bibtex_format",
    "is_simple_format",
    "validate_citations",
    "validate_source_register",
]
