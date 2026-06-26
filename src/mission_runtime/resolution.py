"""Execution-state resolution entry point (canonical surface, internal module).

This is an **internal** submodule of the :mod:`mission_runtime` umbrella. It is
import-forbidden from outside the package — consumers use the symbols re-exported
from :mod:`mission_runtime` only (see ADR 2026-06-07-1 and
``tests/architectural/test_mission_runtime_surface.py``).

WP03 relocates the hardened ``resolve_action_context`` (and its helpers) from
``specify_cli.core.execution_context`` here under the Strangler migration. The
implementation is moved verbatim — this is the single sanctioned resolver
(FR-003/FR-005); behaviour is preserved (NFR-001) and no parallel resolver
survives (NFR-002). The old ``core/execution_context.py`` is removed entirely —
no importers remained after the caller migration, so it is deleted, not shimmed.

Prompts should not discover context on their own. They call into this
command-owned resolver, which determines the active mission, target branch,
work package, workspace path, and any action-specific commands to run.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, cast, get_args

from mission_runtime.artifacts import (
    MissionArtifactKind,
    _PRIMARY_ARTIFACT_KINDS,
)
from mission_runtime.context import (
    ArtifactPlacementFragment,
    BranchRefFragment,
    CommitTarget,
    ExecutionContext,
    IdentityFragment,
    MissionTopology,
    StatusSurfaceFragment,
    WorkspaceFragment,
    routes_through_coordination,
)


ActionName = Literal[
    "specify",
    "plan",
    "analyze",
    "tasks",
    "tasks_outline",
    "tasks_packages",
    "tasks_finalize",
    "implement",
    "review",
    "accept",
    "status",
]
ACTION_NAMES: tuple[str, ...] = cast(tuple[str, ...], get_args(ActionName))

__all__ = [
    "ACTION_NAMES",
    "ActionContextError",
    "ActionName",
    "resolve_action_context",
    # resolve_context_for_mission: demoted — no cross-module src/ from-import
    # callers (WP01 harden-dead-symbol-gate-01KW0RJR).
    "resolve_placement_only",
]


class ActionContextError(RuntimeError):
    """Raised when canonical action context cannot be resolved.

    The single error type consumers catch. The resolver raises this on
    unresolvable context — there is never a silent fallback (see the contract).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# Mission-level lifecycle actions resolve the mission context without a work
# package (FR-011 full-lifecycle parity).
_MISSION_LEVEL_ACTIONS: frozenset[str] = frozenset(
    {
        "specify",
        "plan",
        "analyze",
        "tasks",
        "tasks_outline",
        "tasks_packages",
        "tasks_finalize",
        "accept",
        "status",
    }
)


def build_execution_context(
    **fields: Any,
) -> ExecutionContext:
    """Construct the ONE :class:`ExecutionContext` — the sole construction door.

    This is the **package-private** single factory for the canonical context
    composite (D-6 / IC-01 / C-001 — no new public symbol; it is not exported
    from :mod:`mission_runtime`). :func:`resolve_action_context` delegates every
    construction here; there is exactly one ``ExecutionContext(`` call in
    production code (this body). The composite is frozen, so callers assemble all
    fields up front and never patch a built context.

    Build-time invariant (C-IC01 / FR-009 / D-2): when a ``branch_ref`` fragment
    is supplied, ``target_branch`` MUST equal ``branch_ref.target_branch``; on
    mismatch this raises ``ActionContextError("CONTEXT_INVARIANT_VIOLATION", …)``
    naming both values. The invariant is **never** asserted against
    ``branch_name`` — the WP lane branch legitimately differs from the mission
    target branch (D-2 supersedes the spec's original FR-009 wording).

    Write-projection boundary contract (D-6): write surfaces compose
    names/paths/identity from the factory-projected :class:`IdentityFragment` +
    :class:`BranchRefFragment` (+ workspace/surface); they **MUST NOT** re-derive
    ``mission_id`` / ``mid8`` / ``primary_root`` independently. ``branch_naming``
    is the grammar collaborator the resolver *calls*; the factory is the
    identity/topology authority that feeds it. The deferred write-side
    (#1716 / #1878, Mission B) adopts against this frozen seam — not a rewrite.
    """
    context = ExecutionContext(**fields)
    branch_ref = context.branch_ref
    if branch_ref is not None and context.target_branch != branch_ref.target_branch:
        raise ActionContextError(
            "CONTEXT_INVARIANT_VIOLATION",
            "ExecutionContext.target_branch "
            f"({context.target_branch!r}) must equal branch_ref.target_branch "
            f"({branch_ref.target_branch!r}); the composite is internally "
            "inconsistent (FR-009 / C-IC01).",
        )
    return context


def resolve_context_for_mission(
    mission_id: str,
    topology: MissionTopology,
    *,
    action: ActionName,
    mission_slug: str,
    feature_dir: str,
    target_branch: str,
    identity: IdentityFragment,
    branch_ref: BranchRefFragment,
    status_surface: StatusSurfaceFragment | None = None,
    workspace: WorkspaceFragment | None = None,
    coordination_branch_signal: str | None = None,
    has_lanes_signal: bool | None = None,
    **extra_fields: Any,
) -> ExecutionContext:
    """PURE projection of an :class:`ExecutionContext` from stored topology (FR-004).

    The **functional core** of the single planning-surface authority. Given a
    mission identity + the WP02 **stored** :class:`MissionTopology` (read from
    ``meta.json`` by the imperative shell) and the shell-assembled fragments, it
    projects exactly one :class:`ExecutionContext` through the PURE construction
    door :func:`build_execution_context` (``resolution.py`` factory). It performs
    **zero** filesystem or git I/O (NFR-005): there is no ``open`` / ``read_text``
    / ``load_meta`` / ``subprocess`` / ``git`` / ``*.exists()`` / ``*.stat()`` /
    ``_assemble_core_fragments`` call in this body — every such read happens in the
    shell BEFORE the resolver and arrives as an argument.

    Placement (C-001 / FR-004 / FR-001b): the destination/placement ref is a
    ref-only :class:`CommitTarget` (C-007) — the coord-routing decision is read
    from the stored ``topology`` via :func:`routes_through_coordination`, never
    from a retired per-ref enum. The supplied ``branch_ref.destination_ref`` is
    carried through unchanged, and the matching
    :class:`ArtifactPlacementFragment` shares that one ``CommitTarget`` (C-PLACE-1).

    C-003 (binding): this is a **thin projection over the PURE door**, sharing
    :func:`resolve_placement_only`'s narrow-projection *discipline* while sitting
    one layer UP. ``resolve_placement_only`` is the imperative SHELL — it itself
    calls :func:`_assemble_core_fragments` (FS/git) and projects the
    ``destination_ref`` out of those fragments. This resolver does NOT call
    ``_assemble_core_fragments`` or any reader: the shell assembles the fragments
    + reads the stored ``topology`` and threads them in; the resolver projects
    only :func:`build_execution_context`. That separation is what makes the
    zero-fixture purity test possible (T018 / SC-002).

    Optional input-assertion (T016 / C-003 spirit, fail-closed): when the shell
    ALSO supplies the structured ``coordination_branch_signal`` /
    ``has_lanes_signal`` it already read, and the **supplied** ``topology``
    disagrees with what those signals would classify, this raises
    ``ActionContextError("TOPOLOGY_INPUT_MISMATCH", …)`` naming BOTH topologies. It
    is an assertion over shell-provided inputs, NOT a disk re-derivation — the
    resolver stays pure. When the corroborating signals are not supplied the guard
    is skipped cleanly, so pure callers passing only the topology are unaffected.

    Args:
        mission_id: The canonical mission identity (already resolved by the shell).
        topology: The WP02 stored mission topology (authoritative input).
        action: The action name the context is resolved for.
        mission_slug: The mission directory name / slug.
        feature_dir: The resolved mission feature directory (string substrate).
        target_branch: The mission target branch (resolved once by the shell).
        identity: Shell-assembled identity fragment.
        branch_ref: Shell-assembled branch-ref fragment; its ref-only
            ``destination_ref`` is carried through unchanged (C-007).
        status_surface: Shell-assembled status-surface fragment (optional).
        workspace: Shell-assembled workspace fragment (optional).
        coordination_branch_signal: Raw coordination-branch value the shell read,
            supplied ONLY to corroborate the topology (optional T016 guard).
        has_lanes_signal: Whether the mission has lanes, supplied ONLY to
            corroborate the topology (optional T016 guard).
        **extra_fields: Additional flat-substrate fields forwarded to the factory.

    Returns:
        The single projected :class:`ExecutionContext`.

    Raises:
        ActionContextError: ``TOPOLOGY_INPUT_MISMATCH`` when the optional
            corroborating signals contradict the supplied topology, or
            ``CONTEXT_INVARIANT_VIOLATION`` from the door.
    """
    if mission_id != identity.mission_id:
        raise ActionContextError(
            "TOPOLOGY_INPUT_MISMATCH",
            f"mission_id {mission_id!r} does not match identity fragment "
            f"mission_id {identity.mission_id!r}; the shell threaded inconsistent "
            "identity inputs.",
        )
    _assert_topology_corroborated(
        topology,
        coordination_branch_signal=coordination_branch_signal,
        has_lanes_signal=has_lanes_signal,
    )

    # ``CommitTarget`` is a ref-only carrier (C-007 / FR-001b): the coord-routing
    # decision is read from the stored ``topology`` via
    # :func:`routes_through_coordination`, never from a ref-local enum, so the
    # destination ref the shell already resolved is carried through unchanged and
    # the artifact placement shares that one ``CommitTarget`` (C-PLACE-1).
    destination_ref = branch_ref.destination_ref
    projected_branch_ref = branch_ref
    artifact_placement = ArtifactPlacementFragment(placement_ref=destination_ref)

    return build_execution_context(
        action=action,
        mission_slug=mission_slug,
        feature_dir=feature_dir,
        target_branch=target_branch,
        detection_method="explicit",
        identity=identity,
        branch_ref=projected_branch_ref,
        status_surface=status_surface,
        workspace=workspace,
        artifact_placement=artifact_placement,
        **extra_fields,
    )


def _assert_topology_corroborated(
    topology: MissionTopology,
    *,
    coordination_branch_signal: str | None,
    has_lanes_signal: bool | None,
) -> None:
    """Fail closed when supplied topology disagrees with corroborating signals.

    The T016 optional input-assertion. Skipped cleanly when ``has_lanes_signal``
    is ``None`` (the shell did not supply corroborating structured signals), so a
    pure caller passing only ``(mission_id, topology)`` is unaffected. This is an
    assertion over shell-provided inputs — it does NOT read disk (the resolver
    stays pure); it imports the WP01 :func:`classify_topology` authority to
    compute the signal-implied topology rather than re-implementing the 2×2 grid.
    """
    if has_lanes_signal is None:
        return
    from mission_runtime.context import classify_topology

    implied = classify_topology(coordination_branch_signal, has_lanes_signal)
    if implied is not topology:
        raise ActionContextError(
            "TOPOLOGY_INPUT_MISMATCH",
            f"supplied topology {topology.value!r} disagrees with the topology "
            f"{implied.value!r} implied by the corroborating signals "
            f"(coordination_branch={coordination_branch_signal!r}, "
            f"has_lanes={has_lanes_signal!r}); refusing to silently prefer one "
            "(C-003 fail-closed).",
        )


def _resolve_mission_slug(
    repo_root: Path,
    *,
    feature: str | None,
    cwd: Path | None,  # noqa: ARG001 -- kept for signature compatibility
    env: Mapping[str, str] | None,  # noqa: ARG001 -- kept for signature compatibility
) -> tuple[str, Path]:
    """Resolve the CANONICAL mission slug and read-side directory.

    Mission directory resolution is CWD-independent and topology-aware
    (WP08 T037, FR-030): for missions on the coord-branch topology the
    returned ``feature_dir`` points into the coordination worktree;
    for legacy missions it points into the primary checkout.  The
    caller never has to guess which view the operator is sitting in.

    The returned slug is the canonical mission-dir name (the resolved
    directory's name), NOT the raw operator handle: a bare ``mid8`` or
    numeric-prefix handle must yield the SAME identity, status surface,
    and placement as the full slug (F-001), so the raw handle never
    flows into downstream compositions.

    Raises ActionContextError if feature is not provided or the mission
    directory cannot be located in either view.
    """
    from specify_cli.core.paths import require_explicit_feature

    try:
        slug = require_explicit_feature(feature, command_hint="--mission <slug>")
    except ValueError as exc:
        raise ActionContextError("FEATURE_CONTEXT_UNRESOLVED", str(exc)) from exc

    # Route through the SINGLE guarded read-side seam (WP01 reroute, IC-01 /
    # FR-001): ``resolve_handle_to_read_path`` owns the primary-meta probe AND
    # the ONE sanctioned mid8 cascade internally, so this caller no longer
    # pre-derives the mid8 (``mid8_from_slug`` → ``_mid8_from_primary_meta``).
    # Byte-identical: the seam runs the same cascade and forwards the result to
    # the existence-gated topology resolver. Handle forms (bare mid8, numeric
    # prefix, ULID) are canonicalized inside the seam itself.
    #
    # Late import to avoid a hard module-load dependency for legacy consumers of
    # the resolver that pre-date its introduction.
    from specify_cli.missions._read_path_resolver import (
        MissionSelectorAmbiguous,
        StatusReadPathNotFound,
        resolve_handle_to_read_path,
    )

    try:
        feature_dir = resolve_handle_to_read_path(repo_root, slug)
    except StatusReadPathNotFound as exc:
        # Boundary translation (PR #1850 M6): the read resolver's fail-closed
        # refusal (coord worktree root materialized without the mission dir)
        # must surface as the single consumer-facing error type, preserving
        # the refusal message — never a raw specify_cli exception.
        raise ActionContextError(exc.error_code, str(exc)) from exc
    except MissionSelectorAmbiguous as exc:
        # Boundary translation (WP05 / FR-005 / #2010 bug #15): an ambiguous
        # handle propagates as a raw specify_cli exception if uncaught here.
        # Translate to the single consumer-facing type preserving the stable
        # error code (MISSION_AMBIGUOUS_SELECTOR) — never a silent fallback.
        raise ActionContextError(exc.error_code, str(exc)) from exc
    if not feature_dir.exists():
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED",
            f"Mission directory not found: {feature_dir}. Check that "
            f"'{slug}' is the correct mission slug.",
        )
    # Parse, don't re-derive: the resolved directory's name IS the canonical
    # mission slug (identical in the coord-worktree and primary views).
    return feature_dir.name, feature_dir


def _mid8_from_primary_meta(repo_root: Path, mission_slug: str) -> str:
    """Canonical mid8 for a slug whose name carries no parseable suffix.

    Reads the primary-checkout ``meta.json`` and runs the ONE sanctioned mid8
    cascade (:func:`resolve_declared_mid8`, NFR-005/#1868) instead of a
    hand-rolled ``meta.mid8`` → ``mission_id[:8]`` parallel impl (FR-002, C-007).
    Returns ``""`` when no identity-bearing meta exists (raw handles, scaffolds,
    pre-identity legacy missions), preserving the literal-slug behaviour.

    Subsumption note (T013): the retired body derived ``meta.mid8`` first, then
    ``resolve_mid8(slug, mission_id)`` under a ``len >= 8`` guard, returning
    ``""`` otherwise — exactly the first two tiers of ``resolve_declared_mid8``.

    WP01 reroute note: ``_resolve_mission_slug`` now routes through
    ``resolve_handle_to_read_path`` (which runs the same cascade internally), so
    this helper is no longer on that call path. It is retained as a directly
    tested primitive (``test_mid8_direct_routing.py``,
    ``test_read_path_resolver_validation.py``); collapsing it is a separate tidy.
    """
    from specify_cli.coordination.surface_resolver import resolve_declared_mid8
    from specify_cli.mission_metadata import load_meta
    from specify_cli.missions._read_path_resolver import (
        primary_feature_dir_for_mission,
    )

    # FR-006: canonical reader contract (a) — None on a missing file, ValueError on
    # malformed; the ``except ValueError`` below reproduces the historical
    # malformed→"" degrade. Defaults are stated explicitly to document the chosen arm.
    try:
        meta = load_meta(
            primary_feature_dir_for_mission(repo_root, mission_slug),
            allow_missing=True,
            on_malformed="raise",
        )
    except ValueError:
        return ""
    if not meta:
        return ""
    # ``follow_imports=skip`` on ``specify_cli.*`` erases the str return across
    # the package boundary, so bind explicitly.
    resolved: str = resolve_declared_mid8(meta, mission_slug)
    return resolved


def _tasks_commands(mission_slug: str) -> dict[str, str]:
    return {
        "check_prerequisites": (f"spec-kitty agent mission check-prerequisites --json --paths-only --include-tasks --mission {mission_slug}"),
        "finalize_tasks": (f"spec-kitty agent mission finalize-tasks --mission {mission_slug} --json"),
    }


def _wp_workflow_commands(
    *,
    action: ActionName,
    wp_id: str,
    mission_slug: str,
    agent: str | None,
) -> dict[str, str]:
    """Compute the action-specific ``commands`` for a WP-bearing context.

    Built up-front (not patched onto a built context) so the single
    construction door (``build_execution_context``) is fed the complete
    ``commands`` mapping — the frozen composite forbids the historical
    ``context.commands["workflow"] = …`` post-build dict-write (T005).
    """
    verb = "implement" if action == "implement" else "review"
    workflow = f"spec-kitty agent action {verb} {wp_id}"
    if agent:
        workflow += f" --agent {agent}"
    commands = {"workflow": workflow}
    if action != "implement":
        commands["approve"] = (
            f"spec-kitty agent tasks move-task {wp_id} --to approved "
            f'--mission {mission_slug} --note "Review passed: <summary>"'
        )
        commands["reject"] = (
            f"spec-kitty agent tasks move-task {wp_id} --to planned "
            f"--review-feedback-file <feedback-file> --mission {mission_slug}"
        )
    return commands


def _resolve_wp_lane(
    feature_dir: Path,
    wp_id: str,
    *,
    resolve_lane_alias: Callable[[str], str],
    planned_lane: str,
) -> str:
    """Resolve a WP's lane from the canonical event log (FR-011).

    WPs without a canonical event yet (or with the ``uninitialized`` sentinel)
    are treated as ``planned`` so legacy missions that have not emitted events
    for every WP still resolve.
    """
    from specify_cli.status import CanonicalStatusNotFoundError
    from specify_cli.status import get_wp_lane as _ec_get_wp_lane

    try:
        raw_lane = str(_ec_get_wp_lane(feature_dir, wp_id))
    except CanonicalStatusNotFoundError:
        raw_lane = planned_lane
    except Exception as exc:
        raise ActionContextError("CANONICAL_STATUS_UNREADABLE", str(exc)) from exc
    if raw_lane == "uninitialized":
        raw_lane = planned_lane
    return resolve_lane_alias(raw_lane)


def _resolve_wp_bearing_fields(
    repo_root: Path,
    *,
    action: ActionName,
    mission_slug: str,
    feature_dir: Path,
    wp_id: str | None,
    agent: str | None,
    locate_work_package: Callable[..., Any],
    parse_wp_dependencies: Callable[[Path], list[str]],
    resolve_workspace_for_wp: Callable[..., Any],
    resolve_lane_alias: Callable[[str], str],
    planned_lane: str,
) -> dict[str, Any]:
    """Assemble the WP-bearing fields (incl. ``commands``) for one build call.

    Returns the field mapping the factory consumes; performs NO construction or
    post-build mutation (T005 — verification-by-deletion of the ``:800-808``
    mutator and the ``commands["workflow"] =`` dict-write).
    """
    normalized_wp_id = _resolve_wp_id(action, feature_dir, wp_id)
    if normalized_wp_id is None:
        raise ActionContextError(
            "WORK_PACKAGE_UNRESOLVED",
            f"No work package available for action '{action}' in feature {mission_slug}.",
        )

    try:
        wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
    except Exception as exc:
        raise ActionContextError("WORK_PACKAGE_UNRESOLVED", str(exc)) from exc

    dependencies = parse_wp_dependencies(wp.path)
    lane = _resolve_wp_lane(
        feature_dir,
        normalized_wp_id,
        resolve_lane_alias=resolve_lane_alias,
        planned_lane=planned_lane,
    )
    wp_workspace = resolve_workspace_for_wp(repo_root, mission_slug, normalized_wp_id)

    return {
        "wp_id": normalized_wp_id,
        "wp_file": str(wp.path),
        "lane": lane,
        "lane_id": wp_workspace.lane_id,
        "branch_name": wp_workspace.branch_name,
        "execution_mode": wp_workspace.execution_mode,
        "resolution_kind": wp_workspace.resolution_kind,
        "dependencies": dependencies,
        "workspace_path": str(wp_workspace.worktree_path),
        "commands": _wp_workflow_commands(
            action=action,
            wp_id=normalized_wp_id,
            mission_slug=mission_slug,
            agent=agent,
        ),
    }


def _find_first_wp(feature_dir: Path, lane: str) -> str | None:
    """Find the first WP with the given lane from the canonical event log."""
    import re as _re
    from specify_cli.status import CanonicalStatusNotFoundError
    from specify_cli.status import Lane
    from specify_cli.status import get_wp_lane
    from specify_cli.status import resolve_lane_alias

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        wp_match = _re.match(r"(WP\d+)", wp_file.stem)
        if wp_match is None:
            continue
        wp_id = wp_match.group(1)
        try:
            wp_lane_raw = str(get_wp_lane(feature_dir, wp_id))
        except CanonicalStatusNotFoundError:
            wp_lane_raw = Lane.PLANNED
        # WPs with no canonical event yet (or an "uninitialized" sentinel) are
        # treated as planned for the purposes of "find the first WP in this
        # lane". This matches the legacy ``event_log_lanes.get(wp_id, "planned")``
        # fallback that previous iterations used and keeps zero-migration
        # support (FR-019) intact for missions that have not emitted events for
        # every WP.
        if wp_lane_raw == "uninitialized":
            wp_lane_raw = Lane.PLANNED
        wp_lane = resolve_lane_alias(wp_lane_raw)
        if wp_lane == lane:
            return wp_id
    return None


def _resolve_review_wp_id(feature_dir: Path) -> str | None:
    """Find the WP to review: first ``for_review``, else a review-claimed WP."""
    from specify_cli.status import CanonicalStatusNotFoundError
    from specify_cli.status import Lane
    from specify_cli.status import get_wp_lane
    from specify_cli.status import read_events
    from specify_cli.task_utils import extract_scalar, split_frontmatter

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    try:
        events = read_events(feature_dir)

        candidate_wp_ids = _review_candidate_wp_ids(
            tasks_dir,
            extract_scalar=extract_scalar,
            split_frontmatter=split_frontmatter,
        )

        review_ready_wp_id = _first_wp_in_lane(
            feature_dir,
            candidate_wp_ids,
            target_lane=Lane.FOR_REVIEW,
            get_wp_lane=get_wp_lane,
        )
        if review_ready_wp_id is not None:
            return review_ready_wp_id

        for candidate_wp_id in candidate_wp_ids:
            candidate_lane = get_wp_lane(feature_dir, candidate_wp_id)
            if candidate_lane not in (Lane.IN_PROGRESS, Lane.IN_REVIEW):
                continue
            if _is_review_claimed(events, candidate_wp_id, Lane=Lane):
                return candidate_wp_id
    except CanonicalStatusNotFoundError as exc:
        raise ActionContextError("CANONICAL_STATUS_NOT_FOUND", str(exc)) from exc
    except ActionContextError:
        raise
    except Exception:
        return None
    return None


def _review_candidate_wp_ids(
    tasks_dir: Path,
    *,
    extract_scalar: Callable[[str, str], str | None],
    split_frontmatter: Callable[[str], tuple[str, str, str]],
) -> list[str]:
    candidate_wp_ids: list[str] = []
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        frontmatter = split_frontmatter(wp_file.read_text(encoding="utf-8-sig"))[0]
        candidate_wp_id = extract_scalar(frontmatter, "work_package_id")
        if candidate_wp_id:
            candidate_wp_ids.append(str(candidate_wp_id))
    return candidate_wp_ids


def _first_wp_in_lane(
    feature_dir: Path,
    candidate_wp_ids: list[str],
    *,
    target_lane: object,
    get_wp_lane: Callable[[Path, str], object],
) -> str | None:
    for candidate_wp_id in candidate_wp_ids:
        if get_wp_lane(feature_dir, candidate_wp_id) == target_lane:
            return candidate_wp_id
    return None


def _is_review_claimed(events: Sequence[Any], candidate_wp_id: str, *, Lane: Any) -> bool:
    latest_event = next(
        (
            event
            for event in reversed(events)
            if getattr(event, "wp_id", None) == candidate_wp_id
        ),
        None,
    )
    if latest_event is None:
        return False
    return bool(
        latest_event.to_lane == Lane.IN_REVIEW
        or (
            latest_event.to_lane == Lane.IN_PROGRESS
            and latest_event.review_ref == "action-review-claim"
        )
    )


def _resolve_wp_id(
    action: ActionName,
    feature_dir: Path,
    explicit_wp_id: str | None,
) -> str | None:
    from specify_cli.status import Lane

    if explicit_wp_id:
        return explicit_wp_id.upper().split("-", 1)[0]

    if action == "implement":
        for lane in (Lane.PLANNED, Lane.IN_PROGRESS):
            wp_id = _find_first_wp(feature_dir, lane)
            if wp_id:
                return wp_id
        return None

    if action == "review":
        return _resolve_review_wp_id(feature_dir)

    return None


def _resolve_coordination_branch(primary_root: Path, mission_slug: str) -> str | None:
    """Read the mission ``coordination_branch`` from meta (canonical anchor).

    Returns ``None`` under flattened topology (no separate coordination branch,
    C-001). Anchored on the canonical *primary* dir so the value is identical
    from any CWD (never trust a lane-supplied surface — WP02 carry-forward).

    FR-003 / C-GUARD-3a (coord-topology placement regression fix): ``meta.json``
    is written by ``mission create`` and only ever lives on the PRIMARY checkout.
    Reading it through the topology-aware ``candidate_feature_dir_for_mission``
    selected the coordination worktree once one was materialized — and that
    worktree's ``kitty-specs/<slug>/`` dir carries no ``meta.json`` — so the
    coordination branch read back as ``None`` and the placement *kind* flipped
    from COORDINATION to FLATTENED depending on whether a coord worktree existed.
    That made the single placement authority CWD/topology-DEPENDENT (e.g.
    ``setup-plan`` resolved COORDINATION and committed plan.md to the coord
    worktree, while ``finalize-tasks`` later resolved FLATTENED and committed to
    the target branch — a split-brain). The fix is to anchor the ``meta.json``
    read on the topology-BLIND primary constructor (the SAME anchoring
    ``finalize-tasks`` uses for its merge-target read), restoring a CWD-invariant
    placement with NO second destination authority.
    """
    from specify_cli.mission_metadata import load_meta
    from specify_cli.missions._read_path_resolver import (
        primary_feature_dir_for_mission,
    )

    primary_dir = primary_feature_dir_for_mission(primary_root, mission_slug)
    # FR-006: canonical reader contract (a) — None on missing, ValueError on
    # malformed (defaults stated explicitly to document the chosen arm).
    try:
        meta = load_meta(primary_dir, allow_missing=True, on_malformed="raise")
    except ValueError:
        # Malformed meta: treat coordination topology as undeclared. Downstream
        # surface resolution reports the same condition consistently.
        return None
    if not meta:
        return None
    raw = meta.get("coordination_branch")
    return str(raw) if raw else None


def _resolve_topology(primary_root: Path, mission_slug: str) -> MissionTopology:
    """Read the WP02 **stored** :class:`MissionTopology` from meta (PURE shell read).

    The imperative-shell topology read: anchored on the canonical PRIMARY dir
    (where ``meta.json`` lives, mirroring :func:`_resolve_coordination_branch`)
    and delegated to WP02's :func:`read_topology` — the **pure** stored-topology
    reader. It returns the stored value when present and derives the shape ONCE
    (via WP01's :func:`classify_topology`) for a pre-WP02 mission, **without ever
    writing** — so a READ path (``resolve_action_context`` for finalize
    ``--validate-only`` / accept-readiness / a transactional read) never mutates
    ``meta.json`` (the read-only contract, #1814). Persisting the back-fill is the
    job of the explicit ``ensure_topology`` mint / ``migrate backfill-topology``
    command, never an incidental read side effect. Falls back to the
    ``(coordination_branch, has_lanes=False)`` classification when ``meta.json`` is
    absent/malformed so bootstrap windows still resolve a stable shape.
    """
    from mission_runtime.context import classify_topology
    from specify_cli.migration.backfill_topology import read_topology
    from specify_cli.missions._read_path_resolver import (
        primary_feature_dir_for_mission,
    )

    primary_dir = primary_feature_dir_for_mission(primary_root, mission_slug)
    try:
        stored: MissionTopology = read_topology(primary_dir)
        return stored
    except (FileNotFoundError, ValueError):
        # No persisted meta yet (bootstrap window) or malformed: classify from the
        # coordination-branch value-read with no lanes signal. This is the same
        # degraded-but-stable shape the surface resolver reports for the window.
        coordination_branch = _resolve_coordination_branch(primary_root, mission_slug)
        return classify_topology(coordination_branch, has_lanes=False)


def resolve_topology(repo_root: Path, mission_handle: str) -> MissionTopology:
    """Public seam: read the WP02 **stored** :class:`MissionTopology` for a mission.

    The single public entry point a caller uses to obtain the stored topology so
    it can route through the ONE canonical :func:`routes_through_coordination`
    predicate (FR-005 / FR-001b) — replacing the retired per-ref ``.kind`` arm
    that once let the predicate take a ``CommitTarget``.

    The operator ``mission_handle`` is canonicalized FIRST (bare mid8 / numeric
    prefix → the full ``<slug>-<mid8>`` dir name), EXACTLY as
    :func:`resolve_placement_only` does, so a coord-topology mission addressed by a
    bare handle is NOT mis-classified as a coord-less primary surface (the #1784
    flip class). After canonicalization it delegates to the same pure
    :func:`_resolve_topology` shell read the full resolver uses, so the value is
    byte-identical to what ``resolve_placement_only`` / ``_assemble_core_fragments``
    derive for the same mission (no second derivation). A pure READ — it never
    writes ``meta.json`` (#1814). When the handle does not resolve, the raw handle
    passes through and the topology degrades exactly as the full resolver does.
    """
    from specify_cli.core.paths import get_main_repo_root
    from specify_cli.missions._read_path_resolver import (
        MissionSelectorAmbiguous,
        StatusReadPathNotFound,
        candidate_feature_dir_for_mission,
    )

    primary_root = get_main_repo_root(repo_root)
    mission_slug = mission_handle
    try:
        candidate_dir = candidate_feature_dir_for_mission(repo_root, mission_handle)
    except (StatusReadPathNotFound, MissionSelectorAmbiguous):
        # Unresolvable / ambiguous handle: pass the raw handle through so the
        # topology degrades exactly as the full resolver does for a missing mission
        # (the routing caller already tolerates a degraded shape).
        candidate_dir = None
    if candidate_dir is not None and candidate_dir.exists():
        mission_slug = candidate_dir.name
    return _resolve_topology(primary_root, mission_slug)


def _resolve_mission_id(primary_root: Path, mission_slug: str) -> str:
    """Resolve the canonical ``mission_id`` for the mission.

    Reads ``meta.json`` at the canonical primary dir. Falls back to a
    ``legacy-<slug>`` sentinel (mirroring ``status_transition`` identity
    resolution) so pre-identity missions still resolve a stable, CWD-invariant
    value — ``mid8`` is then derived once from that value (FR-012 / C-CTX-3).

    FR-003 / C-GUARD-3a: ``meta.json`` only ever lives on the PRIMARY checkout,
    so the read is anchored on the topology-blind primary constructor — the
    coord-aware resolver would return the (meta-less) coordination worktree once
    one exists and spuriously degrade to the ``legacy-`` sentinel (see
    :func:`_resolve_coordination_branch` for the full split-brain rationale).
    """
    from specify_cli.mission_metadata import load_meta
    from specify_cli.missions._read_path_resolver import (
        primary_feature_dir_for_mission,
    )

    primary_dir = primary_feature_dir_for_mission(primary_root, mission_slug)
    # FR-006: canonical reader contract (a) — None on missing, ValueError on
    # malformed; the malformed arm degrades to the ``legacy-`` sentinel below.
    try:
        meta = load_meta(primary_dir, allow_missing=True, on_malformed="raise")
    except ValueError:
        meta = None
    if meta:
        raw_mission_id = meta.get("mission_id")
        if raw_mission_id:
            return str(raw_mission_id)
    return f"legacy-{mission_slug}"


def _resolve_status_surface_dir(
    primary_root: Path, mission_slug: str, topology: MissionTopology
) -> Path:
    """Resolve the canonical status-surface DIRECTORY via WP02's resolver.

    Consumes :func:`resolve_status_surface` (IC-01) — the single status-surface
    authority — and returns the containing directory (the resolver yields the
    ``status.events.jsonl`` path). Never re-derives the surface (FR-003/#1737).
    Falls back to the canonical primary dir when meta is absent/malformed so
    bootstrap windows and ad-hoc fixtures keep resolving. The fail-closed
    surface refusal is NOT a fallback case: it translates to
    :class:`ActionContextError` (PR #1850 M6).

    The stored ``topology`` is threaded through to
    :func:`resolve_status_surface` so the PRIMARY-vs-coordination surface SHAPE is
    decided from the WP02 stored value (FR-004 / SC-001), not from a parallel
    ``coordination_branch is None`` re-inference inside the surface resolver.
    """
    from specify_cli.coordination.surface_resolver import resolve_status_surface
    from specify_cli.missions._read_path_resolver import (
        StatusReadPathNotFound,
        candidate_feature_dir_for_mission,
    )

    try:
        surface = resolve_status_surface(primary_root, mission_slug, topology)
    except StatusReadPathNotFound as exc:
        # Fail closed (FR-005 / #1589 / #1821): the coord worktree root is
        # materialized but its mission dir is absent. Degrading to the primary
        # dir here would hand back the stale split-brain surface the refusal
        # exists to kill — translate to the boundary's single error type
        # instead, preserving the refusal message (PR #1850 M6).
        raise ActionContextError(exc.error_code, str(exc)) from exc
    except (FileNotFoundError, ValueError):
        fallback_dir: Path = candidate_feature_dir_for_mission(primary_root, mission_slug)
        return fallback_dir
    surface_parent: Path = surface.parent
    return surface_parent


def _assemble_workspace_fragment(
    primary_root: Path,
    *,
    mission_slug: str,
    mid8: str,
    coordination_branch: str | None,
    cwd: Path | None,
) -> WorkspaceFragment:
    """Assemble the WP05-owned WorkspaceFragment (IC-04 / C-005).

    ``primary_root`` is the canonical main-checkout root produced by the
    **single** worktree-pointer parser
    (:func:`specify_cli.core.paths.resolve_canonical_root`, which
    :func:`get_main_repo_root` feeds — IC-04). It is never the lane-supplied
    root, so it is CWD-invariant (C-CTX-2 / WP02 carry-forward): the parity
    ratchet asserts that both the primary-CWD and lane-CWD arms resolve the
    same ``primary_root``.

    ``coord_worktree`` is the per-mission coordination worktree path when the
    mission declares a coordination branch, else ``None`` under flattened
    topology (C-001). It is derived from the canonical primary root, not the
    current CWD, so it too is CWD-invariant. ``current_cwd`` records where the
    command actually runs; ``allowed_command_cwd`` is the primary-resolving
    guard CWD for surfaces that must run git ops against the main checkout.
    ``execution_workspace`` (the lane worktree for implement/review) is attached
    later by the action-specific branch when a WP is resolved.
    """
    from specify_cli.coordination.workspace import CoordinationWorkspace

    current_cwd = (cwd or primary_root).resolve()
    coord_worktree: Path | None = None
    if coordination_branch is not None:
        coord_worktree = CoordinationWorkspace.worktree_path(
            primary_root, mission_slug, mid8
        )

    return WorkspaceFragment(
        primary_root=primary_root,
        current_cwd=current_cwd,
        coord_worktree=coord_worktree,
        execution_workspace=None,
        allowed_command_cwd=primary_root,
    )


def _assemble_core_fragments(
    repo_root: Path,
    *,
    mission_slug: str,
    target_branch: str,
    topology: MissionTopology,
    cwd: Path | None,
) -> tuple[IdentityFragment, BranchRefFragment, StatusSurfaceFragment, WorkspaceFragment]:
    """Assemble the WP02/WP03/WP05-owned fragments of the op-composite (IC-02).

    This is the single fragment-assembly path (C-CTX-1): the builder derives
    each fragment's domain values exactly once and never lets a call site
    recompute them.

    * ``IdentityFragment`` — ``mid8`` single-derived as ``mission_id[:8]``.
    * ``BranchRefFragment`` — ``target_branch`` carried (already resolved once by
      the caller, FR-012); ``coordination_branch`` from meta (the value-read,
      ``None`` when flattened, C-001); ``destination_ref`` a ref-only
      :class:`CommitTarget` (C-007) whose ref is the coord branch when the
      **stored** ``topology`` routes through coordination
      (:func:`routes_through_coordination`, WP03 / FR-004) — NOT inferred from
      ``coordination_branch is None``. The shape is READ, not guessed.
    * ``StatusSurfaceFragment`` — read/write dirs from WP02's
      :func:`resolve_status_surface` (IC-01), classified by the same stored
      ``topology``; collapse to one dir absent a coord worktree.
    * ``WorkspaceFragment`` — ``primary_root`` via the single worktree-pointer
      parser (WP05 / IC-04 / C-005); CWD-invariant by construction.

    The canonical *primary* root is resolved here (never the lane-supplied root)
    so every fragment value is CWD-invariant (C-CTX-2 / WP02 carry-forward).
    ArtifactPlacement / PromptSource fragments are intentionally NOT assembled
    here — they land in WP04/06/07 (C-004 strangler ordering).

    ``topology`` (WP02 stored field) is supplied by the caller — the shell reads
    it once from ``meta.json`` (via :func:`_resolve_topology`) alongside the
    existing ``target_branch`` read and threads it in. It is the SSOT for the
    placement/surface coord-routing classification.
    """
    from specify_cli.core.paths import get_main_repo_root

    primary_root = get_main_repo_root(repo_root)

    mission_id = _resolve_mission_id(primary_root, mission_slug)
    identity = IdentityFragment.derive(
        mission_id=mission_id, mission_slug=mission_slug
    )

    # ``_resolve_coordination_branch`` stays as the VALUE reader for the ref
    # string the BranchRefFragment carries (the shell still needs the ref). The
    # retired ``is None ⇒ FLATTENED`` *decision* is replaced by reading the stored
    # topology: the placement ``kind`` is now classified from ``topology`` (FR-004
    # / SC-001), never inferred from the branch value's presence.
    coordination_branch = _resolve_coordination_branch(primary_root, mission_slug)
    # The coord-routing DECISION reads the STORED topology via the SINGLE predicate
    # (FR-005 / WP04 drain) — never a re-derived per-ref enum. ``CommitTarget`` is a
    # ref-only carrier (C-007 / FR-001b): the destination ref is the coord branch
    # when the stored topology routes through coordination, else the target branch.
    coord_ref = (
        coordination_branch
        if routes_through_coordination(topology)
        and coordination_branch is not None
        else target_branch
    )
    destination_ref = CommitTarget(ref=coord_ref)
    branch_ref = BranchRefFragment(
        target_branch=target_branch,
        coordination_branch=coordination_branch,
        destination_ref=destination_ref,
    )

    surface_dir = _resolve_status_surface_dir(primary_root, mission_slug, topology)
    status_surface = StatusSurfaceFragment(
        status_read_dir=surface_dir,
        status_write_dir=surface_dir,
    )

    workspace = _assemble_workspace_fragment(
        primary_root,
        mission_slug=mission_slug,
        mid8=identity.mid8,
        coordination_branch=coordination_branch,
        cwd=cwd,
    )

    return identity, branch_ref, status_surface, workspace


def _assemble_artifact_placement_fragment(
    branch_ref: BranchRefFragment,
) -> ArtifactPlacementFragment:
    """Assemble the WP06-owned ArtifactPlacementFragment (IC-05 / C-PLACE-1).

    The placement ref is the **same** :class:`CommitTarget` carried on
    :class:`BranchRefFragment.destination_ref` — it is not re-derived from
    meta.json or git here (C-005: no parallel placement logic). This makes the
    FR-004 invariant a *structural* identity: planning artifacts
    (spec/plan/tasks/analysis-report) and status events resolve to literally the
    same value object, so implement-claim (#1816) and record-analysis (#1814)
    can never reconcile a primary↔coord split — under flattened topology the
    shared ``destination_ref`` already collapses (``kind == FLATTENED``, WP08).

    The fragment is CWD-invariant by construction because ``destination_ref`` is
    assembled from the canonical primary root (C-CTX-2 / WP02 carry-forward).
    """
    return ArtifactPlacementFragment(placement_ref=branch_ref.destination_ref)


def resolve_placement_only(
    repo_root: Path,
    mission_slug: str,
    *,
    kind: MissionArtifactKind,
) -> CommitTarget:
    """Resolve the placement :class:`CommitTarget` for a mission artifact ``kind``.

    The **WP-less placement projection** (IC-04 / C-GUARD-3a): the planning
    phase (specify / plan / tasks / finalize-tasks) has no ``wp_id`` — no work
    packages exist yet — so the full :func:`resolve_action_context` cannot be
    driven to obtain an :class:`ArtifactPlacementFragment`. This function is a
    narrower entry point over the **same** resolution authority, NOT a parallel
    resolver (C-CTX-1): it resolves ``target_branch`` once via
    :func:`get_feature_target_branch` and runs the single
    :func:`_assemble_core_fragments` builder, then projects out the one
    ``destination_ref`` :class:`CommitTarget` that builder already computes. The
    topology classification (primary / coordination / flattened) is therefore
    BYTE-IDENTICAL to what the full resolver assembles for the same mission —
    there is no second derivation from ``meta.json`` or git on the planning
    commit path (the #1784 catch-22 root: ``_resolve_planning_branch`` reading
    one authority while the placement fragment reads another).

    This is the literal #1784 fix: on a protected-target repo ``mission create``
    materializes a coordination branch, so the resolved placement is the
    NON-protected coordination ref — a ``GuardCapability.STANDARD`` commit lands
    there cleanly, with no "switch to the lane branch before lanes exist"
    refusal-to-nowhere.

    The projection is now kind-aware (write-surface-coherence WP01, FR-002 /
    FR-004): the READ side (:func:`artifact_home_for`) has routed by kind since
    #2090; this WRITE-side projection now agrees. A ``_PRIMARY_ARTIFACT_KINDS``
    member (spec / data-model / research / checklist / finalized plan /
    tasks-index / WP task / lanes / metadata) resolves to the primary
    ``target_branch`` for EVERY topology shape; every other kind keeps the
    topology-routed ``destination_ref`` (the coordination branch under
    coordination topology, else the target branch). ``kind`` is a REQUIRED
    keyword (DECISION 1): there is no default, so an un-threaded call site fails
    at the type/import level rather than silently flipping coord→primary.

    Args:
        repo_root: Repository root (resolved to the canonical primary root by
            the shared builder, so the result is CWD-invariant).
        mission_slug: The mission directory name / slug.
        kind: The mission artifact kind being placed. REQUIRED — no default;
            its partition membership selects the primary vs topology-routed ref.

    Returns:
        The single :class:`CommitTarget` the artifact commits to — the primary
        ``target_branch`` ref for a primary kind, else the topology-routed
        ``destination_ref`` (the value object status events resolve to).

    Raises:
        ActionContextError: when the mission slug cannot be resolved (no silent
            fallback — mirrors :func:`resolve_action_context`).
    """
    from specify_cli.core.paths import get_feature_target_branch
    from specify_cli.missions._read_path_resolver import (
        MissionSelectorAmbiguous,
        StatusReadPathNotFound,
        candidate_feature_dir_for_mission,
    )

    if not mission_slug or not mission_slug.strip():
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED",
            "resolve_placement_only requires an explicit mission_slug.",
        )

    # F-001: canonicalize the operator handle at entry. A bare mid8 / numeric
    # prefix must compose the SAME placement (ref AND kind) as the full slug —
    # composing from the raw handle reads no meta.json, flips a coord-topology
    # mission to FLATTENED, and targets the (possibly protected) target branch
    # (the #1784 class). When nothing resolves, the raw slug passes through and
    # the builder degrades exactly as before (no behaviour change for missing
    # missions).
    try:
        candidate_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
    except StatusReadPathNotFound as exc:
        # Fail-closed surface refusal at entry canonicalization: translate to
        # the boundary's single error type, preserving the refusal message
        # (PR #1850 M6) — mirrors :func:`_resolve_mission_slug`.
        raise ActionContextError(exc.error_code, str(exc)) from exc
    except MissionSelectorAmbiguous as exc:
        # Boundary translation (WP05 / FR-005 / #2010 bug #15): mirrors the
        # _resolve_mission_slug arm — the ambiguous handle must not escape as a
        # raw specify_cli exception from this entry point either.
        raise ActionContextError(exc.error_code, str(exc)) from exc
    if candidate_dir.exists():
        mission_slug = candidate_dir.name

    # FR-012 / C-CTX-3: ``target_branch`` is resolved exactly once here, exactly
    # as ``resolve_action_context`` does, and threaded into the shared builder.
    # The WP02 stored ``topology`` is read once alongside it (the shell read) and
    # threaded in so the placement ``kind`` is classified from the stored shape,
    # never re-inferred from ``coordination_branch`` (FR-004).
    from specify_cli.core.paths import get_main_repo_root

    target_branch = get_feature_target_branch(repo_root, mission_slug)
    topology = _resolve_topology(get_main_repo_root(repo_root), mission_slug)
    _identity, branch_ref, _status_surface, _workspace = _assemble_core_fragments(
        repo_root,
        mission_slug=mission_slug,
        target_branch=target_branch,
        topology=topology,
        cwd=None,
    )
    # FR-002 / FR-004 (write-surface-coherence WP01): the projection is
    # kind-aware. A ``_PRIMARY_ARTIFACT_KINDS`` member routes to the primary
    # ``target_branch`` already resolved above (via ``get_feature_target_branch``)
    # for EVERY topology shape, so planning + identity artifacts live with their
    # mission on the primary surface. Every other kind keeps the topology-routed
    # ``destination_ref`` — the SAME CommitTarget the full resolver projects via
    # ``_assemble_artifact_placement_fragment`` (C-PLACE-1): one authority, two
    # projections. We return a bare CommitTarget rather than an
    # ArtifactPlacementFragment because planning callers hand it straight to
    # ``safe_commit(target=...)``.
    if kind in _PRIMARY_ARTIFACT_KINDS:
        return CommitTarget(ref=target_branch)
    return branch_ref.destination_ref


def resolve_action_context(
    repo_root: Path,
    *,
    action: ActionName,
    feature: str | None = None,
    wp_id: str | None = None,
    agent: str | None = None,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ExecutionContext:
    """Resolve canonical mission/work-package context for an agent action.

    CWD-invariant, topology-aware, mode-correct. Raises
    :class:`ActionContextError` on unresolvable context (no silent fallback).
    """
    if action not in ACTION_NAMES:
        raise ActionContextError(
            "INVALID_ACTION",
            f"Invalid action '{action}'. Expected one of: {', '.join(ACTION_NAMES)}.",
        )

    from specify_cli.core.dependency_graph import parse_wp_dependencies
    from specify_cli.core.paths import get_feature_target_branch
    from specify_cli.status import Lane
    from specify_cli.status import resolve_lane_alias
    from specify_cli.task_utils import locate_work_package
    from specify_cli.workspace.context import resolve_workspace_for_wp

    from specify_cli.core.paths import get_main_repo_root

    mission_slug, feature_dir = _resolve_mission_slug(repo_root, feature=feature, cwd=cwd, env=env)
    # FR-012 / C-CTX-3: ``target_branch`` is resolved exactly once here and
    # threaded onto both the flat substrate field and the BranchRefFragment; no
    # downstream surface re-derives it. The WP02 stored ``topology`` is read once
    # alongside it (shell read) and threaded in so the placement/surface ``kind``
    # is classified from the stored shape, never re-inferred (FR-004 / SC-001).
    target_branch = get_feature_target_branch(repo_root, mission_slug)
    topology = _resolve_topology(get_main_repo_root(repo_root), mission_slug)

    identity, branch_ref, status_surface, workspace = _assemble_core_fragments(
        repo_root,
        mission_slug=mission_slug,
        target_branch=target_branch,
        topology=topology,
        cwd=cwd,
    )
    # IC-05 (WP06 / T019): the artifact-placement ref is the SAME CommitTarget
    # status events resolve to (C-PLACE-1) — assembled from ``branch_ref`` so no
    # surface re-derives a parallel primary/coord placement (C-005).
    artifact_placement = _assemble_artifact_placement_fragment(branch_ref)

    if action in _MISSION_LEVEL_ACTIONS:
        # Mission-level lifecycle actions (planning/analysis/status) resolve the
        # mission context without a work package — FR-011 full-lifecycle parity.
        #
        # FR-004 SSOT adoption (#2070): route the mission-level door through the
        # PURE :func:`resolve_context_for_mission` projection so the "single
        # planning-surface authority" is actually INVOKED, not dead-exported. It
        # carries ``branch_ref.destination_ref`` (a ref-only ``CommitTarget``, C-007)
        # + the artifact placement through unchanged — the SAME ref
        # ``_assemble_core_fragments`` already resolved for the same mission from the
        # stored ``topology``, so this is behaviour-preserving (NFR-003): the
        # destination ref value is byte-identical to the prior direct-factory build. The
        # WP-bearing path still composes its WP fields into the single factory door
        # below; wiring those 13 call sites through the projection is the remaining
        # #2070 increment (carved conservatively — they assemble WP-only fragments
        # the projection does not yet accept).
        return resolve_context_for_mission(
            identity.mission_id,
            topology,
            action=action,
            mission_slug=mission_slug,
            feature_dir=str(feature_dir),
            target_branch=target_branch,
            identity=identity,
            branch_ref=branch_ref,
            status_surface=status_surface,
            workspace=workspace,
            commands=_tasks_commands(mission_slug),
        )

    # The factory (``build_execution_context``) is the SOLE construction door for
    # ``ExecutionContext`` (D-6 / IC-01). The WP-bearing actions assemble their
    # fields BEFORE the single build call (no post-build mutation — the composite
    # is frozen).
    base_fields: dict[str, Any] = {
        "action": action,
        "mission_slug": mission_slug,
        "feature_dir": str(feature_dir),
        "target_branch": target_branch,
        "detection_method": "explicit",
        "identity": identity,
        "branch_ref": branch_ref,
        "status_surface": status_surface,
        "workspace": workspace,
        "artifact_placement": artifact_placement,
    }

    wp_fields = _resolve_wp_bearing_fields(
        repo_root,
        action=action,
        mission_slug=mission_slug,
        feature_dir=feature_dir,
        wp_id=wp_id,
        agent=agent,
        locate_work_package=locate_work_package,
        parse_wp_dependencies=parse_wp_dependencies,
        resolve_workspace_for_wp=resolve_workspace_for_wp,
        resolve_lane_alias=resolve_lane_alias,
        planned_lane=Lane.PLANNED,
    )
    return build_execution_context(**base_fields, **wp_fields)
