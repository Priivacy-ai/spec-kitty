"""LintFinding and DecayReport data models for the charter lint pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

SEVERITY_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class LintFinding:
    """A single charter-decay finding from one checker."""

    category: str
    """Broad bucket, e.g. 'orphan', 'contradiction', 'staleness', 'reference_integrity'."""

    type: str
    """Fine-grained type within the category, e.g. 'orphaned_directive'."""

    id: str
    """Stable finding ID, usually the URN of the offending node."""

    severity: str
    """One of: 'low', 'medium', 'high', 'critical'."""

    message: str
    """Human-readable description of the problem."""

    feature_id: str | None = None
    """Optional: which feature scope this finding belongs to."""

    remediation_hint: str | None = None
    """Optional: what the operator should do to fix this."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "type": self.type,
            "id": self.id,
            "severity": self.severity,
            "message": self.message,
            "feature_id": self.feature_id,
            "remediation_hint": self.remediation_hint,
        }


@dataclass
class DecayReport:
    """Aggregated output from all charter lint checkers."""

    findings: list[LintFinding] = field(default_factory=list)
    scanned_at: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat()
    )
    feature_scope: str | None = None
    duration_seconds: float = 0.0
    drg_node_count: int = 0
    drg_edge_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned_at": self.scanned_at,
            "feature_scope": self.feature_scope,
            "duration_seconds": self.duration_seconds,
            "drg_node_count": self.drg_node_count,
            "drg_edge_count": self.drg_edge_count,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def filter_by_severity(self, min_severity: str) -> DecayReport:
        """Return a new DecayReport containing only findings at or above ``min_severity``."""
        threshold = SEVERITY_ORDER.get(min_severity, 0)
        filtered = [
            f for f in self.findings if SEVERITY_ORDER.get(f.severity, 0) >= threshold
        ]
        return DecayReport(
            findings=filtered,
            scanned_at=self.scanned_at,
            feature_scope=self.feature_scope,
            duration_seconds=self.duration_seconds,
            drg_node_count=self.drg_node_count,
            drg_edge_count=self.drg_edge_count,
        )
