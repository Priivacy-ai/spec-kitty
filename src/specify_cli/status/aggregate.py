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
* When the coord worktree has been materialized but lacks the mission dir,
  ``CoordAuthorityUnavailable`` is raised. Before materialization, the primary
  checkout remains authoritative for the create→first-write window.
* All status reads go through the ``status/`` façade (never direct submodule
  imports from callers).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from specify_cli.core.constants import KITTY_SPECS_DIR

if TYPE_CHECKING:
    from specify_cli.status import StatusEvent, TransitionRequest

_logger = logging.getLogger(__name__)

# FR-007 / DIRECTIVE_010: mission slugs are ASCII identifier-safe handles used to
# compose filesystem paths, git refs, and worktree names. Anything outside this
# allowlist is rejected at the aggregate boundary before it can reach those
# surfaces. ``re.ASCII`` keeps ``\w`` semantics ASCII-only, but the pattern is
# already explicit, so the flag is belt-and-suspenders alongside the
# ``.isascii()`` guard.
_MISSION_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$", re.ASCII)


def _enrich_transition_request(
    request: TransitionRequest,  # noqa: F821
    *,
    read_dir: Path,
    mission_slug: str,
) -> TransitionRequest:  # noqa: F821
    """Inject aggregate-owned path/slug into a transition request."""
    import dataclasses

    return dataclasses.replace(
        request,
        feature_dir=read_dir,
        mission_slug=mission_slug,
    )


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


class InvalidMissionSlug(ValueError):
    """Raised when a ``mission_slug`` violates the ASCII identifier allowlist.

    Mission slugs feed filesystem paths, git refs, and worktree names, so they
    must match ``^[A-Za-z0-9_-]+$`` and be pure ASCII (FR-007, DIRECTIVE_010).
    The offending slug is carried so callers can surface a precise diagnostic.
    """

    def __init__(self, mission_slug: str) -> None:
        self.mission_slug = mission_slug
        super().__init__(
            f"Invalid mission slug {mission_slug!r}: mission slugs must match "
            r"'^[A-Za-z0-9_-]+$' and contain ASCII characters only."
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
    repo_root: Path
    coordination_branch: str | None = None

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
        3. If a coord worktree root exists but lacks the mission dir, raise
           ``CoordAuthorityUnavailable`` (fail closed).
        4. Otherwise return the aggregate with the appropriate ``read_dir``.

        Args:
            repo_root: Absolute repository root (primary checkout).
            mission_slug: Mission slug; may be bare human form or
                ``<human>-<mid8>`` (post-WP03).

        Returns:
            Populated :class:`MissionStatus` aggregate.

        Raises:
            CoordAuthorityUnavailable: When the coord worktree exists but
                lacks the mission directory.
            MissionMetadataUnavailable: When ``meta.json`` exists but cannot
                be parsed as a trusted object.
            InvalidMissionSlug: When ``mission_slug`` is empty, non-ASCII, or
                contains characters outside ``^[A-Za-z0-9_-]+$`` (FR-007).
        """
        # 0. Guard the slug at the boundary (FR-007 / DIRECTIVE_010) before it
        #    is used to compose paths, git refs, or worktree names.
        cls._validate_mission_slug(mission_slug)

        # 1. Load meta.json (best-effort; legacy missions may not have one)
        mission_id, coordination_branch, primary_candidate = cls._read_meta(repo_root, mission_slug)
        declares_coord_branch = coordination_branch is not None
        mid8 = mission_id[:8] if mission_id else ""

        # 2. Build candidate paths using the same helper as _read_path_resolver.
        coord_candidate: Path | None = None
        coord_worktree_materialized = False
        if mid8:
            from specify_cli.coordination.workspace import CoordinationWorkspace
            from specify_cli.missions._read_path_resolver import _compose_mission_dir

            mission_dir_name = _compose_mission_dir(mission_slug, mid8)
            coord_root = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
            coord_worktree_materialized = coord_root.exists()
            coord_candidate = coord_root / KITTY_SPECS_DIR / mission_dir_name

        # 3. Resolve topology & read_dir.
        if coord_candidate is not None and coord_candidate.exists():
            return cls(
                mission_slug=mission_slug,
                mission_id=mission_id,
                mid8=mid8,
                topology="coordination",
                read_dir=coord_candidate,
                repo_root=repo_root,
                coordination_branch=coordination_branch,
            )

        # Coord topology declared but the worktree root is already materialized
        # without the mission dir → fail closed. If the coord worktree has not
        # been created yet, the primary checkout is still authoritative for the
        # create→first-write window.
        if (
            declares_coord_branch
            and coord_candidate is not None
            and coord_worktree_materialized
        ):
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
            repo_root=repo_root,
            coordination_branch=coordination_branch,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_mission_slug(mission_slug: str) -> None:
        """Reject mission slugs outside the ASCII identifier allowlist (FR-007).

        Raises:
            InvalidMissionSlug: When the slug is non-ASCII or does not match
                ``^[A-Za-z0-9_-]+$``.
        """
        if not mission_slug.isascii() or _MISSION_SLUG_PATTERN.match(mission_slug) is None:
            raise InvalidMissionSlug(mission_slug)

    @staticmethod
    def _read_meta(
        repo_root: Path, mission_slug: str
    ) -> tuple[str | None, str | None, Path]:
        """Read ``meta.json`` and extract identity fields.

        Returns:
            ``(mission_id, coordination_branch, primary_dir)`` — identity
            values may be ``None`` for legacy missions.
        """
        meta_path, primary_dir = MissionStatus._find_meta_path(repo_root, mission_slug)
        if not meta_path.exists():
            return None, None, primary_dir
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
                primary_candidate=primary_dir,
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
                primary_candidate=primary_dir,
                reason=f"expected object, got {type(meta).__name__}",
            )

        mission_id_value = meta.get("mission_id")
        if mission_id_value is not None and not isinstance(mission_id_value, str):
            raise MissionMetadataUnavailable(
                mission_slug=mission_slug,
                meta_path=meta_path,
                primary_candidate=primary_dir,
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
                primary_candidate=primary_dir,
                reason=f"coordination_branch must be string or null, got {type(coord_branch).__name__}",
            )
        coordination_branch = coord_branch.strip() if isinstance(coord_branch, str) and coord_branch.strip() else None

        return mission_id, coordination_branch, primary_dir

    @staticmethod
    def _find_meta_path(repo_root: Path, mission_slug: str) -> tuple[Path, Path]:
        """Return ``(meta_path, primary_dir)`` for raw or composed mission dirs."""
        primary_dir = repo_root / KITTY_SPECS_DIR / mission_slug
        raw_meta = primary_dir / "meta.json"
        if raw_meta.exists():
            return raw_meta, primary_dir

        from specify_cli.lanes.branch_naming import mid8_from_slug

        if mid8_from_slug(mission_slug):
            return raw_meta, primary_dir

        specs_dir = repo_root / KITTY_SPECS_DIR
        if specs_dir.exists():
            for candidate in sorted(specs_dir.glob(f"{mission_slug}-*/meta.json")):
                if mid8_from_slug(candidate.parent.name):
                    return candidate, candidate.parent

        return raw_meta, primary_dir

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
            read_current_wp_state_transactional,
        )
        from specify_cli.status import emit as status_emit

        # Derive from_lane from the same target the transactional writer will
        # use. For declared coordination branches without a materialized
        # worktree, this reads the branch ref rather than stale primary files.
        from_lane_enum, current_actor = read_current_wp_state_transactional(
            feature_dir=self.read_dir,
            mission_slug=self.mission_slug,
            wp_id=request.wp_id or "",
            repo_root=self.repo_root,
        )
        if str(from_lane_enum) == "uninitialized":
            from_lane_enum = Lane.PLANNED
        to_lane_str = request.to_lane or ""
        from_lane_str = str(from_lane_enum)

        from specify_cli.status.transitions import resolve_lane_alias

        resolved_to_lane = resolve_lane_alias(to_lane_str)
        workspace_context = request.workspace_context
        if workspace_context is None:
            context_root = request.repo_root if request.repo_root is not None else self.read_dir
            workspace_context = f"{request.execution_mode}:{context_root}"

        subtasks_complete = request.subtasks_complete
        implementation_evidence_present = request.implementation_evidence_present
        if subtasks_complete is None and from_lane_str == Lane.IN_PROGRESS and resolved_to_lane == Lane.FOR_REVIEW:
            subtasks_complete = status_emit._infer_subtasks_complete(self.read_dir, request.wp_id or "")
        if (
            implementation_evidence_present is None
            and from_lane_str == Lane.IN_PROGRESS
            and resolved_to_lane == Lane.FOR_REVIEW
        ):
            implementation_evidence_present = status_emit._infer_implementation_evidence(
                self.read_dir, request.wp_id or ""
            )

        if status_emit._legacy_alias_collapses_to_current_lane(
            to_lane_str,
            resolved_to_lane,
            from_lane_str,
        ):
            enriched = _enrich_transition_request(
                request,
                read_dir=self.read_dir,
                mission_slug=self.mission_slug,
            )
            return emit_status_transition_transactional(enriched)

        evidence = request.evidence
        if evidence is not None:
            evidence = status_emit._build_done_evidence(evidence)

        # Build a GuardContext from behavior-preserving inferred request fields.
        ctx = GuardContext(
            actor=request.actor,
            workspace_context=workspace_context,
            subtasks_complete=subtasks_complete,
            implementation_evidence_present=implementation_evidence_present,
            reason=request.reason,
            review_ref=request.review_ref,
            evidence=evidence,
            force=request.force,
            review_result=request.review_result,
            current_actor=current_actor,
        )
        ok, error = validate_transition(from_lane_str, resolved_to_lane, ctx)
        if not ok:
            from specify_cli.status.emit import TransitionError

            raise TransitionError(error or f"Illegal transition: {from_lane_str} -> {resolved_to_lane}")

        # Inject the resolved read_dir so the transactional path uses the
        # correct (possibly coord-worktree) directory.
        enriched = _enrich_transition_request(
            request,
            read_dir=self.read_dir,
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

        if self.mission_id is None or not self.mid8:
            raise MissionMetadataUnavailable(
                mission_slug=self.mission_slug,
                meta_path=self.repo_root / KITTY_SPECS_DIR / self.mission_slug / "meta.json",
                primary_candidate=self.repo_root / KITTY_SPECS_DIR / self.mission_slug,
                reason="mission_id is required to persist via BookkeepingTransaction",
            )
        destination_ref = self.coordination_branch or f"kitty/mission-{self.mission_slug}"

        with BookkeepingTransaction.acquire(
            repo_root=self.repo_root,
            mission_id=self.mission_id,
            mission_slug=self.mission_slug,
            mid8=self.mid8,
            destination_ref=destination_ref,
            operation=operation,
        ) as txn:
            for artifact_name in ("status.events.jsonl", "status.json"):
                artifact = txn.feature_dir / artifact_name
                if artifact.exists():
                    txn.stage_path(artifact)
            return txn.commit(operation)


__all__ = [
    "ActiveWPStatus",
    "CoordAuthorityUnavailable",
    "InvalidMissionSlug",
    "MissionMetadataUnavailable",
    "MissionStatus",
]
