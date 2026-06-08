"""Transactional status-transition emission helpers.

Production workflow callers must append status events through
``BookkeepingTransaction`` so SaaS/dossier fanout runs only after the
bookkeeping commit succeeds.
"""

from __future__ import annotations

from specify_cli.core.constants import KITTY_SPECS_DIR
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from specify_cli.coordination.outbound import queue_saas_emission
from specify_cli.coordination.status_service import (
    EventLogReadContract,
    read_event_log,
    wp_lane_actor_from_events,
)
from specify_cli.coordination.transaction import BookkeepingTransaction
from specify_cli.mission_metadata import load_meta
from specify_cli.status import emit as _emit
from specify_cli.status.adapters import fire_dossier_sync
from specify_cli.status.models import DoneEvidence, GuardContext, Lane, StatusEvent, TransitionRequest
from specify_cli.status.transitions import resolve_lane_alias, validate_transition
from specify_cli.workspace import canonicalize_feature_dir


@dataclass(frozen=True)
class _TransactionIdentity:
    repo_root: Path
    feature_dir: Path
    mission_id: str
    mid8: str
    destination_ref: str
    meta_exists: bool
    coordination_branch: str | None
    transaction_meta_exists: bool


def _repo_root_for_feature(feature_dir: Path, repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root
    if feature_dir.parent.name == KITTY_SPECS_DIR:
        return feature_dir.parent.parent
    return feature_dir


def _current_branch(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    branch = result.stdout.strip()
    return branch if result.returncode == 0 and branch else "HEAD"


def _repo_supports_transactions(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _branch_exists(repo_root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _transaction_dir_name(mission_slug: str, mid8: str) -> str:
    return mission_slug if mission_slug.endswith(f"-{mid8}") else f"{mission_slug}-{mid8}"


def _transaction_topology_available(identity: _TransactionIdentity, mission_slug: str) -> bool:
    if not _repo_supports_transactions(identity.repo_root):
        return False
    if identity.coordination_branch is not None:
        return True
    if identity.meta_exists:
        # Legacy missions with meta but no coordination_branch are handled by
        # BookkeepingTransaction's legacy lane fallback when its derived
        # kitty-specs/<slug>-<mid8>/meta.json path can see that meta.
        return identity.transaction_meta_exists

    from specify_cli.coordination.workspace import CoordinationWorkspace  # noqa: PLC0415

    return _branch_exists(
        identity.repo_root,
        CoordinationWorkspace.branch_name(mission_slug, identity.mid8),
    )


def _is_coordination_feature_dir(feature_dir: Path) -> bool:
    return ".worktrees" in feature_dir.parts


def _identity_for_request(request: TransitionRequest) -> _TransactionIdentity:
    raw_feature_dir = request.feature_dir or request.mission_dir
    if raw_feature_dir is None:
        raise TypeError("transactional status emit requires feature_dir/mission_dir")

    feature_dir = canonicalize_feature_dir(raw_feature_dir)
    repo_root = _repo_root_for_feature(feature_dir, request.repo_root)
    mission_slug = request.mission_slug or request._legacy_mission_slug
    if mission_slug is None:
        raise TypeError("transactional status emit requires mission_slug")

    meta = load_meta(feature_dir)

    coord_branch: str | None = None
    mission_id: str | None = None
    mid8: str | None = None
    meta_exists = isinstance(meta, dict)
    if meta_exists:
        raw_coord = meta.get("coordination_branch")
        raw_mission_id = meta.get("mission_id")
        raw_mid8 = meta.get("mid8")
        coord_branch = str(raw_coord) if raw_coord else None
        mission_id = str(raw_mission_id) if raw_mission_id else None
        mid8 = str(raw_mid8) if raw_mid8 else None
        if mid8 is None and mission_id and len(mission_id) >= 8:
            mid8 = mission_id[:8]

    effective_mission_id = mission_id or f"legacy-{mission_slug}"
    effective_mid8 = mid8 or (
        mission_id[:8] if mission_id and len(mission_id) >= 8 else (mission_slug.replace("-", "") + "00000000")[:8]
    )
    transaction_dir_name = _transaction_dir_name(mission_slug, effective_mid8)
    return _TransactionIdentity(
        repo_root=repo_root,
        feature_dir=feature_dir,
        mission_id=effective_mission_id,
        mid8=effective_mid8,
        destination_ref=coord_branch or _current_branch(repo_root),
        meta_exists=meta_exists,
        coordination_branch=coord_branch,
        transaction_meta_exists=(feature_dir.parent / transaction_dir_name / "meta.json").exists(),
    )


def _prepare_event(
    *,
    feature_dir: Path,
    request: TransitionRequest,
    mission_slug: str,
    mission_id: str | None,
    from_lane: str,
    at: str | None = None,
) -> tuple[StatusEvent | None, str]:
    if request.wp_id is None or request.to_lane is None or request.actor is None:
        raise TypeError("Each status transition requires wp_id, to_lane, and actor")

    raw_to_lane = str(request.to_lane).strip().lower()
    resolved_lane = resolve_lane_alias(str(request.to_lane))

    workspace_context = request.workspace_context
    if workspace_context is None:
        context_root = request.repo_root if request.repo_root is not None else feature_dir
        workspace_context = f"{request.execution_mode}:{context_root}"

    subtasks_complete = request.subtasks_complete
    implementation_evidence_present = request.implementation_evidence_present
    if subtasks_complete is None and from_lane == Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:
        subtasks_complete = _emit._infer_subtasks_complete(feature_dir, request.wp_id)
    if implementation_evidence_present is None and from_lane == Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:
        implementation_evidence_present = _emit._infer_implementation_evidence(feature_dir, request.wp_id)

    if _emit._legacy_alias_collapses_to_current_lane(raw_to_lane, resolved_lane, from_lane):
        _emit._mirror_phase1_frontmatter_lane(feature_dir, request.wp_id, resolved_lane)
        return None, resolved_lane

    done_evidence: DoneEvidence | None = None
    if request.evidence is not None:
        done_evidence = _emit._build_done_evidence(request.evidence)

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
        raise _emit.TransitionError(error_msg)

    return (
        _emit.build_status_event(
            mission_slug=mission_slug,
            wp_id=request.wp_id,
            from_lane=from_lane,
            to_lane=resolved_lane,
            actor=request.actor,
            at=at,
            mission_id=mission_id,
            force=request.force,
            execution_mode=request.execution_mode,
            reason=request.reason,
            review_ref=request.review_ref,
            evidence=done_evidence,
            policy_metadata=request.policy_metadata,
        ),
        resolved_lane,
    )


def _defer_dossier_sync(
    txn: BookkeepingTransaction,
    *,
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path | None,
    sync_dossier: bool,
) -> None:
    if not sync_dossier or repo_root is None:
        return
    txn.defer_outbound(lambda: fire_dossier_sync(feature_dir, mission_slug, repo_root))


def _read_events_from_transaction_target(
    identity: _TransactionIdentity,
    mission_slug: str,
) -> list[StatusEvent]:
    """Read target status events without creating worktrees or commits."""
    if not _transaction_topology_available(identity, mission_slug):
        if _is_coordination_feature_dir(identity.feature_dir):
            return read_event_log(EventLogReadContract.coordination_worktree(identity.feature_dir))
        return read_event_log(EventLogReadContract.primary_checkout(identity.feature_dir))
    if identity.coordination_branch is None:
        return read_event_log(EventLogReadContract.primary_checkout(identity.feature_dir))

    from specify_cli.coordination.workspace import CoordinationWorkspace  # noqa: PLC0415

    worktree_root = CoordinationWorkspace.worktree_path(
        identity.repo_root,
        mission_slug,
        identity.mid8,
    )
    transaction_feature_dir = worktree_root / KITTY_SPECS_DIR / _transaction_dir_name(
        mission_slug,
        identity.mid8,
    )
    if worktree_root.exists():
        return read_event_log(
            EventLogReadContract.coordination_worktree(transaction_feature_dir)
        )

    return read_event_log(
        EventLogReadContract.coordination_branch_ref(
            repo_root=identity.repo_root,
            destination_ref=identity.destination_ref,
            feature_dir=transaction_feature_dir,
            parser_feature_dir=identity.feature_dir,
        )
    )


def read_current_wp_state_transactional(
    *,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    repo_root: Path | None = None,
) -> tuple[Lane, str | None]:
    """Read current WP lane/actor from the transaction's write target."""
    identity = _identity_for_request(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            to_lane=Lane.PLANNED,
            actor="status-read",
            repo_root=repo_root,
        )
    )
    contract = _read_contract_from_transaction_target(identity, mission_slug)
    events = read_event_log(contract)
    if not events and not _transaction_topology_available(identity, mission_slug):
        from specify_cli.status.lane_reader import get_wp_lane  # noqa: PLC0415

        try:
            return Lane(resolve_lane_alias(get_wp_lane(identity.feature_dir, wp_id))), None
        except Exception:  # noqa: BLE001 -- non-git test fixtures may lack WP files
            # No events and no WP file resolved → unseeded WP; report GENESIS
            # (matching _derive_from_lane on the write side — Contract 3, FR-009).
            return Lane.GENESIS, None
    return wp_lane_actor_from_events(events, wp_id)


def _read_contract_from_transaction_target(
    identity: _TransactionIdentity,
    mission_slug: str,
) -> EventLogReadContract:
    """Resolve the read-only contract for the transaction write target."""
    if not _transaction_topology_available(identity, mission_slug):
        if _is_coordination_feature_dir(identity.feature_dir):
            return EventLogReadContract.coordination_worktree(identity.feature_dir)
        return EventLogReadContract.primary_checkout(identity.feature_dir)
    if identity.coordination_branch is None:
        return EventLogReadContract.primary_checkout(identity.feature_dir)

    from specify_cli.coordination.workspace import CoordinationWorkspace  # noqa: PLC0415

    worktree_root = CoordinationWorkspace.worktree_path(
        identity.repo_root,
        mission_slug,
        identity.mid8,
    )
    transaction_feature_dir = worktree_root / KITTY_SPECS_DIR / _transaction_dir_name(
        mission_slug,
        identity.mid8,
    )
    if worktree_root.exists():
        return EventLogReadContract.coordination_worktree(transaction_feature_dir)
    return EventLogReadContract.coordination_branch_ref(
        repo_root=identity.repo_root,
        destination_ref=identity.destination_ref,
        feature_dir=transaction_feature_dir,
        parser_feature_dir=identity.feature_dir,
    )


def read_events_transactional(
    *,
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path | None = None,
) -> list[StatusEvent]:
    """Read status events from the same target transactional writes use."""
    identity = _identity_for_request(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id="WP00",
            to_lane=Lane.PLANNED,
            actor="status-read",
            repo_root=repo_root,
        )
    )
    return _read_events_from_transaction_target(identity, mission_slug)


def has_transition_to_transactional(
    *,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    to_lane: str,
    repo_root: Path | None = None,
) -> bool:
    """Return whether the transaction write target already has a lane event."""
    identity = _identity_for_request(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            to_lane=Lane.PLANNED,
            actor="status-read",
            repo_root=repo_root,
        )
    )
    return any(
        event.wp_id == wp_id and str(event.to_lane) == str(to_lane)
        for event in _read_events_from_transaction_target(identity, mission_slug)
    )


def emit_status_transition_transactional(
    request: TransitionRequest,
    *,
    ensure_sync_daemon: bool = True,
    sync_dossier: bool = True,
    operation: str | None = None,
    allow_protected_branch_in_test_mode: bool = False,
) -> StatusEvent:
    """Validate, append, commit, then fan out one status transition."""
    feature_dir = request.feature_dir or request.mission_dir
    mission_slug = request.mission_slug or request._legacy_mission_slug
    if feature_dir is None or mission_slug is None or request.wp_id is None:
        raise TypeError("transactional status emit requires feature_dir, mission_slug, and wp_id")

    identity = _identity_for_request(request)
    if not _transaction_topology_available(identity, mission_slug):
        return _emit.emit_status_transition(
            request,
            ensure_sync_daemon=ensure_sync_daemon,
            sync_dossier=sync_dossier,
        )

    with BookkeepingTransaction.acquire(
        repo_root=identity.repo_root,
        mission_id=identity.mission_id,
        mission_slug=mission_slug,
        mid8=identity.mid8,
        destination_ref=identity.destination_ref,
        operation=operation or f"status transition {request.wp_id}",
        allow_protected_branch_in_test_mode=allow_protected_branch_in_test_mode,
    ) as txn:
        mission_id_for_event = None if identity.mission_id.startswith("legacy-") else identity.mission_id
        from_lane = str(_emit._derive_from_lane(txn.feature_dir, request.wp_id))
        event, _resolved_lane = _prepare_event(
            feature_dir=txn.feature_dir,
            request=request,
            mission_slug=mission_slug,
            mission_id=mission_id_for_event,
            from_lane=from_lane,
        )
        if event is None:
            return _emit.build_status_event(
                mission_slug=mission_slug,
                wp_id=request.wp_id,
                from_lane=from_lane,
                to_lane=from_lane,
                actor=request.actor or "unknown",
                mission_id=mission_id_for_event,
                force=request.force,
                execution_mode=request.execution_mode,
                reason=request.reason,
                review_ref=request.review_ref,
                policy_metadata=request.policy_metadata,
            )
        txn.append_event(event)
        queue_saas_emission(
            txn,
            event,
            mission_slug=mission_slug,
            repo_root=request.repo_root,
            ensure_sync_daemon=ensure_sync_daemon,
        )
        _defer_dossier_sync(
            txn,
            feature_dir=txn.feature_dir,
            mission_slug=mission_slug,
            repo_root=request.repo_root,
            sync_dossier=sync_dossier,
        )
        return event


def emit_status_transition_batch_transactional(
    requests: list[TransitionRequest],
    *,
    ensure_sync_daemon: bool = True,
    sync_dossier: bool = True,
    operation: str | None = None,
    allow_protected_branch_in_test_mode: bool = False,
) -> list[StatusEvent]:
    """Validate, append, commit, then fan out a same-WP transition batch."""
    if not requests:
        return []

    first = requests[0]
    mission_slug = first.mission_slug or first._legacy_mission_slug
    if mission_slug is None or first.wp_id is None:
        raise TypeError("transactional status batch requires mission_slug and wp_id")

    identity = _identity_for_request(first)
    if not _transaction_topology_available(identity, mission_slug):
        return cast(
            list[StatusEvent],
            _emit.emit_status_transition_batch(
                requests,
                ensure_sync_daemon=ensure_sync_daemon,
                sync_dossier=sync_dossier,
            ),
        )

    with BookkeepingTransaction.acquire(
        repo_root=identity.repo_root,
        mission_id=identity.mission_id,
        mission_slug=mission_slug,
        mid8=identity.mid8,
        destination_ref=identity.destination_ref,
        operation=operation or f"status transition batch {first.wp_id}",
        allow_protected_branch_in_test_mode=allow_protected_branch_in_test_mode,
    ) as txn:
        mission_id_for_event = None if identity.mission_id.startswith("legacy-") else identity.mission_id
        from_lane = str(_emit._derive_from_lane(txn.feature_dir, first.wp_id))
        built: list[tuple[StatusEvent, TransitionRequest]] = []
        started_at = datetime.now(UTC)

        for request in requests:
            request_feature_dir = request.feature_dir or request.mission_dir
            request_mission_slug = request.mission_slug or request._legacy_mission_slug
            if (
                request_feature_dir is None
                or canonicalize_feature_dir(request_feature_dir) != identity.feature_dir
                or request_mission_slug != mission_slug
                or request.wp_id != first.wp_id
            ):
                raise TypeError("transactional status batch only supports one feature/mission/wp")

            event, resolved_lane = _prepare_event(
                feature_dir=txn.feature_dir,
                request=request,
                mission_slug=mission_slug,
                mission_id=mission_id_for_event,
                from_lane=from_lane,
                at=(started_at + timedelta(microseconds=len(built))).isoformat(),
            )
            if event is None:
                from_lane = resolved_lane
                continue
            built.append((event, request))
            from_lane = resolved_lane

        for event, request in built:
            txn.append_event(event)
            queue_saas_emission(
                txn,
                event,
                mission_slug=mission_slug,
                repo_root=request.repo_root,
                ensure_sync_daemon=ensure_sync_daemon,
            )

        repo_root = next((request.repo_root for request in requests if request.repo_root is not None), None)
        _defer_dossier_sync(
            txn,
            feature_dir=txn.feature_dir,
            mission_slug=mission_slug,
            repo_root=repo_root,
            sync_dossier=sync_dossier,
        )
        return [event for event, _request in built]
