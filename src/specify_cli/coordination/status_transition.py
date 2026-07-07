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
from typing import Any

from specify_cli.coordination.outbound import queue_saas_emission
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.coordination.status_service import (
    EventLogReadContract,
    read_event_log,
    wp_lane_actor_from_events,
)
from specify_cli.coordination.transaction import BookkeepingTransaction
from specify_cli.lanes._git import branch_exists as _branch_exists
from specify_cli.lanes.branch_naming import (
    coord_mission_dir_name as _seam_coord_mission_dir_name,
    resolve_transaction_mid8,
    worktree_dir_name,
)
from specify_cli.mission_metadata import load_meta
from specify_cli.status import emit as _emit
from specify_cli.status.adapters import fire_dossier_sync
from specify_cli.status.models import DoneEvidence, GuardContext, Lane, StatusEvent, TransitionRequest
from specify_cli.status.reducer import reduce as _reduce_events
from specify_cli.status.store import read_events as _read_raw_events
from specify_cli.status.transitions import is_terminal, resolve_lane_alias, validate_transition
from specify_cli.workspace import canonicalize_feature_dir, delete_context


@dataclass(frozen=True)
class _TransactionIdentity:
    repo_root: Path
    feature_dir: Path
    mission_id: str | None  # WP04/FR-004: ULID or None; never a slug-derived fallback
    mid8: str
    destination_ref: str
    meta_exists: bool
    coordination_branch: str | None
    transaction_meta_exists: bool


def _repo_root_for_feature(feature_dir: Path, repo_root: Path | None) -> Path:
    """Resolve the canonical primary repo root for a status-transition feature dir.

    R5 adoption (FR-001 / D-12): the prior ``feature_dir.parent.parent`` walk
    keyed on ``kitty-specs`` resolved the *enclosing worktree* root (the coord
    worktree under coord topology — the #2004/#2007 flatten hazard). It is now
    routed to the single canonical worktree-pointer resolver
    (``workspace.primary_root`` semantics), so a coord/lane worktree feature dir
    follows its ``.git`` pointer back to the canonical MAIN checkout and a
    submodule stops at the submodule root (#2011). The explicit ``repo_root``
    short-circuit is preserved for callers that already carry one. When no
    enclosing git repo can be resolved (ad-hoc test fixtures built outside a
    worktree) we degrade to ``feature_dir`` — byte-identical to the prior
    non-``kitty-specs`` fallback — so those callers keep working.
    """
    if repo_root is not None:
        return repo_root
    from specify_cli.workspace.root_resolver import (  # noqa: PLC0415
        WorkspaceRootNotFound,
        resolve_canonical_root,
    )

    try:
        canonical: Path = resolve_canonical_root(feature_dir)
    except WorkspaceRootNotFound:
        return feature_dir
    return canonical


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


def _transaction_dir_name(mission_slug: str, mid8: str) -> str:
    """Return the on-disk transaction (kitty-specs) dir name for this mission.

    Delegates to the seam's VERBATIM coordination primitive
    (``lanes.branch_naming.coord_mission_dir_name``, FR-010): exactly ONE
    algorithm for the coordination ``<slug>-<mid8>`` grammar, reconstructed
    byte-identical to the prior hand-rolled body. The ``mission_slug`` arrives
    VERBATIM from ``meta.json`` (including any legacy ``NNN-`` prefix); the seam
    primitive does NOT strip it, so the transaction dir matches the on-disk coord
    target (#1589). ``mid8`` may be ``""`` for the legacy/flattened routing path —
    the verbatim primitive preserves the prior ``f"{slug}-"`` form there, so
    routing stays byte-identical. The canonical, NNN-stripping ``mission_dir_name``
    is NOT used here.
    """
    return _seam_coord_mission_dir_name(mission_slug, mid8=mid8)


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


def _is_under_worktree(feature_dir: Path) -> bool:
    """Return whether *feature_dir* lives under a ``.worktrees`` segment.

    #1900 / FR-001: the raw ``".worktrees" in parts`` path-shape proposal is no
    longer spelled here — it routes through the blessed seam authority
    :func:`is_under_worktrees_segment` (``coordination/surface_resolver.py``), the
    single home of that shape idiom (C-SEAM-1). This is a *shape* read (generic
    worktree-context detection / re-anchor gate), NOT a coord-vs-lane routing
    decision; coord routing uses :func:`_is_coord_worktree_status_surface` below,
    which consults the git registry.
    """
    from specify_cli.coordination.surface_resolver import (  # noqa: PLC0415
        is_under_worktrees_segment,
    )

    return bool(is_under_worktrees_segment(feature_dir))


def _is_coord_worktree_status_surface(feature_dir: Path) -> bool:
    """Return True only when *feature_dir* is a *registered* coord worktree.

    #1900 / FR-001 / FR-007: the former hand-rolled ``-coord`` suffix + parts
    predicate (a 5th parallel topology-selection site) is migrated to the single
    canonical authority :func:`is_registered_coord_worktree`
    (``coordination/surface_resolver.py``) — name proposes, the git worktree
    registry disposes (C-SEAM-1). A lane worktree, the primary checkout, or an
    unregistered husk therefore returns ``False``, killing the split-brain where
    a lane/husk path silently received coord write-contract routing
    (#1589/#1821).

    Fails *open to non-coord* when the registry cannot be read
    (:class:`WorktreeRegistryUnavailable`) — e.g. ad-hoc test fixtures or paths
    outside a git repo. The historical predicate was pure-path and never raised;
    treating an unreadable registry as "not a coord surface" preserves that
    no-raise contract here while keeping the authoritative answer whenever git
    *can* be consulted. (The genuine fail-closed posture for status reads lives
    in the resolver itself, not in this routing convenience.)
    """
    from specify_cli.coordination.surface_resolver import (  # noqa: PLC0415
        WorktreeRegistryUnavailable,
        is_registered_coord_worktree,
    )

    try:
        return bool(is_registered_coord_worktree(feature_dir))
    except WorktreeRegistryUnavailable:
        return False


def _canonical_repo_root(feature_dir: Path, repo_root: Path) -> Path:
    """Return the canonical (main-checkout) repo root for the status anchor.

    The CWD-invariant primary feature-dir anchor must be composed from the
    *main-checkout* repo root; deriving it from a lane-worktree root would
    anchor status on a lane-local (sparse-excluded) surface. We therefore
    canonicalize the root via the single worktree-pointer resolver. Worktree
    roots (coordination or lane) are returned as-is here — the lane re-anchor to
    the canonical primary surface happens one level up in
    :func:`_canonical_primary_feature_dir`'s ``_fallback`` (which DOES split coord
    from lane via the registry authority). Falls back to the supplied root when
    no enclosing git repo is found (ad-hoc test fixtures built outside a
    worktree).

    #1900 / FR-001: the worktree-context read is the blessed seam shape predicate
    (:func:`_is_under_worktree` → ``is_under_worktrees_segment``), not a raw
    ``".worktrees" in parts`` test (C-SEAM-1). Byte-identical to the prior
    ``_is_coordination_feature_dir`` membership it replaces.
    """
    if _is_under_worktree(feature_dir):
        return repo_root

    from specify_cli.workspace.root_resolver import (  # noqa: PLC0415
        WorkspaceRootNotFound,
        resolve_canonical_root,
    )

    try:
        canonical: Path = resolve_canonical_root(feature_dir)
    except WorkspaceRootNotFound:
        return repo_root
    return canonical


def _canonical_primary_feature_dir(
    repo_root: Path, mission_slug: str, fallback: Path
) -> Path:
    """Resolve the CWD-invariant primary feature-dir anchor via the facade.

    Consumes the single canonical authority (``candidate_feature_dir_for_mission``
    — the coord-aware resolver that ``resolve_status_surface`` / ``MissionStatus``
    are built on) so the primary anchor is identical whether the request
    originates from a sparse lane worktree or the primary checkout. This is the
    #1737 / F-007 root fix: the transaction-identity anchor no longer re-derives
    where status lives from a CWD-dependent path, so an in-progress WP can no
    longer be misread as ``genesis`` from a lane worktree.

    Coordination topology resolution downstream
    (``_read_contract_from_transaction_target``) still derives the coord path
    from this anchor + ``meta.json``; we keep the anchor on the canonical primary
    dir so that meta loading and coord-ref derivation remain intact (C-004).

    Returns ``fallback`` (the canonicalized request dir) when no canonical
    surface can be resolved — e.g. ad-hoc test fixtures or bootstrap windows
    where ``meta.json`` is not yet present.
    """
    from specify_cli.coordination.surface_resolver import (  # noqa: PLC0415
        resolve_status_surface_with_anchor,
    )
    from specify_cli.missions._read_path_resolver import (  # noqa: PLC0415
        StatusReadPathNotFound,
    )
    from specify_cli.missions._read_path_resolver import (  # noqa: PLC0415
        candidate_feature_dir_for_mission,
    )

    def _fallback() -> Path:
        # The request-derived fallback is only safe when it is the canonical
        # coord surface or a non-worktree primary path. A *lane* ``.worktrees``
        # path is a sparse-excluded surface that would both misread status and
        # trip the primary-checkout read contract, so anchor on the canonical
        # primary candidate instead (fail to the authority, never to the lane).
        # #1900 / FR-001: coord-vs-lane is the git-registry authority's call
        # (_is_coord_worktree_status_surface → is_registered_coord_worktree), and
        # the generic "am I under a worktree" gate is the blessed shape predicate
        # (_is_under_worktree → is_under_worktrees_segment) — neither spells a raw
        # ``-coord``/``.worktrees`` path test here (C-SEAM-1).
        if _is_coord_worktree_status_surface(fallback):
            return fallback
        if _is_under_worktree(fallback):
            anchor: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
            return anchor
        return fallback

    # FR-005 / #1821: resolve the canonical surface ONCE and consume the carried
    # primary anchor. The previous code resolved the surface for validation,
    # discarded it, then re-invoked candidate_feature_dir_for_mission — a second
    # composition of the same path. Now both halves come from one resolution.
    try:
        resolved = resolve_status_surface_with_anchor(repo_root, mission_slug)
    except FileNotFoundError:
        # No meta.json at the canonical location: degrade to the request dir so
        # ad-hoc fixtures and the create→first-write window keep working.
        return _fallback()
    except ValueError:
        # Malformed meta — surface the canonical anchor anyway; downstream meta
        # loading will report the same condition consistently.
        malformed_anchor: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
        return malformed_anchor
    except StatusReadPathNotFound as exc:
        # Fail-closed surface refusal (PR #1850 M6): the coord worktree root is
        # materialized without the mission dir (#1589/#1821). The refusal
        # protects status READERS from a stale primary surface; the transaction
        # identity needs only the canonical primary anchor — which the
        # structured error already carries (re-resolving via the candidate
        # resolver would just re-raise). Coordination topology is still
        # honoured downstream by ``_read_contract_from_transaction_target``.
        refusal_anchor: Path = exc.primary_candidate
        return refusal_anchor
    return resolved.primary_anchor


def _resolve_write_target(
    repo_root: Path, mission_slug: str, coord_branch: str | None
) -> str:
    """Resolve the status write-target ref via the canonical placement resolver.

    FR-004 / D-2 adoption (the latent-bug fix): the prior inline selector was
    ``coord_branch or _current_branch(repo_root)``. The flat arm
    (``_current_branch`` = ``git rev-parse --abbrev-ref HEAD``) was **CWD-dependent**
    — it routed status events to whatever branch happened to be checked out,
    diverging from the CWD-invariant ``target_branch`` the read/placement path
    resolves to (reduction-census §6). This routes the write-target through the
    single public placement resolver
    (:func:`mission_runtime.resolve_placement_only`), whose
    ``CommitTarget`` is BYTE-IDENTICAL to the value the full execution context
    builder computes:

    * **Coord topology** (``meta.coordination_branch`` declared) →
      ``CommitTarget(ref=coordination_branch)`` — identical to the prior
      ``coord_branch`` short-circuit (idempotency-preserving, NFR-004).
    * **Flat/base topology** (no coord branch) → ``CommitTarget(ref=target_branch)``
      — the CWD-invariant fix that supersedes ``_current_branch``.

    When the placement resolver cannot resolve the mission (no ``meta.json`` yet
    — the create→first-write window, or an ad-hoc fixture outside a resolvable
    mission), it degrades to the prior selector so those callers keep working
    without churn.
    """
    from mission_runtime import (  # noqa: PLC0415
        ActionContextError,
        MissionArtifactKind,
        resolve_placement_only,
    )
    from specify_cli.missions._read_path_resolver import (  # noqa: PLC0415
        StatusReadPathNotFound,
    )

    try:
        # The STATUS write target MUST keep resolving the coordination branch under
        # coord topology (write-surface-coherence WP02 / T031 / C-001 / G-2).
        # STATUS_STATE is a coordination kind, so the kind-aware placement keeps the
        # topology-routed ref — it MUST NOT be flipped to a primary kind.
        return resolve_placement_only(
            repo_root, mission_slug, kind=MissionArtifactKind.STATUS_STATE
        ).ref
    except (ActionContextError, StatusReadPathNotFound, FileNotFoundError):
        # Unresolvable mission (pre-meta create window / ad-hoc fixture): fall
        # back to the prior selector so the bootstrap path stays functional.
        return coord_branch or _current_branch(repo_root)


def _identity_for_request(request: TransitionRequest) -> _TransactionIdentity:
    raw_feature_dir = request.feature_dir or request.mission_dir
    if raw_feature_dir is None:
        raise TypeError("transactional status emit requires feature_dir/mission_dir")

    mission_slug = request.mission_slug or request._legacy_mission_slug
    if mission_slug is None:
        raise TypeError("transactional status emit requires mission_slug")

    # #1737 / F-007: anchor the transaction identity on the CWD-invariant
    # canonical primary feature dir resolved through the facade, instead of
    # trusting the (CWD-dependent, existence-gated) canonicalize redirect alone.
    canonical_feature_dir = canonicalize_feature_dir(raw_feature_dir)
    interim_repo_root = _repo_root_for_feature(canonical_feature_dir, request.repo_root)
    canonical_repo_root = _canonical_repo_root(canonical_feature_dir, interim_repo_root)
    feature_dir = _canonical_primary_feature_dir(
        canonical_repo_root, mission_slug, fallback=canonical_feature_dir
    )
    repo_root = request.repo_root or canonical_repo_root

    # FR-006: canonical reader contract (a) — None on missing, ValueError on
    # malformed (defaults stated explicitly). ``meta_exists`` below keys on the
    # ``None`` (missing) arm; a malformed meta surfaces the typed corrupt-meta error.
    meta = load_meta(feature_dir, allow_missing=True, on_malformed="raise")

    coord_branch: str | None = None
    mission_id: str | None = None
    mid8: str | None = None
    meta_exists = isinstance(meta, dict)
    if isinstance(meta, dict):
        raw_coord = meta.get("coordination_branch")
        raw_mission_id = meta.get("mission_id")
        raw_mid8 = meta.get("mid8")
        coord_branch = str(raw_coord) if raw_coord else None
        mission_id = str(raw_mission_id) if raw_mission_id else None
        mid8 = str(raw_mid8) if raw_mid8 else None
        # Single grammar (FR-010): when meta carries no explicit ``mid8`` we leave
        # it ``None`` and let the canonical ``resolve_transaction_mid8`` derive it
        # from the declared ``mission_id`` (its cascade does ``mission_id[:8]``).
        # Pre-deriving here via the bare slicer was redundant (proven byte-equal)
        # and is the last external caller of the demoted ``mid8`` primitive
        # (mission 01KV7SFD / WP01).

    # WP04/FR-004: mission_id is the canonical ULID or None — never a slug-derived
    # fallback. The f"legacy-{slug}" sentinel is removed from the stored field;
    # BookkeepingTransaction.acquire receives it ONLY as an explicit worktree-lock
    # identifier for legacy missions (not persisted to any mission_id event field).
    effective_mission_id = mission_id
    # FR-007: the mid8 names the ON-DISK transaction dir. Route through the
    # canonical fail-closed authority instead of fabricating a zero-padded mid8
    # from the slug — that idiom invented a wrong-but-plausible dir name and
    # mis-routed the transaction/lock target.
    effective_mid8 = resolve_transaction_mid8(
        mission_slug,
        mission_id=mission_id,
        mid8=mid8,
        coordination_branch=coord_branch,
    )
    transaction_dir_name = _transaction_dir_name(mission_slug, effective_mid8)
    return _TransactionIdentity(
        repo_root=repo_root,
        feature_dir=feature_dir,
        mission_id=effective_mission_id,
        mid8=effective_mid8,
        destination_ref=_resolve_write_target(repo_root, mission_slug, coord_branch),
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
    return read_event_log(_read_contract_from_transaction_target(identity, mission_slug))


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
        from specify_cli.status.lane_reader import (  # noqa: PLC0415
            CanonicalStatusNotFoundError,
            get_wp_lane,
        )

        try:
            return Lane(resolve_lane_alias(get_wp_lane(identity.feature_dir, wp_id))), None
        except (ValueError, FileNotFoundError, CanonicalStatusNotFoundError):
            # GENESIS-fallback contract (FR-008d / R7): exactly two expected
            # failure shapes mean "unseeded WP" and fall back to GENESIS
            # (matching _derive_from_lane on the write side — Contract 3,
            # FR-009): a pre-schema/unknown lane value (ValueError from
            # Lane()/resolve_lane_alias, e.g. the "uninitialized" sentinel)
            # and an absent log/WP file. ``CanonicalStatusNotFoundError`` is
            # the codebase's concrete "absent log" signal (``get_wp_lane``
            # raises it instead of FileNotFoundError; the contract names the
            # shape, this names the type). Every other exception
            # (PermissionError, corruption signals, ...) is a real error and
            # MUST propagate — the former broad ``except Exception`` silently
            # converted genesis-corruption signals into "unseeded WP" (#1736
            # dormant mask 1).
            return Lane.GENESIS, None
    return wp_lane_actor_from_events(events, wp_id)


def _read_contract_routes_through_coordination(
    identity: _TransactionIdentity,
) -> bool:
    """Decide the coord-vs-primary read-contract SHAPE from the STORED topology.

    FR-009 / SC-001: the read-contract coord-vs-primary SHAPE is decided by the
    WP02 topology SSOT, never re-inferred from a bare ``coordination_branch is
    None`` SURFACE test — the exact forbidden re-derivation SC-001 gates against.

    This answers ONLY "is this a coord-SHAPED mission?". The transient on-disk
    arms in the caller (worktree-exists / branch-deleted) keep PROBING the
    materialized-yet/deleted-now state (C-006: #1718 create-window / #1848
    coord-deleted) — the stored topology must NOT answer that transient question.

    Mirrors the canonical WP03 surface-resolver pattern
    (``surface_resolver._topology_uses_coord_surface``): the binary
    coord-vs-primary SHAPE is disposed by the WP02 topology SSOT
    (:func:`mission_runtime.classify_topology`) over the stored
    ``coordination_branch`` VALUE, NOT by a bare ``coordination_branch is None``
    re-inference. ``has_lanes`` is irrelevant to the binary coord-routing SHAPE
    (both ``COORD`` and ``LANES_WITH_COORD`` route through coordination), so the
    coord-less default arm is used — identical to the surface resolver's
    historical two-arg call sites.

    The shape is READ from the WP02 stored ``topology`` (the relocated read site
    now READS the stored value rather than relaying a parallel
    ``classify_topology(coord_branch, …)`` inference — randy #2 / SC-001): the
    PURE :func:`read_topology` reader is anchored on the canonical primary
    ``feature_dir`` the identity carries (where ``meta.json`` lives). An
    un-backfilled legacy mission (or absent/malformed meta) degrades to deriving
    the shape ONCE from the ``coordination_branch`` value via WP01's
    :func:`classify_topology` SSOT — the same single authority, no parallel grid.

    The derivation is **pure** (no ``meta.json`` write), so a status READ never
    persists a ``topology`` back-fill (the read-must-not-write contract, #1814).
    ``mid8`` materialization / branch-deletion stay the transient probe arms below
    (C-006).
    """
    from mission_runtime import (  # noqa: PLC0415
        classify_topology,
        routes_through_coordination,
    )
    from specify_cli.migration.backfill_topology import (  # noqa: PLC0415
        read_topology,
    )

    try:
        topology = read_topology(identity.feature_dir)
    except (FileNotFoundError, ValueError, OSError):
        # Un-backfilled legacy mission / absent / malformed primary meta: derive
        # the shape ONCE from the coordination-branch value-read (the historical
        # two-arg arm). Same single ``classify_topology`` authority, no re-inference.
        # This is the C-002 genuine-fallback RELAY — the exception arm reads the
        # stored topology first and only relays via ``classify_topology`` here; it
        # is NOT a routing predicate and stays distinct from the coord-routing
        # disposal below (NFR-005).
        topology = classify_topology(identity.coordination_branch, has_lanes=False)
    # The coord-routing membership is disposed by the ONE canonical predicate over
    # the ONE canonical set — no inline ``{COORD, LANES_WITH_COORD}`` frozenset is
    # restated here (FR-005 / S1192).
    return routes_through_coordination(topology)


def _read_contract_from_transaction_target(
    identity: _TransactionIdentity,
    mission_slug: str,
) -> EventLogReadContract:
    """Resolve the read-only contract for the transaction write target."""
    if not _transaction_topology_available(identity, mission_slug):
        # #1900 / FR-001: the worktree-context read is the blessed seam shape
        # predicate (_is_under_worktree → is_under_worktrees_segment), not a raw
        # ``.worktrees`` membership test (C-SEAM-1). Byte-identical to the prior
        # ``_is_coordination_feature_dir`` membership it replaces — a feature dir
        # already inside a worktree carries the coordination read contract.
        if _is_under_worktree(identity.feature_dir):
            return EventLogReadContract.coordination_worktree(identity.feature_dir)
        return EventLogReadContract.primary_checkout(identity.feature_dir)
    # FR-009 / SC-001: the coord-vs-primary SHAPE is read from the STORED topology
    # (the WP03 seam), retiring the prior ``coordination_branch is None`` SURFACE
    # re-inference. The transient on-disk arms below stay probe-discriminated.
    if not _read_contract_routes_through_coordination(identity):
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
    if not _branch_exists(identity.repo_root, identity.destination_ref):
        # The coordination branch was deleted (e.g. post-merge cleanup).
        # FR-018 recreates it from the destination ref at write time, so the
        # primary checkout is the authoritative read source until then;
        # reading the dangling ref would report every WP as genesis (#1847).
        return EventLogReadContract.primary_checkout(identity.feature_dir)
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


# ---------------------------------------------------------------------------
# Workspace-context tombstone on cancel (FR-005 / LC-6, #1842 WP03)
# ---------------------------------------------------------------------------


def _lane_wp_ids_all_terminal(
    work_packages: dict[str, dict[str, Any]], wp_ids: tuple[str, ...]
) -> bool:
    """Return whether every WP in *wp_ids* has reached a terminal lane.

    Mirrors ``status/doctor.py``'s ``check_orphan_workspaces`` all-terminal
    gate (``all(wp.lane in {done, canceled})``), scoped to one lane's WPs
    instead of every WP in the mission: the workspace-context JSON is
    per-lane, while a ``canceled`` transition is emitted per-WP, so a lane's
    shared context may only be tombstoned once every WP sharing that
    worktree is done or canceled. A WP absent from *work_packages* (never
    transitioned) is treated as non-terminal.
    """
    for wp_id in wp_ids:
        wp_state = work_packages.get(wp_id)
        lane_value = wp_state.get("lane") if wp_state else None
        if lane_value is None or not is_terminal(lane_value):
            return False
    return True


def _tombstone_lane_workspace_context_on_cancel(
    *,
    repo_root: Path,
    mission_slug: str,
    read_feature_dir: Path,
    event: StatusEvent | None,
) -> None:
    """Delete a lane's ``.kittify/workspaces/<slug>-<lane>.json`` once a
    ``canceled`` transition leaves every WP sharing that lane terminal.

    FR-005 / C-004: additive only — this changes no validation, persistence,
    or fan-out behavior for any other transition. No-ops when: *event* is
    ``None`` (the legacy alias-collapse no-op arm — nothing actually
    transitioned); the transition is not into ``canceled``; the mission has
    no ``lanes.json`` (flat/legacy execution has no lane-scoped context to
    tombstone); the WP is not lane-owned; or the lane still has a
    non-terminal WP. ``delete_context`` is a pure, order-independent unlink
    (no worktree gate) — safe to call even when the context file was never
    created (planning-artifact WPs) or was already removed.
    """
    if event is None or event.to_lane != Lane.CANCELED:
        return

    from mission_runtime import MissionArtifactKind  # noqa: PLC0415
    from specify_cli.lanes.persistence import CorruptLanesError, read_lanes_json  # noqa: PLC0415
    from specify_cli.missions._read_path_resolver import resolve_planning_read_dir  # noqa: PLC0415

    lanes_read_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.LANE_STATE
    )
    try:
        lanes_manifest = read_lanes_json(lanes_read_dir)
    except CorruptLanesError:
        return  # Malformed lanes.json is not this hook's problem to repair.
    if lanes_manifest is None:
        return

    lane = lanes_manifest.lane_for_wp(event.wp_id)
    if lane is None or not lane.wp_ids:
        return

    snapshot = _reduce_events(_read_raw_events(read_feature_dir))
    if not _lane_wp_ids_all_terminal(snapshot.work_packages, lane.wp_ids):
        return

    workspace_name = worktree_dir_name(mission_slug, mission_id=None, lane_id=lane.lane_id)
    delete_context(repo_root, workspace_name)


def emit_status_transition_transactional(
    request: TransitionRequest,
    *,
    ensure_sync_daemon: bool = True,
    sync_dossier: bool = True,
    operation: str | None = None,
    capability: GuardCapability = GuardCapability.STANDARD,
) -> StatusEvent:
    """Validate, append, commit, then fan out one status transition."""
    feature_dir = request.feature_dir or request.mission_dir
    mission_slug = request.mission_slug or request._legacy_mission_slug
    if feature_dir is None or mission_slug is None or request.wp_id is None:
        raise TypeError("transactional status emit requires feature_dir, mission_slug, and wp_id")

    identity = _identity_for_request(request)
    if not _transaction_topology_available(identity, mission_slug):
        event = _emit.emit_status_transition(
            request,
            ensure_sync_daemon=ensure_sync_daemon,
            sync_dossier=sync_dossier,
        )
        _tombstone_lane_workspace_context_on_cancel(
            repo_root=identity.repo_root,
            mission_slug=mission_slug,
            read_feature_dir=identity.feature_dir,
            event=event,
        )
        return event

    # WP04/FR-004: BookkeepingTransaction.acquire requires str for its lock/path
    # management. For legacy missions (identity.mission_id is None), use the
    # explicit f"legacy-{slug}" string ONLY for the transaction lock — this is
    # documented and NOT written into any mission_id event field.
    _txn_mission_id = identity.mission_id or f"legacy-{mission_slug}"
    with BookkeepingTransaction.acquire(
        repo_root=identity.repo_root,
        mission_id=_txn_mission_id,
        mission_slug=mission_slug,
        mid8=identity.mid8,
        destination_ref=identity.destination_ref,
        operation=operation or f"status transition {request.wp_id}",
        capability=capability,
    ) as txn:
        # WP04: identity.mission_id is now str | None; None means no ULID (legacy).
        # The old .startswith("legacy-") sentinel is replaced by the None check.
        mission_id_for_event = identity.mission_id
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
        _tombstone_lane_workspace_context_on_cancel(
            repo_root=identity.repo_root,
            mission_slug=mission_slug,
            read_feature_dir=txn.feature_dir,
            event=event,
        )
        return event


def emit_status_transition_batch_transactional(
    requests: list[TransitionRequest],
    *,
    ensure_sync_daemon: bool = True,
    sync_dossier: bool = True,
    operation: str | None = None,
    capability: GuardCapability = GuardCapability.STANDARD,
) -> list[StatusEvent]:
    """Validate, append, commit, then fan out a same-WP transition batch."""
    if not requests:
        return []

    first = requests[0]
    mission_slug = first.mission_slug or first._legacy_mission_slug
    first_feature_dir_raw = first.feature_dir or first.mission_dir
    if mission_slug is None or first.wp_id is None or first_feature_dir_raw is None:
        raise TypeError(
            "transactional status batch requires feature_dir/mission_dir, mission_slug, and wp_id"
        )

    identity = _identity_for_request(first)
    if not _transaction_topology_available(identity, mission_slug):
        return _emit.emit_status_transition_batch(
            requests,
            ensure_sync_daemon=ensure_sync_daemon,
            sync_dossier=sync_dossier,
        )

    # WP04/FR-004: explicit legacy fallback for transaction lock only (not event field).
    _txn_mission_id_batch = identity.mission_id or f"legacy-{mission_slug}"
    with BookkeepingTransaction.acquire(
        repo_root=identity.repo_root,
        mission_id=_txn_mission_id_batch,
        mission_slug=mission_slug,
        mid8=identity.mid8,
        destination_ref=identity.destination_ref,
        operation=operation or f"status transition batch {first.wp_id}",
        capability=capability,
    ) as txn:
        # WP04: identity.mission_id is str | None; None replaces the old "legacy-" sentinel.
        mission_id_for_event = identity.mission_id
        from_lane = str(_emit._derive_from_lane(txn.feature_dir, first.wp_id))
        built: list[tuple[StatusEvent, TransitionRequest]] = []
        started_at = datetime.now(UTC)

        # The loop below makes sure every transition in this batch is for the
        # same work package, by checking they all sit in the same mission folder.
        # We compare against the first request's folder.
        #
        # We must NOT compare against identity.feature_dir. In coordination mode a
        # mission exists in two folders on disk: the normal checkout, and a
        # separate "coordination" worktree. The requests point at the coordination
        # folder, but identity.feature_dir points at the normal one — same work
        # package, different folder. Comparing against it rejected valid batches.
        #
        # (We work this out here, not earlier, because the transaction above just
        # registered the coordination worktree with git, and canonicalize_feature_dir
        # only keeps the coordination folder once that registration exists.)
        first_feature_dir = canonicalize_feature_dir(first_feature_dir_raw)

        for request in requests:
            request_feature_dir = request.feature_dir or request.mission_dir
            request_mission_slug = request.mission_slug or request._legacy_mission_slug
            if (
                request_feature_dir is None
                or canonicalize_feature_dir(request_feature_dir) != first_feature_dir
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
