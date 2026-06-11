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

from mission_runtime.context import (
    ArtifactPlacementFragment,
    BranchRefFragment,
    CommitTarget,
    CommitTargetKind,
    ExecutionContext,
    IdentityFragment,
    PromptSourceFragment,
    StatusSurfaceFragment,
    WorkspaceFragment,
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


def _resolve_mission_slug(
    repo_root: Path,
    *,
    feature: str | None,
    cwd: Path | None,  # noqa: ARG001 -- kept for signature compatibility
    env: Mapping[str, str] | None,  # noqa: ARG001 -- kept for signature compatibility
) -> tuple[str, Path]:
    """Resolve mission slug and read-side directory.

    Mission directory resolution is CWD-independent and topology-aware
    (WP08 T037, FR-030): for missions on the coord-branch topology the
    returned ``feature_dir`` points into the coordination worktree;
    for legacy missions it points into the primary checkout.  The
    caller never has to guess which view the operator is sitting in.

    Raises ActionContextError if feature is not provided or the mission
    directory cannot be located in either view.
    """
    from specify_cli.core.paths import require_explicit_feature

    try:
        slug = require_explicit_feature(feature, command_hint="--mission <slug>")
    except ValueError as exc:
        raise ActionContextError("FEATURE_CONTEXT_UNRESOLVED", str(exc)) from exc

    # Derive mid8 from the post-WP03 ``<slug>-<mid8>`` shape when present.
    mid8 = _read_side_mid8_from_slug(slug)

    # Late import to avoid a hard module-load dependency for legacy
    # consumers of the resolver that pre-date its introduction.
    from specify_cli.missions._read_path_resolver import (
        resolve_mission_read_path,
    )

    feature_dir = resolve_mission_read_path(repo_root, slug, mid8)
    if not feature_dir.exists():
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED",
            f"Mission directory not found: {feature_dir}. Check that "
            f"'{slug}' is the correct mission slug.",
        )
    return slug, feature_dir


def _read_side_mid8_from_slug(slug: str) -> str:
    from specify_cli.lanes.branch_naming import mid8_from_slug

    parsed = mid8_from_slug(slug)
    if parsed:
        return str(parsed)
    tail = slug.rsplit("-", 1)[-1] if "-" in slug else ""
    if len(tail) == 8 and tail == tail.upper() and tail.isalnum():
        return tail
    return ""


def _tasks_commands(mission_slug: str) -> dict[str, str]:
    return {
        "check_prerequisites": (f"spec-kitty agent mission check-prerequisites --json --paths-only --include-tasks --mission {mission_slug}"),
        "finalize_tasks": (f"spec-kitty agent mission finalize-tasks --mission {mission_slug} --json"),
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
    """
    from specify_cli.mission_metadata import load_meta
    from specify_cli.missions.feature_dir_resolver import (
        candidate_feature_dir_for_mission,
    )

    primary_dir = candidate_feature_dir_for_mission(primary_root, mission_slug)
    try:
        meta = load_meta(primary_dir)
    except ValueError:
        # Malformed meta: treat coordination topology as undeclared. Downstream
        # surface resolution reports the same condition consistently.
        return None
    if not meta:
        return None
    raw = meta.get("coordination_branch")
    return str(raw) if raw else None


def _resolve_mission_id(primary_root: Path, mission_slug: str) -> str:
    """Resolve the canonical ``mission_id`` for the mission.

    Reads ``meta.json`` at the canonical primary dir. Falls back to a
    ``legacy-<slug>`` sentinel (mirroring ``status_transition`` identity
    resolution) so pre-identity missions still resolve a stable, CWD-invariant
    value — ``mid8`` is then derived once from that value (FR-012 / C-CTX-3).
    """
    from specify_cli.mission_metadata import load_meta
    from specify_cli.missions.feature_dir_resolver import (
        candidate_feature_dir_for_mission,
    )

    primary_dir = candidate_feature_dir_for_mission(primary_root, mission_slug)
    try:
        meta = load_meta(primary_dir)
    except ValueError:
        meta = None
    if meta:
        raw_mission_id = meta.get("mission_id")
        if raw_mission_id:
            return str(raw_mission_id)
    return f"legacy-{mission_slug}"


def _resolve_status_surface_dir(primary_root: Path, mission_slug: str) -> Path:
    """Resolve the canonical status-surface DIRECTORY via WP02's resolver.

    Consumes :func:`resolve_status_surface` (IC-01) — the single status-surface
    authority — and returns the containing directory (the resolver yields the
    ``status.events.jsonl`` path). Never re-derives the surface (FR-003/#1737).
    Falls back to the canonical primary dir when meta is absent/malformed so
    bootstrap windows and ad-hoc fixtures keep resolving.
    """
    from specify_cli.coordination.surface_resolver import resolve_status_surface
    from specify_cli.missions.feature_dir_resolver import (
        candidate_feature_dir_for_mission,
    )

    try:
        surface = resolve_status_surface(primary_root, mission_slug)
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
    cwd: Path | None,
) -> tuple[IdentityFragment, BranchRefFragment, StatusSurfaceFragment, WorkspaceFragment]:
    """Assemble the WP02/WP03/WP05-owned fragments of the op-composite (IC-02).

    This is the single fragment-assembly path (C-CTX-1): the builder derives
    each fragment's domain values exactly once and never lets a call site
    recompute them.

    * ``IdentityFragment`` — ``mid8`` single-derived as ``mission_id[:8]``.
    * ``BranchRefFragment`` — ``target_branch`` carried (already resolved once by
      the caller, FR-012); ``coordination_branch`` from meta (``None`` when
      flattened, C-001); ``destination_ref`` a :class:`CommitTarget` whose
      ``kind`` reflects coord-branch presence. The flattened-topology *kind*
      collapse (``kind == FLATTENED``) is WP08's resolution (IC-12); WP03 only
      stands up the CommitTarget value object with a coordination-vs-primary
      kind.
    * ``StatusSurfaceFragment`` — read/write dirs from WP02's
      :func:`resolve_status_surface` (IC-01); collapse to one dir absent a coord
      worktree.
    * ``WorkspaceFragment`` — ``primary_root`` via the single worktree-pointer
      parser (WP05 / IC-04 / C-005); CWD-invariant by construction.

    The canonical *primary* root is resolved here (never the lane-supplied root)
    so every fragment value is CWD-invariant (C-CTX-2 / WP02 carry-forward).
    ArtifactPlacement / PromptSource fragments are intentionally NOT assembled
    here — they land in WP04/06/07 (C-004 strangler ordering).
    """
    from specify_cli.core.paths import get_main_repo_root

    primary_root = get_main_repo_root(repo_root)

    mission_id = _resolve_mission_id(primary_root, mission_slug)
    identity = IdentityFragment.derive(
        mission_id=mission_id, mission_slug=mission_slug
    )

    coordination_branch = _resolve_coordination_branch(primary_root, mission_slug)
    if coordination_branch is not None:
        destination_ref = CommitTarget(
            ref=coordination_branch, kind=CommitTargetKind.COORDINATION
        )
    else:
        # WP08 / IC-12 directed out-of-map edit: no coordination branch ⇒ flattened
        # topology (landing == coordination == target on the single branch, C-001 /
        # C-PLACE-1). WP03 left this kind as PRIMARY pending the WP08 collapse; here
        # we classify it FLATTENED so there is no primary↔coord split to reconcile.
        destination_ref = CommitTarget(
            ref=target_branch, kind=CommitTargetKind.FLATTENED
        )
    branch_ref = BranchRefFragment(
        target_branch=target_branch,
        coordination_branch=coordination_branch,
        destination_ref=destination_ref,
    )

    surface_dir = _resolve_status_surface_dir(primary_root, mission_slug)
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


def _assemble_prompt_source_fragment(feature_dir: Path) -> PromptSourceFragment:
    """Assemble the WP04-owned PromptSourceFragment (IC-03 / T014, FR-012).

    ``prompt_source_dir`` is routed through the resolved read path
    (``<feature_dir>/tasks``, where the per-WP prompt files live), so
    implement/review prompt files are located via the context rather than an
    independent derivation. ``feature_dir`` is the output of the single read
    primitive (``_read_path_resolver.resolve_mission_read_path``), so the
    prompt-source dir is CWD-invariant by construction (C-CTX-2).

    The read-path *directory* itself is carried on
    :class:`StatusSurfaceFragment.status_read_dir` (attached by the core
    assembler): IC-03 folds the duplicate read-path resolver into the one read
    surface, and that surface is the status read dir. WP04 does not attach a
    :class:`WorkspaceFragment` — ``primary_root`` and the single worktree-pointer
    parser land in WP05 (IC-04, C-004 strangler ordering).
    """
    return PromptSourceFragment(prompt_source_dir=feature_dir / "tasks")


def resolve_placement_only(repo_root: Path, mission_slug: str) -> CommitTarget:
    """Resolve the planning-phase :class:`CommitTarget` for a mission (FR-003).

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

    Args:
        repo_root: Repository root (resolved to the canonical primary root by
            the shared builder, so the result is CWD-invariant).
        mission_slug: The mission directory name / slug.

    Returns:
        The single :class:`CommitTarget` (``ref`` + topology ``kind``) planning
        artifacts commit to — the same value object status events resolve to.

    Raises:
        ActionContextError: when the mission slug cannot be resolved (no silent
            fallback — mirrors :func:`resolve_action_context`).
    """
    from specify_cli.core.paths import get_feature_target_branch

    if not mission_slug or not mission_slug.strip():
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED",
            "resolve_placement_only requires an explicit mission_slug.",
        )

    # FR-012 / C-CTX-3: ``target_branch`` is resolved exactly once here, exactly
    # as ``resolve_action_context`` does, and threaded into the shared builder.
    target_branch = get_feature_target_branch(repo_root, mission_slug)
    _identity, branch_ref, _status_surface, _workspace = _assemble_core_fragments(
        repo_root,
        mission_slug=mission_slug,
        target_branch=target_branch,
        cwd=None,
    )
    # The placement ref is the SAME CommitTarget the full resolver projects via
    # ``_assemble_artifact_placement_fragment`` (C-PLACE-1): one authority, two
    # projections. We return the ``destination_ref`` directly rather than wrap it
    # in an ArtifactPlacementFragment because planning callers want the bare
    # CommitTarget to hand to ``safe_commit(target=...)``.
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

    mission_slug, feature_dir = _resolve_mission_slug(repo_root, feature=feature, cwd=cwd, env=env)
    # FR-012 / C-CTX-3: ``target_branch`` is resolved exactly once here and
    # threaded onto both the flat substrate field and the BranchRefFragment; no
    # downstream surface re-derives it.
    target_branch = get_feature_target_branch(repo_root, mission_slug)

    identity, branch_ref, status_surface, workspace = _assemble_core_fragments(
        repo_root,
        mission_slug=mission_slug,
        target_branch=target_branch,
        cwd=cwd,
    )
    # IC-03 (WP04 / T014): route the prompt-source dir through the single read
    # primitive's resolved ``feature_dir`` so consumers never re-derive it
    # (FR-012). The read-path *directory* is carried on
    # ``status_surface.status_read_dir`` (the one read surface, C-005).
    prompt_source = _assemble_prompt_source_fragment(feature_dir)
    # IC-05 (WP06 / T019): the artifact-placement ref is the SAME CommitTarget
    # status events resolve to (C-PLACE-1) — assembled from ``branch_ref`` so no
    # surface re-derives a parallel primary/coord placement (C-005).
    artifact_placement = _assemble_artifact_placement_fragment(branch_ref)

    context = ExecutionContext(
        action=action,
        mission_slug=mission_slug,
        feature_dir=str(feature_dir),
        target_branch=target_branch,
        detection_method="explicit",
        commands=_tasks_commands(mission_slug),
        identity=identity,
        branch_ref=branch_ref,
        status_surface=status_surface,
        workspace=workspace,
        artifact_placement=artifact_placement,
        prompt_source=prompt_source,
    )

    if action in {
        "specify",
        "plan",
        "analyze",
        "tasks",
        "tasks_outline",
        "tasks_packages",
        "tasks_finalize",
        "accept",
        "status",
    }:
        # Mission-level lifecycle actions (planning/analysis/status) resolve the
        # mission context without a work package — FR-011 full-lifecycle parity.
        return context

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
    # Lane is event-log-only; read from canonical event log not frontmatter.
    # WPs without a canonical event yet (or with the "uninitialized" sentinel)
    # are treated as ``planned`` so legacy missions that have not emitted events
    # for every WP still resolve.
    try:
        from specify_cli.status import CanonicalStatusNotFoundError
        from specify_cli.status import get_wp_lane as _ec_get_wp_lane

        _ec_raw_lane = str(_ec_get_wp_lane(feature_dir, normalized_wp_id))
    except CanonicalStatusNotFoundError:
        _ec_raw_lane = Lane.PLANNED
    except Exception as exc:
        raise ActionContextError("CANONICAL_STATUS_UNREADABLE", str(exc)) from exc
    if _ec_raw_lane == "uninitialized":
        _ec_raw_lane = Lane.PLANNED
    lane = resolve_lane_alias(_ec_raw_lane)
    workspace = resolve_workspace_for_wp(repo_root, mission_slug, normalized_wp_id)

    context.wp_id = normalized_wp_id
    context.wp_file = str(wp.path)
    context.lane = lane
    context.lane_id = workspace.lane_id
    context.branch_name = workspace.branch_name
    context.execution_mode = workspace.execution_mode
    context.resolution_kind = workspace.resolution_kind
    context.dependencies = dependencies
    context.workspace_path = str(workspace.worktree_path)

    if action == "implement":
        command = f"spec-kitty agent action implement {normalized_wp_id}"
        if agent:
            command += f" --agent {agent}"
        context.commands["workflow"] = command
        return context

    command = f"spec-kitty agent action review {normalized_wp_id}"
    if agent:
        command += f" --agent {agent}"
    context.commands["workflow"] = command
    context.commands["approve"] = f'spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed: <summary>"'
    context.commands["reject"] = f"spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file <feedback-file> --mission {mission_slug}"
    return context
