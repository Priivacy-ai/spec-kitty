"""Status emit orchestration pipeline.

Single entry point for ALL state changes in the canonical status model.
Validates a transition, appends an event to the JSONL log, materializes
a status snapshot, updates legacy compatibility views, and emits SaaS
telemetry.

Pipeline order (critical -- do not reorder):
    1. resolve_lane_alias(to_lane)
    2. Derive from_lane from last event for this WP (or "planned")
    3. validate_transition(from_lane, resolved_lane, ...)
    4. Create StatusEvent with ULID event_id
    5. store.append_event(feature_dir, event)
    6. reducer.materialize(feature_dir)
    7. legacy_bridge.update_all_views(feature_dir, snapshot)  [try/except]
    8. _saas_fan_out(event, feature_slug, repo_root)
    9. Return the event
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ulid as _ulid_mod

from .models import (
    DoneEvidence,
    Lane,
    RepoEvidence,
    ReviewApproval,
    StatusEvent,
    VerificationResult,
)
from .transitions import resolve_lane_alias, validate_transition
from . import store as _store
from . import reducer as _reducer

logger = logging.getLogger(__name__)

class TransitionError(Exception):
    """Raised when a status transition is invalid."""


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    if hasattr(_ulid_mod, "new"):
        return _ulid_mod.new().str
    return str(_ulid_mod.ULID())


def _now_utc() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _derive_from_lane(feature_dir: Path, wp_id: str) -> str:
    """Derive the current lane for a WP from canonical reduced state.

    The event log may not be append-ordered by logical transition time,
    so we must reduce the full log to determine the current lane
    deterministically.
    """
    events = _store.read_events(feature_dir)
    if not events:
        return "planned"

    snapshot = _reducer.reduce(events)
    wp_state = snapshot.work_packages.get(wp_id)
    if wp_state is None:
        return "planned"

    lane = wp_state.get("lane")
    if isinstance(lane, str):
        return lane
    return "planned"


def _build_done_evidence(evidence: dict[str, Any]) -> DoneEvidence:
    """Build a DoneEvidence dataclass from a raw dict.

    Raises TransitionError if the evidence dict is missing required
    fields (review.reviewer, review.verdict, review.reference).
    """
    review_data = evidence.get("review")
    if not isinstance(review_data, dict):
        raise TransitionError(
            "Moving to done requires evidence with review.reviewer "
            "review.verdict, and review.reference"
        )
    reviewer = review_data.get("reviewer")
    verdict = review_data.get("verdict")
    reference = review_data.get("reference")
    if (
        not reviewer
        or not verdict
        or not reference
        or not str(reference).strip()
    ):
        raise TransitionError(
            "Moving to done requires evidence with review.reviewer "
            "review.verdict, and review.reference"
        )

    review_approval = ReviewApproval(
        reviewer=reviewer,
        verdict=verdict,
        reference=str(reference),
    )

    repos = [
        RepoEvidence(**r) for r in evidence.get("repos", [])
    ]
    verification = [
        VerificationResult(**v) for v in evidence.get("verification", [])
    ]

    return DoneEvidence(
        review=review_approval,
        repos=repos,
        verification=verification,
    )


def _infer_subtasks_complete(feature_dir: Path, wp_id: str) -> bool:
    """Infer subtask completion from tasks.md checkboxes for a WP section."""
    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.exists():
        return True
    content = tasks_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    in_wp_section = False
    unchecked_found = False

    for line in lines:
        if re.search(rf"^##.*\b{re.escape(wp_id)}\b", line):
            in_wp_section = True
            continue
        if in_wp_section and re.search(r"^##\s+", line):
            break
        if not in_wp_section:
            continue
        if re.match(r"^\s*-\s*\[\s*\]\s+", line):
            unchecked_found = True
            break
    if not in_wp_section:
        return True
    return not unchecked_found


def _infer_implementation_evidence(feature_dir: Path, wp_id: str) -> bool:
    """Infer implementation evidence from prior canonical events for this WP."""
    for event in _store.read_events(feature_dir):
        if event.wp_id == wp_id:
            return True
    return False


def emit_status_transition(
    feature_dir: Path,
    feature_slug: str,
    wp_id: str,
    to_lane: str,
    actor: str,
    *,
    force: bool = False,
    reason: str | None = None,
    evidence: dict | None = None,
    review_ref: str | None = None,
    workspace_context: str | None = None,
    subtasks_complete: bool | None = None,
    implementation_evidence_present: bool | None = None,
    execution_mode: str = "worktree",
    repo_root: Path | None = None,
    policy_metadata: dict | None = None,
) -> StatusEvent:
    """Central orchestration function for all status state changes.

    Performs the entire pipeline: validate, persist event, materialize
    snapshot, update legacy views, and emit SaaS telemetry.

    Validation failures raise TransitionError BEFORE any data is
    persisted. SaaS failures never block canonical persistence.

    Args:
        feature_dir: Path to the kitty-specs feature directory.
        feature_slug: Feature identifier (e.g. "034-feature-name").
        wp_id: Work package identifier (e.g. "WP01").
        to_lane: Target lane (canonical or alias).
        actor: Identity of the actor performing the transition.
        force: If True, bypass guard conditions (requires actor + reason).
        reason: Reason for the transition (required for force and some guards).
        evidence: Evidence dict for done transitions.
        review_ref: Review feedback reference (required for for_review -> in_progress).
        workspace_context: Active workspace context identifier.
        subtasks_complete: Whether subtasks are complete for review handoff.
        implementation_evidence_present: Whether implementation evidence is present.
        execution_mode: "worktree" or "direct_repo".
        repo_root: Repository root for SaaS fan-out (optional).
        policy_metadata: Orchestrator policy metadata dict (optional).

    Returns:
        The persisted StatusEvent.

    Raises:
        TransitionError: If the transition is invalid.
        specify_cli.status.store.StoreError: If the event log is corrupted.
    """
    # Step 1: Resolve alias
    resolved_lane = resolve_lane_alias(to_lane)

    # Step 2: Derive from_lane from last event for this WP
    from_lane = _derive_from_lane(feature_dir, wp_id)

    if workspace_context is None:
        context_root = repo_root if repo_root is not None else feature_dir
        workspace_context = f"{execution_mode}:{context_root}"
    if (
        subtasks_complete is None
        and from_lane == "in_progress"
        and resolved_lane == "for_review"
    ):
        subtasks_complete = _infer_subtasks_complete(feature_dir, wp_id)
    if (
        implementation_evidence_present is None
        and from_lane == "in_progress"
        and resolved_lane == "for_review"
    ):
        implementation_evidence_present = _infer_implementation_evidence(
            feature_dir, wp_id
        )

    # Step 3: Validate the transition
    # Build DoneEvidence early so we can pass it to validate_transition
    done_evidence: DoneEvidence | None = None
    if evidence is not None:
        done_evidence = _build_done_evidence(evidence)

    ok, error_msg = validate_transition(
        from_lane,
        resolved_lane,
        force=force,
        actor=actor,
        workspace_context=workspace_context,
        subtasks_complete=subtasks_complete,
        implementation_evidence_present=implementation_evidence_present,
        reason=reason,
        review_ref=review_ref,
        evidence=done_evidence,
    )
    if not ok:
        raise TransitionError(error_msg)

    # Step 4: Create StatusEvent with ULID event_id
    event = StatusEvent(
        event_id=_generate_ulid(),
        feature_slug=feature_slug,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(resolved_lane),
        at=_now_utc(),
        actor=actor,
        force=force,
        execution_mode=execution_mode,
        reason=reason,
        review_ref=review_ref,
        evidence=done_evidence,
        policy_metadata=policy_metadata,
    )

    # Step 5: Persist event to JSONL log
    _store.append_event(feature_dir, event)

    # Step 6: Materialize snapshot from event log
    try:
        snapshot = _reducer.materialize(feature_dir)
    except Exception:
        logger.warning(
            "Materialization failed after event %s was persisted; "
            "run 'status materialize' to recover",
            event.event_id,
        )
        snapshot = None

    # Step 7: Update legacy bridge views (WP06 may not be merged yet)
    if snapshot is not None:
        try:
            from specify_cli.status.legacy_bridge import update_all_views

            update_all_views(feature_dir, snapshot)
        except ImportError:
            pass  # WP06 not yet available
        except Exception:
            logger.warning(
                "Legacy bridge update failed for event %s; "
                "canonical log and snapshot are unaffected",
                event.event_id,
            )

    # Step 8: SaaS fan-out (never blocks canonical persistence)
    _saas_fan_out(event, feature_slug, repo_root, policy_metadata=policy_metadata)

    # Step 9: Return the event
    return event


def _saas_fan_out(
    event: StatusEvent,
    feature_slug: str,
    repo_root: Path | None,
    *,
    policy_metadata: dict | None = None,
) -> None:
    """Conditionally emit a SaaS telemetry event via the sync pipeline.

    Uses try/except ImportError to handle the 0.1x branch where
    the sync module does not exist. A broad Exception catch ensures
    SaaS failures NEVER block canonical persistence.
    """
    try:
        from specify_cli.sync.events import emit_wp_status_changed

        emit_wp_status_changed(
            wp_id=event.wp_id,
            from_lane=str(event.from_lane),
            to_lane=str(event.to_lane),
            actor=event.actor,
            feature_slug=feature_slug,
            policy_metadata=policy_metadata,
        )
    except ImportError:
        pass  # SaaS sync not available (0.1x branch)
    except Exception:
        logger.warning(
            "SaaS fan-out failed for event %s; canonical log unaffected",
            event.event_id,
        )
