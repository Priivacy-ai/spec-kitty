"""Status doctor: health check framework for operational hygiene.

Detects stale claims, orphan workspaces, materialization drift,
and derived-view drift. Reports problems and recommends actions
but NEVER modifies files (read-only).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path

from .models import StatusSnapshot
from .reducer import SNAPSHOT_FILENAME, reduce
from .store import read_events

logger = logging.getLogger(__name__)


class Severity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class Category(StrEnum):
    STALE_CLAIM = "stale_claim"
    ORPHAN_WORKSPACE = "orphan_workspace"
    MATERIALIZATION_DRIFT = "materialization_drift"
    DERIVED_VIEW_DRIFT = "derived_view_drift"


@dataclass
class Finding:
    """A single health check finding."""

    severity: Severity
    category: Category
    wp_id: str | None
    message: str
    recommended_action: str


@dataclass
class DoctorResult:
    """Aggregate result of all health checks."""

    feature_slug: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        return any(f.severity == Severity.WARNING for f in self.findings)

    @property
    def is_healthy(self) -> bool:
        return len(self.findings) == 0

    def findings_by_category(self, category: Category) -> list[Finding]:
        return [f for f in self.findings if f.category == category]


def _load_or_reduce_snapshot(
    feature_dir: Path,
    feature_slug: str,
) -> dict | None:
    """Load snapshot from status.json or reduce from events.

    Returns the snapshot as a dict (work_packages keyed by WP ID),
    or None if neither source is available.
    """
    # Try status.json first
    status_path = feature_dir / SNAPSHOT_FILENAME
    if status_path.exists():
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError):
            logger.debug("Could not read status.json, trying event log")

    # Try reducing from event log
    try:
        events = read_events(feature_dir)
        if events:
            snapshot = reduce(events)
            return snapshot.to_dict()
    except Exception:
        logger.debug("Could not reduce from event log", exc_info=True)

    return None


def check_stale_claims(
    feature_dir: Path,
    snapshot: dict,
    *,
    claimed_threshold_days: int = 7,
    in_progress_threshold_days: int = 14,
) -> list[Finding]:
    """Check for WPs stuck in claimed or in_progress."""
    findings: list[Finding] = []
    now = datetime.now(timezone.utc)

    work_packages = snapshot.get("work_packages", {})
    for wp_id, wp_state in work_packages.items():
        lane = wp_state.get("lane")
        last_transition_at = wp_state.get("last_transition_at")

        if not last_transition_at:
            continue

        try:
            transition_time = datetime.fromisoformat(last_transition_at)
        except (ValueError, TypeError):
            continue

        age_days = (now - transition_time).days

        if lane == "claimed" and age_days > claimed_threshold_days:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    category=Category.STALE_CLAIM,
                    wp_id=wp_id,
                    message=(
                        f"{wp_id} has been in 'claimed' for {age_days} days "
                        f"(threshold: {claimed_threshold_days} days). "
                        f"Actor: {wp_state.get('actor', 'unknown')}"
                    ),
                    recommended_action=(
                        f"Either begin work on {wp_id} (move to in_progress) "
                        f"or release the claim (move back to planned)."
                    ),
                )
            )

        if lane == "in_progress" and age_days > in_progress_threshold_days:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    category=Category.STALE_CLAIM,
                    wp_id=wp_id,
                    message=(
                        f"{wp_id} has been in 'in_progress' for {age_days} days "
                        f"(threshold: {in_progress_threshold_days} days). "
                        f"Actor: {wp_state.get('actor', 'unknown')}"
                    ),
                    recommended_action=(
                        f"Check if {wp_id} is blocked (move to blocked with reason) "
                        f"or complete the work (move to for_review)."
                    ),
                )
            )

    return findings


def check_orphan_workspaces(
    repo_root: Path,
    feature_slug: str,
    snapshot: dict,
) -> list[Finding]:
    """Detect orphan worktrees for completed/canceled features."""
    findings: list[Finding] = []

    # Check if all WPs are in terminal states
    work_packages = snapshot.get("work_packages", {})
    if not work_packages:
        return findings

    terminal_lanes = {"done", "canceled"}
    all_terminal = all(
        wp.get("lane") in terminal_lanes for wp in work_packages.values()
    )

    if not all_terminal:
        return findings  # Feature still has active WPs, worktrees are legitimate

    # Scan for worktrees matching this feature
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return findings

    feature_pattern = f"{feature_slug}-WP*"
    orphan_dirs = list(worktrees_dir.glob(feature_pattern))

    for orphan_dir in orphan_dirs:
        if orphan_dir.is_dir():
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    category=Category.ORPHAN_WORKSPACE,
                    wp_id=None,
                    message=(
                        f"Worktree '{orphan_dir.name}' exists but all WPs in "
                        f"'{feature_slug}' are terminal "
                        f"({', '.join(sorted(terminal_lanes))}). "
                        f"Path: {orphan_dir}"
                    ),
                    recommended_action=(
                        f"Remove the orphan worktree: "
                        f"git worktree remove {orphan_dir.name}"
                    ),
                )
            )

    return findings


def check_drift(feature_dir: Path) -> list[Finding]:
    """Delegate to validation engine for drift detection.

    Uses try/except import to handle the case where WP11
    (validate) is not yet implemented.
    """
    findings: list[Finding] = []
    try:
        from specify_cli.status.validate import (
            validate_derived_views,
            validate_materialization_drift,
        )
    except ImportError:
        # Validation engine not available yet (WP11 not merged)
        return findings

    # Materialization drift
    drift_findings = validate_materialization_drift(feature_dir)
    for msg in drift_findings:
        findings.append(
            Finding(
                severity=Severity.WARNING,
                category=Category.MATERIALIZATION_DRIFT,
                wp_id=None,
                message=msg,
                recommended_action=(
                    "Run 'spec-kitty agent status materialize' to regenerate "
                    "status.json from the canonical event log."
                ),
            )
        )

    # Derived-view drift
    try:
        status_path = feature_dir / SNAPSHOT_FILENAME
        if status_path.exists():
            snapshot = json.loads(status_path.read_text(encoding="utf-8"))
            from specify_cli.status.phase import resolve_phase

            phase, _ = resolve_phase(feature_dir.parent.parent, feature_dir.name)
            view_findings = validate_derived_views(
                feature_dir,
                snapshot.get("work_packages", {}),
                phase,
            )
            for msg in view_findings:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        category=Category.DERIVED_VIEW_DRIFT,
                        wp_id=None,
                        message=msg,
                        recommended_action=(
                            "Run 'spec-kitty agent status materialize' to "
                            "regenerate derived views from status.json."
                        ),
                    )
                )
    except Exception:
        logger.debug("Could not check derived-view drift", exc_info=True)

    return findings


def run_doctor(
    feature_dir: Path,
    feature_slug: str,
    repo_root: Path,
    *,
    stale_claimed_days: int = 7,
    stale_in_progress_days: int = 14,
) -> DoctorResult:
    """Run all health checks for a feature.

    This is the main entry point. It loads the snapshot (from status.json
    or by reducing the event log), then runs all checks.

    Args:
        feature_dir: Path to the feature's kitty-specs directory.
        feature_slug: Feature identifier (e.g., "034-feature-name").
        repo_root: Path to the repository root.
        stale_claimed_days: Days before a claimed WP is flagged as stale.
        stale_in_progress_days: Days before an in_progress WP is flagged.

    Returns:
        DoctorResult with all findings.

    Raises:
        FileNotFoundError: If feature_dir does not exist.
    """
    if not feature_dir.exists():
        raise FileNotFoundError(
            f"Feature directory does not exist: {feature_dir}"
        )

    result = DoctorResult(feature_slug=feature_slug)

    # Load snapshot (from status.json or reduce from events)
    snapshot = _load_or_reduce_snapshot(feature_dir, feature_slug)

    if snapshot:
        result.findings.extend(
            check_stale_claims(
                feature_dir,
                snapshot,
                claimed_threshold_days=stale_claimed_days,
                in_progress_threshold_days=stale_in_progress_days,
            )
        )
        result.findings.extend(
            check_orphan_workspaces(repo_root, feature_slug, snapshot)
        )
        result.findings.extend(check_drift(feature_dir))

    return result
