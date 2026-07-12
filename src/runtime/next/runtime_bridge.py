"""Bridge between CLI ``decide_next()`` and the CLI-internal ``_internal_runtime`` engine.

The runtime is now internalized as part of mission
``shared-package-boundary-cutover-01KQ22DS``; production code no longer imports
the standalone ``spec-kitty-runtime`` PyPI package.

Maps the CLI's Decision dataclass to the runtime's NextDecision by:

1. Starting or loading a mission run (persisted under .kittify/runtime/)
2. Delegating step planning to the runtime DAG planner
3. Handling WP-level iteration within "implement" and "review" steps
4. Enforcing CLI-level guards (artifact checks, WP status)
5. Preserving the existing JSON output contract

Run state is stored locally under ``.kittify/runtime/runs/<run_id>/``.
A tracked-mission-to-run compatibility index currently lives at
``.kittify/runtime/feature-runs.json``.
"""

# ─────────────────────────────────────────────────────────────────────────────
# #2531 DECOMPOSITION IN PROGRESS (mission runtime-bridge-degod-01KX8M1C).
#
# This module is being progressively decomposed from a single ~3800-LOC /
# 62-symbol god module into cohesive, independently-tested seams under
# ``runtime/next/``. Extracted so far:
#
#   runtime_bridge_engine.py   sole home of ``_internal_runtime`` engine /
#                              planner private access (FR-013); also owns the
#                              ``advance_run_state_after_composition`` logic
#                              (former CC23 ``_advance_run_state_after_composition``
#                              body, reduced to <=15) — this module keeps only
#                              a thin residual compat delegate under the same
#                              name so its 8x-patch/9x-attr monkeypatch surface
#                              still intercepts (contracts/compat-surface.md).
#
#   runtime_bridge_retrospective.py   sole home of the self-contained
#                              Confirm.ask-gated retrospective / learning-
#                              capture cluster (FR-006). This module keeps a
#                              native thin compat delegate under each of the 9
#                              symbols the WP02 compat guard binds (see the
#                              seam module's docstring for why a plain
#                              re-export is insufficient here — the guard's
#                              identity check hardcodes the cross-module
#                              baseline).
#
#   runtime_bridge_io.py       sole home of the narrow I/O ports (IC-04):
#                              feature-runs.json index, template/pack
#                              discovery, run lifecycle, the OperationalContext
#                              builder, the FR-009 gather_artifact_presence
#                              fact-port, and the pure resolve_commit_target
#                              lifted out of _wrap_with_decision_git_log. Same
#                              native-thin-delegate rule as the retrospective
#                              seam applies to every compat-tracked symbol
#                              moved there.
#
#   runtime_bridge_cores.py    sole home of the pure, zero-dependency leaves
#                              (FR-009): the tasks.md parse family and the
#                              guard inversion (`evaluate_guards(snapshot)`
#                              folding `_check_cli_guards` /
#                              `_check_composed_action_guard` /
#                              `_check_requirement_mapping_ready`'s decision
#                              tail over the WP05 `ArtifactPresenceSnapshot`
#                              fact-port). Same native-thin-delegate rule for
#                              every compat-tracked symbol moved there; two
#                              symbols (`_parse_wp_sections_from_tasks_md` /
#                              `_parse_requirement_refs_from_tasks_md`) use a
#                              same-module live-lookup between their two
#                              residual delegates rather than forwarding to
#                              the cores-internal call, closing the
#                              intra-seam false-green trap for their mutual
#                              call (see their docstrings below).
#
#   runtime_bridge_cores.py    ALSO owns the Decision-builder (FR-011,
#                              WP07): ``DecisionEnvelope`` + ``step_or_
#                              blocked`` collapse the 29 open-coded
#                              ``Decision(...)`` constructions (+ the 4x
#                              ``_state_to_action -> _build_prompt_or_error
#                              -> step-or-blocked`` triad) that used to be
#                              scattered across this module's three public
#                              entries. This module keeps ``_materialize_
#                              decision`` (the thin residual wrapper
#                              supplying the production ``prompt_exists``
#                              port) plus ``_map_wp_step_decision`` /
#                              ``_map_non_wp_step_decision`` /
#                              ``_build_decision_required_prompt_file``, the
#                              extractions that keep ``_map_runtime_
#                              decision`` / ``query_current_state`` at or
#                              under the complexity ceiling.
#
#   runtime_bridge_composition.py   sole home of the composition-dispatch
#                              cluster (WP08): the dispatch entry
#                              (``_dispatch_via_composition``), the
#                              composed-action guard
#                              (``_check_composed_action_guard``), the
#                              composition-input resolution helpers, the
#                              research/documentation guard-fact readers, and
#                              — the FR-008 headline — the
#                              ``_should_dispatch_via_composition`` selection
#                              seam isolated as a clean, gates-#2535-free
#                              predicate for a future WP14 consumer to route
#                              through. Same native-thin-delegate rule for
#                              every compat-tracked symbol moved there.
#                              ``_advance_run_state_after_composition``
#                              (WP03) is unaffected — its logic already lives
#                              in the engine adapter and its thin residual
#                              delegate stays defined right here, unmoved.
#
#   runtime_bridge_identity.py   sole home of the hottest fracture line
#                              (WP10, LAST): coord-branch naming
#                              (``_resolve_coordination_branch``), mission-ULID
#                              resolution (``_resolve_mission_ulid``), and
#                              primary-feature-dir resolution
#                              (``_primary_runtime_feature_dir``) — the scars
#                              #2091/#1978/#1918/#1814/#2069 cluster. Same
#                              native-thin-delegate rule for every compat-
#                              tracked symbol moved there; both intra-seam
#                              callers of ``_primary_runtime_feature_dir``
#                              (patched 6x) route back through THIS module's
#                              own delegate via a live, deferred lookup rather
#                              than a bare intra-seam call (research.md
#                              §Compat's grounded false-green trap).
#                              ``_wrap_with_decision_git_log`` (the cluster's
#                              caller) and ``_mission_routes_through_
#                              coordination`` are KEEP-IN-PLACE here, unmoved.
#
# This is the FINAL extraction (WP10) — see
# ``kitty-specs/runtime-bridge-degod-01KX8M1C/``.
#
# RULES (do NOT regress):
#   * Never reach into ``_internal_runtime.engine`` / ``.planner`` directly
#     from this module — go through ``runtime_bridge_engine`` (arch-guarded,
#     see ``tests/runtime/test_bridge_engine.py``).
#   * ``__all__`` (below) covers the 8 public names only (governs
#     ``import *``); the ~50 private symbols tests patch stay preserved by the
#     explicit guarded compat re-export block, not by ``__all__`` (FR-012).
#
# De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2531
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import dataclasses
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from charter.invocation_context import OperationalContext as OperationalContextT

from runtime.next._internal_runtime import (
    DiscoveryContext,
    MissionRunRef,
    NextDecision,
    next_step as runtime_next_step,
    provide_decision_answer as runtime_provide_decision_answer,
)
from runtime.next._internal_runtime.schema import ActorIdentity, MissionRuntimeError, load_mission_template_file
from runtime.next import runtime_bridge_composition as _composition
from runtime.next import runtime_bridge_cores as _cores
from runtime.next import runtime_bridge_engine as _engine_adapter
from runtime.next import runtime_bridge_identity as _identity_seam
from runtime.next import runtime_bridge_io as _io_seam
from runtime.next import runtime_bridge_retrospective as _retrospective_seam

# _extract_wp_heading / _collect_requirement_refs_for_section /
# _iter_requirement_refs / _requirement_inline_refs_suffix /
# _is_requirement_heading are NOT in the WP02 compat guard's tracked symbol
# inventory (nothing patches them — grep-verified against
# test_bridge_compat_surface.py), so a plain re-export is safe here (unlike
# the two native thin delegates below for the two tracked parse-family
# symbols). The redundant "as X" self-alias is mypy's explicit-reexport
# idiom (see the analogous note on the decision.py import below).
from runtime.next.runtime_bridge_cores import (
    _collect_requirement_refs_for_section as _collect_requirement_refs_for_section,
    _extract_wp_heading as _extract_wp_heading,
    _is_requirement_heading as _is_requirement_heading,
    _iter_requirement_refs as _iter_requirement_refs,
    _requirement_inline_refs_suffix as _requirement_inline_refs_suffix,
)

# _retrospective_blocks_completion is NOT in the WP02 compat guard's tracked
# symbol inventory (nothing patches it — see test_bridge_engine.py's analogous
# note), so a plain re-export is safe here (unlike the 9 thin native delegates
# below). The redundant "as X" self-alias is mypy's explicit-reexport idiom —
# without it, strict mode's --no-implicit-reexport blocks attribute access
# from other checked modules (e.g. runtime_bridge_engine.py's _rb.<name> live
# lookup) even though the name is a genuine module-level import.
from runtime.next.runtime_bridge_retrospective import (
    _retrospective_blocks_completion as _retrospective_blocks_completion,
)

# _composition_dispatch_inputs / _has_generated_docs are NOT in the WP02
# compat guard's tracked symbol inventory (nothing patches them), so a plain
# re-export is safe here (unlike the native thin delegates below for the
# tracked composition symbols): ``decide_next_via_runtime`` still calls
# ``_composition_dispatch_inputs`` bare, and ``runtime_bridge_io.gather_
# artifact_presence`` still reaches ``_has_generated_docs`` via its own live
# ``_rb._has_generated_docs(...)`` lookup (#2531 WP08).
from runtime.next.runtime_bridge_composition import (
    _composition_dispatch_inputs as _composition_dispatch_inputs,
    _has_generated_docs as _has_generated_docs,
)

from specify_cli.mission import get_mission_type
from specify_cli.status import CanonicalStatusNotFoundError
from specify_cli.status import Lane
from specify_cli.status import wp_state_for
from runtime.next.decision import (
    Decision,
    DecisionKind,
    _build_prompt_or_error,
    _build_prompt_safe,
    _compute_wp_progress,
    _find_first_wp_by_lane,
    _state_to_action,
)
from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter
from mission_runtime import routes_through_coordination

logger = logging.getLogger(__name__)

KITTIFY_DIR = ".kittify"
# MISSION_RUNTIME_YAML / MISSION_YAML moved to runtime_bridge_io.py (T017 —
# their only residual users, the discovery cluster, moved with them).

class DecisionGitLogUnavailable(RuntimeError):
    """Decision audit logging cannot be made durable for a modern mission."""


def _primary_runtime_feature_dir(repo_root: Path, mission_slug: str) -> Path:
    """Thin compat delegate (native ``def``; FR-012 compat surface, #2531
    WP10) — forwards to :func:`runtime_bridge_identity._primary_runtime_feature_dir`.
    Patched 6x by ``tests/runtime/test_runtime_bridge_identity.py`` — kept as a
    native ``def`` (never a plain re-export) so this name's ``__module__``
    stays ``runtime_bridge``, and both intra-seam callers of the real
    implementation (:func:`runtime_bridge_identity._resolve_coordination_branch`
    / ``._resolve_mission_ulid``) route back through THIS delegate via a live,
    deferred lookup rather than a bare intra-seam call — see
    ``runtime_bridge_identity``'s module docstring for the false-green
    mechanism this closes."""
    return _identity_seam._primary_runtime_feature_dir(repo_root, mission_slug)


def _resolve_coordination_branch(mission_slug: str, repo_root: Path) -> str:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_identity._resolve_coordination_branch` (FR-012
    compat surface, #2531 WP10; see module-level comment above and
    ``runtime_bridge_identity``'s docstring)."""
    return _identity_seam._resolve_coordination_branch(mission_slug, repo_root)


def _resolve_mission_ulid(mission_slug: str, repo_root: Path) -> str | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_identity._resolve_mission_ulid` (FR-012 compat
    surface, #2531 WP10; see module-level comment above and
    ``runtime_bridge_identity``'s docstring)."""
    return _identity_seam._resolve_mission_ulid(mission_slug, repo_root)


def _mission_routes_through_coordination(mission_slug: str, repo_root: Path) -> bool:
    """Return True when the mission's STORED topology routes through coordination.

    Reads the WP02 stored :class:`MissionTopology` (FR-004) from ``meta.json`` via
    the **pure** :func:`read_topology` reader and disposes the coord-vs-flattened
    SHAPE from it — replacing the retired ``meta.coordination_branch is not None``
    derivation (the second #2069 inference, which keyed the decision on a value
    presence rather than the stored shape, SC-001). The read is PURE: an
    un-backfilled mission is classified once and NOT persisted, so this read path
    never writes ``meta.json`` (the read-only contract, #1814). The coord-routing
    membership is disposed by the ONE canonical predicate
    (:func:`routes_through_coordination`) over the ONE canonical set — no second
    ``{COORD, LANES_WITH_COORD}`` set is restated here (FR-005). A coord-routing
    topology (``COORD`` / ``LANES_WITH_COORD``) returns ``True``; the coord-less
    cells return ``False``. Missing/malformed meta degrades to non-coord (matching
    the historical "no declared coord topology" arm).
    """
    from specify_cli.migration.backfill_topology import read_topology
    from specify_cli.missions._read_path_resolver import (
        _canonicalize_primary_read_handle,
        primary_feature_dir_for_mission,
    )

    # Anchor the stored-topology read on the topology-BLIND primary dir (where
    # meta.json lives), mirroring ``resolution._resolve_coordination_branch`` — the
    # coord-aware resolver fail-closes for a materialized-but-empty coord worktree,
    # so it must not gate this read.
    # WP05/FR-005: route through _canonicalize_primary_read_handle.
    feature_dir = primary_feature_dir_for_mission(
        repo_root,
        _canonicalize_primary_read_handle(repo_root, mission_slug),
    )
    try:
        topology = read_topology(feature_dir)
    except (FileNotFoundError, ValueError, OSError):
        return False
    return routes_through_coordination(topology)


def _wrap_with_decision_git_log(
    emitter: SyncRuntimeEventEmitter,
    mission_slug: str,
    repo_root: Path,
) -> Any:
    """Wrap ``emitter`` with DecisionGitLog for durable decision recording.

    Returns the wrapped emitter.  If construction fails (e.g. import error),
    the original emitter is returned unchanged so mission execution is not
    blocked.
    """
    coord_routing_topology = _mission_routes_through_coordination(
        mission_slug, repo_root,
    )
    try:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.events.decision_log import DecisionGitLog

        coordination_branch = _resolve_coordination_branch(mission_slug, repo_root)
        mission_id = _resolve_mission_ulid(mission_slug, repo_root)  # str | None

        # T019 (#2531 WP05): mid8 derivation + the fail-closed mid8-required
        # validation + CommitTarget/worktree_root-candidate selection is the
        # ONE pure decision that used to live inline here — lifted into
        # runtime_bridge_io.resolve_commit_target (data-model.md §Ports). See
        # that function's docstring for why this call raises
        # DecisionGitLogUnavailable identically to the pre-extraction inline
        # code (still caught by the except below) and why the .exists()-gated
        # branch remains here as the one genuinely I/O-bearing decision.
        _mid8, worktree_root_candidate, decision_target = _io_seam.resolve_commit_target(
            coord_routing_topology=coord_routing_topology,
            mission_slug=mission_slug,
            mission_id=mission_id,
            coordination_branch=coordination_branch,
            repo_root=repo_root,
        )

        # The decision-target topology SHAPE is READ from the WP02 stored topology
        # (FR-004 / SC-001) — never from ``_coord_path.exists()`` (the retired
        # disk-``stat`` ladder, C-004). The on-disk worktree-materialization check
        # (``_coord_path.exists()``) survives ONLY to choose the worktree_root for a
        # coord-routing mission (C-006 transient discrimination: materialized →
        # use it; not-yet-materialized → compose via ``CoordinationWorkspace.resolve``)
        # — it is NOT the topology classifier.
        if coord_routing_topology:
            # C-011 risk site: the worktree_root selection is preserved EXACTLY —
            # keyed off the stored-topology coord-routing decision and the C-006
            # transient on-disk materialization check, never ``.kind``.
            worktree_root = (
                worktree_root_candidate
                if worktree_root_candidate.exists()
                else CoordinationWorkspace.resolve(repo_root, mission_slug, _mid8)
            )
        else:
            # Coord-less topology: decisions land on the primary checkout's
            # current branch (a lane/mission branch); landing == coordination ==
            # target. worktree_root is the repo_root (preserved exactly).
            worktree_root = worktree_root_candidate

        return DecisionGitLog(
            repo_root=repo_root,
            worktree_root=worktree_root,
            destination_ref=coordination_branch,
            mission_slug=mission_slug,
            inner=emitter,
            mission_id=mission_id,
            target=decision_target,
        )
    except Exception as exc:
        if coord_routing_topology:
            raise DecisionGitLogUnavailable(
                "DecisionGitLog construction failed for declared coordination "
                f"topology mission {mission_slug!r}; refusing to continue "
                "without durable decision evidence."
            ) from exc
        logger.warning(
            "DecisionGitLog construction failed for mission %s; "
            "falling back to plain emitter.",
            mission_slug,
            exc_info=True,
        )
        return emitter


# FR-001 / C-IC02: the typed read-path codes whose fidelity MUST be preserved
# across the next-family catch-sites. These are *read-path topology* failures
# (the mission exists but its status read surface is broken / ambiguous), as
# opposed to a genuinely-missing mission (``FEATURE_CONTEXT_UNRESOLVED`` and the
# like), which legitimately stays ``MISSION_NOT_FOUND``. Collapsing a code in
# this set into ``MISSION_NOT_FOUND`` mis-routes the operator (the disease #15).
_READ_PATH_ERROR_CODES: frozenset[str] = frozenset(
    {
        "STATUS_READ_PATH_NOT_FOUND",
        "COORDINATION_BRANCH_DELETED",
        "MISSION_AMBIGUOUS_SELECTOR",
    }
)


def _is_read_path_error(exc: object) -> bool:
    """Return True when *exc* carries a typed read-path topology code (C-IC02)."""
    return getattr(exc, "code", None) in _READ_PATH_ERROR_CODES


class QueryModeValidationError(ValueError):
    """Raised when query mode cannot produce a truthful read-only preview."""


class MissionNotFoundError(Exception):
    """Raised when a mission handle cannot be resolved to an existing mission.

    Carries the attempted handle so callers can include it in structured
    error output (FR-004 / WP03 — fail-closed next query mode), plus an
    actionable ``next_step`` remediation so operators are told concretely how
    to recover (list available missions / verify the handle). The ``next_step``
    affordance restores the operator guidance the superseded
    ``QueryModeValidationError`` used to carry (#1911).
    """

    error_code: str = "MISSION_NOT_FOUND"

    def __init__(self, handle: str, next_step: str | None = None) -> None:
        self.handle = handle
        self.next_step = next_step or (
            "Run 'spec-kitty mission list' to see available missions, then "
            f"re-run with a valid handle (attempted: '{handle}')."
        )
        super().__init__(f"Mission not found: '{handle}'")


# ---------------------------------------------------------------------------
# Feature → Run index — bodies moved to runtime_bridge_io.py (T017); see
# ``_load_feature_runs`` below for the residual thin compat delegate.
#
# tasks.md parse family — bodies moved to runtime_bridge_cores.py (#2531
# WP06, T021; verbatim, zero-dependency pure leaf). ``TASKS_GLOB`` stays
# here (still used by ``_should_advance_wp_step`` / ``_check_requirement_
# mapping_ready``, neither of which moved).
# ---------------------------------------------------------------------------

TASKS_GLOB = "WP*.md"


def _parse_wp_sections_from_tasks_md(tasks_content: str) -> dict[str, str]:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_cores._parse_wp_sections_from_tasks_md`."""
    return _cores._parse_wp_sections_from_tasks_md(tasks_content)


def _parse_requirement_refs_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Thin compat delegate — parse requirement references per WP.

    Composed via THIS module's own :func:`_parse_wp_sections_from_tasks_md`
    delegate (bare call, resolved against ``runtime_bridge``'s own globals)
    rather than forwarding to :func:`runtime_bridge_cores._parse_requirement_
    refs_from_tasks_md` (whose internal call to the cores-local
    ``_parse_wp_sections_from_tasks_md`` would resolve against
    ``runtime_bridge_cores``'s globals instead). Both symbols are WP02
    compat-tracked and patched independently
    (``tests/runtime/test_bridge_compat_surface.py``'s ``REACH`` map); a
    blind forward here would make ``monkeypatch.setattr(runtime_bridge,
    "_parse_wp_sections_from_tasks_md", ...)`` a no-op false-green for any
    scenario that reaches it only through this function (the exact
    intra-seam-call trap research.md §Compat documents for
    ``_primary_runtime_feature_dir``)."""
    return {
        wp_id: _cores._collect_requirement_refs_for_section(section_content)
        for wp_id, section_content in _parse_wp_sections_from_tasks_md(tasks_content).items()
    }


class _BufferingRuntimeEmitter(_retrospective_seam._BufferingRuntimeEmitter):
    """Thin compat delegate (native ``class`` statement; FR-012 compat
    surface, #2531 WP04). Real implementation lives in
    :class:`runtime_bridge_retrospective._BufferingRuntimeEmitter` — inherited
    unchanged (no override). Kept as a native subclass definition (not a
    plain re-export alias) so ``_BufferingRuntimeEmitter.__module__`` stays
    ``runtime_bridge`` — the WP02 compat guard's identity/relocated-symbol
    check only tolerates the pre-existing ``runtime.next.decision``-origin
    cross-module symbols; see the module-level #2531 comment block above and
    ``runtime_bridge_retrospective``'s docstring."""


def _rich_hic_prompt() -> tuple[bool, str | None]:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._rich_hic_prompt` (FR-012 compat
    surface, #2531 WP04; see module-level comment above)."""
    return _retrospective_seam._rich_hic_prompt()


def _resolve_mission_id_for_terminus(feature_dir: Path) -> str:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._resolve_mission_id_for_terminus`."""
    return _retrospective_seam._resolve_mission_id_for_terminus(feature_dir)


def _build_retrospective_facilitator_callback(
    mission_slug: str,
    repo_root: Path,
    provenance_kind: str = "runtime_post_completion",
) -> Any:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._build_retrospective_facilitator_callback`."""
    return _retrospective_seam._build_retrospective_facilitator_callback(
        mission_slug, repo_root, provenance_kind
    )


def _resolve_retrospective_policy_for_runtime(
    repo_root: Path,
) -> tuple[Any, dict[str, str], Exception | None]:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._resolve_retrospective_policy_for_runtime`."""
    return _retrospective_seam._resolve_retrospective_policy_for_runtime(repo_root)


def _run_retrospective_learning_capture(
    *,
    mission_id: str,
    mission_slug: str,
    feature_dir: Path,
    repo_root: Path,
    block_on_failure: bool,
) -> None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._run_retrospective_learning_capture`."""
    _retrospective_seam._run_retrospective_learning_capture(
        mission_id=mission_id,
        mission_slug=mission_slug,
        feature_dir=feature_dir,
        repo_root=repo_root,
        block_on_failure=block_on_failure,
    )


def _classify_exc(exc: Exception) -> str:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._classify_exc`."""
    return _retrospective_seam._classify_exc(exc)


def _remediation_hint(exc: Exception, source_map: dict[str, str]) -> str | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._remediation_hint`."""
    return _retrospective_seam._remediation_hint(exc, source_map)


def _classify_and_emit_failure(
    *,
    mission_id: str,
    mission_slug: str,
    repo_root: Path,
    exc: Exception,
    source_map: dict[str, str],
    provenance_kind: str,
    emit_capture_failed: Any,
) -> None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_retrospective._classify_and_emit_failure`."""
    _retrospective_seam._classify_and_emit_failure(
        mission_id=mission_id,
        mission_slug=mission_slug,
        repo_root=repo_root,
        exc=exc,
        source_map=source_map,
        provenance_kind=provenance_kind,
        emit_capture_failed=emit_capture_failed,
    )


def _load_feature_runs(repo_root: Path) -> dict[str, _io_seam._FeatureRunEntry]:
    """Thin compat delegate — forwards to :func:`runtime_bridge_io.load_feature_runs`
    (via the repo_root -> path resolver :func:`runtime_bridge_io._feature_runs_path`)."""
    return _io_seam.load_feature_runs(_io_seam._feature_runs_path(repo_root))


def _mission_key_for_run_ref(run_ref: MissionRunRef, default: str) -> str:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._mission_key_for_run_ref`."""
    return _io_seam._mission_key_for_run_ref(run_ref, default)


def _build_run_ref(*, run_id: str, run_dir: str, mission_type: str) -> MissionRunRef:
    """Thin compat delegate — forwards to :func:`runtime_bridge_io._build_run_ref`."""
    return _io_seam._build_run_ref(run_id=run_id, run_dir=run_dir, mission_type=mission_type)


# ---------------------------------------------------------------------------
# WP iteration helpers
# ---------------------------------------------------------------------------

_WP_ITERATION_STEPS = frozenset({"implement", "review"})


def _is_wp_iteration_step(step_id: str) -> bool:
    """Check if a step is a WP-iteration step (implement, review)."""
    return step_id in _WP_ITERATION_STEPS


def _finalized_task_board_override_step(
    feature_dir: Path,
    progress: dict[str, int | float] | None,
    *,
    status_dir: Path | None = None,
) -> str | None:
    """Return the next step implied by finalized WP state, if available.

    This is intentionally narrow: it only overrides stale early runtime phases
    after a mission already has tasks.md, finalized WP files, and canonical WP
    lane state. It does not reorder non-finalized mission DAG execution.
    """
    if progress is None:
        return None
    total = int(progress.get("total_wps", 0) or 0)
    if total <= 0:
        return None
    if not (feature_dir / "tasks.md").is_file() or not (feature_dir / "tasks").is_dir():
        return None

    if _find_first_wp_by_lane(feature_dir, "planned", status_dir=status_dir) is not None:
        return "implement"
    if _find_first_wp_by_lane(feature_dir, "claimed", status_dir=status_dir) is not None:
        return "implement"
    if _find_first_wp_by_lane(feature_dir, "in_progress", status_dir=status_dir) is not None:
        return "implement"
    if _find_first_wp_by_lane(feature_dir, "for_review", status_dir=status_dir) is not None:
        return "review"
    if _find_first_wp_by_lane(feature_dir, "in_review", status_dir=status_dir) is not None:
        return "blocked:review_in_progress"

    done = int(progress.get("done_wps", 0) or 0)
    approved = int(progress.get("approved_wps", 0) or 0)
    if done == total:
        return "done"
    if approved + done == total:
        return "accept"
    return "blocked:no_actionable_wp"


def _should_advance_wp_step(step_id: str, feature_dir: Path) -> bool:
    """Check if all WPs are done for this phase, meaning we should advance.

    For implement: all WPs must be handed off or complete
    (for_review, approved, or done).
    For review: all WPs must be approved or done.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return True  # no WPs to iterate over

    wp_files = sorted(tasks_dir.glob(TASKS_GLOB))
    if not wp_files:
        return True

    # Get canonical lane state from event log (hard-fail if absent)
    import re as _re
    from specify_cli.status import get_wp_lane

    for wp_file in wp_files:
        wp_match = _re.match(r"(WP\d+)", wp_file.stem)
        wp_id = wp_match.group(1) if wp_match else wp_file.stem
        raw_lane = get_wp_lane(feature_dir, wp_id)
        try:
            state = wp_state_for(raw_lane)
        except ValueError:
            # Unknown lane (e.g. "uninitialized" before status bootstrap) — treat as
            # not-yet-handed-off, so this WP blocks advancement.
            return False
        if _wp_blocks_step(step_id, state):
            return False

    return True


def _wp_blocks_step(step_id: str, state: Any) -> bool:
    """Return whether a WP state blocks advancement for ``step_id``."""
    lane = state.lane
    if step_id == "implement":
        # Advance past implement only when the WP has been handed off
        # (for_review or approved) or completed (done/canceled).
        # is_run_affecting is True for all active lanes; we further restrict
        # to only allow advancement for the "handed off" active lanes.
        return (
            state.is_blocked
            or (state.is_run_affecting and lane not in (Lane.FOR_REVIEW, Lane.APPROVED))
        )
    if step_id == "review":
        return lane not in (Lane.DONE, Lane.APPROVED)
    return False


# ---------------------------------------------------------------------------
# Guard evaluation (CLI-level, not runtime-level)
# ---------------------------------------------------------------------------


SPEC_ARTIFACT = "spec.md"
TASKS_ARTIFACT = "tasks.md"
STATE_FILE = "state.json"


def _check_cli_guards(step_id: str, feature_dir: Path) -> list[str]:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_cores.evaluate_guards` over a
    :func:`runtime_bridge_io.gather_artifact_presence` snapshot (#2531 WP06,
    T022). ``wp_advance_ready`` is threaded through separately (not gathered
    by the snapshot) for ``implement``/``review`` so the pre-existing,
    unmoved :func:`_should_advance_wp_step` I/O read — and its own WP02
    compat reach — stay exactly where they were.

    Returns list of failure descriptions; empty list means all guards pass.
    """
    snapshot = _io_seam.gather_artifact_presence(
        feature_dir, mission_family="software-dev", step_id=step_id
    )
    if step_id in ("implement", "review"):
        snapshot = dataclasses.replace(
            snapshot, wp_advance_ready=_should_advance_wp_step(step_id, feature_dir)
        )
    return _cores.evaluate_guards(snapshot)


def _occurrence_gate_failures(feature_dir: Path) -> list[str]:
    """Bulk-edit occurrence-map gate errors (empty when not bulk_edit or map is valid).

    Reuses the existing ``ensure_occurrence_classification_ready`` enforcement
    (C-001: no new validation logic). Self-conditions on stored ``change_mode``
    (C-003), so it is safe to call unconditionally at the tasks_finalize
    boundary — non-bulk-edit missions and valid-admissible bulk-edit missions
    both return an empty list.
    """
    from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready

    return list(ensure_occurrence_classification_ready(feature_dir).errors)


def _check_requirement_mapping_ready(feature_dir: Path) -> list[str]:
    """Validate requirement coverage before issuing the finalize-tasks prompt.

    This intentionally mirrors ``agent mission finalize-tasks`` requirement
    source precedence: WP frontmatter is primary, and ``tasks.md`` is only a
    legacy fallback when no ``wps.yaml`` manifest is present.

    Gather-only shell (#2531 WP06, T023): reads spec.md/tasks.md/the WPs
    manifest and builds a :class:`runtime_bridge_cores.RequirementMappingFacts`
    bundle; the missing/unknown/unmapped decision itself (former CC~22 tail)
    now lives in the pure :func:`runtime_bridge_cores._evaluate_requirement_
    mapping` — the ``# noqa: C901`` this function used to carry is REMOVED,
    not relocated (FR-004/NFR-002).
    """
    spec_md = feature_dir / SPEC_ARTIFACT
    if not spec_md.exists():
        return []

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return []

    try:
        from specify_cli.core.wps_manifest import load_wps_manifest
        from specify_cli.requirement_mapping import (
            parse_requirement_ids_from_spec_md,
            read_all_wp_requirement_refs,
        )

        spec_ids = parse_requirement_ids_from_spec_md(spec_md.read_text(encoding="utf-8"))
        all_spec_requirement_ids = set(spec_ids["all"])
        functional_requirement_ids = set(spec_ids["functional"])

        wps_manifest = load_wps_manifest(feature_dir)
        wp_requirement_refs = read_all_wp_requirement_refs(tasks_dir)

        if wps_manifest is None:
            tasks_md = feature_dir / TASKS_ARTIFACT
            if tasks_md.exists():
                tasks_md_refs = _parse_requirement_refs_from_tasks_md(tasks_md.read_text(encoding="utf-8"))
                for wp_id, refs in tasks_md_refs.items():
                    if refs and not wp_requirement_refs.get(wp_id):
                        wp_requirement_refs[wp_id] = refs
    except Exception as exc:
        return [f"Requirement mapping preflight failed: {exc}"]

    wp_ids = tuple(sorted(wp_file.stem.split("-", 1)[0] for wp_file in tasks_dir.glob(TASKS_GLOB)))
    facts = _cores.RequirementMappingFacts(
        spec_requirement_ids=frozenset(all_spec_requirement_ids),
        functional_requirement_ids=frozenset(functional_requirement_ids),
        wp_ids=wp_ids,
        wp_requirement_refs={wp_id: tuple(refs) for wp_id, refs in wp_requirement_refs.items()},
        feature_dir_name=feature_dir.name,
    )
    return _cores._evaluate_requirement_mapping(facts)


def _has_raw_dependencies_field(wp_file: Path) -> bool:
    """Check if WP file has an explicit 'dependencies' field in raw frontmatter.

    Reads raw text to avoid auto-injection by read_frontmatter().
    """
    try:
        text = wp_file.read_text(encoding="utf-8")
    except OSError:
        return False
    if not text.startswith("---"):
        return False
    end = text.find("---", 3)
    if end == -1:
        return False
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies:"):
            return True
    return False


# ---------------------------------------------------------------------------
# Composition dispatch (WP02 / mission software-dev-composition-rewrite-01KQ26CY)
# ---------------------------------------------------------------------------
#
# The cluster itself now lives in ``runtime_bridge_composition.py`` (#2531
# WP08) — see that module's docstring for the constraints (C-001/C-002/
# C-003/C-008) that still govern it. This residual keeps:
#
#   * a **native thin compat delegate** for every WP02-tracked symbol
#     (FR-012) below, so ``monkeypatch.setattr(runtime_bridge, "<name>", …)``
#     keeps intercepting exactly as before the move;
#   * a **plain re-export** for the two untracked helpers
#     (``_composition_dispatch_inputs``, ``_has_generated_docs``) that
#     ``decide_next_via_runtime`` / ``runtime_bridge_io`` still reach bare /
#     via live lookup, respectively.
#
# ``_resolve_step_binding`` and ``_LEGACY_TASKS_STEP_IDS`` have no caller left
# in this module and are not compat-tracked — they live ONLY in
# ``runtime_bridge_composition.py`` now, with no residual re-export.
# (``_composition_dispatch_inputs`` / ``_has_generated_docs`` plain
# re-exports live in the top-of-file import block above, alongside the
# other untracked-helper re-exports, to keep them module-level per E402.)


def _normalize_action_for_composition(step_id: str) -> str:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._normalize_action_for_composition`
    (FR-012 compat surface, #2531 WP08)."""
    return _composition._normalize_action_for_composition(step_id)


def _should_dispatch_via_composition(
    mission: str,
    step_id: str,
    *,
    run_dir: Path | None = None,
    repo_root: Path | None = None,
) -> bool:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._should_dispatch_via_composition`
    (FR-008 selection seam; FR-012 compat surface, #2531 WP08). See the seam
    module's docstring for the full order-critical charter-lookup /
    custom-widening contract."""
    return _composition._should_dispatch_via_composition(
        mission, step_id, run_dir=run_dir, repo_root=repo_root
    )


def _resolve_step_agent_profile(run_dir: Path, step_id: str) -> str | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._resolve_step_agent_profile`
    (FR-012 compat surface, #2531 WP08)."""
    return _composition._resolve_step_agent_profile(run_dir, step_id)


def _resolve_runtime_contract_for_step(
    *,
    repo_root: Path,
    run_dir: Path,
    mission: str,
    step_id: str,
) -> Any | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._resolve_runtime_contract_for_step`
    (identity-only compat surface — GUARD_B_ONLY_IMPORT_SURFACE in
    contracts/compat-surface.md; #2531 WP08)."""
    return _composition._resolve_runtime_contract_for_step(
        repo_root=repo_root, run_dir=run_dir, mission=mission, step_id=step_id
    )


def _count_source_documented_events(feature_dir: Path) -> int:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._count_source_documented_events`
    (FR-012 compat surface, #2531 WP08)."""
    return _composition._count_source_documented_events(feature_dir)


def _publication_approved(feature_dir: Path) -> bool:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._publication_approved`
    (FR-012 compat surface, #2531 WP08)."""
    return _composition._publication_approved(feature_dir)


def _check_composed_action_guard(
    action: str,
    feature_dir: Path,
    *,
    mission: str = "software-dev",
    legacy_step_id: str | None = None,
) -> list[str]:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._check_composed_action_guard`
    (FR-012 compat surface, #2531 WP08). See the seam module's docstring for
    the full guard-branch-family / legacy-vs-composition-only contract."""
    return _composition._check_composed_action_guard(
        action, feature_dir, mission=mission, legacy_step_id=legacy_step_id
    )


def _dispatch_via_composition(
    *,
    repo_root: Path,
    mission: str,
    action: str,
    actor: str,
    profile_hint: str | None,
    request_text: str | None,
    mode_of_work: Any | None,
    feature_dir: Path,
    legacy_step_id: str | None = None,
    contract: Any | None = None,
) -> list[str] | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_composition._dispatch_via_composition`
    (FR-012 compat surface, #2531 WP08). See the seam module's docstring for
    the full ``StepContractExecutor`` handoff / structured-failure contract."""
    return _composition._dispatch_via_composition(
        repo_root=repo_root,
        mission=mission,
        action=action,
        actor=actor,
        profile_hint=profile_hint,
        request_text=request_text,
        mode_of_work=mode_of_work,
        feature_dir=feature_dir,
        legacy_step_id=legacy_step_id,
        contract=contract,
    )


# Single-dispatch invariant (FR-001 / phase6-composition-stabilization-01KQ2JAS):
# After a composition-backed software-dev action succeeds, run state must still
# advance through the next public step — but the legacy ``runtime_next_step``
# DAG dispatch handler MUST NOT be invoked for the same action attempt.
#
# THIN RESIDUAL COMPAT DELEGATE (#2531 WP03, FR-013): the logic that used to
# live here now lives at ``runtime_bridge_engine.advance_run_state_after_composition``
# (adapter-owned — it reuses the same engine primitives ``runtime_next_step``
# uses internally: ``_read_snapshot``, ``_append_event``, ``_load_frozen_template``,
# ``plan_next``, ``_write_snapshot``). This delegate exists ONLY so the heavy
# monkeypatch surface tests bind to (8x ``monkeypatch.setattr``/``mocker.patch``
# + 9x bare-attribute reads across the suite, per contracts/compat-surface.md)
# keeps resolving against ``runtime_bridge._advance_run_state_after_composition``
# unchanged. Do not add logic here — extend the adapter instead.
def _advance_run_state_after_composition(
    *,
    run_ref: MissionRunRef,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict[str, int | float] | None,
    origin: dict[str, Any],
    sync_emitter: SyncRuntimeEventEmitter,
) -> Decision:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_engine.advance_run_state_after_composition`. See the
    module-level comment above for why this delegate must stay (FR-012 compat
    surface) even though the logic itself moved (FR-013)."""
    return _engine_adapter.advance_run_state_after_composition(
        run_ref=run_ref,
        agent=agent,
        mission_slug=mission_slug,
        mission_type=mission_type,
        repo_root=repo_root,
        feature_dir=feature_dir,
        timestamp=timestamp,
        progress=progress,
        origin=origin,
        sync_emitter=sync_emitter,
    )


# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------


def _build_discovery_context(repo_root: Path) -> DiscoveryContext:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._build_discovery_context`. Flagged 🔴 high-risk in
    research.md §Compat (patched at ``test_query_mode_unit.py:751``, reached
    only via intra-seam movers in ``runtime_bridge_io.py``) — every one of
    those intra-seam callers routes back through this delegate via a live
    lookup rather than a bare intra-module call; see the seam module's
    docstring."""
    return _io_seam._build_discovery_context(repo_root)


def _resolve_runtime_template_in_root(root: Path, mission_type: str) -> Path | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._resolve_runtime_template_in_root`."""
    return _io_seam._resolve_runtime_template_in_root(root, mission_type)


def _runtime_template_key(mission_type: str, repo_root: Path) -> str:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._runtime_template_key`."""
    return _io_seam._runtime_template_key(mission_type, repo_root)


def _existing_run_ref(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
) -> MissionRunRef | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._existing_run_ref`."""
    return _io_seam._existing_run_ref(mission_slug, repo_root, mission_type)


def _start_ephemeral_query_run(
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
) -> tuple[MissionRunRef, Path]:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._start_ephemeral_query_run`."""
    return _io_seam._start_ephemeral_query_run(mission_slug, mission_type, repo_root)


def get_or_start_run(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
    *,
    emitter: Any | None = None,
) -> MissionRunRef:
    """Thin compat delegate — forwards to :func:`runtime_bridge_io.get_or_start_run`.

    Run mapping stored in .kittify/runtime/feature-runs.json:
    { "042-test-feature": { "run_id": "abc", "run_dir": "..." } }
    """
    return _io_seam.get_or_start_run(
        mission_slug, repo_root, mission_type, emitter=emitter
    )


# ---------------------------------------------------------------------------
# OperationalContext wiring (FR-017, NFR-004) — bodies live in
# runtime_bridge_io.py (T017); these are native thin compat delegates.
# ---------------------------------------------------------------------------


def _resolve_run_dir_for_mission(
    repo_root: Path, mission_slug: str
) -> Path | None:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._resolve_run_dir_for_mission`."""
    return _io_seam._resolve_run_dir_for_mission(repo_root, mission_slug)


def _resolve_tech_stack_for_profile(
    repo_root: Path, profile_id: str | None
) -> frozenset[str]:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._resolve_tech_stack_for_profile`."""
    return _io_seam._resolve_tech_stack_for_profile(repo_root, profile_id)


def build_operational_context_for_claim(
    *,
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    actor: str | None,
    active_model: str | None,
    active_role: str | None,
    current_activity: str = "implement",
    active_profile: str | None = None,
) -> OperationalContextT:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io.build_operational_context_for_claim`. See that
    function's docstring for the full OC-builder contract (shared by the two
    claim entry points, ``implement.py`` and ``agent/workflow.py``)."""
    return _io_seam.build_operational_context_for_claim(
        repo_root=repo_root,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        actor=actor,
        active_model=active_model,
        active_role=active_role,
        current_activity=current_activity,
        active_profile=active_profile,
    )


def _build_operational_context_for_decision(
    *,
    agent: str,
    run_ref: MissionRunRef,
    feature_dir: Path,
    repo_root: Path,
    step_id: str | None,
    mission_state: str | None = None,
) -> OperationalContextT:
    """Thin compat delegate — forwards to
    :func:`runtime_bridge_io._build_operational_context_for_decision`."""
    return _io_seam._build_operational_context_for_decision(
        agent=agent,
        run_ref=run_ref,
        feature_dir=feature_dir,
        repo_root=repo_root,
        step_id=step_id,
        mission_state=mission_state,
    )


# ---------------------------------------------------------------------------
# Main bridge functions
# ---------------------------------------------------------------------------


def _resolve_runtime_feature_dir(repo_root: Path, mission_slug: str) -> Path:
    """Resolve a mission dir for runtime reads without importing CLI context.

    Routes through the single guarded read-side seam
    (:func:`resolve_handle_to_read_path`, WP01/IC-01): it reads the PRIMARY
    ``meta.json``, runs the ONE sanctioned mid8 cascade (``resolve_declared_mid8``)
    and returns the existence-gated topology-aware dir — folding away the bespoke
    ``_resolve_mission_ulid`` → ``resolve_mid8`` cascade here (FR-002, C-007).

    Boundary-safe fold-in (C-007): ``runtime_bridge`` already imports
    ``specify_cli.missions._read_path_resolver`` (see
    ``_mission_routes_through_coordination`` above; ``_primary_runtime_
    feature_dir`` moved to ``runtime_bridge_identity`` at #2531 WP10 but keeps
    the same import), so consuming ``resolve_handle_to_read_path`` from the
    same module adds NO new package-boundary edge.

    Subsumption note (T013): the retired body derived ``mid8`` as
    ``resolve_mid8(slug, mission_id=<declared ULID or None>)`` — exactly tier 2 of
    the seam's ``resolve_declared_mid8``. The seam additionally honours an explicit
    declared ``meta.mid8`` (tier 1) before that and the ``mid8_from_slug`` heuristic
    (tier 3) after, so it resolves the SAME dir for any meta the old body handled
    while also covering the explicit-mid8 case the old body silently skipped.
    """
    from specify_cli.missions._read_path_resolver import (
        resolve_handle_to_read_path as _resolve_handle,
    )

    return _resolve_handle(repo_root, mission_slug)


# ---------------------------------------------------------------------------
# Decision-builder residual (#2531 WP07, FR-011) — every ``Decision(...)``
# construction below is routed through ``runtime_bridge_cores.step_or_
# blocked`` over a ``runtime_bridge_cores.DecisionEnvelope``. This module
# supplies the one genuinely I/O-bearing dependency the pure core needs (the
# step branch's on-disk prompt-file check) and threads the caller-computed
# non-deterministic fields (timestamp/run_id/decision_id) — the core itself
# never stamps them (NFR-003).
# ---------------------------------------------------------------------------


def _prompt_exists(path: str) -> bool:
    """Production ``prompt_exists`` port for :func:`runtime_bridge_cores.step_or_blocked`.

    Mirrors ``Decision.__post_init__``'s own check (``decision.py:129``)
    exactly (``Path(prompt).is_file()``) — the injected predicate and the
    dataclass invariant agree on what "resolves on disk" means.
    """
    return Path(path).is_file()


def _materialize_decision(
    envelope: _cores.DecisionEnvelope,
    guard_failures: list[str] | None = None,
) -> Decision:
    """Thin residual wrapper around :func:`runtime_bridge_cores.step_or_blocked`
    supplying the production ``prompt_exists`` port (FR-011)."""
    return _cores.step_or_blocked(envelope, guard_failures, prompt_exists=_prompt_exists)


@dataclasses.dataclass(frozen=True)
class DecideNextContext:
    """Frozen value carrier threading ``decide_next_via_runtime``'s shared
    locals through its four-phase early-return chain (FR-010,
    data-model.md §DecideNextContext): bootstrap -> dependency-gate ->
    composition-dispatch -> decision-materialize.

    Populated once by the bootstrap phase; carries no I/O of its own. This
    is an internal residual type — never re-exported, not a new public
    surface (NFR-004) — so the ``decision.py:428`` lazy edge to the
    orchestrator stays lazy (C-007).
    """

    agent: str
    mission_slug: str
    result: str
    repo_root: Path
    feature_dir: Path
    now: str
    mission_type: str
    sync_emitter: SyncRuntimeEventEmitter
    emitter_for_engine: Any
    origin: dict[str, Any]
    progress: dict[str, int | float] | None
    run_ref: MissionRunRef
    run_dir: Path
    current_step_id: str | None


def _dn_bootstrap(
    agent: str,
    mission_slug: str,
    result: str,
    repo_root: Path,
) -> tuple[DecideNextContext | None, Decision | None]:
    """Phase 1/4 of ``decide_next_via_runtime`` (FR-010) — resolve
    feature/mission/run and build the shared :class:`DecideNextContext`.

    Unlike the other three phases this one cannot accept a
    ``DecideNextContext`` as input (there is nothing to thread yet), so its
    signature is the raw entry params in, ``(ctx, decision)`` out: exactly
    one of the pair is non-``None``. A non-``None`` ``Decision`` means
    bootstrap itself short-circuited (feature dir missing / run failed to
    start) and the caller must return it immediately without running the
    remaining phases.
    """
    feature_dir = _resolve_runtime_feature_dir(repo_root, mission_slug)
    now = datetime.now(UTC).isoformat()

    if not feature_dir.is_dir():
        return None, _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission="unknown",
                mission_state="unknown",
                timestamp=now,
                reason=f"Feature directory not found: {feature_dir}",
            )
        )

    mission_type = get_mission_type(feature_dir)
    sync_emitter = SyncRuntimeEventEmitter.for_feature(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        mission_type=mission_type,
    )
    # Wrap with DecisionGitLog so decision events are durably committed to
    # the coordination branch (spec-kitty #1546, FR-001–FR-005).
    emitter_for_engine: Any = _wrap_with_decision_git_log(
        sync_emitter, mission_slug, repo_root
    )

    # Resolve origin info
    origin: dict[str, Any] = {}
    try:
        from specify_cli.runtime.resolver import resolve_mission as resolve_mission_path

        mission_result = resolve_mission_path(mission_type, repo_root)
        origin = {
            "mission_tier": getattr(mission_result.tier, "value", str(mission_result.tier)),
            "mission_path": str(mission_result.path.parent),
        }
    except FileNotFoundError:
        origin = {"mission_tier": "unknown", "mission_path": "unknown"}

    progress = _compute_wp_progress(feature_dir)

    # Get or start runtime run (before result handling so failed/blocked
    # decisions include canonical run_id, step_id, and mission_state)
    try:
        run_ref = get_or_start_run(
            mission_slug,
            repo_root,
            mission_type,
            emitter=emitter_for_engine,
        )
    except Exception as exc:
        return None, _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state="unknown",
                timestamp=now,
                reason=f"Failed to start/load runtime run: {exc}",
                progress=progress,
                origin=origin,
            )
        )

    run_dir = Path(run_ref.run_dir)

    # Read current run state
    try:
        snapshot = _engine_adapter._read_snapshot(run_dir)
        current_step_id = snapshot.issued_step_id
        sync_emitter.seed_from_snapshot(snapshot)
    except Exception:
        current_step_id = None

    # FR-017: populate the runtime OperationalContext at the `next` decision
    # boundary via the extracted helper (keeps the bootstrap phase flat). The
    # builder is read-only — it never allocates a worktree or emits a status
    # event (NFR-004).
    operational_context = _build_operational_context_for_decision(
        agent=agent,
        run_ref=run_ref,
        feature_dir=feature_dir,
        repo_root=repo_root,
        step_id=current_step_id,
        mission_state=current_step_id,
    )
    logger.debug(
        "decide_next operational context: model=%s profile=%s role=%s activity=%s",
        operational_context.active_model,
        operational_context.active_profile,
        operational_context.active_role,
        operational_context.current_activity,
    )

    return (
        DecideNextContext(
            agent=agent,
            mission_slug=mission_slug,
            result=result,
            repo_root=repo_root,
            feature_dir=feature_dir,
            now=now,
            mission_type=mission_type,
            sync_emitter=sync_emitter,
            emitter_for_engine=emitter_for_engine,
            origin=origin,
            progress=progress,
            run_ref=run_ref,
            run_dir=run_dir,
            current_step_id=current_step_id,
        ),
        None,
    )


def _dn_dependency_gate(ctx: DecideNextContext) -> Decision | None:
    """Phase 2/4 of ``decide_next_via_runtime`` (FR-010) — the
    dependency/guard gate: the WP-iteration stay-in-step check (plus its
    on-advance guard check), and the non-WP-step guard check. Returns a
    blocked/step ``Decision`` when a guard holds the run in place, else
    ``None`` to fall through to composition-dispatch.
    """
    agent = ctx.agent
    mission_slug = ctx.mission_slug
    mission_type = ctx.mission_type
    feature_dir = ctx.feature_dir
    repo_root = ctx.repo_root
    now = ctx.now
    progress = ctx.progress
    origin = ctx.origin
    run_ref = ctx.run_ref
    current_step_id = ctx.current_step_id

    # WP iteration check: if we're on a WP step and WPs remain, don't advance runtime
    if ctx.result == "success" and current_step_id and _is_wp_iteration_step(current_step_id):
        try:
            should_advance = _should_advance_wp_step(current_step_id, feature_dir)
        except CanonicalStatusNotFoundError as exc:
            return _materialize_decision(
                _cores.DecisionEnvelope(
                    kind=DecisionKind.blocked,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    reason=str(exc),
                    progress=progress,
                    origin=origin,
                    run_id=run_ref.run_id,
                    step_id=current_step_id,
                ),
                [str(exc)],
            )
        if not should_advance:
            # Stay in current step, return WP-level action
            return _build_wp_iteration_decision(
                current_step_id,
                agent,
                mission_slug,
                mission_type,
                feature_dir,
                repo_root,
                now,
                progress,
                origin,
                run_ref,
            )
        # All WPs done for this step — check guards before advancing
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            return _build_wp_iteration_decision(
                current_step_id,
                agent,
                mission_slug,
                mission_type,
                feature_dir,
                repo_root,
                now,
                progress,
                origin,
                run_ref,
                guard_failures=guard_failures,
            )

    # Check guards for non-WP steps before advancing
    if ctx.result == "success" and current_step_id and not _is_wp_iteration_step(current_step_id):
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            action, wp_id, workspace_path = _state_to_action(
                current_step_id,
                mission_slug,
                feature_dir,
                repo_root,
                mission_type,
            )
            prompt_file: str | None = None
            prompt_error: str | None = None
            if action:
                prompt_file, prompt_error = _build_prompt_or_error(
                    action,
                    feature_dir,
                    mission_slug,
                    wp_id,
                    agent,
                    repo_root,
                    mission_type,
                )
            else:
                prompt_error = (
                    f"no action mapped for step '{current_step_id}'; cannot resolve prompt"
                )
            # WP06 (FR-006/FR-013) / WP07 (FR-011): step_or_blocked never
            # issues kind=step with an unresolvable prompt_file — it falls
            # back to kind=blocked using this pre-computed reason (matches
            # the original "prompt_file is None" branch's literal exactly;
            # the "resolved-but-vanished-by-construction-time" race uses the
            # core's own hard-coded literal — see DecisionEnvelope's
            # docstring for why that is safe to share across sites).
            return _materialize_decision(
                _cores.DecisionEnvelope(
                    kind=DecisionKind.step,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    reason=prompt_error or "prompt_file_not_resolvable",
                    action=action,
                    wp_id=wp_id,
                    workspace_path=workspace_path,
                    prompt_file=prompt_file,
                    progress=progress,
                    origin=origin,
                    run_id=run_ref.run_id,
                    step_id=current_step_id,
                ),
                guard_failures,
            )

    return None


def _dn_composition_blocked_decision(
    ctx: DecideNextContext,
    current_step_id: str,
    composition_failures: list[str],
) -> Decision:
    """Build the blocked ``Decision`` for a composition-dispatch guard
    failure — the ``_state_to_action`` -> ``_build_prompt_safe`` prompt
    resolution the composition-dispatch phase needs when the executor
    reports guard failures instead of advancing (FR-008 composition
    guard-failure surface). Split out of ``_dn_composition_dispatch`` to
    keep that phase's own complexity down; it re-extracts nothing WP06-08
    already own — it is pure orchestration plumbing local to this phase.
    """
    action, wp_id, workspace_path = _state_to_action(
        current_step_id,
        ctx.mission_slug,
        ctx.feature_dir,
        ctx.repo_root,
        ctx.mission_type,
    )
    prompt_file = (
        _build_prompt_safe(
            action or current_step_id,
            ctx.feature_dir,
            ctx.mission_slug,
            wp_id,
            ctx.agent,
            ctx.repo_root,
            ctx.mission_type,
        )
        if action
        else None
    )
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.blocked,
            agent=ctx.agent,
            mission_slug=ctx.mission_slug,
            mission=ctx.mission_type,
            mission_state=current_step_id,
            timestamp=ctx.now,
            reason=composition_failures[0],
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            prompt_file=prompt_file,
            progress=ctx.progress,
            origin=ctx.origin,
            run_id=ctx.run_ref.run_id,
            step_id=current_step_id,
        ),
        composition_failures,
    )


def _dn_composition_dispatch(ctx: DecideNextContext) -> Decision | None:
    """Phase 3/4 of ``decide_next_via_runtime`` (FR-010) — composition
    dispatch (mission `software-dev-composition-rewrite-01KQ26CY`).

    For the built-in `software-dev` mission's five public actions, route the
    just-completed step through `StepContractExecutor.execute` BEFORE we let
    the runtime planner advance run state. The composition produces the
    invocation_id chain (host harness interprets it); a structured guard
    failure surface (Decision.kind=blocked, guard_failures populated) is
    used in lieu of a Python traceback when the executor raises
    `StepContractExecutionError`. C-008 hard-guards this on
    `mission == "software-dev"`; every other mission falls through (returns
    ``None``) to composition unchanged so decision-materialize runs the
    runtime planner next.
    """
    agent = ctx.agent
    mission_slug = ctx.mission_slug
    mission_type = ctx.mission_type
    feature_dir = ctx.feature_dir
    repo_root = ctx.repo_root
    now = ctx.now
    progress = ctx.progress
    origin = ctx.origin
    run_ref = ctx.run_ref
    current_step_id = ctx.current_step_id

    if (
        ctx.result == "success"
        and current_step_id
        and _should_dispatch_via_composition(
            mission_type,
            current_step_id,
            run_dir=ctx.run_dir,
            repo_root=repo_root,
        )
    ):
        composed_action = _normalize_action_for_composition(current_step_id)
        # R-005: for custom missions, the active step's ``agent_profile`` is
        # the source of truth for ``profile_hint``. For built-in missions
        # (e.g., ``software-dev``), built-in templates do NOT set
        # ``agent_profile``, so this resolves to ``None`` and the executor's
        # ``_resolve_profile_hint`` falls back to ``_ACTION_PROFILE_DEFAULTS``
        # — preserving byte-identical built-in dispatch behavior (FR-010).
        resolved_profile, runtime_contract = _composition_dispatch_inputs(
            repo_root=repo_root,
            run_dir=ctx.run_dir,
            mission=mission_type,
            step_id=current_step_id,
            action=composed_action,
        )
        composition_failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission=mission_type,
            action=composed_action,
            actor=agent,
            profile_hint=resolved_profile,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir,
            # Thread the original step_id so the post-action guard can branch
            # on substep semantics for legacy tasks_outline/tasks_packages/
            # tasks_finalize. Without this, the collapsed guard demands the
            # terminal post-finalize state on every substep and blocks the
            # live tasks_outline → tasks_packages → tasks_finalize flow.
            legacy_step_id=current_step_id,
            contract=runtime_contract,
        )
        if composition_failures:
            return _dn_composition_blocked_decision(
                ctx, current_step_id, composition_failures
            )
        # Composition succeeded; advance run state via the
        # composition-specific advancement helper and short-circuit the
        # legacy ``runtime_next_step`` fall-through (FR-001/FR-002). The
        # helper emits the same lane / state events the legacy path emits;
        # any error from it surfaces through the existing ``Decision``
        # ``blocked`` shape (EDGE-003) — the legacy DAG dispatch handler is
        # **not** entered as a fallback.
        try:
            return _advance_run_state_after_composition(
                run_ref=run_ref,
                agent=agent,
                mission_slug=mission_slug,
                mission_type=mission_type,
                repo_root=repo_root,
                feature_dir=feature_dir,
                timestamp=now,
                progress=progress,
                origin=origin,
                sync_emitter=ctx.sync_emitter,
            )
        except Exception as exc:  # noqa: BLE001 — EDGE-003 contract: any
            # advancement-helper failure must surface as a structured
            # Decision, not as a Python traceback, and MUST NOT silently
            # fall through to the legacy DAG dispatch handler.
            logger.exception(
                "advancement helper failed after composition for %s/%s",
                mission_type,
                composed_action,
            )
            return _materialize_decision(
                _cores.DecisionEnvelope(
                    kind=DecisionKind.blocked,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    reason=(
                        f"Run-state advancement after composition failed for "
                        f"{mission_type}/{composed_action}: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    progress=progress,
                    origin=origin,
                    run_id=run_ref.run_id,
                    step_id=current_step_id,
                )
            )

    return None


def _dn_capture_pre_speculative_state(
    run_dir: Path,
) -> tuple[bytes | None, int | None] | None:
    """Capture ``(state.json bytes, run.events.jsonl size)`` before a
    speculative engine advance, so a later retrospective-gate refusal can
    roll back cleanly. Returns ``None`` on a disk-read failure — the caller
    must then surface a blocked ``Decision`` rather than advance into a
    state it cannot retract (mirrors the original inline try/except
    exactly)."""
    state_path = run_dir / STATE_FILE
    events_path = run_dir / "run.events.jsonl"
    try:
        pre_state_bytes = state_path.read_bytes() if state_path.exists() else None
        pre_events_size = events_path.stat().st_size if events_path.exists() else 0
    except OSError:
        return None
    return pre_state_bytes, pre_events_size


def _dn_rollback_buffered_run_state(
    run_dir: Path,
    pre_state_bytes: bytes | None,
    pre_events_size: int | None,
) -> None:
    """Restore state.json / truncate run.events.jsonl to their pre-speculative-
    advance values after the retrospective gate refuses completion. Mirrors
    the original inline rollback exactly, including its error-logging-only
    failure mode — a failed rollback is logged, not itself surfaced as a
    Decision (the caller has already committed to returning the gate-refused
    blocked Decision)."""
    if pre_state_bytes is not None:
        try:
            (run_dir / STATE_FILE).write_bytes(pre_state_bytes)
        except OSError as restore_exc:
            logger.error(
                "rollback of state.json failed after gate block: %s",
                restore_exc,
            )
    if pre_events_size is not None:
        events_path = run_dir / "run.events.jsonl"
        try:
            if events_path.exists():
                with open(events_path, "r+b") as handle:
                    handle.truncate(pre_events_size)
        except OSError as restore_exc:
            logger.error(
                "rollback of run.events.jsonl failed after gate block: %s",
                restore_exc,
            )


def _dn_terminal_retrospective_gate(
    ctx: DecideNextContext,
    policy_error: Exception | None,
    buffer: _BufferingRuntimeEmitter | None,
    pre_state_bytes: bytes | None,
    pre_events_size: int | None,
) -> Decision | None:
    """Run the strict (block-on) retrospective gate for a just-produced
    terminal ``Decision``. On refusal: drop the buffered emit calls (so no
    ``MissionRunCompleted`` ever reaches the real emitter), roll back
    state.json/run.events.jsonl, and return the blocked ``Decision``. On
    success (gate passes, or was never entered because ``policy_error`` is
    ``None`` and capture raises nothing) returns ``None`` so the caller
    proceeds to flush the buffer. Split out of ``_dn_decision_materialize``
    to keep that phase's own complexity down — pure orchestration plumbing
    local to this phase, not a re-extraction of WP04's retrospective seam.
    """
    mission_id = _resolve_mission_id_for_terminus(ctx.feature_dir)
    try:
        if policy_error is not None:
            raise policy_error
        _run_retrospective_learning_capture(
            mission_id=mission_id,
            mission_slug=ctx.mission_slug,
            feature_dir=ctx.feature_dir,
            repo_root=ctx.repo_root,
            block_on_failure=True,
        )
    except Exception as exc:
        # Gate refused. Drop the buffered emit calls (so no
        # MissionRunCompleted ever reaches the real emitter) and
        # restore state.json + truncate run.events.jsonl to pre-call.
        if buffer is not None:
            buffer.discard()
        _dn_rollback_buffered_run_state(ctx.run_dir, pre_state_bytes, pre_events_size)
        return _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.blocked,
                agent=ctx.agent,
                mission_slug=ctx.mission_slug,
                mission=ctx.mission_type,
                mission_state=ctx.current_step_id or "unknown",
                timestamp=ctx.now,
                reason=f"Retrospective gate refused completion: {exc}",
                progress=ctx.progress,
                origin=ctx.origin,
            )
        )
    return None


def _dn_decision_materialize(ctx: DecideNextContext) -> Decision:
    """Phase 4/4 of ``decide_next_via_runtime`` (FR-010) — advance via the
    runtime planner and materialize the terminal/step/query ``Decision``
    through WP07's Decision-builder. Always returns a ``Decision`` (never
    ``None``): this is the chain's terminal phase.

    Strict retrospective policy remains a pre-completion gate. The default
    post-completion policy is best-effort and must not buffer or roll back
    MissionRunCompleted; it runs after terminal events have flushed.
    """
    policy, _source_map, policy_error = _resolve_retrospective_policy_for_runtime(ctx.repo_root)
    retrospective_enabled = bool(getattr(policy, "enabled", False))
    block_on_retrospective = _retrospective_blocks_completion(policy)

    pre_state_bytes: bytes | None = None
    pre_events_size: int | None = None
    # Use the DecisionGitLog-wrapped emitter as the engine's emitter so that
    # decision events are durably committed to the coordination branch.
    engine_emitter: Any = ctx.emitter_for_engine
    buffer: _BufferingRuntimeEmitter | None = None

    if block_on_retrospective:
        captured = _dn_capture_pre_speculative_state(ctx.run_dir)
        if captured is None:
            # If we cannot capture pre-state we cannot guarantee a clean
            # rollback. Surface this as a blocked Decision rather than
            # advancing into a state we cannot retract.
            return _materialize_decision(
                _cores.DecisionEnvelope(
                    kind=DecisionKind.blocked,
                    agent=ctx.agent,
                    mission_slug=ctx.mission_slug,
                    mission=ctx.mission_type,
                    mission_state=ctx.current_step_id or "unknown",
                    timestamp=ctx.now,
                    reason=(
                        "Cannot read run state.json / run.events.jsonl before "
                        "speculative engine advance; refusing to advance"
                    ),
                    progress=ctx.progress,
                    origin=ctx.origin,
                )
            )
        pre_state_bytes, pre_events_size = captured
        buffer = _BufferingRuntimeEmitter()
        engine_emitter = buffer

    # Advance via runtime
    try:
        runtime_decision = runtime_next_step(
            ctx.run_ref,
            agent_id=ctx.agent,
            result=ctx.result,
            emitter=engine_emitter,
        )
    except Exception as exc:
        # Engine raised: discard any buffered events; nothing left to flush.
        if buffer is not None:
            buffer.discard()
        return _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.blocked,
                agent=ctx.agent,
                mission_slug=ctx.mission_slug,
                mission=ctx.mission_type,
                mission_state=ctx.current_step_id or "unknown",
                timestamp=ctx.now,
                reason=f"Runtime engine error: {exc}",
                progress=ctx.progress,
                origin=ctx.origin,
            )
        )

    if block_on_retrospective and runtime_decision.kind == DecisionKind.terminal:
        gate_decision = _dn_terminal_retrospective_gate(
            ctx, policy_error, buffer, pre_state_bytes, pre_events_size
        )
        if gate_decision is not None:
            return gate_decision

    # Gate either passed (terminal allow) or never ran (non-terminal /
    # not opted in): flush any buffered emit calls into the real sync
    # emitter so observers receive them in original order.
    if buffer is not None:
        buffer.flush(ctx.sync_emitter)

    if (
        retrospective_enabled
        and not block_on_retrospective
        and runtime_decision.kind == DecisionKind.terminal
    ):
        mission_id = _resolve_mission_id_for_terminus(ctx.feature_dir)
        _run_retrospective_learning_capture(
            mission_id=mission_id,
            mission_slug=ctx.mission_slug,
            feature_dir=ctx.feature_dir,
            repo_root=ctx.repo_root,
            block_on_failure=False,
        )

    return _map_runtime_decision(
        runtime_decision,
        ctx.agent,
        ctx.mission_slug,
        ctx.mission_type,
        ctx.repo_root,
        ctx.feature_dir,
        ctx.now,
        ctx.progress,
        ctx.origin,
    )


def decide_next_via_runtime(
    agent: str,
    mission_slug: str,
    result: str,
    repo_root: Path,
) -> Decision:
    """Main entry point replacing old decide_next().

    A linear four-phase early-return chain over :class:`DecideNextContext`
    (FR-010): bootstrap builds the context (and may itself short-circuit —
    feature dir missing / run failed to start); dependency-gate,
    composition-dispatch, and decision-materialize each take ``ctx`` and
    return ``Decision | None``, the first non-``None`` short-circuiting.
    decision-materialize is the terminal phase and always resolves.

    Flow:
    1. Resolve mission_type from meta.json
    2. get_or_start_run() to obtain MissionRunRef
    3. Check if current step is a WP-iteration step
       a. If yes and WPs remain: skip runtime advance, build WP prompt, return step
       b. If yes and all WPs done: call next_step(result="success") to advance
    4. For non-WP steps: call next_step(run_ref, agent, result) directly
    5. Map NextDecision -> Decision (preserving JSON contract)
    """
    ctx, early_decision = _dn_bootstrap(agent, mission_slug, result, repo_root)
    if early_decision is not None:
        return early_decision
    assert ctx is not None  # _dn_bootstrap always pairs a ctx with None (or vice versa)

    for phase in (_dn_dependency_gate, _dn_composition_dispatch, _dn_decision_materialize):
        decision = phase(ctx)
        if decision is not None:
            return decision

    raise AssertionError(  # pragma: no cover — decision-materialize always resolves
        "decide_next_via_runtime: no phase produced a Decision"
    )


def _build_finalized_override_query_decision(
    *,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
    repo_root: Path,
    finalized_override: str,
) -> Decision:
    override_wp_id: str | None = None
    if finalized_override == "done":
        mission_state = "done"
        preview_step = None
        reason = "All work packages are done"
    elif finalized_override.startswith("blocked:"):
        mission_state = "blocked"
        preview_step = None
        reason = finalized_override.split(":", 1)[1].replace("_", " ")
    else:
        mission_state = finalized_override
        preview_step = finalized_override
        reason = None
        if finalized_override == "implement":
            from mission_runtime import MissionArtifactKind, mission_context_for
            from runtime.next.discovery import preview_claimable_wp

            mission_context = mission_context_for(repo_root, mission_slug)
            preview = preview_claimable_wp(
                mission_context.artifact(MissionArtifactKind.WORK_PACKAGE_TASK).read_dir,
                status_dir=mission_context.artifact(MissionArtifactKind.STATUS_STATE).read_dir,
            )
            override_wp_id = preview.wp_id
            if preview.wp_id is None and preview.selection_reason is not None:
                reason = preview.selection_reason
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=mission_state,
            timestamp=now,
            reason=reason,
            progress=progress,
            run_id=emitted_run_id,
            preview_step=preview_step,
            wp_id=override_wp_id,
        )
    )


def _build_initial_query_decision(
    *,
    runtime_decision: Any,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
) -> Decision:
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="not_started",
            timestamp=now,
            reason=None,
            progress=progress,
            run_id=emitted_run_id,
            preview_step=runtime_decision.step_id,
        )
    )


def _build_decision_required_query(
    *,
    runtime_decision: Any,
    snapshot: Any,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
) -> Decision:
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=snapshot.issued_step_id or runtime_decision.step_id or "unknown",
            timestamp=now,
            reason=None,
            progress=progress,
            run_id=emitted_run_id,
            step_id=snapshot.issued_step_id or runtime_decision.step_id,
            decision_id=runtime_decision.decision_id,
            input_key=runtime_decision.input_key,
            question=runtime_decision.question,
            options=runtime_decision.options,
        )
    )


def _build_runtime_query_decision(
    *,
    runtime_decision: Any,
    snapshot: Any,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
) -> Decision:
    mission_state = runtime_decision.step_id or "unknown"
    blocked_reason: str | None = None
    if runtime_decision.kind == DecisionKind.terminal:
        mission_state = "done"
    elif runtime_decision.kind == DecisionKind.blocked:
        mission_state = snapshot.issued_step_id or runtime_decision.step_id or "blocked"
        blocked_reason = snapshot.blocked_reason or getattr(runtime_decision, "reason", None)
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=mission_state,
            timestamp=now,
            reason=blocked_reason,
            progress=progress,
            run_id=emitted_run_id,
            step_id=snapshot.issued_step_id or runtime_decision.step_id,
        )
    )


def query_current_state(
    agent: str | None,
    mission_slug: str,
    repo_root: Path,
) -> Decision:
    """Return current mission state without advancing the DAG.

    Reads the run snapshot idempotently. Does NOT call next_step().
    Returns a Decision with kind=DecisionKind.query and is_query=True.

    Args:
        agent: Agent name (for Decision construction only).
        mission_slug: Mission slug (e.g. '069-planning-pipeline-integrity').
        repo_root: Repository root path.
    """
    from mission_runtime import ActionContextError, MissionArtifactKind, mission_context_for

    now = datetime.now(UTC).isoformat()
    try:
        mission_context = mission_context_for(repo_root, mission_slug)
        mission_slug = mission_context.mission_slug
    except ActionContextError as exc:
        # FR-001 / C-IC02: pass a typed *read-path* error through VERBATIM. The
        # resolver already produced the precise code (e.g.
        # COORDINATION_BRANCH_DELETED / STATUS_READ_PATH_NOT_FOUND) plus the real
        # read-path remediation; collapsing it into a generic MISSION_NOT_FOUND
        # ("run mission list") points the operator the wrong way (the mission is
        # not missing — its read path is broken; the disease #15). The command
        # layer surfaces ``exc.code`` + checked paths from the typed error.
        # (Earlier this raised ``MissionNotFoundError`` for ALL ActionContextError
        # and mis-attributed the collapse to FR-004 / WP03; that attribution was
        # stale — the next-family collapse is owned by THIS WP.)
        if _is_read_path_error(exc):
            raise
        # A genuinely-missing mission (e.g. FEATURE_CONTEXT_UNRESOLVED — no mission
        # directory at all) is legitimately MISSION_NOT_FOUND (FR-004 / WP03).
        raise MissionNotFoundError(mission_slug) from exc

    task_board = mission_context.artifact(MissionArtifactKind.WORK_PACKAGE_TASK)
    status_state = mission_context.artifact(MissionArtifactKind.STATUS_STATE)

    if not task_board.read_dir.is_dir():
        # Conscious decision (C-IC02): reaching here means the resolver RESOLVED
        # a directory and verified it ``exists()`` (see resolution.py), yet it is
        # not a directory on disk — i.e. the canonical mission dir name resolved
        # to a regular file. That is a genuinely malformed / missing mission, not
        # a read-path topology miss, so ``MISSION_NOT_FOUND`` is the correct,
        # deliberately-kept classification here (NOT a read-path collapse).
        raise MissionNotFoundError(mission_slug)

    mission_type = mission_context.mission_type
    progress = _compute_wp_progress(task_board.read_dir, status_dir=status_state.read_dir)

    run_ref = _existing_run_ref(mission_slug, repo_root, mission_type)
    ephemeral_run_store: Path | None = None

    # Read current step WITHOUT calling next_step(). When no step has been
    # issued yet, use the planner read-only to compute a truthful preview.
    # The try/finally below guarantees the ephemeral run store is cleaned up
    # on every return path (success, raise, or early exit).
    try:
        try:
            if run_ref is None:
                run_ref, ephemeral_run_store = _start_ephemeral_query_run(
                    mission_slug,
                    mission_type,
                    repo_root,
                )
                snapshot = _engine_adapter._read_snapshot(Path(run_ref.run_dir))
                template_path = Path(run_ref.run_dir) / "mission_template_frozen.yaml"
                template = load_mission_template_file(template_path)
            else:
                snapshot = _engine_adapter._read_snapshot(Path(run_ref.run_dir))
                template_path = Path(snapshot.template_path)
                template = load_mission_template_file(template_path)
            runtime_decision = _engine_adapter.plan_next(
                snapshot,
                template,
                snapshot.policy_snapshot,
                live_template_path=template_path,
            )
        except QueryModeValidationError:
            raise
        except Exception as exc:
            raise QueryModeValidationError(f"Could not read query state for mission '{mission_slug}': {exc}") from exc

        # Query mode never persists the ephemeral run it bootstraps for a
        # not-yet-started mission. Returning that run's id in the JSON would
        # mislead callers into thinking they can issue ``spec-kitty next
        # --mission <slug> --result …`` against it; in reality the run state
        # is wiped in the finally block before the function returns. Only
        # emit ``run_id`` when the run is a real, persisted one.
        emitted_run_id: str | None = None
        if ephemeral_run_store is None:
            emitted_run_id = getattr(run_ref, "run_id", None)

        finalized_override = _finalized_task_board_override_step(
            task_board.read_dir,
            progress,
            status_dir=status_state.read_dir,
        )
        if finalized_override is not None:
            return _build_finalized_override_query_decision(
                agent=agent,
                mission_slug=mission_slug,
                mission_type=mission_type,
                now=now,
                progress=progress,
                emitted_run_id=emitted_run_id,
                repo_root=repo_root,
                finalized_override=finalized_override,
            )

        if not snapshot.completed_steps and not snapshot.pending_decisions and not snapshot.decisions:
            if runtime_decision.kind in {DecisionKind.step, DecisionKind.decision_required} and runtime_decision.step_id:
                return _build_initial_query_decision(
                    runtime_decision=runtime_decision,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission_type=mission_type,
                    now=now,
                    progress=progress,
                    emitted_run_id=emitted_run_id,
                )
            raise QueryModeValidationError(f"Mission '{mission_type}' has no issuable first step for run '{mission_slug}'")

        if runtime_decision.kind == DecisionKind.decision_required:
            return _build_decision_required_query(
                runtime_decision=runtime_decision,
                snapshot=snapshot,
                agent=agent,
                mission_slug=mission_slug,
                mission_type=mission_type,
                now=now,
                progress=progress,
                emitted_run_id=emitted_run_id,
            )

        return _build_runtime_query_decision(
            runtime_decision=runtime_decision,
            snapshot=snapshot,
            agent=agent,
            mission_slug=mission_slug,
            mission_type=mission_type,
            now=now,
            progress=progress,
            emitted_run_id=emitted_run_id,
        )
    finally:
        if ephemeral_run_store is not None:
            shutil.rmtree(ephemeral_run_store, ignore_errors=True)


def answer_decision_via_runtime(
    mission_slug: str,
    decision_id: str,
    answer: str,
    agent: str,
    repo_root: Path,
    *,
    actor_type: str = "human",
) -> None:
    """Answer a pending decision.

    CLI answers are human-authored by default even though the command still
    carries an ``--agent`` identity for the surrounding mission loop.
    """
    import logging

    logger = logging.getLogger(__name__)

    from mission_runtime import ActionContextError, resolve_action_context

    try:
        _ctx = resolve_action_context(
            repo_root,
            action="tasks",
            feature=mission_slug,
        )
        feature_dir = Path(_ctx.feature_dir)
    except ActionContextError as exc:
        # FR-001 / C-IC02: preserve the typed read-path error IDENTICALLY on the
        # decision-answer path (the same fidelity obligation as the query path).
        # Collapsing it into a generic "not found" MissionRuntimeError would drop
        # ``exc.code`` (e.g. COORDINATION_BRANCH_DELETED) and the read-path
        # remediation, mis-routing the operator. Log the context, then re-raise
        # the typed ActionContextError so the command layer surfaces its code.
        logger.warning(
            "answer_decision_via_runtime: read-path error (%s) for mission %r in "
            "repo %s — cannot answer decision %r",
            exc.code,
            mission_slug,
            repo_root,
            decision_id,
        )
        raise
    if not feature_dir.is_dir():
        logger.warning(
            "answer_decision_via_runtime: mission %r resolved to missing dir %s — cannot answer decision %r",
            mission_slug,
            feature_dir,
            decision_id,
        )
        raise MissionRuntimeError(
            f"Mission {mission_slug!r} not found; cannot answer decision {decision_id!r}"
        )
    mission_type = get_mission_type(feature_dir)
    run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
    sync_emitter = SyncRuntimeEventEmitter.for_feature(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        mission_type=mission_type,
    )
    try:
        sync_emitter.seed_from_snapshot(_engine_adapter._read_snapshot(Path(run_ref.run_dir)))
    except Exception as exc:
        logger.warning(
            "answer_decision_via_runtime: failed to seed emitter from snapshot for run %r: %s",
            run_ref.run_dir,
            exc,
        )
    # Wrap with DecisionGitLog so the answered decision is committed to the
    # coordination branch (spec-kitty #1546, FR-001–FR-005).
    answer_emitter: Any = _wrap_with_decision_git_log(
        sync_emitter, mission_slug, repo_root
    )
    actor = ActorIdentity(actor_id=agent, actor_type=actor_type)
    runtime_provide_decision_answer(
        run_ref,
        decision_id,
        answer,
        actor,
        emitter=answer_emitter,
    )


# ---------------------------------------------------------------------------
# Internal mapping helpers
# ---------------------------------------------------------------------------


def _build_wp_iteration_decision(
    step_id: str,
    agent: str,
    mission_slug: str,
    mission_type: str,
    feature_dir: Path,
    repo_root: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
    run_ref: MissionRunRef,
    guard_failures: list[str] | None = None,
) -> Decision:
    """Build a Decision for WP iteration within a step."""
    action, wp_id, workspace_path = _state_to_action(
        step_id,
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )

    if action is None:
        return _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                reason=f"No action mapped for step '{step_id}'",
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=step_id,
            ),
            guard_failures or [],
        )

    prompt_file, prompt_error = _build_prompt_or_error(
        action,
        feature_dir,
        mission_slug,
        wp_id,
        agent,
        repo_root,
        mission_type,
    )
    # WP06 (FR-006/FR-013) / WP07 (FR-011): step_or_blocked never issues
    # kind=step with an unresolvable prompt_file; see the analogous note in
    # decide_next_via_runtime for why the shared core's hard-coded
    # "prompt_file_not_resolvable" literal is safe for the
    # resolved-but-vanished-by-construction-time race.
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.step,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=prompt_error or "no_prompt_template",
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            prompt_file=prompt_file,
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
            step_id=step_id,
        ),
        guard_failures or [],
    )


def _build_decision_required_prompt_file(
    decision: NextDecision,
    mission_slug: str,
    repo_root: Path,
    agent: str,
) -> str | None:
    """Best-effort ``decision_required`` prompt build (silently ``None`` on failure).

    Verbatim extraction of ``_map_runtime_decision``'s former inline
    try/except (#2531 WP07/T026 — CC reduction; no behavior change: a failed
    ``build_decision_prompt`` still yields ``prompt_file=None``, same as
    before)."""
    if not decision.question:
        return None
    from runtime.next.prompt_builder import build_decision_prompt

    try:
        _, prompt_path = build_decision_prompt(
            question=decision.question,
            options=decision.options,
            decision_id=decision.decision_id or "unknown",
            mission_slug=mission_slug,
            repo_root=repo_root,
            agent=agent,
        )
        return str(prompt_path)
    except Exception:
        return None


def _map_wp_step_decision(
    *,
    step_id: str,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
    run_id: str | None,
) -> Decision:
    """WP-iteration branch of the ``kind="step"`` mapping (#2531 WP07/T026).

    Extracted verbatim from ``_map_runtime_decision``'s former WP-step
    triad — the ``action is None`` early-blocked case, plus the
    ``step_or_blocked`` collapse of the former prompt-resolution triad."""
    action, wp_id, workspace_path = _state_to_action(
        step_id,
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )
    if action is None:
        return _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                reason=f"No action mapped for WP step '{step_id}'",
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )
        )
    prompt_file, prompt_error = _build_prompt_or_error(
        action,
        feature_dir,
        mission_slug,
        wp_id,
        agent,
        repo_root,
        mission_type,
    )
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.step,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=prompt_error or "prompt_file_not_resolvable",
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            prompt_file=prompt_file,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )
    )


def _map_non_wp_step_decision(
    *,
    step_id: str | None,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
    run_id: str | None,
) -> Decision:
    """Non-WP branch of the ``kind="step"`` mapping (#2531 WP07/T026).

    Extracted verbatim from ``_map_runtime_decision``'s former non-WP
    triad — template-resolution via ``_state_to_action`` +
    ``_build_prompt_or_error``, collapsed via ``step_or_blocked``."""
    action, wp_id, workspace_path = _state_to_action(
        step_id or "unknown",
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )
    prompt_file: str | None = None
    prompt_error: str | None = None
    if action or step_id:
        prompt_file, prompt_error = _build_prompt_or_error(
            action or step_id or "unknown",
            feature_dir,
            mission_slug,
            wp_id,
            agent,
            repo_root,
            mission_type,
        )
    else:
        prompt_error = "no action and no step_id; cannot resolve prompt"
    return _materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.step,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=prompt_error or "no_prompt_template",
            action=action or step_id,
            wp_id=wp_id,
            workspace_path=workspace_path,
            prompt_file=prompt_file,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )
    )


def _map_runtime_decision(
    decision: NextDecision,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
) -> Decision:
    """Convert runtime NextDecision to CLI Decision dataclass.

    Exit-code contract (FR-008):
    - ``kind="terminal"`` → ``DecisionKind.terminal`` → ``next_cmd`` exits 0
    - ``kind="blocked"``  → ``DecisionKind.blocked``  → ``next_cmd`` exits 1
    - ``kind="step"``     → ``DecisionKind.step``     → ``next_cmd`` exits 0

    ``next_cmd.py`` maps the kind to exit code; this function must not change
    the kind semantics. Verified by:
    - ``tests/next/test_next_command_integration.py::TestNextCommandCLI::test_terminal_state_exit_code_zero``
    - ``tests/next/test_next_command_integration.py::TestNextCommandCLI::test_blocked_result_exit_code``

    #2531 WP07/T026: every branch now builds a
    :class:`runtime_bridge_cores.DecisionEnvelope` and materializes it via
    :func:`runtime_bridge_cores.step_or_blocked` (FR-011); the WP-step and
    non-WP-step branches (the former CC-heaviest part of this function) are
    extracted to :func:`_map_wp_step_decision` / :func:`_map_non_wp_step_
    decision` so this dispatcher stays a flat kind-lookup.
    """
    step_id = decision.step_id
    run_id = decision.run_id

    if decision.kind == DecisionKind.terminal:
        return _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.terminal,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state="done",
                timestamp=timestamp,
                reason=decision.reason or "Mission complete",
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )
        )

    if decision.kind == DecisionKind.blocked:
        return _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id or "unknown",
                timestamp=timestamp,
                reason=decision.reason,
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )
        )

    if decision.kind == DecisionKind.decision_required:
        prompt_file = _build_decision_required_prompt_file(decision, mission_slug, repo_root, agent)
        return _materialize_decision(
            _cores.DecisionEnvelope(
                kind=DecisionKind.decision_required,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id or "unknown",
                timestamp=timestamp,
                reason=decision.reason or "Decision required",
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
                decision_id=decision.decision_id,
                input_key=decision.input_key,
                question=decision.question,
                options=decision.options,
                prompt_file=prompt_file,
            )
        )

    # kind == "step"
    if step_id and _is_wp_iteration_step(step_id):
        return _map_wp_step_decision(
            step_id=step_id,
            agent=agent,
            mission_slug=mission_slug,
            mission_type=mission_type,
            repo_root=repo_root,
            feature_dir=feature_dir,
            timestamp=timestamp,
            progress=progress,
            origin=origin,
            run_id=run_id,
        )

    return _map_non_wp_step_decision(
        step_id=step_id,
        agent=agent,
        mission_slug=mission_slug,
        mission_type=mission_type,
        repo_root=repo_root,
        feature_dir=feature_dir,
        timestamp=timestamp,
        progress=progress,
        origin=origin,
        run_id=run_id,
    )


# ---------------------------------------------------------------------------
# Public surface (FR-007 / #2531 WP03). Governs ``from runtime_bridge import *``
# ONLY — it does NOT preserve the ~50 private symbols tests patch (those live
# in the explicit guarded compat re-export block introduced as later WPs
# relocate them; see contracts/compat-surface.md §``__all__``).
# ---------------------------------------------------------------------------
__all__ = [
    "DecisionGitLogUnavailable",
    "MissionNotFoundError",
    "QueryModeValidationError",
    "answer_decision_via_runtime",
    "build_operational_context_for_claim",
    "decide_next_via_runtime",
    "get_or_start_run",
    "query_current_state",
]
