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
from dataclasses import dataclass
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
    ActorField,
    DoneEvidence,
    EventStream,
    GuardContext,
    InnerStateChanged,
    Lane,
    RepoEvidence,
    ReviewApproval,
    ReviewResult,
    StatusEvent,
    TransitionRequest,
    VerificationResult,
    WPInnerStateDelta,
    actor_identity_str,
)
from .resolved_binding import ResolvedBinding
from .transitions import resolve_lane_alias, validate_transition
from .wp_state import annotate
from . import store as _store
from . import reducer as _reducer
from .adapters import fire_dossier_sync, fire_resolved_binding_fanout, fire_saas_fanout
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
    # First-class resolved-binding bridge gate (FR-015 / IC-09, T049). Mirrors the
    # genesis gate: detect at import time whether the installed spec_kitty_events
    # exposes ``WPResolvedBindingChanged``. 6.1.0 does NOT; 6.2.0 (a SEPARATE
    # cross-repo deliverable) will. When absent, the fan-out for an off-transition
    # binding change is deliberately skipped (logged), NEVER a swallowed
    # ValidationError — local persistence is completely unaffected. When the event
    # ships and the pin is bumped, this gate resolves True on all installs and the
    # bridge lights up automatically with no code change here.
    _EVENTS_SUPPORTS_RESOLVED_BINDING: bool = hasattr(
        _spec_kitty_events_mod, "WPResolvedBindingChanged"
    )
except (ImportError, AttributeError):
    # ImportError: spec_kitty_events not installed. AttributeError: installed but
    # lacks a Lane enum. Either way, treat both capabilities as unsupported.
    _EVENTS_SUPPORTS_GENESIS = False
    _EVENTS_SUPPORTS_RESOLVED_BINDING = False


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
    actor: ActorField,
    at: str | None = None,
    mission_id: str | None = None,
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: DoneEvidence | None = None,
    review_result: ReviewResult | None = None,
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
        review_result: Optional structured review outcome for review exits.
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
        review_result=review_result,
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


def build_claim_policy_metadata(
    shell_pid: int,
    shell_pid_created_at: str,
    agent: str,
) -> dict[str, Any]:
    """Return the ``planned -> claimed`` ``policy_metadata`` sidecar.

    Pinned keys — ``shell_pid``, ``shell_pid_created_at``, ``agent`` — are the
    exact keys the reducer's claim fold (``reducer._wp_state_from_event``)
    extracts into the snapshot runtime slots. Defining the builder here gives
    the claim-writer WP and the reducer a single agreed shape; downstream WPs
    import this exact symbol rather than re-deriving the dict.
    """
    return {
        "shell_pid": shell_pid,
        "shell_pid_created_at": shell_pid_created_at,
        "agent": agent,
    }


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


def _infer_subtasks_complete(
    feature_dir: Path,
    wp_id: str,
    *,
    status_dir: Path | None = None,
    event_stream: EventStream | None = None,
) -> bool:
    """Infer subtask completion for a WP from the frontmatter-roster model.

    Mirrors the CLI door (``tasks_shared._check_unchecked_subtasks``) exactly
    (#2816 IC-10 / FR-016 / SC-010). The subtask **roster** (which task ids
    belong to ``wp_id``) is the authored ``subtasks:`` frontmatter list — static
    design intent — sourced via
    :func:`core.subtask_rows.authored_subtask_roster`, NOT ``tasks.md`` checkbox
    rows. **Completion** is resolved solely from the event-sourced reduced
    snapshot's ``subtasks`` slot via
    :func:`core.subtask_rows.unchecked_subtask_ids_from_snapshot`.

    ``feature_dir`` is the PRIMARY planning surface that owns the authored WP
    roster. ``status_dir`` is the topology-aware STATUS surface that owns the
    event log; flat missions default it to ``feature_dir``. Keeping these legs
    separate prevents coordination missions from reading completion out of the
    primary planning checkout.

    Fail-closed and symmetric with the CLI door: an empty authored roster is
    "nothing to block on" -> complete; a WP with an authored roster but an
    absent/silent snapshot slot has every roster id reported incomplete ->
    blocks. The ``tasks.md`` checkbox proxy is retired — a raw checkbox edit
    without ``mark-status`` no longer moves the gate (the D-13 incoherence is
    closed).
    """
    from specify_cli.core.subtask_rows import (  # noqa: PLC0415
        authored_subtask_roster,
        unchecked_subtask_ids_from_event_stream,
        unchecked_subtask_ids_from_snapshot,
    )

    roster = authored_subtask_roster(feature_dir, wp_id)
    if not roster:
        return True
    if event_stream is not None:
        return not unchecked_subtask_ids_from_event_stream(event_stream, wp_id, roster)
    return not unchecked_subtask_ids_from_snapshot(
        status_dir or feature_dir,
        wp_id,
        roster,
    )


def _infer_implementation_evidence(feature_dir: Path, wp_id: str) -> bool:
    """Infer implementation evidence from prior canonical events for this WP."""
    return _infer_implementation_evidence_from_event_stream(
        _store.read_event_stream(feature_dir), wp_id
    )


def _infer_implementation_evidence_from_event_stream(
    event_stream: EventStream, wp_id: str
) -> bool:
    """Infer implementation evidence from an already-resolved canonical stream."""
    return any(event.wp_id == wp_id for event in event_stream.transitions)


def _read_status_phase(feature_dir: Path) -> int | None:
    """Return the parsed ``status_phase`` int from meta.json, or ``None``.

    ``None`` covers a missing meta.json, a malformed meta.json, and a
    non-numeric ``status_phase`` — every "the feature did not declare a numeric
    phase" case, degrading to OFF at both gate call sites without raising.
    Uses ``on_malformed="none"`` so both missing and malformed degrade to
    ``None``; a malformed-but-present file still logs the warning (existence
    check first).
    """
    meta = load_meta(feature_dir, allow_missing=True, on_malformed="none")
    if meta is None:
        if (feature_dir / "meta.json").exists():
            logger.warning("Invalid meta.json in %s; skipping phase-1 gating", feature_dir)
        return None
    status_phase = meta.get("status_phase")
    try:
        return int(str(status_phase).strip())
    except (TypeError, ValueError):
        return None


# The transitional frontmatter ``lane`` mirror keys on ``status_phase`` (the
# runtime-slot snapshot authority is now unconditional — its predicate was
# deleted in the #2816 cutover). The lane-mirror gate is retained separately so
# it can be retired independently of the runtime-slot cutover (C-004).
def _legacy_lane_mirror_enabled(feature_dir: Path) -> bool:
    """Return True when the transitional frontmatter ``lane`` mirror is active.

    Governs whether :func:`_mirror_phase1_frontmatter_lane` still writes the
    legacy ``lane`` field. Keys on ``status_phase >= 1`` (phase-2 recognition:
    a mission advanced to ``status_phase: 2`` still mirrors — a strict ``"1"``
    equality would silently drop a phase-2 mission's lane mirror). Non-numeric
    / missing / malformed -> OFF. Retained per C-004 (the ``lane`` field is
    still frontmatter-authored; evicting it is a separate follow-up).
    """
    phase = _read_status_phase(feature_dir)
    return phase is not None and phase >= 1


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
    if not _legacy_lane_mirror_enabled(feature_dir):
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

    return cast(Path, resolve_status_lock_root(feature_dir, repo_root))


def emit_status_transition(  # NOSONAR — central orchestration hub; 15 of 20 params are optional with stable defaults; refactor tracked separately
    feature_dir: TransitionRequest | Path | None = None,
    _legacy_mission_slug: str | None = None,
    wp_id: str | None = None,
    to_lane: str | None = None,
    actor: ActorField | None = None,
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
    annotation_delta: WPInnerStateDelta | None = None
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
        annotation_delta = request.annotation_delta
    else:
        feature_dir = feature_dir or mission_dir
        mission_slug = mission_slug or _legacy_mission_slug

    if feature_dir is None or mission_slug is None or wp_id is None or to_lane is None or actor is None:
        raise TypeError("emit_status_transition requires feature_dir/mission_dir, mission_slug, wp_id, to_lane, and actor")

    # WP03/T014/FR-013: route the feature_dir through the canonical-root
    # resolver. When the caller hands us a worktree-rooted path, this
    # rewrites it to the main repo's kitty-specs/<slug>/ so the event log
    # never lands in a stale worktree-local copy.
    canonical_feature_dir: Path = canonicalize_feature_dir(feature_dir)

    lock_root = _feature_status_lock_root(canonical_feature_dir, repo_root)
    with feature_status_lock(lock_root, mission_slug):
        # T023: Load mission_id (ULID) from meta.json to use as the canonical
        # machine-facing identity for new events.  None for legacy/pre-3.1.1 missions.
        mission_id = _load_mission_id(canonical_feature_dir)

        raw_to_lane = to_lane.strip().lower()

        # Step 1: Resolve alias
        resolved_lane = resolve_lane_alias(to_lane)

        # Step 2: Derive from_lane from last event for this WP
        from_lane = _derive_from_lane(canonical_feature_dir, wp_id)

        if workspace_context is None:
            context_root = repo_root if repo_root is not None else canonical_feature_dir
            workspace_context = f"{execution_mode}:{context_root}"
        if (
            not force
            and from_lane == Lane.IN_PROGRESS
            and resolved_lane == Lane.FOR_REVIEW
        ):
            from specify_cli.missions._read_path_resolver import resolve_subtasks_gate_dir  # noqa: PLC0415

            primary_subtasks_dir = resolve_subtasks_gate_dir(
                canonical_feature_dir,
                repo_root,
                mission_slug,
            )
            subtasks_complete = _infer_subtasks_complete(
                primary_subtasks_dir,
                wp_id,
                status_dir=canonical_feature_dir,
            )
        if implementation_evidence_present is None and from_lane == Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:
            implementation_evidence_present = _infer_implementation_evidence(
                canonical_feature_dir,
                wp_id,
            )

        if _legacy_alias_collapses_to_current_lane(raw_to_lane, resolved_lane, from_lane):
            logger.info(
                "Collapsing legacy alias %s to existing lane %s for %s/%s",
                to_lane,
                resolved_lane,
                mission_slug,
                wp_id,
            )
            _mirror_phase1_frontmatter_lane(
                canonical_feature_dir,
                wp_id,
                resolved_lane,
            )
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
                review_result=review_result,
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
                # Guards do string ops on the actor (``.strip()`` truthiness);
                # project a structured resolved-binding actor to its string
                # identity here. The dict form is preserved on the StatusEvent
                # below so it still reaches ``_saas_fan_out`` (FR-015 / IC-09).
                actor=actor_identity_str(actor),
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
            review_result=review_result,
            policy_metadata=policy_metadata,
            mission_id=mission_id,
        )

        annotation = (
            annotate(
                wp_id,
                annotation_delta,
                actor=actor,
                at=now_utc_iso(),
                event_id=_generate_ulid(),
            )
            if annotation_delta is not None
            else None
        )

        # Persist the transition and its claim annotation as one unit. A
        # resolved binding must never lag behind the claim it describes.
        _store.append_event_stream_atomic_verified(
            canonical_feature_dir,
            [event, *([annotation] if annotation is not None else [])],
        )

        # Step 6: Materialize snapshot from event log
        try:
            _reducer.materialize(canonical_feature_dir)
        except Exception:
            logger.warning(
                "Materialization failed after event %s was persisted; run 'status materialize' to recover",
                event.event_id,
            )

        _mirror_phase1_frontmatter_lane(
            canonical_feature_dir,
            wp_id,
            resolved_lane,
        )

    # Step 7: SaaS fan-out (never blocks canonical persistence)
    _saas_fan_out(
        event,
        mission_slug,
        repo_root,
        policy_metadata=policy_metadata,
        ensure_sync_daemon=ensure_sync_daemon,
    )
    if annotation is not None:
        _resolved_binding_fan_out(annotation, mission_slug)

    # Step 8: Dossier sync (fire-and-forget, never blocks)
    if sync_dossier and repo_root is not None:
        fire_dossier_sync(canonical_feature_dir, mission_slug, repo_root)

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
        if (
            not request.force
            and from_lane == Lane.IN_PROGRESS
            and resolved_lane == Lane.FOR_REVIEW
        ):
            from specify_cli.missions._read_path_resolver import resolve_subtasks_gate_dir  # noqa: PLC0415

            primary_subtasks_dir = resolve_subtasks_gate_dir(feature_dir, request.repo_root, mission_slug)
            subtasks_complete = _infer_subtasks_complete(
                primary_subtasks_dir,
                wp_id,
                status_dir=feature_dir,
            )
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
                actor=actor_identity_str(request.actor),
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
            review_result=request.review_result,
            policy_metadata=request.policy_metadata,
            mission_id=mission_id,
        )
        built.append((event, request))
        from_lane = resolved_lane

    if not built:
        return []

    events = [event for event, _request in built]
    annotations: list[InnerStateChanged] = []
    for index, (_event, request) in enumerate(built):
        if request.annotation_delta is None:
            continue
        if request.actor is None:  # guarded while building; keeps the type invariant explicit
            raise TypeError("Batch claim annotations require an actor")
        annotations.append(
            annotate(
                wp_id,
                request.annotation_delta,
                actor=request.actor,
                at=(batch_started_at + timedelta(microseconds=len(built) + index)).isoformat(),
                event_id=_generate_ulid(),
            )
        )
    _store.append_event_stream_atomic_verified(feature_dir, [*events, *annotations])

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
    for annotation in annotations:
        _resolved_binding_fan_out(annotation, mission_slug)

    if sync_dossier:
        repo_root = next((request.repo_root for _event, request in built if request.repo_root is not None), None)
        if repo_root is not None:
            fire_dossier_sync(feature_dir, mission_slug, repo_root)

    return events


def emit_inner_state_changed(
    feature_dir: Path,
    wp_id: str,
    delta: WPInnerStateDelta,
    *,
    actor: str,
    mission_slug: str,
    at: str | None = None,
    repo_root: Path | None = None,
) -> InnerStateChanged:
    """Persist a single off-axis ``InnerStateChanged`` annotation.

    This is the public emit API downstream WPs call to record runtime-state
    changes (``shell_pid``, subtask marks, notes, tracker refs, reassignment,
    review overrides) without traversing the FSM.

    Pipeline:
        1. Resolve the write target via ``canonicalize_feature_dir(feature_dir)``
           — never ``Path.cwd()`` (FR-012 / C-003 / #2647).
        2. Mint a real ULID and build the typed event via the sanctioned
           ``wp_state.annotate()`` non-transition seam (which refuses an empty
           delta and validates ``wp_id``).
        3. Persist through the durability-verified store append seam under the
           per-feature status lock, then best-effort materialize the snapshot.

    Args:
        feature_dir: kitty-specs feature directory (canonicalized here).
        wp_id: Target work-package id (e.g. ``"WP01"``).
        delta: Typed partial runtime-state payload. An empty delta is refused.
        actor: Identity of the actor causing the change.
        mission_slug: Mission identifier — used only as the status-lock key.
        at: Optional ISO-8601 occurrence timestamp; defaults to now.
        repo_root: Optional repo root for status-lock resolution.

    Returns:
        The persisted :class:`InnerStateChanged`.

    Raises:
        ValueError: for a malformed ``wp_id`` or an empty delta.
        specify_cli.status.store.StoreError: if persistence/readback fails.
    """
    feature_dir = canonicalize_feature_dir(feature_dir)

    event = annotate(
        wp_id,
        delta,
        actor=actor,
        at=at or now_utc_iso(),
        event_id=_generate_ulid(),
    )

    lock_root = _feature_status_lock_root(feature_dir, repo_root)
    with feature_status_lock(lock_root, mission_slug):
        _store.append_annotations_atomic_verified(feature_dir, [event])
        try:
            _reducer.materialize(feature_dir)
        except Exception:
            logger.warning(
                "Materialization failed after annotation %s was persisted; "
                "run 'status materialize' to recover",
                event.event_id,
            )

    # First-class resolved-binding bridge (FR-015 / IC-09, T049). Additive and
    # best-effort — runs AFTER the annotation is durably persisted + materialized,
    # so it can never alter local persistence or the reduced snapshot. A non-
    # binding annotation is a no-op; a binding annotation fans out when the events
    # package supports it, else logs an intentional skip (version-gated).
    _resolved_binding_fan_out(event, mission_slug)

    return event


#: The resolved-binding delta slots (FR-013) that make an ``InnerStateChanged`` a
#: genuine binding change worth a ``WPResolvedBindingChanged`` fan-out. A delta
#: touching none of these (e.g. a ``shell_pid``/note/subtask annotation) is not a
#: binding change and never bridges.
_RESOLVED_BINDING_DELTA_FIELDS: tuple[str, ...] = (
    "role",
    "agent_profile",
    "agent_profile_version",
    "model",
    "provider",
)


def _resolved_binding_fan_out(event: InnerStateChanged, mission_slug: str) -> None:
    """Version-gated ``WPResolvedBindingChanged`` fan-out for a binding change.

    ``emit_inner_state_changed`` has no fan-out of its own; this adds the
    first-class resolved-binding bridge (spec-kitty ↔ spec-kitty-saas) additively.
    Only an annotation that actually carries a resolved binding fans out — a plain
    runtime annotation (``shell_pid``/note/subtask) is a no-op here.

    Gated exactly like the genesis gate (:data:`_EVENTS_SUPPORTS_RESOLVED_BINDING`
    / :func:`_saas_fan_out`): when the installed ``spec_kitty_events`` lacks
    ``WPResolvedBindingChanged`` the fan-out is a **logged, intentional skip**,
    never a swallowed ``ValidationError``, and canonical local state is untouched.
    The concrete payload model is built by the registered sync handler once 6.2.0
    ships; the status layer only feature-detects via the gate and hands off kwargs
    (the same handoff shape as :func:`_saas_fan_out` — no local type definition).
    """
    delta = event.delta
    binding = {name: getattr(delta, name) for name in _RESOLVED_BINDING_DELTA_FIELDS}
    if all(value is None for value in binding.values()):
        return  # not a resolved-binding annotation — nothing to bridge

    if not _EVENTS_SUPPORTS_RESOLVED_BINDING:
        logger.info(
            "Skipping WPResolvedBindingChanged fan-out (wp_id=%s mission_slug=%s); "
            "installed spec_kitty_events lacks WPResolvedBindingChanged (needs "
            ">=6.2.0). Canonical local state is unaffected.",
            event.wp_id,
            mission_slug,
        )
        return

    fire_resolved_binding_fanout(
        wp_id=event.wp_id,
        # ``mission_slug`` is the canonical identity (Terminology Canon); no
        # ``feature_slug`` alias is introduced on this new write path.
        mission_slug=mission_slug,
        actor=event.actor,
        causation_id=event.event_id,
        occurred_at=event.at,
        **binding,
    )


def build_resolved_actor(
    *,
    role: str,
    tool: str | None,
    binding: ResolvedBinding | None,
) -> dict[str, str | None]:
    """Structured ``{role, profile, tool, model}`` actor for the IC-09 fan-out.

    ``spec_kitty_events`` 6.1.0 ``StatusTransitionPayload.actor`` already accepts
    ``Union[str, Dict]`` — so no shared-package change is needed to carry this
    shape. The dict form lets the SaaS fan-out ride the transition's *resolved*
    identity rather than the bare ``--agent`` tool string.

    The ``model`` is the genuine dispatch-resolved model or ``None`` when a
    pick-up resolved none (the ``RESOLVED_MODEL_ABSENT`` delta sentinel is a
    reduced-slot concern, not an actor concern — the actor carries a plain
    ``None`` for "no model").

    .. note:: WP12 (FR-015) landed the plumbing this seam waited on. The
       ``emit_status_transition`` / ``build_status_event`` / ``StatusEvent.actor``
       surfaces are now typed :data:`~specify_cli.status.models.ActorField`
       (``str | dict``), and ``decode_actor`` guards the ``from_dict`` round-trip,
       so a caller may pass this dict as the claim/review transition ``actor`` and
       it reaches ``_saas_fan_out`` (``fire_saas_fanout(actor=event.actor, …)``)
       uncorrupted. The ``emit_status_transition`` ``# NOSONAR`` hub was NOT
       inflated — the guard reads a projected string via ``actor_identity_str``.
       The off-transition binding change additionally bridges through the
       version-gated :func:`_resolved_binding_fan_out` (``WPResolvedBindingChanged``).
    """
    return {
        "role": role,
        "profile": binding.agent_profile if binding is not None else None,
        "tool": tool,
        "model": binding.model if binding is not None else None,
    }


# Compatibility alias for the WP10 test/import surface.
_build_resolved_actor = build_resolved_actor


@dataclass(frozen=True)
class ResolvedBindingEmit:
    """Outcome of a resolved-binding claim-seam emit (FR-014 / T039).

    ``annotation`` is the persisted :class:`InnerStateChanged` — the latest-wins
    channel the IC-07 reconstruction reads — or ``None`` when no binding was
    threaded (a bare ``--agent`` claim with no dispatch context). ``structured_actor``
    is the ``{role, profile, tool, model}`` form staged for the IC-09 SaaS fan-out
    (consumed by WP12 once the emit signatures widen; see :func:`_build_resolved_actor`).
    """

    annotation: InnerStateChanged | None
    structured_actor: dict[str, str | None]


def emit_resolved_binding(
    feature_dir: Path,
    wp_id: str,
    *,
    mission_slug: str,
    actor: str,
    role: str,
    binding: ResolvedBinding | None,
    tool: str | None = None,
    repo_root: Path | None = None,
) -> ResolvedBindingEmit:
    """Record a claim seam's genuinely dispatch-resolved binding (FR-014 / T039).

    Emitted at BOTH the implement-claim and review-claim seams so the resolved
    identity folds **latest-wins** across the lifecycle. This is a mandatory
    complement to the ``policy_metadata`` claim fold, which the reducer applies
    ONLY on ``planned → claimed`` (``reducer._wp_state_from_event``): a
    review-claim (``for_review → in_review``) never hits that fold, so relying on
    it alone would freeze the resolved identity at the implementer's binding.
    The :class:`InnerStateChanged` annotation folds regardless of lane.

    When ``binding`` is ``None`` (a claim with no dispatch context) NO annotation
    is written — the resolved slots stay absent (a valid "never-reclaimed-with-
    dispatch" state per the resolved-binding contract). The structured actor is
    still produced for the caller (role + tool), so a future WP12 fan-out has an
    actor even for a bindingless claim.

    Args:
        feature_dir: kitty-specs feature directory (canonicalized by the emit).
        wp_id: Target work-package id (e.g. ``"WP01"``).
        mission_slug: Mission identifier — used only as the status-lock key.
        actor: Identity of the actor performing the claim (the annotation actor).
        role: The *actual* role that ran at this seam (``"implementer"`` /
            ``"reviewer"``) — never the authored recommendation.
        binding: The dispatch-resolved binding, or ``None`` for no dispatch context.
        tool: The AI tool string (the ``--agent`` value) for the structured actor.
        repo_root: Optional repo root for status-lock resolution.

    Returns:
        A :class:`ResolvedBindingEmit` carrying the persisted annotation (or
        ``None``) and the staged structured actor.
    """
    structured_actor = build_resolved_actor(role=role, tool=tool, binding=binding)
    if binding is None:
        return ResolvedBindingEmit(annotation=None, structured_actor=structured_actor)
    annotation = emit_inner_state_changed(
        feature_dir,
        wp_id,
        binding.to_delta(role=role),
        actor=actor,
        mission_slug=mission_slug,
        repo_root=repo_root,
    )
    return ResolvedBindingEmit(annotation=annotation, structured_actor=structured_actor)


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
        # Deliver the actor verbatim (FR-015 / IC-09): a resolved-binding claim
        # carries a ``{role, profile, tool, model}`` dict — which spec_kitty_events
        # 6.1.0 ``StatusTransitionPayload.actor`` already accepts (Union[str, Dict])
        # — while a plain-string actor (the common case) fans out exactly as
        # before. No dict is ever fabricated for a bare string (defensive
        # feature-detection is the pass-through itself).
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
