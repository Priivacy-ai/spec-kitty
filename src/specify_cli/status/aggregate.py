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

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.mission_metadata import load_meta

# Legacy sentinel emitted by older transactional readers; not a Lane enum value.
# Canonical definition lives in lane_reader (the canonical read surface); imported
# as a private alias to preserve existing usage patterns throughout this module.
# See LEGACY_UNINITIALIZED_SENTINEL in status/lane_reader.py for documentation.
from .lane_reader import LEGACY_UNINITIALIZED_SENTINEL as _LEGACY_UNINITIALIZED_SENTINEL

if TYPE_CHECKING:
    from specify_cli.coordination.types import CommitReceipt
    from specify_cli.status import TransitionRequest
    from specify_cli.status.models import Lane, StatusEvent

_logger = logging.getLogger(__name__)

# The mission ``meta.json`` filename (Sonar S1192 — the literal appears in several
# path joins across the meta-resolution helpers; hoisted to a single constant).
_META_JSON_FILENAME = "meta.json"


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
    """Raised when a ``mission_slug`` is not a safe path segment.

    Mission slugs feed filesystem paths, git refs, and worktree names, so they
    must be a single safe path segment per the canonical
    :func:`specify_cli.core.paths.assert_safe_path_segment` grammar — pure ASCII,
    no path separators, no ``..`` traversal, no leading dot (FR-007,
    DIRECTIVE_010). The offending slug is carried so callers can surface a
    precise diagnostic.
    """

    def __init__(self, mission_slug: str) -> None:
        self.mission_slug = mission_slug
        super().__init__(
            f"Invalid mission slug {mission_slug!r}: mission slugs must be a "
            "single safe path segment (ASCII, no path separators, no '..', no "
            "leading dot)."
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
    current_lane: Lane | str
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
    ) -> MissionStatus:
        """Resolve topology once and return the authoritative status aggregate.

        Resolution logic
        ----------------
        1. Read ``meta.json`` to learn ``mission_id`` (and derive ``mid8``).
        2. Resolve the authoritative status directory **once** through the
           canonical :func:`resolve_status_surface` helper — the single
           coord-aware surface authority that ``status_transition`` is also
           built on.
        3. If the coord worktree root exists but lacks the mission dir, the
           canonical helper fails closed; ``load`` surfaces this as
           ``CoordAuthorityUnavailable`` (preserving the historical contract).
        4. Otherwise return the aggregate with the resolved ``read_dir``.

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
            InvalidMissionSlug: When ``mission_slug`` is not a safe path segment
                per ``assert_safe_path_segment`` (empty, non-ASCII, separators,
                ``..`` traversal, or leading dot) (FR-007).
        """
        # 0. Guard the slug at the boundary (FR-007 / DIRECTIVE_010) before it
        #    is used to compose paths, git refs, or worktree names.
        cls._validate_mission_slug(mission_slug)

        # 1. Load meta.json (best-effort; legacy missions may not have one) so
        #    the aggregate carries identity + coord-branch declaration. The
        #    read_dir itself comes from the canonical surface, not from any
        #    hand-rolled composition here (FR-005 / #1821).
        mission_id, coordination_branch, primary_candidate = cls._read_meta(repo_root, mission_slug)
        # Route the mid8 through the authoritative failover resolver instead of
        # an inline ``[:8]`` slice (WP03 / FR-009). ``resolve_mid8`` declines to
        # ``""`` when no declared identity is available, preserving the legacy
        # empty-string contract for missions without a mission_id.
        from specify_cli.lanes.branch_naming import resolve_mid8

        mid8 = resolve_mid8(mission_slug, mission_id=mission_id)

        # 2. Resolve the authoritative status directory through the single
        #    canonical surface. Consume a carried fragment when present; never
        #    re-derive the coord candidate by hand (the second-composition seam
        #    Debby flagged at 01KTPKST closeout).
        read_dir = cls._resolve_read_dir(
            repo_root=repo_root,
            mission_slug=mission_slug,
            primary_candidate=primary_candidate,
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

        # ``bool(...)`` re-narrows the value mypy widens to ``Any`` across the
        # function-local import chain (the predicate is annotated ``-> bool`` at
        # its source; the late import loses the annotation) — Boy Scout fix, no
        # behaviour change.
        return bool(is_registered_coord_worktree(read_dir, repo_root=repo_root))

    @classmethod
    def _resolve_read_dir(
        cls,
        *,
        repo_root: Path,
        mission_slug: str,
        primary_candidate: Path,
    ) -> Path:
        """Resolve the authoritative read dir as a thin adapter over the delegator.

        Delegates the resolve-dir-or-typed-error body to the single WP03
        delegator :func:`resolve_surface_dir_or_typed_error` (FR-009/T4): there
        is now exactly ONE resolution body shared with
        ``mission_runtime.resolution`` rather than a duplicate re-implementation
        of the ``resolve_status_surface`` happy/error tail here. This call site
        keeps only the two aggregate-specific concerns the delegator cannot own:

        * **on_missing_meta = primary_candidate** — the delegator catches
          ``FileNotFoundError`` / ``ValueError`` (no ``meta.json`` yet: the
          create→first-write window) and returns the caller-supplied primary
          directory, so the primary checkout stays authoritative until first
          write (mutation-guarded by ``test_create_first_write_window_*``).
        * **StatusReadPathNotFound → CoordAuthorityUnavailable** — the delegator
          propagates the surface's fail-closed signal unchanged (typed-error
          convergence is WP06's job); the aggregate translates it to its own
          historical boundary type here.
        * **Unmaterialised-coord create-window gate** — when the canonical
          :func:`resolve_status_surface` composes a coord path whose worktree is
          declared but **not yet materialised** (coord branch in meta, pre-first
          write), it returns that composed coord path *as-is* and explicitly
          defers the authority decision to this call site (see the WP03
          delegator docstring: this gate "stays at the aggregate call site"). The
          aggregate keeps the primary checkout authoritative until the coord
          worktree exists, matching the historical ``coord_candidate.exists()``
          semantics — a shape-only check on a not-yet-materialised path, so it
          consumes the blessed ``is_under_worktrees_segment`` shape predicate
          rather than the (git-touching) registry authority.

        The body that re-implemented ``resolve_status_surface``'s happy/error
        tail inline (the ``FileNotFoundError`` → primary and the
        ``StatusReadPathNotFound`` translation) is **consolidated** onto the one
        WP03 delegator (FR-009/T4); only the two genuinely aggregate-specific
        concerns above remain at this seam. C-004: the consolidation is gated on
        WP02's equivalence matrix staying green/xfail-tracked for aggregate's
        input classes.
        """
        from specify_cli.coordination.surface_resolver import (
            CoordinationBranchDeleted,
            is_under_worktrees_segment,
        )
        from specify_cli.missions._read_path_resolver import (
            StatusReadPathNotFound,
            resolve_surface_dir_or_typed_error,
        )

        try:
            resolved_dir: Path = resolve_surface_dir_or_typed_error(
                repo_root,
                mission_slug,
                on_missing_meta=primary_candidate,
            )
        except CoordinationBranchDeleted:
            # ORDERING (WP05 / T023, FR-005): ``CoordinationBranchDeleted`` SUBCLASSES
            # ``StatusReadPathNotFound``, so this more-specific handler MUST sit
            # AHEAD of the re-wrap below — otherwise the subclass is swallowed and
            # re-spelled ``CoordAuthorityUnavailable``, masking the data-loss
            # verdict. A deleted coord branch carrying unmerged status is data loss,
            # not a degraded read: propagate the loud, distinct error VERBATIM so
            # every leg converges on ``COORDINATION_BRANCH_DELETED`` (#1848).
            raise
        except StatusReadPathNotFound as exc:
            raise CoordAuthorityUnavailable(
                mission_slug=mission_slug,
                coord_candidate=exc.coord_candidate,
                primary_candidate=exc.primary_candidate,
            ) from exc
        # Aggregate-specific create-window authority (see docstring): a composed
        # coord dir whose worktree is not yet materialised is not authoritative;
        # the primary checkout owns the create→first-write window until the coord
        # worktree exists. The canonical surface deliberately defers this to the
        # call site (WP03 delegator docstring), so it stays here, not in the
        # shared delegator.
        if is_under_worktrees_segment(resolved_dir) and not resolved_dir.exists():
            return primary_candidate
        return resolved_dir

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_mission_slug(mission_slug: str) -> None:
        """Reject mission slugs outside the ASCII identifier allowlist (FR-007).

        Delegates to the canonical ``assert_safe_path_segment`` (FR-001 / WP01) and
        re-raises any ``ValueError`` as ``InvalidMissionSlug`` to preserve the
        call-site contract (C-001: migrate, don't wrap — no parallel mechanism).

        Raises:
            InvalidMissionSlug: When the slug is empty, non-ASCII, or contains
                characters outside the safe-segment grammar.
        """
        try:
            assert_safe_path_segment(mission_slug)
        except ValueError as exc:
            raise InvalidMissionSlug(mission_slug) from exc

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
            # Canonical reader (FR-005/WP12): allow_missing=False because the
            # ``exists()`` precondition above already resolved the tolerant-missing
            # branch -- a FileNotFoundError here means the file vanished in a race
            # window, which is a genuine failure, not a legacy-tolerant miss.
            # on_malformed="raise" folds the JSON-syntax AND non-dict-shape checks
            # into ONE ValueError, replacing the two ad-hoc except/isinstance arms
            # this call site used to hand-roll.
            meta = load_meta(primary_dir, allow_missing=False, on_malformed="raise") or {}
        except (FileNotFoundError, ValueError) as exc:
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
        """Return ``(meta_path, primary_dir)`` via the canonical handle resolver.

        Routes EVERY handle form (full slug, bare mid8, full ULID, numeric
        prefix, ``<slug>-<mid8>`` dir name) through the one canonical read
        primitive :func:`candidate_feature_dir_for_mission` so identity is
        derived exactly once — aggregate never self-composes the surface path or
        does its own ``glob`` selection (FR-008). The resolved candidate may land
        in a coord worktree (which carries no ``meta.json``), so only its
        canonical NAME re-anchors the meta read on the primary checkout, where
        ``meta.json`` always lives.

        The historical silent-first-match glob
        (``sorted(specs_dir.glob(f"{slug}-*/meta.json"))``) is **removed**: an
        ambiguous handle now propagates :class:`MissionSelectorAmbiguous`
        (``error_code == MISSION_AMBIGUOUS_SELECTOR``) instead of silently
        picking the lexically-first candidate — the no-silent-fallback contract
        (C-CTX-4 / C-009 / FR-008). The fail-closed coordination window
        (``StatusReadPathNotFound``) is swallowed so the downstream
        ``_resolve_read_dir`` is the single place that translates it to
        ``CoordAuthorityUnavailable`` (one authority for the typed error).

        Raises:
            MissionSelectorAmbiguous: When ``mission_slug`` is a handle that
                matches more than one mission (FR-008 — never a silent pick).
        """
        from specify_cli.missions._read_path_resolver import (
            StatusReadPathNotFound,
            _canonicalize_primary_read_handle,
            candidate_feature_dir_for_mission,
            primary_feature_dir_for_mission,
            resolve_bare_modern_mission_dir_name,
        )

        # Compose the primary candidate through the blessed path-constructor
        # (the sanctioned ``KITTY_SPECS_DIR`` owner that carries its own
        # ``assert_safe_path_segment`` guard), so aggregate never self-composes a
        # raw ``repo_root / KITTY_SPECS_DIR / <slug>`` surface path (WP01
        # raw-bypass; FR-008). The slug is also grammar-checked one level up at
        # the ``load`` boundary.
        # WP05/FR-005: route through _canonicalize_primary_read_handle so every
        # handle form (bare mid8 / ULID / numeric prefix / bare human slug) lands
        # on the correct composed primary dir — not a wrong literal dir.
        primary_dir = primary_feature_dir_for_mission(
            repo_root,
            _canonicalize_primary_read_handle(repo_root, mission_slug),
        )
        raw_meta = primary_dir / _META_JSON_FILENAME
        # Pure-path happy path: when the literal slug already names an existing
        # primary mission dir with ``meta.json``, it IS the canonical directory
        # — no handle disambiguation (and no git-registry read) is needed. This
        # mirrors ``resolve_mission_read_path``'s own literal-first short-circuit
        # and keeps the meta read off the heavier (git-touching) resolver on the
        # common case.
        if raw_meta.exists():
            return raw_meta, primary_dir
        # Bare modern slug → composed ``<slug>-<mid8>`` primary dir (#2050 read
        # mirror): the operator typed a bare human slug whose on-disk primary dir
        # carries the canonical ``<slug>-<mid8>`` name (e.g. before the coord
        # worktree is materialized, only the composed primary dir exists). The
        # identity resolver below keys on the dir NAME and so cannot map a bare
        # slug onto a composed dir name; the shared canonical primitive bridges
        # that gap (NFR-004 — same definition the ``agent status`` CLI consumes).
        # Re-anchor the meta read on the composed primary dir when it resolves.
        bare_dir_name = resolve_bare_modern_mission_dir_name(repo_root, mission_slug)
        if bare_dir_name is not None:
            composed_primary = primary_feature_dir_for_mission(repo_root, bare_dir_name)
            composed_meta = composed_primary / _META_JSON_FILENAME
            if composed_meta.exists():
                return composed_meta, composed_primary
        try:
            candidate_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
        except StatusReadPathNotFound:
            # Fail-closed coordination window (coord worktree root materialized,
            # mission dir absent): defer to the literal primary candidate so the
            # downstream ``_resolve_read_dir`` surfaces the converged fail-closed
            # type for EVERY handle form — ``CoordinationBranchDeleted`` when the
            # declared coord branch is gone (#1848, propagated verbatim), else
            # ``CoordAuthorityUnavailable`` — instead of leaking the resolver's raw
            # ``StatusReadPathNotFound`` here.
            return raw_meta, primary_dir
        # ``candidate_feature_dir_for_mission`` resolved a canonical mission
        # directory NAME; re-anchor the meta read on the primary checkout under
        # that canonical name (the candidate itself may be a coord-worktree dir
        # with no ``meta.json``), again via the blessed constructor. For a
        # literal slug that already matched on disk the name is unchanged and
        # this collapses to the same primary candidate.
        canonical_primary = primary_feature_dir_for_mission(
            repo_root, candidate_dir.name
        )
        return canonical_primary / _META_JSON_FILENAME, canonical_primary

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
            # Compose the diagnostic paths through the blessed path-constructor
            # (the sanctioned ``KITTY_SPECS_DIR`` owner) so aggregate carries no
            # raw ``repo_root / KITTY_SPECS_DIR / <slug>`` self-composition for
            # any surface — even error-path diagnostics (WP01 raw-bypass).
            from specify_cli.missions._read_path_resolver import (
                _canonicalize_primary_read_handle,
                primary_feature_dir_for_mission,
            )

            # WP05/FR-005: route through _canonicalize_primary_read_handle.
            diag_primary = primary_feature_dir_for_mission(
                self.repo_root,
                _canonicalize_primary_read_handle(self.repo_root, self.mission_slug),
            )
            raise MissionMetadataUnavailable(
                mission_slug=self.mission_slug,
                meta_path=diag_primary / _META_JSON_FILENAME,
                primary_candidate=diag_primary,
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
