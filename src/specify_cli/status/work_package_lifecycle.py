"""Shared lifecycle operations for work-package starts.

These helpers are the single status-facing implementation of "start work" for
agent commands, the internal implement command, and orchestrator-api. Workspace
creation stays with the caller; durable lane transitions live here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specify_cli.status.emit import TransitionError, emit_status_transition, emit_status_transition_batch
from specify_cli.status.locking import feature_status_lock
from specify_cli.status.models import Lane, StatusEvent, TransitionRequest
from specify_cli.status.reducer import reduce
from specify_cli.status.store import read_events
from specify_cli.workspace import canonicalize_feature_dir

_GENERIC_IMPLEMENTATION_ACTORS = frozenset({"implement-command", "unknown"})


class WorkPackageClaimConflict(TransitionError):
    """Raised when another actor owns an implementation or review claim."""

    def __init__(self, wp_id: str, claimed_by: str, requesting_actor: str, *, review: bool = False) -> None:
        kind = "review" if review else "implementation"
        super().__init__(f"WP {wp_id} is already claimed for {kind} by '{claimed_by}'")
        self.wp_id = wp_id
        self.claimed_by = claimed_by
        self.requesting_actor = requesting_actor


class WorkPackageStartRejected(TransitionError):
    """Raised when a WP cannot be started from its current lane."""


@dataclass(frozen=True)
class WorkPackageStartResult:
    """Outcome for an idempotent implementation/review start operation."""

    wp_id: str
    from_lane: Lane
    to_lane: Lane
    actor: str
    events: tuple[StatusEvent, ...]
    no_op: bool = False
    claimed_by: str | None = None

    @property
    def status_changed(self) -> bool:
        return bool(self.events)


def _repo_root_for_lock(feature_dir: Path, repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root
    if feature_dir.parent.name == "kitty-specs":
        return feature_dir.parent.parent
    return feature_dir


def _actor_key(actor: object | None) -> str | None:
    if actor is None:
        return None
    value = str(actor).strip()
    return value or None


def _actors_compatible(existing: object | None, requested: object | None, *, allow_generic_existing: bool = False) -> bool:
    existing_key = _actor_key(existing)
    requested_key = _actor_key(requested)
    if existing_key is None or requested_key is None:
        return True
    if existing_key == requested_key:
        return True
    return allow_generic_existing and existing_key in _GENERIC_IMPLEMENTATION_ACTORS


def _current_lane_and_actor(feature_dir: Path, wp_id: str) -> tuple[Lane, str | None]:
    events = read_events(feature_dir)
    if not events:
        return Lane.PLANNED, None

    snapshot = reduce(events)
    state = snapshot.work_packages.get(wp_id)
    if not state:
        return Lane.PLANNED, None

    try:
        lane = Lane(str(state.get("lane", Lane.PLANNED)))
    except ValueError:
        lane = Lane.PLANNED
    return lane, _actor_key(state.get("actor"))


def start_implementation_status(
    *,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    actor: str,
    workspace_context: str,
    execution_mode: str,
    repo_root: Path | None = None,
    policy_metadata: dict[str, Any] | None = None,
    allow_rework: bool = False,
    rework_reason: str = "Re-implementing after review feedback",
) -> WorkPackageStartResult:
    """Idempotently move a WP into ``in_progress`` for an implementation actor."""
    feature_dir = canonicalize_feature_dir(feature_dir)
    lock_root = _repo_root_for_lock(feature_dir, repo_root)

    with feature_status_lock(lock_root, mission_slug):
        current_lane, current_actor = _current_lane_and_actor(feature_dir, wp_id)

        if current_lane == Lane.PLANNED:
            events = emit_status_transition_batch(
                [
                    TransitionRequest(
                        feature_dir=feature_dir,
                        mission_slug=mission_slug,
                        wp_id=wp_id,
                        to_lane=Lane.CLAIMED,
                        actor=actor,
                        execution_mode=execution_mode,
                        repo_root=repo_root,
                        policy_metadata=policy_metadata,
                    ),
                    TransitionRequest(
                        feature_dir=feature_dir,
                        mission_slug=mission_slug,
                        wp_id=wp_id,
                        to_lane=Lane.IN_PROGRESS,
                        actor=actor,
                        workspace_context=workspace_context,
                        execution_mode=execution_mode,
                        repo_root=repo_root,
                        policy_metadata=policy_metadata,
                    ),
                ]
            )
            return WorkPackageStartResult(wp_id, Lane.PLANNED, Lane.IN_PROGRESS, actor, tuple(events), claimed_by=actor)

        if current_lane == Lane.CLAIMED:
            if not _actors_compatible(current_actor, actor, allow_generic_existing=True):
                raise WorkPackageClaimConflict(wp_id, current_actor or "unknown", actor)
            events = emit_status_transition_batch(
                [
                    TransitionRequest(
                        feature_dir=feature_dir,
                        mission_slug=mission_slug,
                        wp_id=wp_id,
                        to_lane=Lane.IN_PROGRESS,
                        actor=actor,
                        workspace_context=workspace_context,
                        execution_mode=execution_mode,
                        repo_root=repo_root,
                        policy_metadata=policy_metadata,
                    )
                ]
            )
            return WorkPackageStartResult(wp_id, Lane.CLAIMED, Lane.IN_PROGRESS, actor, tuple(events), claimed_by=actor)

        if current_lane == Lane.IN_PROGRESS:
            if not _actors_compatible(current_actor, actor, allow_generic_existing=True):
                raise WorkPackageClaimConflict(wp_id, current_actor or "unknown", actor)
            return WorkPackageStartResult(wp_id, Lane.IN_PROGRESS, Lane.IN_PROGRESS, actor, (), no_op=True, claimed_by=current_actor)

        if allow_rework and current_lane in {Lane.FOR_REVIEW, Lane.APPROVED, Lane.IN_REVIEW}:
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=wp_id,
                    to_lane=Lane.IN_PROGRESS,
                    actor=actor,
                    force=True,
                    reason=rework_reason,
                    workspace_context=workspace_context,
                    execution_mode=execution_mode,
                    repo_root=repo_root,
                    policy_metadata=policy_metadata,
                )
            )
            return WorkPackageStartResult(wp_id, current_lane, Lane.IN_PROGRESS, actor, (event,), claimed_by=actor)

    raise WorkPackageStartRejected(f"WP {wp_id} is in '{current_lane}', cannot start implementation")


def start_review_status(
    *,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    actor: str,
    workspace_context: str,
    execution_mode: str,
    repo_root: Path | None = None,
    policy_metadata: dict[str, Any] | None = None,
    review_ref: str | None = "action-review-claim",
) -> WorkPackageStartResult:
    """Idempotently move a WP into ``in_review`` for a reviewer actor."""
    feature_dir = canonicalize_feature_dir(feature_dir)
    lock_root = _repo_root_for_lock(feature_dir, repo_root)

    with feature_status_lock(lock_root, mission_slug):
        current_lane, current_actor = _current_lane_and_actor(feature_dir, wp_id)

        if current_lane == Lane.FOR_REVIEW:
            event = emit_status_transition(
                TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=wp_id,
                    to_lane=Lane.IN_REVIEW,
                    actor=actor,
                    reason="Started review via action command",
                    review_ref=review_ref,
                    workspace_context=workspace_context,
                    execution_mode=execution_mode,
                    repo_root=repo_root,
                    policy_metadata=policy_metadata,
                )
            )
            return WorkPackageStartResult(wp_id, Lane.FOR_REVIEW, Lane.IN_REVIEW, actor, (event,), claimed_by=actor)

        if current_lane == Lane.IN_REVIEW:
            if not _actors_compatible(current_actor, actor):
                raise WorkPackageClaimConflict(wp_id, current_actor or "unknown", actor, review=True)
            return WorkPackageStartResult(wp_id, Lane.IN_REVIEW, Lane.IN_REVIEW, actor, (), no_op=True, claimed_by=current_actor)

    raise WorkPackageStartRejected(f"WP {wp_id} is in '{current_lane}', cannot start review")
