"""Shared, topology-aware ``for_review`` commit gate (FR-011, contract C-7).

The ONE ``in_progress -> for_review`` commit gate, hoisted here as a ``lanes``-side
leaf so every surface -- ``orchestrator-api transition`` and (WP09)
``agent status emit`` -- enforces identical semantics: a lane WP cannot reach
``for_review`` with no implementation commit on its lane branch beyond the base.

**Surface-neutral error contract.** :func:`evaluate_for_review_gate` *returns* a
:class:`GateDecision`; it NEVER raises the orchestrator envelope (``_fail`` /
``NoReturn``). Each caller renders its own failure (envelope JSON on the
orchestrator, a CLI error on ``agent status emit``) from the decision fields.

**Why ``lanes`` and not ``status``.** ``status`` already carries a bidirectional
deferred-import cycle with ``lanes``; this gate needs ``lanes._git`` and
``lanes.worktree_allocator.predict_lane_worktree``, so a ``lanes``-side leaf keeps
it a leaf and avoids hardening that cycle. It imports only sibling ``lanes``
modules plus the lower ``mission_runtime`` / ``core`` layers -- never
``orchestrator_api`` or a ``status`` aggregate.

**Topology-aware, both directions.** The verdict is decided on *commit state*
(``git rev-list <base>..HEAD`` inside the lane worktree), not on a
clone-vs-primary topology guess: a checkout with satisfied commits PASSES and a
checkout with unsatisfied commits FAILS, identically on every surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ExecutionLane, LanesManifest

__all__ = ["GateDecision", "evaluate_for_review_gate", "resolve_lane_base_ref"]


@dataclass(frozen=True)
class GateDecision:
    """Surface-neutral verdict of the ``for_review`` commit gate.

    ``passed`` is the only field a caller must consult to allow/deny. On a
    failure (``passed is False``) ``reason`` carries surface-neutral guidance and
    ``lane_id`` / ``lane_branch`` / ``base_ref`` let the caller render a
    structured, machine-readable error without re-deriving the lane.
    """

    passed: bool
    reason: str = ""
    lane_id: str | None = None
    lane_branch: str | None = None
    base_ref: str | None = None


def resolve_lane_base_ref(main_repo_root: Path, mission_slug: str, manifest: object) -> str:
    """The ref the lane was parented on -- the base for the commit gate.

    Uses the canonical placement authority (``resolve_placement_only``) -- the
    same one the native review gate consults -- which resolves to the
    coordination branch under coord topology, so both gates agree on the base.
    Never returns an empty ref (an empty base degrades ``rev-list <base>..HEAD``
    to an unreliable ``HEAD..HEAD``): falls back to the manifest's
    ``mission_branch`` then the repo default branch.
    """
    from mission_runtime import (
        ActionContextError,
        MissionArtifactKind,
        resolve_placement_only,
    )

    try:
        # base-ref read under coord topology: STATUS_STATE keeps the coord ref;
        # a primary kind would read the primary ref and corrupt the gate's
        # `rev-list <base>..HEAD` ancestry check.
        return str(resolve_placement_only(main_repo_root, mission_slug, kind=MissionArtifactKind.STATUS_STATE).ref)
    except ActionContextError:
        from specify_cli.core.git_ops import resolve_primary_branch

        return str(getattr(manifest, "mission_branch", "") or resolve_primary_branch(main_repo_root))


def _resolve_lane(main_repo_root: Path, mission_slug: str, wp_id: str) -> tuple[LanesManifest, ExecutionLane] | None:
    """Resolve ``(manifest, lane)`` for ``wp_id``, or ``None`` when gate-exempt.

    ``None`` means the gate does not apply: no ``lanes.json`` (legacy / non-lane
    mission) or ``wp_id`` is not assigned to any lane (planning-artifact WP).

    ``lanes.json`` is a PRIMARY-partition artifact -- read from the primary
    surface via the canonical kind-aware placement seam (mirrors the
    orchestrator's ``_planning_read_dir``), so a coord-topology mission resolves
    the manifest off the primary rather than the coordination worktree.
    """
    from mission_runtime import MissionArtifactKind, placement_seam

    from .persistence import read_lanes_json

    planning_dir = placement_seam(main_repo_root, mission_slug).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)
    manifest = read_lanes_json(planning_dir)
    lane = manifest.lane_for_wp(wp_id) if manifest is not None else None
    if manifest is None or lane is None:
        return None
    return manifest, lane


def evaluate_for_review_gate(
    main_repo_root: Path,
    mission_slug: str,
    wp_id: str,
    *,
    force: bool = False,
) -> GateDecision:
    """Decide whether ``wp_id`` may move ``in_progress -> for_review``.

    Returns a passing :class:`GateDecision` when the transition is allowed and a
    failing one (with ``reason`` + lane identity) when the lane has no
    implementation commit beyond its base. No-ops (pass) when bypassed
    (``force``) or when the gate does not apply (no ``lanes.json``, or the WP is
    not in any lane). Never raises the orchestrator envelope.
    """
    if force:
        return GateDecision(passed=True)

    resolved = _resolve_lane(main_repo_root, mission_slug, wp_id)
    if resolved is None:
        # Legacy / non-lane arm => guard exempt: no lane branch to check commits on.
        return GateDecision(passed=True)
    manifest, lane = resolved

    from .worktree_allocator import predict_lane_worktree

    lane_id = lane.lane_id
    worktree, lane_branch = predict_lane_worktree(main_repo_root, mission_slug, lane_id)
    base_ref = resolve_lane_base_ref(main_repo_root, mission_slug, manifest)

    from ._git import lane_has_commit_beyond_base

    if worktree.exists() and lane_has_commit_beyond_base(worktree, base_ref):
        return GateDecision(
            passed=True,
            lane_id=lane_id,
            lane_branch=lane_branch,
            base_ref=base_ref,
        )
    return GateDecision(
        passed=False,
        reason=(
            f"{wp_id} cannot move to for_review: no implementation commit on lane "
            f"{lane_id} ({lane_branch}) beyond {base_ref}. Commit the work in the "
            "lane worktree first, or pass --force if there is genuinely nothing to "
            "commit."
        ),
        lane_id=lane_id,
        lane_branch=lane_branch,
        base_ref=base_ref,
    )
