"""Data models for the read-only mission-state audit engine.

This module defines the core types used throughout the audit package:
- Severity: ordered StrEnum (error < warning < info)
- MissionFinding: immutable finding record
- MissionAuditResult: per-mission audit outcome
- RepoAuditReport: full repository audit report
- AuditOptions: engine configuration
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class Severity(StrEnum):
    """Audit finding severity level.

    Ordering: error < warning < info (lower index = higher severity).
    Use ``__le__`` / ``__lt__`` for threshold comparisons, e.g.::

        if any(f.severity <= fail_on_threshold for f in findings):
            sys.exit(1)
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __le__(self, other: Severity) -> bool:  # type: ignore[override]
        _order = {"error": 0, "warning": 1, "info": 2}
        return _order[self.value] <= _order[other.value]

    def __lt__(self, other: Severity) -> bool:  # type: ignore[override]
        _order = {"error": 0, "warning": 1, "info": 2}
        return _order[self.value] < _order[other.value]


@dataclass(frozen=True)
class MissionFinding:
    """A single audit finding for a mission artifact.

    Invariants (enforced by callers, not runtime-checked here):
    - ``artifact_path`` must use forward slashes, not OS-native separators.
    - ``artifact_path`` must be relative to the mission directory, never absolute.
    - ``detail`` must not contain any run-varying values (timestamps, PIDs,
      memory addresses) so that deterministic serialization is possible.

    Canonical finding codes are defined in ``detectors.py`` and
    ``identity_adapter.py``; see the WP01 spec for the full table.
    """

    code: str
    severity: Severity
    artifact_path: str
    detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict with severity as its string value."""
        return {
            "artifact_path": self.artifact_path,
            "code": self.code,
            "detail": self.detail,
            "severity": self.severity.value,
        }


@dataclass
class MissionAuditResult:
    """Audit outcome for a single mission directory.

    The engine is responsible for sorting ``findings`` by ``(artifact_path, code)``
    before constructing this object to guarantee deterministic serialization.
    """

    mission_slug: str
    mission_dir: Path
    findings: list[MissionFinding]

    @property
    def has_errors(self) -> bool:
        """True if any finding has ERROR severity."""
        return any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        """True if any finding has WARNING severity."""
        return any(f.severity == Severity.WARNING for f in self.findings)

    @property
    def finding_codes(self) -> set[str]:
        """Set of all finding codes present in this result."""
        return {f.code for f in self.findings}

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict.

        ``mission_dir`` is serialized as a plain string because ``Path`` is
        opaque across platforms; callers should not parse it.
        """
        return {
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "has_errors": self.has_errors,
            "mission_dir": str(self.mission_dir),
            "mission_slug": self.mission_slug,
        }


@dataclass
class RepoAuditReport:
    """Full audit report for a repository's ``kitty-specs/`` tree.

    ``missions`` must be sorted lexicographically by ``mission_slug`` by the
    engine before construction to satisfy NFR-001 (deterministic output).

    ``shape_counters`` maps finding code to total count across all missions.
    ``to_dict()`` sorts this dict by key for determinism.

    ``repo_summary`` shape (produced by the engine)::

        {
            "findings_by_severity": {"error": 5, "info": 3, "warning": 10},
            "missions_with_errors": 3,
            "missions_with_warnings": 7,
            "total_findings": 18,
            "total_missions": 42,
        }
    """

    missions: list[MissionAuditResult]
    shape_counters: dict[str, int]
    repo_summary: dict[str, Any]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict with shape_counters sorted by key."""
        return {
            "missions": [m.to_dict() for m in self.missions],
            "repo_summary": self.repo_summary,
            "shape_counters": dict(sorted(self.shape_counters.items())),
        }


@dataclass
class AuditOptions:
    """Engine configuration passed to ``run_audit()``.

    ``scan_root`` defaults to ``repo_root / "kitty-specs"`` when ``None``
    (never hardcoded here — the engine resolves the default at call time).
    ``fail_on`` is ``None`` for "always exit 0"; set to ``Severity.ERROR``
    to fail on errors only, ``Severity.WARNING`` for errors+warnings, etc.
    """

    repo_root: Path
    scan_root: Path | None = None
    mission_filter: str | None = None
    fail_on: Severity | None = None
