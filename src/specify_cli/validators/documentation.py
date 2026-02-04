"""Documentation mission validation for Spec Kitty.

This module enforces documentation mission requirements during validation
and acceptance flows. It checks:

* documentation_state exists in meta.json
* gap-analysis.md artifact exists in the feature directory
* Recency rule: last_audit_date >= feature created_at

Validation is mission-scoped: checks only run for features whose mission
is ``documentation``. Non-doc missions are unaffected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional


class DocumentationValidationError(Exception):
    """Raised when documentation mission validation fails unexpectedly."""


@dataclass
class DocValidationIssue:
    """Single documentation validation issue."""

    check: str
    issue_type: Literal["error", "warning"]
    message: str
    remediation: str


@dataclass
class DocValidationResult:
    """Result of documentation mission validation."""

    feature_dir: Path
    is_documentation_mission: bool
    issues: List[DocValidationIssue] = field(default_factory=list)

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

    @property
    def passed(self) -> bool:
        """Return True if no errors (warnings are acceptable)."""
        return not self.has_errors

    def error_messages(self) -> List[str]:
        """Return list of error messages for integration with acceptance."""
        return [
            f"[doc-validation] {issue.message}" for issue in self.issues if issue.issue_type == "error"
        ]

    def format_report(self) -> str:
        """Format issues in a reviewer-friendly string."""
        output = [
            f"Documentation Validation: {self.feature_dir.name}",
            f"Is documentation mission: {self.is_documentation_mission}",
            f"Errors: {self.error_count}",
            f"Warnings: {self.warning_count}",
            "",
        ]

        if not self.is_documentation_mission:
            output.append("Skipped: not a documentation mission.")
            return "\n".join(output)

        if not self.issues:
            output.append("All documentation checks passed.")
            return "\n".join(output)

        errors = [i for i in self.issues if i.issue_type == "error"]
        warnings = [i for i in self.issues if i.issue_type == "warning"]

        if errors:
            output.append("ERRORS (must fix):")
            for issue in errors:
                output.append(f"  [{issue.check}] {issue.message}")
                output.append(f"    Remediation: {issue.remediation}")
            output.append("")

        if warnings:
            output.append("WARNINGS (recommended fixes):")
            for issue in warnings:
                output.append(f"  [{issue.check}] {issue.message}")
                output.append(f"    Remediation: {issue.remediation}")

        return "\n".join(output)


def _read_meta(feature_dir: Path) -> Optional[dict]:
    """Read meta.json from feature directory, returning None if missing/invalid."""
    meta_file = feature_dir / "meta.json"
    if not meta_file.exists():
        return None
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _is_documentation_mission(meta: Optional[dict]) -> bool:
    """Check if a feature is a documentation mission."""
    if meta is None:
        return False
    return meta.get("mission") == "documentation"


def _parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parse an ISO datetime string, returning None on failure."""
    if not dt_str:
        return None
    try:
        # Handle both with and without timezone
        # Python 3.11+ fromisoformat handles timezone suffixes
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def validate_documentation_mission(feature_dir: Path) -> DocValidationResult:
    """Validate documentation mission requirements for a feature.

    Checks performed (only for documentation missions):
    1. documentation_state must exist in meta.json
    2. gap-analysis.md must exist at feature_dir/gap-analysis.md
    3. Recency rule: last_audit_date >= created_at

    Args:
        feature_dir: Path to the feature directory (kitty-specs/<feature>/)

    Returns:
        DocValidationResult with any issues found
    """
    meta = _read_meta(feature_dir)
    is_doc = _is_documentation_mission(meta)

    result = DocValidationResult(
        feature_dir=feature_dir,
        is_documentation_mission=is_doc,
    )

    # Skip all checks for non-documentation missions
    if not is_doc:
        return result

    # Check 1: documentation_state must exist in meta.json
    doc_state = meta.get("documentation_state") if meta else None
    if doc_state is None:
        result.issues.append(
            DocValidationIssue(
                check="documentation_state_exists",
                issue_type="error",
                message="documentation_state is missing from meta.json",
                remediation=(
                    "Run the planning phase to initialize documentation state. "
                    "Use: spec-kitty plan or ensure documentation_state is populated "
                    "in meta.json via initialize_documentation_state()."
                ),
            )
        )

    # Check 2: gap-analysis.md must exist
    gap_analysis_path = feature_dir / "gap-analysis.md"
    if not gap_analysis_path.exists():
        result.issues.append(
            DocValidationIssue(
                check="gap_analysis_exists",
                issue_type="error",
                message=f"gap-analysis.md not found at {gap_analysis_path}",
                remediation=(
                    "Run gap analysis for this documentation feature. "
                    "Use: spec-kitty plan (which generates gap-analysis.md) "
                    "or create gap-analysis.md manually with audit results."
                ),
            )
        )

    # Check 3: Recency rule - last_audit_date >= created_at
    if doc_state is not None:
        last_audit_str = doc_state.get("last_audit_date")
        created_at_str = meta.get("created_at") if meta else None

        if last_audit_str is None:
            result.issues.append(
                DocValidationIssue(
                    check="audit_recency",
                    issue_type="error",
                    message="last_audit_date is null in documentation_state",
                    remediation=(
                        "Run gap analysis to set last_audit_date. "
                        "Use: spec-kitty plan or update documentation_state "
                        "with set_audit_metadata()."
                    ),
                )
            )
        elif created_at_str:
            last_audit_dt = _parse_iso_datetime(last_audit_str)
            created_at_dt = _parse_iso_datetime(created_at_str)

            if last_audit_dt is not None and created_at_dt is not None:
                if last_audit_dt < created_at_dt:
                    result.issues.append(
                        DocValidationIssue(
                            check="audit_recency",
                            issue_type="error",
                            message=(
                                f"last_audit_date ({last_audit_str}) is older than "
                                f"feature created_at ({created_at_str}). "
                                "Documentation audit is stale."
                            ),
                            remediation=(
                                "Re-run gap analysis to refresh the audit. "
                                "The audit must be performed after the feature was created."
                            ),
                        )
                    )

    return result


__all__ = [
    "DocValidationIssue",
    "DocValidationResult",
    "DocumentationValidationError",
    "validate_documentation_mission",
]
