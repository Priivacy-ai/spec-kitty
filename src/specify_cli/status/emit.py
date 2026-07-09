"""Status emit orchestration pipeline.

Single entry point for ALL state changes in the canonical status model.
Validates a transition, appends an event to the JSONL log, materializes
a status snapshot, and emits SaaS telemetry.

The event log is the sole authority for mutable WP state. In explicit
phase-1 compatibility mode (``meta.json`` with ``status_phase: 1``),
this pipeline may mirror the canonical lane into an existing WP
frontmatter ``lane`` field. That mirror is transitional and never
authoritative.

Pipeline order (critical -- do not reorder):
    1. resolve_lane_alias(to_lane)
    2. Derive from_lane from last event for this WP (or "genesis" for unseeded WPs)
    3. validate_transition(from_lane, resolved_lane, ...)
    4. Create StatusEvent with ULID event_id
    5. store.append_event(feature_dir, event)
    6. reducer.materialize(feature_dir)
    7. _saas_fan_out(event, mission_slug, repo_root)
    8. Return the event
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, cast

import ulid as _ulid_mod
from pydantic import ValidationError

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.mission_metadata import load_meta
from specify_cli.frontmatter import FrontmatterError, read_frontmatter, write_frontmatter
from specify_cli.workspace import canonicalize_feature_dir
from .wp_metadata import read_wp_frontmatter

from .models import (
    DoneEvidence,
    GuardContext,
    Lane,
    RepoEvidence,
    ReviewApproval,
    StatusEvent,
    TransitionRequest,
    VerificationResult,
)
from .transitions import resolve_lane_alias, validate_transition
from . import store as _store
from . import reducer as _reducer
from .adapters import fire_dossier_sync, fire_saas_fanout
from .locking import feature_status_lock

logger = logging.getLogger(__name__)

_LEGACY_LANE_FIELD = "lane"

# ---------------------------------------------------------------------------
# SaaS package capability gate (T022, WP04)
# ---------------------------------------------------------------------------
# Detect at import time whether the installed spec_kitty_events supports the
# genesis lane. spec_kitty_events 5.2.0 has no genesis member; 6.0.0+ will add
# it. When genesis is absent from the installed package, fan-out for genesis
# transitions is deliberately skipped rather than silently swallowed by pydantic
# ValidationError in _build_payload_via_model. Canonical local persistence is
# completely unaffected — fan-out is best-effort.
#
# NOTE: once spec-kitty-events 6.0.0 (genesis lane) ships and the pyproject.toml
# constraint is bumped to >=6.0.0,<7.0.0, this gate resolves to True on all
# installs and may eventually be removed.
try:
    import spec_kitty_events as _spec_kitty_events_mod

    _EVENTS_SUPPORTS_GENESIS: bool = "genesis" in {
        lane.value for lane in _spec_kitty_events_mod.Lane
    }
except (ImportError, AttributeError):
    # ImportError: spec_kitty_events not installed. AttributeError: installed but
    # lacks a Lane enum. Either way, treat genesis as unsupported (review nit).
    _EVENTS_SUPPORTS_GENESIS = False


def _load_mission_id(feature_dir: Path) -> str | None:
    """Load the canonical mission_id (ULID) from meta.json.

    Returns None when meta.json is absent or does not contain
    a ``mission_id`` key (legacy missions pre-dating 3.1.1).
    Never raises — missing/corrupt meta is a silent degradation
    (on_malformed="none" absorbs both missing and malformed to None).
    """
    meta = load_meta(feature_dir, allow_missing=True, on_malformed="none")
    if meta is None:
        return None
    raw_id = meta.get("mission_id")
    return str(raw_id) if raw_id else None


class TransitionError(Exception):
    """Raised when a status transition is invalid."""


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    if hasattr(_ulid_mod, "new"):
        return str(_ulid_mod.new().str)
    return str(_ulid_mod.ULID())


# ---------------------------------------------------------------------------
# WP06 (T028) -- pure status-domain helpers
# ---------------------------------------------------------------------------
#
# Per FR-032, the status domain stays free of coordination-layer concerns.
# These helpers are pure: ``build_status_event`` mints a StatusEvent in
# memory (ULID, ISO timestamp, Lane coercion) with no I/O;
# ``append_event_jsonl`` performs a single-line JSONL append with no
# commit and no materialization.
#
# Workflow call sites compose ``build_status_event`` + the coordination
# transaction's ``append_event`` (which calls into store + reducer).
# Compatibility callers may still use ``emit_status_transition``.
# Production workflow code routes through coordination.status_transition
# so event append + outbound fanout are transactionally ordered.

def build_status_event(  # noqa: PLR0913 -- pass-through to a dataclass constructor
    *,
    mission_slug: str,
    wp_id: str,
    from_lane: str,
    to_lane: str,
    actor: str,
    at: str | None = None,
    mission_id: str | None = None,
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: DoneEvidence | None = None,
    policy_metadata: dict[str, Any] | None = None,
) -> StatusEvent:
    """Construct a fresh :class:`StatusEvent` with a new ULID and timestamp.

    Pure: no I/O, no validation, no side effects. Callers that need
    transition validation should run :func:`validate_transition` first
    and let it raise; this helper only assembles a value object.

    Args:
        mission_slug: Human mission identifier (e.g. ``"034-feature"``).
        wp_id: Work-package id (e.g. ``"WP01"``).
        from_lane: Canonical lane the WP is leaving.
        to_lane: Canonical lane the WP enters.
        actor: Identity of the actor performing the transition.
        at: Optional producer occurrence timestamp; defaults to now.
        mission_id: ULID-based machine identity (optional for legacy).
        force: True if this transition bypasses guard conditions.
        execution_mode: ``"worktree"`` or ``"direct_repo"``.
        reason: Optional human reason (required for force).
        review_ref: Optional review-feedback reference.
        evidence: Optional :class:`DoneEvidence` for done transitions.
        policy_metadata: Optional orchestrator policy metadata dict.

    Returns:
        A new :class:`StatusEvent` ready to append to the event log.
    """
    return StatusEvent(
        event_id=_generate_ulid(),
        mission_slug=mission_slug,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at=at or now_utc_iso(),
        actor=actor,
        force=force,
        execution_mode=execution_mode,
        reason=reason,
        review_ref=review_ref,
        evidence=evidence,
        policy_metadata=policy_metadata,
        mission_id=mission_id,
    )


def append_event_jsonl(events_path: Path, event: StatusEvent) -> None:
    """Append a single :class:`StatusEvent` to a JSONL event log.

    Pure I/O: writes one canonical JSON line. Does not materialize,
    does not commit, does not fan out. The caller is responsible for
    holding any required lock.

    Args:
        events_path: Path to the ``status.events.jsonl`` file. Parent
            directories are created on demand.
        event: The :class:`StatusEvent` to append.
    """
    # Delegate to the canonical store implementation so the wire format
    # stays consistent (sorted keys, trailing newline, etc.). The store
    # accepts the feature_dir, not the events_path directly.
    feature_dir = events_path.parent
    feature_dir.mkdir(parents=True, exist_ok=True)
    _store.append_event_verified(feature_dir, event)


def _derive_from_lane(feature_dir: Path, wp_id: str) -> str:
    """Derive the current lane for a WP from canonical reduced state.

    The event log may not be append-ordered by logical transition time,
    so we must reduce the full log to determine the current lane
    deterministically.

    A WP with no lane-state events yet (created but not seeded) is reported as
    ``GENESIS`` — distinct from ``PLANNED`` — so the bootstrap seed is an
    explicit ``genesis -> planned`` transition rather than a dropped
    ``planned -> planned`` self-transition.
    """
    # cast: follow_imports=skip makes _store.read_events/_reducer.reduce return Any
    # (specify_cli.* boundary); the real signatures return list[StatusEvent] and
    # StatusSnapshot respectively. Lane(…).value is str but Lane itself is not str —
    # all casts below are type-only with no behaviour change.
    events = _store.read_events(feature_dir)
    if not events:
        return cast(str, Lane.GENESIS)

    snapshot = _reducer.reduce(events)
    wp_state = snapshot.work_packages.get(wp_id)
    if wp_state is None:
        return cast(str, Lane.GENESIS)

    lane_raw: str | None = cast("str | None", wp_state.get("lane"))
    if lane_raw is not None:
        return cast(str, Lane(lane_raw))
    return cast(str, Lane.GENESIS)


def _build_done_evidence(evidence: dict[str, Any]) -> DoneEvidence:
    """Build a DoneEvidence dataclass from a raw dict.

    Raises TransitionError if the evidence dict is missing required
    fields (review.reviewer, review.verdict, review.reference).
    """
    review_data = evidence.get("review")
    if not isinstance(review_data, dict):
        raise TransitionError("Moving to done requires evidence with review.reviewer review.verdict, and review.reference")
    reviewer = review_data.get("reviewer")
    verdict = review_data.get("verdict")
    reference = review_data.get("reference")
    if not reviewer or not verdict or not reference or not str(reference).strip():
        raise TransitionError("Moving to done requires evidence with review.reviewer review.verdict, and review.reference")

    review_approval = ReviewApproval(
        reviewer=reviewer,
        verdict=verdict,
        reference=str(reference),
    )

    repos = [RepoEvidence(**r) for r in evidence.get("repos", [])]
    verification = [VerificationResult(**v) for v in evidence.get("verification", [])]

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
        if re.search(rf"^#{{2,4}}(?!#).*\b{re.escape(wp_id)}\b", line):
            in_wp_section = True
            continue
        if in_wp_section and re.search(r"^#{2,4}(?!#)\s+", line):
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
    return any(event.wp_id == wp_id for event in _store.read_events(feature_dir))


def _phase1_dual_write_enabled(feature_dir: Path) -> bool:
    """Return True when this feature explicitly requests phase-1 mirroring.

    Uses on_malformed="none" so both missing and malformed meta.json degrade
    to False (non-phase-1) without raising.  A missing-but-logged-warning
    case for malformed files is preserved by checking the file existence first.
    """
    meta = load_meta(feature_dir, allow_missing=True, on_malformed="none")
    if meta is None:
        if (feature_dir / "meta.json").exists():
            logger.warning("Invalid meta.json in %s; skipping phase-1 lane mirror", feature_dir)
        return False
    status_phase = meta.get("status_phase")
    return str(status_phase).strip() == "1"


def _find_wp_file(feature_dir: Path, wp_id: str) -> Path | None:
    """Locate the canonical WP markdown file for *wp_id* under tasks/."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return None

    wp_pattern = re.compile(rf"^{re.escape(wp_id)}(?:[-_.]|\.md$)")
    matches = [path for path in tasks_dir.glob("*.md") if path.name.lower() != "readme.md" and wp_pattern.match(path.name)]
    if len(matches) != 1:
        if len(matches) > 1:
            logger.warning(
                "Multiple work package files matched %s in %s; skipping phase-1 lane mirror",
                wp_id,
                feature_dir,
            )
        return None
    return matches[0]


def _mirror_phase1_frontmatter_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Mirror the canonical lane into legacy frontmatter only in phase-1 mode.

    This is a compatibility bridge for repos still marked ``status_phase: 1``.
    It never creates a new ``lane`` field; it only updates an already-present
    field so stale consumers can observe the canonical state during cutover.
    """
    if not _phase1_dual_write_enabled(feature_dir):
        return

    wp_file = _find_wp_file(feature_dir, wp_id)
    if wp_file is None:
        return

    try:
        wp_meta = read_wp_frontmatter(wp_file)
    except (FrontmatterError, ValidationError) as exc:
        logger.warning("Failed to read %s for phase-1 lane mirror: %s", wp_file, exc)
        return

    wp_meta_dict, _ = wp_meta
    if wp_meta_dict.lane is not None and str(wp_meta_dict.lane).strip() == lane:
        return

    frontmatter, body = read_frontmatter(wp_file)
    if _LEGACY_LANE_FIELD not in frontmatter:
        return
    frontmatter[_LEGACY_LANE_FIELD] = lane
    try:
        write_frontmatter(wp_file, frontmatter, body)
    except FrontmatterError as exc:
        logger.warning("Failed to write %s for phase-1 lane mirror: %s", wp_file, exc)


def _legacy_alias_collapses_to_current_lane(
    raw_lane: str,
    resolved_lane: str,
    from_lane: str,
) -> bool:
    """Return True when a legacy alias resolves to the WP's current lane.

    ``in_review`` used to exist as a separate waypoint before the canonical
    model collapsed review work into ``for_review``. Treating this as a no-op
    preserves compatibility without writing illegal self-transitions.
    """
    normalized = raw_lane.strip().lower()
    return normalized != resolved_lane and resolved_lane == from_lane


def _feature_status_lock_root(feature_dir: Path, repo_root: Path | None) -> Path:
    """Resolve the repo root used for per-feature status locking.

    Thin shim — delegates to the single shared implementation in
    :func:`specify_cli.workspace.root_resolver.resolve_status_lock_root`
    (WP02 / SC-002 consolidation).
    """
    from specify_cli.workspace.root_resolver import resolve_status_lock_root

    return resolve_status_lock_root(feature_dir, repo_root)


def emit_status_transition(  # NOSONAR — central orchestration hub; 15 of 20 params are optional with stable defaults; refactor tracked separately
    feature_dir: TransitionRequest | Path | None = None,
    _legacy_mission_slug: str | None = None,
    wp_id: str | None = None,
    to_lane: str | None = None,
    actor: str | None = None,
    *,
    mission_dir: Path | None = None,
    mission_slug: str | None = None,
    force: bool = False,
    reason: str | None = None,
    evidence: dict[str, Any] | None = None,
    review_ref: str | None = None,
    workspace_context: str | None = None,
    subtasks_complete: bool | None = None,
    implementation_evidence_present: bool | None = None,
    execution_mode: str = "worktree",
    repo_root: Path | None = None,
    policy_metadata: dict[str, Any] | None = None,
    review_result: Any = None,
    ensure_sync_daemon: bool = True,
    sync_dossier: bool = True,
) -> StatusEvent:
    """Central orchestration function for all status state changes.

    Performs the entire pipeline: validate, persist event, materialize
    snapshot, update legacy views, and emit SaaS telemetry.

    Validation failures raise TransitionError BEFORE any data is
    persisted. SaaS failures never block canonical persistence.

    Args:
        feature_dir: Path to the kitty-specs feature directory, or a
            ``TransitionRequest`` for the request-object call path.
        mission_slug: Feature identifier (e.g. "034-feature-name").
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
        review_result: Structured ReviewResult for in_review -> * transitions (optional).
        ensure_sync_daemon: If False, emit SaaS events without starting the local sync daemon.
        sync_dossier: If False, skip dossier sync for this transition.

    Returns:
        The persisted StatusEvent.

    Raises:
        TransitionError: If the transition is invalid.
        specify_cli.status.store.StoreError: If the event log is corrupted.
    """
    current_actor = None
    if isinstance(feature_dir, TransitionRequest):
        request = feature_dir
        mixed_legacy_args = (
            any(
                value is not None
                for value in (
                    _legacy_mission_slug,
                    wp_id,
                    to_lane,
                    actor,
                    mission_dir,
                    mission_slug,
                    reason,
                    evidence,
                    review_ref,
                    workspace_context,
                    subtasks_complete,
                    implementation_evidence_present,
                    repo_root,
                    policy_metadata,
                    review_result,
                )
            )
            or force
            or execution_mode != "worktree"
        )
        if mixed_legacy_args:
            raise TypeError("emit_status_transition accepts either a TransitionRequest or legacy transition arguments, not both")
        feature_dir = request.feature_dir or request.mission_dir
        mission_slug = request.mission_slug or request._legacy_mission_slug
        wp_id = request.wp_id
        to_lane = request.to_lane
        actor = request.actor
        force = request.force
        reason = request.reason
        evidence = request.evidence
        review_ref = request.review_ref
        workspace_context = request.workspace_context
        subtasks_complete = request.subtasks_complete
        implementation_evidence_present = request.implementation_evidence_present
        current_actor = request.current_actor
        execution_mode = request.execution_mode
        repo_root = request.repo_root
        policy_metadata = request.policy_metadata
        review_result = request.review_result
    else:
        feature_dir = feature_dir or mission_dir
        mission_slug = mission_slug or _legacy_mission_slug

    if feature_dir is None or mission_slug is None or wp_id is None or to_lane is None or actor is None:
        raise TypeError("emit_status_transition requires feature_dir/mission_dir, mission_slug, wp_id, to_lane, and actor")

    # WP03/T014/FR-013: route the feature_dir through the canonical-root
    # resolver. When the caller hands us a worktree-rooted path, this
    # rewrites it to the main repo's kitty-specs/<slug>/ so the event log
    # never lands in a stale worktree-local copy.
    feature_dir = canonicalize_feature_dir(feature_dir)

    lock_root = _feature_status_lock_root(feature_dir, repo_root)
    with feature_status_lock(lock_root, mission_slug):
        # T023: Load mission_id (ULID) from meta.json to use as the canonical
        # machine-facing identity for new events.  None for legacy/pre-3.1.1 missions.
        mission_id = _load_mission_id(feature_dir)

        raw_to_lane = to_lane.strip().lower()

        # Step 1: Resolve alias
        resolved_lane = resolve_lane_alias(to_lane)

        # Step 2: Derive from_lane from last event for this WP
        from_lane = _derive_from_lane(feature_dir, wp_id)

        if workspace_context is None:
            context_root = repo_root if repo_root is not None else feature_dir
            workspace_context = f"{execution_mode}:{context_root}"
        if subtasks_complete is None and from_lane == Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:
            subtasks_complete = _infer_subtasks_complete(feature_dir, wp_id)
        if implementation_evidence_present is None and from_lane == Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:
            implementation_evidence_present = _infer_implementation_evidence(feature_dir, wp_id)

        if _legacy_alias_collapses_to_current_lane(raw_to_lane, resolved_lane, from_lane):
            logger.info(
                "Collapsing legacy alias %s to existing lane %s for %s/%s",
                to_lane,
                resolved_lane,
                mission_slug,
                wp_id,
            )
            _mirror_phase1_frontmatter_lane(feature_dir, wp_id, resolved_lane)
            return StatusEvent(
                event_id=_generate_ulid(),
                mission_slug=mission_slug,
                wp_id=wp_id,
                from_lane=Lane(from_lane),
                to_lane=Lane(resolved_lane),
                at=now_utc_iso(),
                actor=actor,
                force=force,
                execution_mode=execution_mode,
                reason=reason,
                review_ref=review_ref,
                evidence=None,
                policy_metadata=policy_metadata,
                mission_id=mission_id,
            )

        # Step 3: Validate the transition
        # Build DoneEvidence early so we can pass it to validate_transition
        done_evidence: DoneEvidence | None = None
        if evidence is not None:
            done_evidence = _build_done_evidence(evidence)

        ok, error_msg = validate_transition(
            from_lane,
            resolved_lane,
            GuardContext(
                force=force,
                actor=actor,
                workspace_context=workspace_context,
                subtasks_complete=subtasks_complete,
                implementation_evidence_present=implementation_evidence_present,
                reason=reason,
                review_ref=review_ref,
                evidence=done_evidence,
                review_result=review_result,
                current_actor=current_actor,
            ),
        )
        if not ok:
            raise TransitionError(error_msg)

        # Step 4: Create StatusEvent with ULID event_id.
        # mission_id is the canonical machine-facing identity (ULID from meta.json).
        # T023: New events carry mission_id alongside mission_slug.
        event = StatusEvent(
            event_id=_generate_ulid(),
            mission_slug=mission_slug,
            wp_id=wp_id,
            from_lane=Lane(from_lane),
            to_lane=Lane(resolved_lane),
            at=now_utc_iso(),
            actor=actor,
            force=force,
            execution_mode=execution_mode,
            reason=reason,
            review_ref=review_ref,
            evidence=done_evidence,
            policy_metadata=policy_metadata,
            mission_id=mission_id,
        )

        # Step 5: Persist event to JSONL log and require readback before success.
        _store.append_primary_checkout_event_verified(feature_dir, event)

        # Step 6: Materialize snapshot from event log
        try:
            _reducer.materialize(feature_dir)
        except Exception:
            logger.warning(
                "Materialization failed after event %s was persisted; run 'status materialize' to recover",
                event.event_id,
            )

        _mirror_phase1_frontmatter_lane(feature_dir, wp_id, resolved_lane)

    # Step 7: SaaS fan-out (never blocks canonical persistence)
    _saas_fan_out(
        event,
        mission_slug,
        repo_root,
        policy_metadata=policy_metadata,
        ensure_sync_daemon=ensure_sync_daemon,
    )

    # Step 8: Dossier sync (fire-and-forget, never blocks)
    if sync_dossier and repo_root is not None:
        fire_dossier_sync(feature_dir, mission_slug, repo_root)

    # Step 9: Return the event
    return event


def emit_status_transition_batch(  # noqa: C901 — composite transition orchestration mirrors the single-event pipeline
    requests: list[TransitionRequest],
    *,
    ensure_sync_daemon: bool = True,
    sync_dossier: bool = True,
) -> list[StatusEvent]:
    """Validate and persist a same-WP transition sequence atomically.

    Composite operations such as implementation start have multiple legal lane
    edges but one user-visible lifecycle action. This helper validates the full
    sequence before any write, appends all events via ``append_events_atomic``,
    materializes once, and then performs best-effort fan-out.
    """
    if not requests:
        return []

    first = requests[0]
    feature_dir = first.feature_dir or first.mission_dir
    mission_slug = first.mission_slug or first._legacy_mission_slug
    wp_id = first.wp_id
    if feature_dir is None or mission_slug is None or wp_id is None:
        raise TypeError("emit_status_transition_batch requires feature_dir/mission_dir, mission_slug, and wp_id")

    feature_dir = canonicalize_feature_dir(feature_dir)
    mission_id = _load_mission_id(feature_dir)
    from_lane: str = str(_derive_from_lane(feature_dir, wp_id))
    built: list[tuple[StatusEvent, TransitionRequest]] = []
    batch_started_at = datetime.now(UTC)

    for request in requests:
        request_feature_dir = request.feature_dir or request.mission_dir
        request_mission_slug = request.mission_slug or request._legacy_mission_slug
        if request_feature_dir is None or request_mission_slug is None or request.wp_id is None or request.to_lane is None or request.actor is None:
            raise TypeError("Each batch transition requires feature_dir/mission_dir, mission_slug, wp_id, to_lane, and actor")
        if canonicalize_feature_dir(request_feature_dir) != feature_dir or request_mission_slug != mission_slug or request.wp_id != wp_id:
            raise TypeError("emit_status_transition_batch only supports one feature/mission/wp per batch")

        raw_to_lane = str(request.to_lane).strip().lower()
        resolved_lane = resolve_lane_alias(str(request.to_lane))

        workspace_context = request.workspace_context
        if workspace_context is None and not (from_lane == Lane.CLAIMED and resolved_lane == Lane.IN_PROGRESS):
            context_root = request.repo_root if request.repo_root is not None else feature_dir
            workspace_context = f"{request.execution_mode}:{context_root}"
        subtasks_complete = request.subtasks_complete
        implementation_evidence_present = request.implementation_evidence_present
        if subtasks_complete is None and from_lane == Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:
            subtasks_complete = _infer_subtasks_complete(feature_dir, wp_id)
        if implementation_evidence_present is None and from_lane == Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:
            implementation_evidence_present = _infer_implementation_evidence(feature_dir, wp_id)

        if _legacy_alias_collapses_to_current_lane(raw_to_lane, resolved_lane, from_lane):
            continue

        done_evidence: DoneEvidence | None = None
        if request.evidence is not None:
            done_evidence = _build_done_evidence(request.evidence)

        ok, error_msg = validate_transition(
            from_lane,
            resolved_lane,
            GuardContext(
                force=request.force,
                actor=request.actor,
                workspace_context=workspace_context,
                subtasks_complete=subtasks_complete,
                implementation_evidence_present=implementation_evidence_present,
                reason=request.reason,
                review_ref=request.review_ref,
                evidence=done_evidence,
                review_result=request.review_result,
                current_actor=request.current_actor,
            ),
        )
        if not ok:
            raise TransitionError(error_msg)

        event = StatusEvent(
            event_id=_generate_ulid(),
            mission_slug=mission_slug,
            wp_id=wp_id,
            from_lane=Lane(from_lane),
            to_lane=Lane(resolved_lane),
            at=(batch_started_at + timedelta(microseconds=len(built))).isoformat(),
            actor=request.actor,
            force=request.force,
            execution_mode=request.execution_mode,
            reason=request.reason,
            review_ref=request.review_ref,
            evidence=done_evidence,
            policy_metadata=request.policy_metadata,
            mission_id=mission_id,
        )
        built.append((event, request))
        from_lane = resolved_lane

    if not built:
        return []

    events = [event for event, _request in built]
    _store.append_primary_checkout_events_atomic_verified(feature_dir, events)

    try:
        _reducer.materialize(feature_dir)
    except Exception:
        logger.warning(
            "Materialization failed after batch ending in event %s was persisted; run 'status materialize' to recover",
            events[-1].event_id,
        )

    for event in events:
        _mirror_phase1_frontmatter_lane(feature_dir, event.wp_id, str(event.to_lane))

    for event, request in built:
        _saas_fan_out(
            event,
            mission_slug,
            request.repo_root,
            policy_metadata=request.policy_metadata,
            ensure_sync_daemon=ensure_sync_daemon,
        )

    if sync_dossier:
        repo_root = next((request.repo_root for _event, request in built if request.repo_root is not None), None)
        if repo_root is not None:
            fire_dossier_sync(feature_dir, mission_slug, repo_root)

    return events


def _saas_fan_out(
    event: StatusEvent,
    mission_slug: str,
    _repo_root: Path | None,
    *,
    policy_metadata: dict[str, Any] | None = None,
    ensure_sync_daemon: bool = True,
) -> None:
    """Conditionally fan out a SaaS telemetry event via the registered handlers.

    Routes through specify_cli.status.adapters.fire_saas_fanout, which
    is non-raising and a no-op when no sync handler has been registered
    (e.g., 0.1x branch or test environments without sync imported).
    Canonical status persistence is never affected by handler failures.

    Genesis compatibility gate (T022, WP04):
    When the installed spec_kitty_events does not support the genesis lane
    (i.e., spec_kitty_events < 6.0.0), fan-out for genesis transitions is
    deliberately skipped. This is a logged, intentional skip — NOT a silent
    swallowed ValidationError. Once spec_kitty_events 6.0.0 (genesis lane) is
    installed, this gate resolves True and genesis seeds fan out normally.
    """
    from_lane_str = str(event.from_lane)
    to_lane_str = str(event.to_lane)
    if (from_lane_str == "genesis" or to_lane_str == "genesis") and not _EVENTS_SUPPORTS_GENESIS:
        logger.info(
            "Skipping SaaS fan-out for genesis transition (wp_id=%s from=%s to=%s); "
            "installed spec_kitty_events lacks the genesis lane (needs >=6.0.0). "
            "Canonical local state is unaffected.",
            event.wp_id,
            from_lane_str,
            to_lane_str,
        )
        return

    fire_saas_fanout(
        wp_id=event.wp_id,
        from_lane=str(event.from_lane),
        to_lane=str(event.to_lane),
        actor=event.actor,
        mission_slug=mission_slug,
        mission_id=event.mission_id,
        causation_id=event.event_id,
        policy_metadata=policy_metadata,
        force=event.force,
        reason=event.reason,
        review_ref=event.review_ref,
        execution_mode=event.execution_mode,
        evidence=event.evidence.to_dict() if event.evidence else None,
        # Producer occurrence time: thread the canonical local lane-transition
        # time so SaaS persists Event.occurred_at = StatusEvent.at, not the
        # sync-emission clock (Rule R-T-01 in spec-kitty-events).
        occurred_at=event.at,
        ensure_daemon=ensure_sync_daemon,
    )
