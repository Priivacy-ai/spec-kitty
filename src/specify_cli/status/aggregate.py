"""MissionStatus aggregate root — Mission Management domain (WP04, FR-015–FR-023).

``MissionStatus`` is the authoritative read/write owner of mission WP lane state
within the Mission Management domain.  It encapsulates topology resolution,
the coord-aware read path, and lane transitions behind a single clean façade.

Usage::

    ms = MissionStatus.load(repo_root=Path("."), mission_slug="034-feature")
    wp_status = ms.claim("WP01")
    lane = wp_status.current_lane

Key constraints
---------------
* ``BookkeepingTransaction`` internals are NOT changed (C-004). ``MissionStatus``
  wraps it, does not replace it.
* When coord-topology is detected but the coord worktree is unavailable,
  ``CoordAuthorityUnavailable`` is raised — there is NO silent fallback to
  the legacy path.  Fail closed.
* All status reads go through the ``status/`` façade (never direct submodule
  imports from callers).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CoordAuthorityUnavailable(RuntimeError):
    """Raised when coord-topology is declared but the coord worktree is missing.

    Carry the relevant paths so callers can surface a useful diagnostic.
    """

    def __init__(
        self,
        *,
        mission_slug: str,
        coord_candidate: Path,
        primary_candidate: Path,
    ) -> None:
        self.mission_slug = mission_slug
        self.coord_candidate = coord_candidate
        self.primary_candidate = primary_candidate
        super().__init__(
            f"Coordination worktree unavailable for mission {mission_slug!r}. "
            f"Expected coord path: {coord_candidate}. "
            f"Primary checkout (stale, not used): {primary_candidate}. "
            "Either materialise the coordination worktree or investigate why it is missing."
        )


class MissionMetadataUnavailable(RuntimeError):
    """Raised when an existing mission ``meta.json`` cannot be trusted."""

    def __init__(
        self,
        *,
        mission_slug: str,
        meta_path: Path,
        primary_candidate: Path,
        reason: str,
    ) -> None:
        self.mission_slug = mission_slug
        self.meta_path = meta_path
        self.primary_candidate = primary_candidate
        super().__init__(
            f"Mission metadata unavailable for mission {mission_slug!r}. "
            f"meta.json path: {meta_path}. "
            f"Primary checkout (not used): {primary_candidate}. "
            f"Reason: {reason}. "
            "Fix meta.json before reading mission status."
        )


# ---------------------------------------------------------------------------
# ActiveWPStatus — read projection for a single WP
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActiveWPStatus:
    """Current lane state for a single WorkPackage within a Mission (read projection).

    Attributes:
        wp_id: Work package identifier (e.g. ``"WP01"``).
        current_lane: The WP's current lane from the event log.
        last_event: The most recent ``StatusEvent`` for this WP, or ``None``
            if no events have been recorded yet.
    """

    wp_id: str
    current_lane: Lane  # noqa: F821 — resolved at runtime via TYPE_CHECKING guard
    last_event: StatusEvent | None  # noqa: F821


# ---------------------------------------------------------------------------
# MissionStatus — aggregate root
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MissionStatus:
    """Aggregate root for mission WP lane state in the Mission Management domain.

    Attributes:
        mission_slug: Human-readable mission slug (e.g. ``"034-feature-name"``).
        mission_id: ULID mission identity from ``meta.json``, or ``None`` for
            legacy missions that predate identity minting.
        mid8: First 8 characters of ``mission_id``, or ``""`` for legacy missions.
        topology: ``"legacy"`` when no coord worktree exists; ``"coordination"``
            when the mission carries a ``coordination_branch`` declaration.
        read_dir: Authoritative directory containing ``status.events.jsonl``.
    """

    mission_slug: str
    mission_id: str | None
    mid8: str
    topology: Literal["legacy", "coordination"]
    read_dir: Path

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, repo_root: Path, mission_slug: str) -> MissionStatus:
        """Resolve topology once and return the authoritative status aggregate.

        Resolution logic
        ----------------
        1. Read ``meta.json`` to learn ``mission_id`` (and derive ``mid8``).
        2. Check whether a coordination worktree exists on disk.
        3. If ``meta.json`` declares ``coordination_branch`` but no coord
           worktree is present, raise ``CoordAuthorityUnavailable`` (fail closed).
        4. Otherwise return the aggregate with the appropriate ``read_dir``.

        Args:
            repo_root: Absolute repository root (primary checkout).
            mission_slug: Mission slug; may be bare human form or
                ``<human>-<mid8>`` (post-WP03).

        Returns:
            Populated :class:`MissionStatus` aggregate.

        Raises:
            CoordAuthorityUnavailable: When coord topology is declared but
                the coord worktree is missing.
            MissionMetadataUnavailable: When ``meta.json`` exists but cannot
                be parsed as a trusted object.
        """
        # 1. Load meta.json (best-effort; legacy missions may not have one)
        mission_id, declares_coord_branch = cls._read_meta(repo_root, mission_slug)
        mid8 = mission_id[:8] if mission_id else ""

        # 2. Build candidate paths using the same helper as _read_path_resolver.
        coord_candidate: Path | None = None
        if mid8:
            from specify_cli.coordination.workspace import CoordinationWorkspace
            from specify_cli.missions._read_path_resolver import _compose_mission_dir

            mission_dir_name = _compose_mission_dir(mission_slug, mid8)
            coord_root = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
            coord_candidate = coord_root / "kitty-specs" / mission_dir_name

        primary_candidate = repo_root / "kitty-specs" / mission_slug

        # 3. Resolve topology & read_dir.
        if coord_candidate is not None and coord_candidate.exists():
            return cls(
                mission_slug=mission_slug,
                mission_id=mission_id,
                mid8=mid8,
                topology="coordination",
                read_dir=coord_candidate,
            )

        # Coord topology declared but worktree is missing → fail closed.
        if declares_coord_branch and coord_candidate is not None:
            raise CoordAuthorityUnavailable(
                mission_slug=mission_slug,
                coord_candidate=coord_candidate,
                primary_candidate=primary_candidate,
            )

        # Legacy topology: use primary checkout.
        return cls(
            mission_slug=mission_slug,
            mission_id=mission_id,
            mid8=mid8,
            topology="legacy",
            read_dir=primary_candidate,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_meta(
        repo_root: Path, mission_slug: str
    ) -> tuple[str | None, bool]:
        """Read ``meta.json`` and extract identity fields.

        Returns:
            ``(mission_id, declares_coord_branch)`` — either may be
            ``None`` / ``False`` for legacy missions.
        """
        meta_path = repo_root / "kitty-specs" / mission_slug / "meta.json"
        if not meta_path.exists():
            return None, False
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning(
                "_read_meta: failed to read/parse meta.json for mission %r at %s: %s",
                mission_slug,
                meta_path,
                exc,
            )
            raise MissionMetadataUnavailable(
                mission_slug=mission_slug,
                meta_path=meta_path,
                primary_candidate=repo_root / "kitty-specs" / mission_slug,
                reason=str(exc),
            ) from exc
        if not isinstance(meta, dict):
            _logger.warning(
                "_read_meta: meta.json for mission %r is not a dict (got %s)",
                mission_slug,
                type(meta).__name__,
            )
            raise MissionMetadataUnavailable(
                mission_slug=mission_slug,
                meta_path=meta_path,
                primary_candidate=repo_root / "kitty-specs" / mission_slug,
                reason=f"expected object, got {type(meta).__name__}",
            )

        mission_id_value = meta.get("mission_id")
        if mission_id_value is not None and not isinstance(mission_id_value, str):
            raise MissionMetadataUnavailable(
                mission_slug=mission_slug,
                meta_path=meta_path,
                primary_candidate=repo_root / "kitty-specs" / mission_slug,
                reason=f"mission_id must be string or null, got {type(mission_id_value).__name__}",
            )

        mission_id = mission_id_value or None
        if isinstance(mission_id, str) and not mission_id.strip():
            mission_id = None

        coord_branch = meta.get("coordination_branch")
        if coord_branch is not None and not isinstance(coord_branch, str):
            raise MissionMetadataUnavailable(
                mission_slug=mission_slug,
                meta_path=meta_path,
                primary_candidate=repo_root / "kitty-specs" / mission_slug,
                reason=f"coordination_branch must be string or null, got {type(coord_branch).__name__}",
            )
        declares_coord_branch = isinstance(coord_branch, str) and bool(coord_branch.strip())

        return mission_id, declares_coord_branch

    # ------------------------------------------------------------------
    # Domain operations
    # ------------------------------------------------------------------

    def claim(self, wp_id: str) -> ActiveWPStatus:
        """Return the current lane state for a WP from the coord-aware read path.

        Args:
            wp_id: Work package identifier (e.g. ``"WP01"``).

        Returns:
            :class:`ActiveWPStatus` with the current lane and last event.
        """
        from specify_cli.status import get_wp_lane, read_events

        events = read_events(self.read_dir)
        current_lane = get_wp_lane(self.read_dir, wp_id)
        wp_events = [e for e in events if e.wp_id == wp_id]
        last_event = wp_events[-1] if wp_events else None
        return ActiveWPStatus(
            wp_id=wp_id,
            current_lane=current_lane,
            last_event=last_event,
        )

    def transition(self, request: TransitionRequest) -> StatusEvent:  # noqa: F821
        """Validate and apply a lane transition via ``BookkeepingTransaction`` internally.

        Domain invariant: the transition is validated before it is handed off
        to the transactional path.  ``BookkeepingTransaction`` is called
        internally — it is not exposed to callers.

        Args:
            request: Fully populated :class:`~specify_cli.status.TransitionRequest`.

        Returns:
            The persisted :class:`~specify_cli.status.StatusEvent`.

        Raises:
            :class:`~specify_cli.status.InvalidTransitionError`: When the
                requested (from_lane, to_lane) pair is not allowed.
        """
        from specify_cli.status import validate_transition
        from specify_cli.status.models import GuardContext, Lane
        from specify_cli.coordination.status_transition import (
            emit_status_transition_transactional,
        )

        # Build a GuardContext from the request fields for validation.
        ctx = GuardContext(
            actor=request.actor,
            workspace_context=request.workspace_context,
            subtasks_complete=request.subtasks_complete,
            implementation_evidence_present=request.implementation_evidence_present,
            reason=request.reason,
            review_ref=request.review_ref,
            evidence=request.evidence,
            force=request.force,
            review_result=request.review_result,
        )

        # Derive from_lane from the event log so validation is accurate.
        from specify_cli.status import get_wp_lane
        from specify_cli.status.wp_state import InvalidTransitionError

        from_lane_enum = get_wp_lane(self.read_dir, request.wp_id or "")
        to_lane_str = request.to_lane or ""
        ok, error = validate_transition(str(from_lane_enum), to_lane_str, ctx)
        if not ok:
            # Coerce to Lane enums for InvalidTransitionError constructor
            try:
                from_lane_for_error = Lane(str(from_lane_enum))
            except ValueError:
                from_lane_for_error = Lane.planned
            try:
                from specify_cli.status.transitions import resolve_lane_alias
                to_lane_for_error = Lane(resolve_lane_alias(to_lane_str))
            except ValueError:
                to_lane_for_error = Lane.planned
            raise InvalidTransitionError(from_lane_for_error, to_lane_for_error)

        # Inject the resolved read_dir so the transactional path uses the
        # correct (possibly coord-worktree) directory.
        import dataclasses

        enriched = dataclasses.replace(
            request,
            feature_dir=self.read_dir,
            mission_slug=self.mission_slug,
        )
        return emit_status_transition_transactional(enriched)

    def save(self, *, operation: str) -> CommitReceipt:  # noqa: F821
        """Persist staged transitions via ``BookkeepingTransaction``.

        This is a low-level escape hatch for callers that have already staged
        writes directly on the coord worktree.  Most callers should use
        :meth:`transition` instead.

        Args:
            operation: Human-readable operation label for the commit message.

        Returns:
            :class:`~specify_cli.coordination.types.CommitReceipt` from
            ``BookkeepingTransaction.commit()``.
        """
        from specify_cli.coordination.transaction import BookkeepingTransaction

        with BookkeepingTransaction.acquire(
            repo_root=self.read_dir,
            mission_id=self.mission_id or f"legacy-{self.mission_slug}",
            mission_slug=self.mission_slug,
            mid8=self.mid8,
            destination_ref=f"kitty/mission-{self.mission_slug}",
            operation=operation,
        ) as txn:
            return txn.commit(operation)


__all__ = [
    "ActiveWPStatus",
    "CoordAuthorityUnavailable",
    "MissionMetadataUnavailable",
    "MissionStatus",
]
