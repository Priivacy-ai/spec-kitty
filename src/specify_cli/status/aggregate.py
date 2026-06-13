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
from typing import TYPE_CHECKING, Any, Literal

from specify_cli.core.constants import KITTY_SPECS_DIR

# Legacy sentinel emitted by older transactional readers; not a Lane enum value.
# Canonical definition lives in lane_reader (the canonical read surface); imported
# as a private alias to preserve existing usage patterns throughout this module.
# See LEGACY_UNINITIALIZED_SENTINEL in status/lane_reader.py for documentation.
from .lane_reader import LEGACY_UNINITIALIZED_SENTINEL as _LEGACY_UNINITIALIZED_SENTINEL

if TYPE_CHECKING:
    from mission_runtime import StatusSurfaceFragment
    from specify_cli.coordination.types import CommitReceipt
    from specify_cli.status import TransitionRequest
    from specify_cli.status.models import Lane, StatusEvent

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
    current_lane: Lane
    last_event: StatusEvent | None


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
    def load(
        cls,
        repo_root: Path,
        mission_slug: str,
        *,
        surface: StatusSurfaceFragment | None = None,
    ) -> MissionStatus:
        """Resolve topology once and return the authoritative status aggregate.

        Resolution logic
        ----------------
        1. Read ``meta.json`` to learn ``mission_id`` (and derive ``mid8``).
        2. Resolve the authoritative status directory **once** through the
           canonical :func:`resolve_status_surface` helper — the single
           coord-aware surface authority that ``status_transition`` is also
           built on. When a caller already holds a resolved
           :class:`~mission_runtime.context.StatusSurfaceFragment`, its
           ``status_read_dir`` is consumed directly so the surface is never
           re-derived (FR-005 / #1821).
        3. If the coord worktree root exists but lacks the mission dir, the
           canonical helper fails closed; ``load`` surfaces this as
           ``CoordAuthorityUnavailable`` (preserving the historical contract).
        4. Otherwise return the aggregate with the resolved ``read_dir``.

        Args:
            repo_root: Absolute repository root (primary checkout).
            mission_slug: Mission slug; may be bare human form or
                ``<human>-<mid8>`` (post-WP03).
            surface: Optional carried :class:`StatusSurfaceFragment` from a
                resolved :class:`~mission_runtime.context.MissionExecutionContext`.
                When provided, ``status_read_dir`` is used as the authoritative
                ``read_dir`` and the canonical surface is **not** re-resolved
                (the carried fragment IS the source). The default (``None``)
                resolves once through the canonical helper — the same path, not
                a parallel one.

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

        # 1. Load meta.json (best-effort; legacy missions may not have one) so
        #    the aggregate carries identity + coord-branch declaration. The
        #    read_dir itself comes from the canonical surface, not from any
        #    hand-rolled composition here (FR-005 / #1821).
        mission_id, coordination_branch, primary_candidate = cls._read_meta(repo_root, mission_slug)
        mid8 = mission_id[:8] if mission_id else ""

        # 2. Resolve the authoritative status directory through the single
        #    canonical surface. Consume a carried fragment when present; never
        #    re-derive the coord candidate by hand (the second-composition seam
        #    Debby flagged at 01KTPKST closeout).
        read_dir = cls._resolve_read_dir(
            repo_root=repo_root,
            mission_slug=mission_slug,
            primary_candidate=primary_candidate,
            surface=surface,
        )

        topology: Literal["legacy", "coordination"] = (
            "coordination"
            if cls._is_coord_dir(read_dir, repo_root=repo_root)
            else "legacy"
        )
        return cls(
            mission_slug=mission_slug,
            mission_id=mission_id,
            mid8=mid8,
            topology=topology,
            read_dir=read_dir,
            repo_root=repo_root,
            coordination_branch=coordination_branch,
        )

    @staticmethod
    def _is_coord_dir(read_dir: Path, *, repo_root: Path) -> bool:
        """Return True when the resolved read dir lives in a coord worktree.

        Delegates to the WP03 topology authority
        (:func:`is_registered_coord_worktree`): the git worktree registry
        *disposes* coord-ness, not the path shape. A husk (under ``.worktrees``
        but unregistered) or a lane worktree therefore classifies as ``legacy``,
        killing the split-brain where a lane/husk path silently received coord
        routing (#1589/#1821, F-005). Fails closed via
        :class:`WorktreeRegistryUnavailable` if the registry cannot be read.
        """
        from specify_cli.coordination.surface_resolver import (
            is_registered_coord_worktree,
        )

        return is_registered_coord_worktree(read_dir, repo_root=repo_root)

    @classmethod
    def _resolve_read_dir(
        cls,
        *,
        repo_root: Path,
        mission_slug: str,
        primary_candidate: Path,
        surface: StatusSurfaceFragment | None,
    ) -> Path:
        """Resolve the authoritative read dir via the single canonical surface.

        Consumes the carried :class:`StatusSurfaceFragment` when present (the
        fragment IS the source — FR-005 / #1821). Otherwise resolves exactly
        once through :func:`resolve_status_surface`, the coord-aware authority
        that ``status_transition`` is also built on, and never re-composes the
        coord candidate by hand.

        The canonical helper fails closed (``StatusReadPathNotFound``) when a
        coord worktree is materialized without the mission dir; ``load``
        re-raises that as :class:`CoordAuthorityUnavailable` to preserve the
        historical aggregate contract. When the helper reports no ``meta.json``
        (the create→first-write window), the primary checkout remains
        authoritative. When the helper composes a coord path whose worktree is
        **not yet materialized** (coord branch declared, pre-first-write), the
        primary checkout is likewise authoritative until the worktree exists —
        matching the historical ``coord_candidate.exists()`` gate.
        """
        if surface is not None:
            # The carried fragment already resolved the surface once on the
            # context — consume it directly, do NOT resolve again.
            return surface.status_read_dir

        from specify_cli.coordination.surface_resolver import resolve_status_surface
        from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

        try:
            events_path = resolve_status_surface(repo_root, mission_slug)
        except StatusReadPathNotFound as exc:
            raise CoordAuthorityUnavailable(
                mission_slug=mission_slug,
                coord_candidate=exc.coord_candidate,
                primary_candidate=exc.primary_candidate,
            ) from exc
        except FileNotFoundError:
            # No meta.json at the canonical location yet (create→first-write
            # window): the primary checkout remains authoritative.
            return primary_candidate
        from specify_cli.coordination.surface_resolver import (
            is_under_worktrees_segment,
        )

        resolved_dir: Path = Path(events_path.parent)
        # A composed-but-unmaterialized coord dir is not yet authoritative; the
        # primary checkout owns the create→first-write window (the historical
        # ``coord_candidate.exists()`` semantics). This is a *shape* gate on a
        # not-yet-existing path (the registry cannot dispose a path that is not
        # materialized), so it consumes the blessed shape-proposal predicate
        # ``is_under_worktrees_segment`` rather than the registry authority.
        if is_under_worktrees_segment(resolved_dir) and not resolved_dir.exists():
            return primary_candidate
        return resolved_dir

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

        # F-001: route handles (bare mid8, full ULID, numeric prefix) through
        # the same canonical candidate resolution every other read surface
        # uses, so ``MissionStatus.load(<mid8>)`` carries the real mission_id
        # and primary dir. The candidate may land in a coord worktree (which
        # carries no meta.json), so only its canonical NAME is consumed to
        # re-anchor on the primary checkout. Ambiguous handles fall through to
        # the historical silent-first-match glob below (S8 follow-up).
        from specify_cli.missions._read_path_resolver import (
            MissionSelectorAmbiguous,
            StatusReadPathNotFound,
            candidate_feature_dir_for_mission,
        )

        try:
            candidate_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
        except MissionSelectorAmbiguous:
            candidate_dir = None
        except StatusReadPathNotFound:
            # Fail-closed coordination window (coord worktree root
            # materialized, mission dir absent): fall through to the
            # historical resolution path so ``load`` surfaces the established
            # CoordAuthorityUnavailable shape for EVERY handle form (full
            # slug, mid8, ULID) instead of leaking the resolver's raw
            # StatusReadPathNotFound out of ``MissionStatus.load``.
            candidate_dir = None
        if candidate_dir is not None and candidate_dir.name != mission_slug:
            canonical_primary = repo_root / KITTY_SPECS_DIR / candidate_dir.name
            canonical_meta = canonical_primary / "meta.json"
            if canonical_meta.exists():
                return canonical_meta, canonical_primary

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

    def transition(self, request: TransitionRequest) -> StatusEvent:
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

        from specify_cli.status.transitions import resolve_lane_alias

        from_lane_str, current_actor = self._resolve_current_lane(
            request=request,
            read_current_wp_state_transactional=read_current_wp_state_transactional,
            lane_unseeded=Lane.GENESIS,
        )
        to_lane_str = request.to_lane or ""
        resolved_to_lane = resolve_lane_alias(to_lane_str)
        workspace_context = self._resolve_workspace_context(request)
        subtasks_complete, implementation_evidence_present = self._resolve_review_gate_inputs(
            request=request,
            from_lane_str=from_lane_str,
            resolved_to_lane=resolved_to_lane,
            status_emit=status_emit,
            lane_in_progress=Lane.IN_PROGRESS,
            lane_for_review=Lane.FOR_REVIEW,
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

        raw_evidence = request.evidence
        built_evidence = (
            status_emit._build_done_evidence(raw_evidence)
            if raw_evidence is not None
            else None
        )

        # Build a GuardContext from behavior-preserving inferred request fields.
        ctx = GuardContext(
            actor=request.actor,
            workspace_context=workspace_context,
            subtasks_complete=subtasks_complete,
            implementation_evidence_present=implementation_evidence_present,
            reason=request.reason,
            review_ref=request.review_ref,
            evidence=built_evidence,
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

    def _resolve_current_lane(
        self,
        *,
        request: TransitionRequest,
        read_current_wp_state_transactional: Any,
        lane_unseeded: Any,
    ) -> tuple[str, str | None]:
        """Resolve the lane/current actor from the transactional authority.

        An unseeded WP resolves to ``genesis`` (``lane_unseeded``), NOT ``planned``:
        a created-but-unfinalized WP cannot be claimed, and the FSM correctly
        rejects ``genesis -> claimed``. The transactional reader already returns
        ``Lane.GENESIS`` for unseeded WPs; the ``"uninitialized"`` string sentinel
        is handled here for any reader that still emits it (#1775 review M4/Tier 3).
        """
        from_lane_enum, current_actor = read_current_wp_state_transactional(
            feature_dir=self.read_dir,
            mission_slug=self.mission_slug,
            wp_id=request.wp_id or "",
            repo_root=self.repo_root,
        )
        if str(from_lane_enum) == _LEGACY_UNINITIALIZED_SENTINEL:
            from_lane_enum = lane_unseeded
        return str(from_lane_enum), current_actor

    def _resolve_workspace_context(self, request: TransitionRequest) -> str:
        """Return the workspace context string used by transition guards."""
        if request.workspace_context is not None:
            return str(request.workspace_context)
        context_root = request.repo_root if request.repo_root is not None else self.read_dir
        return f"{request.execution_mode}:{context_root}"

    def _resolve_review_gate_inputs(
        self,
        *,
        request: TransitionRequest,
        from_lane_str: str,
        resolved_to_lane: str,
        status_emit: Any,
        lane_in_progress: Any,
        lane_for_review: Any,
    ) -> tuple[bool | None, bool | None]:
        """Infer review gate inputs only for in-progress -> for-review transitions."""
        subtasks_complete = request.subtasks_complete
        implementation_evidence_present = request.implementation_evidence_present
        entering_review = from_lane_str == lane_in_progress and resolved_to_lane == lane_for_review
        if entering_review and subtasks_complete is None:
            subtasks_complete = status_emit._infer_subtasks_complete(self.read_dir, request.wp_id or "")
        if entering_review and implementation_evidence_present is None:
            implementation_evidence_present = status_emit._infer_implementation_evidence(
                self.read_dir, request.wp_id or ""
            )
        return subtasks_complete, implementation_evidence_present

    def save(self, *, operation: str) -> CommitReceipt:
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
        # FR-006 fold-in (cluster-B): compose the destination ref through the
        # canonical branch-identity authority instead of the legacy
        # ``f"kitty/mission-{slug}"`` f-string (which named a branch that never
        # existed for mid8-era missions). ``mission_id`` is guaranteed present
        # by the guard above, so this always resolves the mid8-era branch.
        from specify_cli.lanes.branch_naming import mission_branch_name_required

        destination_ref = self.coordination_branch or mission_branch_name_required(
            self.mission_slug, self.mission_id
        )

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
