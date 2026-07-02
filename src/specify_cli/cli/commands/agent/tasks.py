"""Task workflow commands for AI agents."""

# ⚠️ GOD-MODULE (tracked for decomposition — do NOT add new responsibilities here).
# This file is an oversized "god module" (~4500 LOC, maxCC ~178). Extract cohesive
# seams into dedicated modules instead of growing this one.
# De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2058

from __future__ import annotations

from specify_cli.core.constants import (
    KITTY_SPECS_DIR,
)
from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
    resolve_feature_dir_for_mission,
    resolve_planning_read_dir,
)
import contextlib
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from kernel._safe_re import re
import subprocess
import traceback
from datetime import datetime, UTC
from pathlib import Path

import typer
from rich.console import Console
from typing import Annotated, Any

from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.sync.events import (
    emit_history_added,
    emit_error_logged,
)

from specify_cli.coordination.status_transition import (
    emit_status_transition_transactional,
    read_events_transactional,
)
from specify_cli.status import Lane, ReviewResult, StatusEvent, TransitionRequest
from specify_cli.status import is_dossier_snapshot as _is_dossier_snapshot
from specify_cli.status import PROGRESS_SEMANTICS
from specify_cli.status import resolve_lane_alias
from specify_cli.status import EventPersistenceError, EVENTS_FILENAME

from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.lanes.persistence import MissingLanesError
from specify_cli.core.paths import locate_project_root, get_main_repo_root, is_worktree_context
from specify_cli.core.paths import get_feature_target_branch
from specify_cli.core.paths import get_status_read_root
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.mission import get_mission_type
from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
)
from specify_cli.coordination.commit_router import commit_for_mission
from specify_cli.git import SafeCommitPathPolicyError
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.status import feature_status_lock
from specify_cli.core.agent_config import get_auto_commit_default
from specify_cli.status import BootstrapResult, bootstrap_canonical_state
from specify_cli.core.utils import write_text_within_directory
from specify_cli.workspace.context import get_normalized_wp, resolve_workspace_for_wp
from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout


def resolve_primary_branch(repo_root: Path) -> str:
    """Resolve the primary branch name (main, master, etc.).

    Delegates to the centralized implementation in core.git_ops.

    Returns:
        Detected primary branch name.
    """
    from specify_cli.core.git_ops import resolve_primary_branch as _resolve

    return _resolve(repo_root)


from specify_cli.task_utils import (
    append_activity_log,
    build_document,
    ensure_lane,
    extract_scalar,
    locate_work_package,
    set_scalar,
    split_frontmatter,
)

# WP02 (#2058): tasks.md/manifest parsing + WP-id resolution helpers and the
# shared result vocabulary live in the ``tasks_outline`` seam. Imported here so
# existing ``from ...agent.tasks import <name>`` call sites keep working.
from specify_cli.cli.commands.agent.tasks_outline import (
    TASKS_MD_FILENAME,
    TaskIdResolutionFormat,
    TaskIdResolutionOutcome,
    TaskIdResult,
    _INLINE_SUBTASKS_RE,
    # WP03 (#2058): the pipe-table row parsers moved to ``tasks_materialization``
    # along with their only former internal caller. They remain re-exported here
    # (explicit ``as`` form) because existing tests import them from ``tasks``.
    _is_pipe_table_task_row as _is_pipe_table_task_row,
    _normalize_task_id_input,
    _parse_pipe_table_header as _parse_pipe_table_header,
    _resolve_history_wp_id,
    _resolve_wp_id,
)

# WP03 (#2058): frontmatter/file persistence + markdown-row mutation helpers
# live in the ``tasks_materialization`` seam. Re-exported here (out-of-map edit:
# tasks.py is owned by WP07) so existing ``from ...agent.tasks import <name>``
# call sites (workflow.py, implement.py, tests) keep working unchanged. Names not
# referenced inside this module use the explicit ``as`` re-export form so ruff
# recognizes the intentional public re-export and does not flag F401.
from specify_cli.cli.commands.agent.tasks_materialization import (
    _collect_status_artifacts,
    _materialize_inline_subtask_status as _materialize_inline_subtask_status,
    _persist_inline_subtask_status,
    _persist_review_artifact_override,
    _persist_review_artifact_override_in_coord as _persist_review_artifact_override_in_coord,
    _persist_review_feedback as _persist_review_feedback,
    _resolve_checkbox,
    _resolve_pipe_table,
    _resolve_wp_slug,
    _update_pipe_table_status as _update_pipe_table_status,
)

# WP06 (#2058): issue-matrix evaluation, review-verdict, the self-review
# fallback guard, the stale/stalled review status annotations, and the
# review-readiness validator live in the ``tasks_parsing_validation`` seam.
# Re-exported here (explicit ``as`` form where not referenced internally) so
# existing ``from ...agent.tasks import <name>`` call sites and the
# ``@patch("...agent.tasks.<name>")`` contracts keep working unchanged. The
# review-readiness validator is wrapped (not aliased) below so its
# ``tasks``-resident collaborators stay injectable from this namespace.
from specify_cli.cli.commands.agent.tasks_parsing_validation import (
    _VALID_VERDICTS as _VALID_VERDICTS,
    _apply_review_status_flags as _apply_review_status_flags,
    _get_latest_review_cycle_verdict,
    _issue_matrix_approval_blocker,
    _self_review_fallback_option_error,
    _validate_ready_for_review as _seam_validate_ready_for_review,
)

# WP04: dependency/cycle validation, lane-metadata helpers, and the
# finalize_tasks validation core live in the ``tasks_finalize_validation`` seam.
# The lane helpers are re-imported here so existing
# ``from ...agent.tasks import <name>`` call sites keep working.
from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    FrontmatterUpdatePlan,
    _lane_targets_for_emit,
    _read_transactional_wp_lane,
    _wp_lane_from_status_events,
    compute_wp_frontmatter_updates,
    detect_dependency_conflicts,
    detect_dependency_cycles,
    read_existing_frontmatter,
    validate_wp_coverage,
)

# WP03: the pure ``move_task`` transition decision core. ``move_task`` gathers
# facts (I/O) and delegates the decision to ``decide_transition``; the returned
# outcome DRIVES the emit/skip/refuse behaviour (the old inline decision block is
# deleted, not shadowed).
from specify_cli.cli.commands.agent.tasks_transition_core import (
    MoveTaskRequest,
    RefuseExit1,
    _effective_note_text,
    arbiter_persist_signal,
    build_transition_plan,
    decide_transition,
    override_persist_signal,
)

# WP04: the pure ``map_requirements`` FR↔WP mapping decision core. The command
# gathers the reads (spec ids, existing per-WP refs, tasks.md fallback) and
# delegates the decision to ``plan_mapping``; the returned plan DRIVES the write
# (``to_write``), the pre-write refusals (``offenders``), and the reported
# coverage (``unmapped_fr``) — the old inline mapping/validation block is deleted,
# not shadowed. The frontmatter WRITE + the post-write stale gate stay in the
# command shell at their original positions (partial-write-on-refusal timing).
from specify_cli.cli.commands.agent.tasks_mapping_core import (
    TRACKER_ONLY_MODE,
    MappingPlan,
    MappingRequest,
    plan_mapping,
)
from specify_cli.requirement_mapping import CoverageSummary

# WP05: the pure ``status`` compute/aggregation core. The command gathers the
# reads (WP frontmatter, reduced event snapshot, per-WP workspace, staleness) and
# delegates the aggregation to ``build_status_view``; the returned view DRIVES the
# kanban rollup (``lanes``), the population counts, the done/weighted percentages,
# the stale count, and the per-WP ``dependency_readiness`` — the old inline
# aggregation block is deleted, not shadowed. Rendering stays in the shell
# (WP07/WP09 migrate it to the Render port). ``build_stale_fallback_results`` is
# the pure git-staleness fallback the command's ``except`` arms invoke.
from specify_cli.cli.commands.agent.tasks_status_view import (
    StatusRequest,
    StatusView,
    build_stale_fallback_results,
    build_status_view,
)
from specify_cli.status import StatusSnapshot

# WP05 (#2058): dependent-gating / dependency-warning glue lives in the
# ``tasks_dependency_graph`` seam. Re-imported here so existing
# ``from ...agent.tasks import <name>`` call sites and ``monkeypatch.setattr``
# targets keep working. NOTE: the ``core.dependency_graph`` call sites used by
# ``validate_workflow`` deliberately stay in this module (no relocation, no cycle).
from specify_cli.cli.commands.agent.tasks_dependency_graph import (
    _behind_commits_touch_only_planning_artifacts,
    _check_dependent_warnings,
    compute_incomplete_dependents,
)

# WP06 (#2116): the move_task orchestrator consumes the WP02 capability ports —
# the coord READ authority (``FsReader``) and the coord WRITE authority's two
# disjoint capabilities (``commit_status`` over the transactional emitter /
# ``commit_artifact`` over the mission commit router). ``GuardCapability`` keys
# the status commit. See ``agent_tasks_ports`` for the stratification rationale.
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CommitStatusResult,
    MissionHandle,
    RealCoordCommitRouter,
    RealFsReader,
    RealGitOps,
    RealRender,
    TasksPorts,
)
from specify_cli.cli.commands.agent.tasks_transition_core import Emit, TransitionPlan
from specify_cli.task_utils import WorkPackage

# Re-exported lane helpers consumed by tests via
# ``from ...agent.tasks import <name>`` even though tasks.py uses them only
# indirectly; listed in ``__all__`` so the re-export is explicit (C-007).
__all__ = [
    "_behind_commits_touch_only_planning_artifacts",
    "_check_dependent_warnings",
    "_lane_targets_for_emit",
    "_wp_lane_from_status_events",
    "app",
    "compute_incomplete_dependents",
]

logger = logging.getLogger(__name__)
SPEC_MD_FILENAME = "spec.md"
UTC_SECOND_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _review_currency_check_branch(
    *,
    main_repo_root: Path,
    mission_slug: str,
    target_branch: str,
    workspace: object | None,
) -> str:
    context = getattr(workspace, "context", None)
    base_branch = getattr(context, "base_branch", None)
    if base_branch:
        return str(base_branch)

    try:
        # base-ref read under coord topology — coord kind preserves G-2
        # (write-surface-coherence WP02 / T031 site 3): review-currency compares
        # against the coordination BASE ref under coord topology. STATUS_STATE keeps
        # the coord ref; a primary kind would read the primary ref as the base and
        # corrupt the currency comparison.
        placement = resolve_placement_only(
            main_repo_root, mission_slug, kind=MissionArtifactKind.STATUS_STATE
        )
    except Exception as exc:  # noqa: BLE001 -- legacy fixtures keep target-branch fallback
        logger.debug("Could not resolve review currency placement: %s", exc)
        return target_branch

    # FR-005 / FR-001b: the coord-vs-primary decision reads the WP02 STORED
    # topology via the ONE canonical predicate, never a per-ref ``.kind``.
    if routes_through_coordination(resolve_topology(main_repo_root, mission_slug)):
        return placement.ref
    return target_branch


def _map_requirements_feature_dir(main_repo_root: Path, mission_slug: str) -> Path:
    """Resolve the WP ``tasks/`` read surface for ``map-requirements`` (#2064).

    Routes through ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` — the
    per-leg seam split (WP03 / FR-001 / C-001): the WP-frontmatter read always
    lands on the PRIMARY checkout regardless of topology (INV-5 symmetry), so a
    coord-topology mission no longer routes to the STATUS-only coord husk for this
    planning-artifact read.

    ``resolve_planning_read_dir`` delegates to the topology-blind
    :func:`primary_feature_dir_for_mission`, which never raises — preserving the
    user-facing contract that ``map-requirements`` surfaces its own
    ``"Mission directory not found: …"`` message via the caller's existence guard
    on the returned path (Risk #1 — unchanged user-facing behaviour).
    """
    # WP03 / FR-001 / C-001: tasks/ is WORK_PACKAGE_TASK (PRIMARY-partition).
    # The topology-blind primary_feature_dir_for_mission never raises, so the
    # caller's existence guard preserves the historical user-facing contract.
    return resolve_planning_read_dir(
        main_repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )


def _review_stall_threshold_minutes(repo_root: Path) -> int:
    """Read review.stall_threshold_minutes from .kittify/config.yaml."""
    config_file = repo_root / ".kittify" / "config.yaml"
    if not config_file.exists():
        return 30
    try:
        import yaml  # noqa: PLC0415

        config = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        value = config.get("review", {}).get("stall_threshold_minutes", 30)
        return int(value)
    except (AttributeError, OSError, TypeError, ValueError):
        return 30


def _get_hic_marker(
    agent_profile: str | None,
    repo_root: Path,
    *,
    repo: object | None = None,
) -> str:
    """Return a marker when the work package profile is a human-run sentinel."""
    if not agent_profile:
        return ""

    try:
        from doctrine.agent_profiles.repository import AgentProfileRepository

        profile_repo = repo
        if profile_repo is None:
            built_in_dir = repo_root / "src" / "doctrine" / "agent_profiles" / "built-in"
            profile_repo = AgentProfileRepository(built_in_dir=built_in_dir)

        profile = profile_repo.get(agent_profile)
        if profile and profile.sentinel:
            return "👤 "
    except Exception:
        return ""

    return ""


app = typer.Typer(name="tasks", help="Task workflow commands for AI agents", no_args_is_help=True)

console = Console()


# ---------------------------------------------------------------------------
# FR-015 / C-003 / C-004: review-handoff runtime-state deny-list
# ---------------------------------------------------------------------------
# Spec-kitty writes review-lock.json and other ephemeral runtime state under
# ``.spec-kitty/`` inside each worktree, and merge/status metadata under
# ``.kittify/`` at the repo root. These directories are git-ignored but do
# show up in ``git status --porcelain`` as untracked noise, which historically
# tripped the "uncommitted changes in worktree" guard in
# ``_validate_ready_for_review`` when an external reviewer (the review lock)
# had only just done its job (issue #589).
#
# C-003: this is a *fixed named list*, NOT a pattern match. Do not add
# entries here without explicit spec coverage; re-opening the door to pattern
# matching lets untracked source files silently slip past the guard.
# C-004: paths OUTSIDE this list still reach the blocking branch unchanged,
# so genuine uncommitted implementation work continues to block review handoff.
_RUNTIME_STATE_DENY_LIST: tuple[str, ...] = (".spec-kitty/", ".kittify/")


# ---------------------------------------------------------------------------
# Mission charter-e2e-827-followups-01KQAJA0 / C-006: dossier snapshot exclude
# ---------------------------------------------------------------------------
# The dossier snapshot at <feature_dir>/.kittify/dossiers/<mission>/snapshot-
# latest.json is a mutable derived artifact. Per the EXCLUDE ownership policy
# (single policy — see ``specify_cli.status.preflight``), it must be filtered
# from any preflight that bypasses ``.gitignore`` so the writer's update does
# not self-block the next ``move-task`` transition.
def _filter_runtime_state_paths(porcelain_output: str) -> str:
    """Strip lines whose path falls under spec-kitty's own runtime-state dirs.

    Input is the raw ``git status --porcelain`` output. Each line has the
    format ``XY path`` where ``XY`` is a two-character status code followed by
    a single space. A ``startswith`` check against the fixed deny-list is
    used intentionally (C-003): no regex, no glob expansion, no fuzzy match.

    Dossier ``snapshot-latest.json`` paths are also stripped here per the
    EXCLUDE ownership policy (C-006); the snapshot writer must never
    self-block a transition.

    Returns a newline-joined string with deny-listed entries removed. Lines
    whose path is OUTSIDE the deny list are preserved verbatim so the
    downstream guard still blocks on genuine drift (C-004).
    """
    kept: list[str] = []
    for line in porcelain_output.splitlines():
        if not line.strip():
            continue
        # git status --porcelain format: first 3 chars are "XY " status prefix.
        path_part = line[3:] if len(line) > 3 else line.strip()
        if any(path_part.startswith(prefix) for prefix in _RUNTIME_STATE_DENY_LIST):
            continue
        if _is_dossier_snapshot(path_part):
            continue
        kept.append(line)
    return "\n".join(kept)


def _emit_sparse_session_warning(repo_root: Path, command: str) -> None:
    """Emit the FR-010/FR-019 sparse-checkout session warning once per process.

    Called from every state-mutating tasks handler at command entry so
    reviewers and implementers discover they are operating inside a
    sparse-checkout worktree before they commit partial work. The underlying
    ``warn_if_sparse_once`` helper from WP02 is self-memoizing (first caller
    wins the ``command`` label) and swallows detection errors, so this
    wrapper is safe to call unconditionally and never crashes the command.
    """
    try:
        from specify_cli.git.sparse_checkout import warn_if_sparse_once

        warn_if_sparse_once(repo_root, command=command)
    except Exception as _exc:  # noqa: BLE001 - defensive; must never break CLI
        # FR-010 contract: detection failures must never break the CLI command
        # that invoked this hook. Log to the module logger at debug level so
        # the failure is still traceable without tripping the ``S110`` lint.
        logging.getLogger(__name__).debug(
            "sparse-checkout session warning failed for %s: %s",
            command,
            _exc,
        )


def _ensure_target_branch_checked_out(
    repo_root: Path,
    mission_slug: str,
    json_output: bool,
) -> tuple[Path, str]:
    """Resolve branch context without auto-checkout (respects user's current branch).

    Returns:
        (main_repo_root, current_branch)
    """
    from specify_cli.core.git_ops import get_current_branch, resolve_target_branch

    # Write path: keep main-repo-root resolution so canonical serialization
    # pins to the primary checkout regardless of where the operator stands.
    main_repo_root = get_main_repo_root(repo_root)

    # Check for detached HEAD using robust branch detection
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        raise RuntimeError("Detached HEAD — checkout a branch before continuing")

    # Resolve branch routing (unified logic, no auto-checkout)
    resolution = resolve_target_branch(mission_slug, main_repo_root, current_branch, respect_current=True)

    # Show consistent branch banner
    if not json_output:
        if not resolution.should_notify:
            console.print(f"[bold cyan]Branch:[/bold cyan] {current_branch} (target for this mission)")
        else:
            console.print(f"[bold yellow]Branch:[/bold yellow] on '{resolution.current}', mission targets '{resolution.target}'")

    # Return current branch (no checkout performed)
    return main_repo_root, resolution.current


def _find_mission_slug(
    explicit_mission: str | None = None,
    *,
    json_output: bool = False,
    repo_root: Path | None = None,
) -> str:
    """Require an explicit mission slug (no auto-detection).

    When repo_root is supplied the handle is resolved via the canonical
    mission resolver (resolve_mission_handle), which handles ambiguous
    numeric-prefix handles, mid8 prefixes, and full ULID forms.  The
    resolver calls sys.exit(2) on error so no try/except is needed.

    Args:
        explicit_mission: Mission slug provided via --mission.
        json_output: Propagate to resolver error rendering.
        repo_root: Repository root; if provided, enables canonical resolver.

    Returns:
        Mission slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If mission slug is not provided.
    """
    if not explicit_mission or not explicit_mission.strip():
        err = "--mission <slug> is required"
        if json_output:
            print(json.dumps({"error": err}))
        else:
            console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)

    raw_handle = explicit_mission.strip()
    if repo_root is not None:
        # Write path: keep main-repo-root resolution so canonical serialization
        # pins to the primary checkout regardless of where the operator stands.
        # Note: repo_root from locate_project_root() already resolves to the main
        # checkout; get_main_repo_root() here guards against caller passing a
        # worktree path directly.
        legacy_dir = candidate_feature_dir_for_mission(get_main_repo_root(repo_root), raw_handle)
        if legacy_dir.exists():
            # F-001: the candidate resolver canonicalizes mid8/ULID/numeric
            # handles, so the resolved directory's NAME — not the raw operator
            # handle — is the canonical mission slug downstream consumers need.
            return legacy_dir.name
        try:
            resolved = resolve_mission_handle(raw_handle, repo_root, json_mode=json_output)
            return resolved.mission_slug
        except (SystemExit, typer.Exit):
            if legacy_dir.exists():
                return legacy_dir.name
            raise

    return raw_handle


def _output_result(json_mode: bool, data: dict, success_message: str | None = None):
    """Output result in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        data: Data to output (used for JSON mode)
        success_message: Message to display in human mode
    """
    if json_mode:
        print(json.dumps(data))
    elif success_message:
        console.print(success_message)


def _output_error(json_mode: bool, error_message: str, diagnostic: dict | None = None):
    """Output error in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        error_message: Error message to display
    """
    if json_mode:
        print(json.dumps(diagnostic if diagnostic is not None else {"error": error_message}))
    else:
        console.print(f"[red]Error:[/red] {error_message}")


def _protected_branch_status_commit_error(branch: str, repo_root: Path, command: str) -> str | None:
    # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
    # config+hatch reads happen once; is_protected() is I/O-free.
    if not ProtectionPolicy.resolve(repo_root).is_protected(branch):
        return None
    return (
        f"Refusing to run `{command}` with auto-commit on protected branch "
        f"'{branch}' before mutating status files. Run status commit "
        "operations from an allowed coordination/lane branch, or rerun with "
        "--no-auto-commit when you intentionally want to handle the status "
        "artifact commit manually."
    )


def _coord_topology_active(repo_root: Path, mission_slug: str) -> bool:
    """Return True if the coordination worktree exists for this mission."""
    try:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.lanes.branch_naming import resolve_transaction_mid8
        # Authoritative topology resolver (FR-004/#1918): a coord-worktree lookup
        # needs the REAL mid8 to name its dir. With no declared mission_id/mid8 the
        # seam falls back to the embedded ``<slug>-<mid8>`` tail (genuine slug) and
        # returns "" only for a legacy/flattened mission with no coord topology —
        # exactly the historical mid8_from_slug behaviour for resolvable slugs.
        mid8 = resolve_transaction_mid8(
            mission_slug, mission_id=None, mid8=None, coordination_branch=None
        )
        path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
        return path.exists()
    except Exception:
        return False


def _skip_target_branch_commit(repo_root: Path, mission_slug: str, target_branch: str) -> bool:
    """Return True when the direct WP-file commit to a protected primary must be skipped.

    NOT a routing authority (write-surface-coherence WP02 / T032 / G-1): the
    commit DESTINATION for the WP file is owned solely by the kind authority
    (``resolve_placement_only(kind=WORK_PACKAGE_TASK)``). This flag only decides
    whether to SKIP the direct primary commit in the genuine protected-primary
    case — coord topology active AND the primary ``target_branch`` is protected —
    where committing directly to the protected ref is refused and the status
    transition committed to the coordination branch is authoritative. It selects
    no ref; it suppresses a commit that the protection policy would refuse anyway.
    """
    # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
    # config+hatch reads happen once; is_protected() is I/O-free.
    return (
        _coord_topology_active(repo_root, mission_slug)
        and ProtectionPolicy.resolve(repo_root).is_protected(target_branch)
    )


def _primary_bundle_status_artifacts(
    main_repo_root: Path, mission_slug: str, status_artifacts: list[Path]
) -> list[Path]:
    """Drop coord-owned status files from a PRIMARY-surface auto-commit bundle.

    #2155 (FR-002 / T010): the ``move_task`` auto-commit routes the WP file (a
    ``WORK_PACKAGE_TASK`` / primary-partition artifact) through
    ``commit_for_mission(kind=WORK_PACKAGE_TASK)``, which commits on the PRIMARY
    repo root. Under coordination topology the coord-owned status files
    (``status.events.jsonl`` / ``status.json``) resolved by
    :func:`_collect_status_artifacts` live UNDER ``.worktrees/`` (the coord
    worktree) and are ALREADY committed to the coordination branch by the
    transactional emitter (``emit_status_transition_transactional``). Staging
    those ``.worktrees/`` paths from the primary root trips the
    ``SafeCommitPathPolicyError`` guard (#1887), which ``commit_for_mission``
    folds into a ``status="error"`` result — leaving the working tree dirty and
    the WP file uncommitted (the surviving #2155 residual).

    The single canonical partition (``COORD_OWNED_STATUS_FILES``, the same set
    ``implement.py:_exclude_coord_owned`` keys on) excludes coord-owned status
    under coord topology only. On a flat/legacy mission the status files ARE
    canonical on PRIMARY, so they stay in the bundle (the never-divergent
    flat-topology behaviour the WP02 stored topology resolves transparently).
    """
    if not routes_through_coordination(resolve_topology(main_repo_root, mission_slug)):
        return status_artifacts
    from specify_cli.status import COORD_OWNED_STATUS_FILES

    return [p for p in status_artifacts if p.name not in COORD_OWNED_STATUS_FILES]


def _coord_status_events_path(repo_root: Path, mission_slug: str) -> Path | None:
    """Return coord-worktree status event path when coord topology is active."""
    try:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.lanes.branch_naming import mission_dir_name, resolve_transaction_mid8

        # Topology resolver (FR-004): resolve the on-disk mid8 from the embedded
        # ``<slug>-<mid8>`` tail; "" for a legacy/flattened mission (no coord dir).
        mid8 = resolve_transaction_mid8(
            mission_slug, mission_id=None, mid8=None, coordination_branch=None
        )
        if not mid8:
            return None
        # Delegate the idempotent ``<slug>-<mid8>`` compose to the seam so the
        # inline endswith-dedup (the #1949 reinvention WP09 bans) lives only in
        # lanes.branch_naming (FR-010).
        mission_dir = mission_dir_name(mission_slug, mid8=mid8)
        coord_root = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
        if not coord_root.exists():
            return None
        return candidate_feature_dir_for_mission(coord_root, mission_dir) / EVENTS_FILENAME
    except Exception:
        return None


def _status_event_result_fields(event: object | None) -> dict[str, str | None]:
    """Return JSON-safe status event fields for command output."""
    if event is None:
        return {"event_id": None, "to_lane": None}

    event_id = getattr(event, "event_id", None)
    if not isinstance(event_id, str):
        event_id = None

    to_lane = getattr(event, "to_lane", None)
    if to_lane is None:
        to_lane_value = None
    else:
        raw_value = getattr(to_lane, "value", to_lane)
        to_lane_value = raw_value if isinstance(raw_value, str) else str(raw_value)

    return {"event_id": event_id, "to_lane": to_lane_value}


def _mission_identity_payload(feature_dir: Path) -> dict[str, str]:
    identity = resolve_mission_identity(feature_dir)
    return {
        "mission_slug": identity.mission_slug,
        "mission_number": identity.mission_number,
        "mission_type": identity.mission_type,
    }


def _detect_reviewer_name() -> str:
    """Detect reviewer name from git config, with safe fallback."""
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _resolve_git_common_dir(main_repo_root: Path) -> Path:
    """Resolve absolute git common-dir for the repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=main_repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    raw_value = result.stdout.strip()
    if not raw_value:
        raise RuntimeError("Unable to resolve git common directory")
    common_dir = Path(raw_value)
    if not common_dir.is_absolute():
        common_dir = (main_repo_root / common_dir).resolve()
    return common_dir


def _check_unchecked_subtasks(repo_root: Path, mission_slug: str, wp_id: str, _force: bool) -> list[str]:
    """Check for unchecked subtasks in tasks.md for a given WP.

    Args:
        repo_root: Repository root path
        mission_slug: Feature slug (e.g., "010-lane-only-runtime")
        wp_id: Work package ID (e.g., "WP01")
        force: If True, only warn; if False, fail on unchecked tasks

    Returns:
        List of unchecked task IDs (empty if all checked or not found)

    Raises:
        typer.Exit: If unchecked tasks found and force=False
    """
    # Write path: keep main-repo-root resolution so canonical serialization
    # pins to the primary checkout regardless of where the operator stands.
    main_repo_root = get_main_repo_root(repo_root)
    # WP04 / FR-006: ``tasks.md`` is a TASKS_INDEX (primary-partition) artifact —
    # read it from PRIMARY (INV-5) so a coord-topology mission's stale ``-coord``
    # husk cannot shadow the real primary ``tasks.md`` (#2062 read-side close).
    from mission_runtime import MissionArtifactKind

    feature_dir = resolve_planning_read_dir(
        main_repo_root, mission_slug, kind=MissionArtifactKind.TASKS_INDEX
    )
    tasks_md = feature_dir / TASKS_MD_FILENAME

    if not tasks_md.exists():
        return []  # No tasks.md, can't check

    content = tasks_md.read_text(encoding="utf-8")

    # Find canonical subtasks for this WP. Only unchecked rows of the form
    # ``- [ ] T### <desc>`` count as blocking. Validation/procedure/checklist
    # command rows (e.g. ``- [ ] swift test``, ``- [ ] git status --short``),
    # prose, and anything inside fenced code blocks are intentionally ignored —
    # they are not work-package subtasks and must not block a lane transition.
    lines = content.split("\n")
    unchecked: list[str] = []
    in_wp_section = False
    in_code_fence = False

    # Canonical subtask row: ``- [ ] T001 ...``. A ``T`` id of at least three
    # digits is mandatory (``\d{3,}`` so ids past T999 still block).
    canonical_unchecked = re.compile(r"^-\s*\[\s*\]\s*(T\d{3,})\b")

    for line in lines:
        stripped = line.strip()

        # Toggle fenced-code-block state on ``` or ~~~ markers. Task-like lines
        # inside fenced code blocks (examples in implementation notes) must not
        # be treated as real subtasks.
        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            continue

        if in_code_fence:
            continue

        # Check if we entered this WP's section
        if re.search(rf"^#{{2,4}}[^#].*{wp_id}\b", line):
            in_wp_section = True
            continue

        # Check if we entered a different WP section
        if in_wp_section and re.search(r"^#{2,4}[^#].*WP\d{2}\b", line):
            break  # Left this WP's section

        # Look for unchecked canonical task rows in this WP's section
        if in_wp_section:
            unchecked_match = canonical_unchecked.match(stripped)
            if unchecked_match:
                unchecked.append(unchecked_match.group(1))

    return unchecked


def _apply_stale_status_fields(wp: dict, stale_result: object) -> None:
    """Populate canonical and deprecated stale fields from one source of truth."""
    stale_payload = stale_result.stale.to_dict()
    wp["stale"] = stale_payload
    wp["is_stale"] = stale_result.is_stale
    wp["minutes_since_commit"] = stale_payload["minutes_since_commit"]
    wp["worktree_exists"] = stale_result.worktree_exists


def _render_stale_status(stale_result: object | None) -> str | None:
    """Return a human-readable stale label for in-progress work packages."""
    if stale_result is None:
        return None

    if stale_result.stale.status == "not_applicable" and stale_result.stale.reason == "planning_artifact_repo_root_shared_workspace":
        return "stale: n/a (repo-root planning work)"

    if getattr(stale_result, "error", None):
        return "stale: unavailable"

    if stale_result.is_stale:
        mins = stale_result.minutes_since_commit
        return f"stale: {mins}m"

    return None


def _validate_ready_for_review(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    force: bool,
    target_lane: str = "for_review",
) -> tuple[bool, list[str]]:
    """Validate that WP is ready for review by checking for uncommitted changes.

    Thin wrapper over the WP06 seam
    (:func:`tasks_parsing_validation._validate_ready_for_review`). The
    ``tasks``-resident collaborators are passed in from this module's live
    globals so the existing ``@patch("...agent.tasks.<name>")`` contracts (e.g.
    ``get_main_repo_root``, ``get_mission_type``, ``get_feature_target_branch``,
    ``resolve_workspace_for_wp``, the git helpers, and ``console``) continue to
    apply unchanged. Behaviour, validation order, error strings, and the
    (bool, list[str]) return shape are preserved exactly.
    """
    return _seam_validate_ready_for_review(
        repo_root,
        mission_slug,
        wp_id,
        force,
        target_lane=target_lane,
        get_main_repo_root=get_main_repo_root,
        get_mission_type=get_mission_type,
        get_feature_target_branch=get_feature_target_branch,
        resolve_workspace_for_wp=resolve_workspace_for_wp,
        review_currency_check_branch=_review_currency_check_branch,
        behind_commits_touch_only_planning_artifacts=_behind_commits_touch_only_planning_artifacts,
        filter_runtime_state_paths=_filter_runtime_state_paths,
        list_wp_branch_specs_changes_for_guard=_list_wp_branch_specs_changes_for_guard,
        console=console,
    )


def _wp_branch_merged_into_target(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    target_branch: str,
) -> tuple[bool, str]:
    """Check whether a lane branch tip is reachable from the target branch.

    Returns:
        (is_merged, message)
    """
    workspace = resolve_workspace_for_wp(repo_root, mission_slug, wp_id)
    wp_branch = workspace.branch_name

    branch_exists = subprocess.run(
        ["git", "rev-parse", "--verify", wp_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if branch_exists.returncode != 0:
        return (
            False,
            (f"Cannot verify merge ancestry: branch '{wp_branch}' not found.\nEither merge and keep branch ref available, or provide --done-override-reason."),
        )

    merged_check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", wp_branch, target_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if merged_check.returncode == 0:
        return True, f"Merge ancestry verified: {wp_branch} is merged into {target_branch}."

    return (
        False,
        (
            f"Merge ancestry check failed: {wp_branch} is not merged into {target_branch}.\n"
            f"Merge first, or provide --done-override-reason to record a conscious exception."
        ),
    )


def _filter_by_planning_tip_content(
    worktree_path: Path, candidates: list[str], base_branch: str
) -> list[str]:
    """Drop candidates byte-identical to the planning-branch tip (FR-007 / #2274).

    Runs ``git diff <planning_tip> HEAD -- <path>`` for each candidate.  An
    empty diff means the file is byte-identical to the planning tip (e.g. after
    a planning-branch rebase that brought no content change) and must not be
    flagged as a lane-hygiene violation.  On any git failure the candidate is
    kept conservatively so the guard never silently loses signal.
    """
    planning_tip_result = subprocess.run(
        ["git", "rev-parse", base_branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if planning_tip_result.returncode != 0 or not planning_tip_result.stdout.strip():
        return candidates

    planning_tip = planning_tip_result.stdout.strip()
    files: list[str] = []
    for path in candidates:
        content_diff = subprocess.run(
            ["git", "diff", planning_tip, "HEAD", "--", path],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        # Non-empty diff or git error → genuinely diverges from planning tip; keep.
        if content_diff.returncode != 0 or content_diff.stdout.strip():
            files.append(path)
    return files


def _list_wp_branch_mission_specs_changes(worktree_path: Path, base_branch: str) -> list[str]:
    """Return kitty-specs/ files genuinely diverged from the planning-branch tip.

    Uses a two-pass strategy (FR-007 / #2274):

    1. Merge-base history diff: ``git diff --name-only <merge_base>..HEAD``
       identifies candidate paths touched on the lane branch.
    2. Content re-check: ``git diff <planning_tip> HEAD -- <path>`` filters out
       any candidate whose content is byte-identical to the planning-branch tip.

    This prevents false positives after a planning-branch rebase where the lane
    branch shares only an ancient merge-base but the file content matches.
    """
    merge_base_result = subprocess.run(
        ["git", "merge-base", "HEAD", base_branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if merge_base_result.returncode != 0:
        return []

    merge_base = merge_base_result.stdout.strip()
    if not merge_base:
        return []

    diff_result = subprocess.run(
        ["git", "diff", "--name-only", f"{merge_base}..HEAD", "--", f"{KITTY_SPECS_DIR}/"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if diff_result.returncode != 0:
        return []

    seen: set[str] = set()
    candidates: list[str] = []
    for raw in diff_result.stdout.splitlines():
        path = raw.strip()
        if not path or not path.startswith(f"{KITTY_SPECS_DIR}/"):
            continue
        if path in seen:
            continue
        seen.add(path)
        candidates.append(path)

    if not candidates:
        return []

    return _filter_by_planning_tip_content(worktree_path, candidates, base_branch)


globals()["_list_wp_branch_" + KITTY_SPECS_DIR.replace("-", "_") + "_changes"] = (
    _list_wp_branch_mission_specs_changes
)


def _list_wp_branch_specs_changes_for_guard(worktree_path: Path, base_branch: str) -> list[str]:
    patched_or_alias = globals()["_list_wp_branch_" + KITTY_SPECS_DIR.replace("-", "_") + "_changes"]
    return patched_or_alias(worktree_path=worktree_path, base_branch=base_branch)


def _detect_arbiter_override(
    feature_dir: Path,
    task_id: str,
    old_lane: Lane,
    target_canonical: str,
    force: bool,
) -> bool:
    """Return whether this move is an arbiter override (WP03 I/O for the core).

    A ``--force`` forward move from ``planned`` that follows a rejection event is
    an arbiter override. Detection reads the event log; the pure
    ``decide_transition`` core consumes the boolean result.
    """
    try:
        from specify_cli.review.arbiter import _is_arbiter_override
    except ImportError:
        return False
    return bool(
        _is_arbiter_override(feature_dir, task_id, old_lane, target_canonical, force)
    )


def _run_arbiter_override(
    *,
    feature_dir: Path,
    mission_slug: str,
    main_repo_root: Path,
    task_id: str,
    note_text: str | None,
    agent: str | None,
    json_output: bool,
) -> str | None:
    """Persist the arbiter decision and return the rejection's ``review_ref``.

    Executes the arbiter-override side effect once ``decide_transition`` has
    authorised it (``Emit.arbiter_forward``). Returns the derived ``review_ref``
    so the emit plan can link the forward event to the rejection it overrides.
    """
    try:
        from specify_cli.review.arbiter import (
            create_arbiter_decision,
            parse_category_from_note,
            persist_arbiter_decision,
        )
    except ImportError:
        return None

    _arb_events = read_events_transactional(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        repo_root=main_repo_root,
    )
    _arb_wp_events = [e for e in _arb_events if e.wp_id == task_id]
    _arb_latest = _arb_wp_events[-1] if _arb_wp_events else None
    _arb_review_ref = _arb_latest.review_ref if _arb_latest else None

    _arb_category, _arb_explanation = parse_category_from_note(note_text)
    _arb_actor = agent or "operator"
    arbiter_decision = create_arbiter_decision(
        arbiter_name=_arb_actor,
        category=_arb_category,
        explanation=_arb_explanation,
    )
    try:
        _arb_path = persist_arbiter_decision(
            feature_dir=feature_dir,
            wp_id=task_id,
            review_ref=_arb_review_ref,
            decision=arbiter_decision,
        )
        if not json_output:
            console.print(f"[yellow]Arbiter override recorded:[/yellow] [bold]{_arb_category}[/bold] — {_arb_explanation}")
            console.print(f"[dim]  Decision persisted: {_arb_path}[/dim]")
    except Exception as _arb_err:
        if not json_output:
            console.print(f"[dim]Warning: Could not persist arbiter decision: {_arb_err}[/dim]")

    return _arb_review_ref


# ===========================================================================
# WP06 (#2116): move_task thin orchestrator over the WP03 decision core and the
# WP02 capability ports. The Typer command declares the CLI surface and delegates
# to ``_do_move_task``; the orchestrator gathers facts (I/O), runs the pure
# ``decide_transition`` core, and executes the resulting ``Emit`` through the two
# coord WRITE capabilities (``commit_status`` for each lane hop, ``commit_artifact``
# for the primary WP-file commit) and the coord READ authority
# (``feature_write_dir`` resolves the FR-010 coord husk — NEVER a primary kind;
# see T027). The partial-write-on-refusal timing (override/arbiter persists at
# their OLD guard positions) and the coord skip-exit-0 arm are preserved verbatim.
# ===========================================================================


class _MoveTaskCoordRouter(RealCoordCommitRouter):
    """Coord WRITE router bound to *this module's* patchable symbols.

    Behaviour-identical to :class:`RealCoordCommitRouter`, but re-resolves
    ``emit_status_transition_transactional`` / ``commit_for_mission`` through the
    ``tasks`` module namespace so the established
    ``@patch("...agent.tasks.<symbol>")`` seams the move_task test-suite relies on
    keep intercepting after the WP06 port rewire (the Real adapter binds the
    ``agent_tasks_ports`` copies, which those module-scoped patches do not reach).
    """

    def commit_status(
        self, request: TransitionRequest, *, capability: GuardCapability
    ) -> CommitStatusResult:
        event = emit_status_transition_transactional(request, capability=capability)
        return CommitStatusResult(event=event, skipped=False)

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: MissionArtifactKind,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        result = commit_for_mission(
            mission.repo_root,
            mission.mission_slug,
            tuple(paths),
            message,
            policy,
            kind=kind,
        )
        return CommitArtifactResult(
            status=result.status,
            placement_ref=result.placement_ref,
            commit_hash=result.commit_hash,
            diagnostic=result.diagnostic,
        )


def _default_move_task_ports() -> TasksPorts:
    """Production port bundle for ``move_task`` (coord router bound to tasks.py)."""
    return TasksPorts(
        fs=RealFsReader(),
        coord=_MoveTaskCoordRouter(),
        git=RealGitOps(),
        render=RealRender(),
    )


class _MapReqCoordRouter(RealCoordCommitRouter):
    """Coord WRITE router for ``map_requirements``, bound to *this* module.

    Behaviour-identical to :class:`RealCoordCommitRouter.commit_artifact`, but (a)
    re-resolves ``commit_for_mission`` through the ``tasks`` module namespace so the
    established ``@patch("...agent.tasks.commit_for_mission")`` seam keeps
    intercepting after the WP07 port rewire, and (b) threads the resolved
    ``target_branch`` so the post-commit ff-advance still fires for a coord write
    (parity with the pre-rewire inline call at the original tasks.py:3257).
    """

    def __init__(self, target_branch: str | None) -> None:
        self._target_branch = target_branch

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: MissionArtifactKind,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        result = commit_for_mission(
            mission.repo_root,
            mission.mission_slug,
            tuple(paths),
            message,
            policy,
            kind=kind,
            target_branch=self._target_branch,
        )
        return CommitArtifactResult(
            status=result.status,
            placement_ref=result.placement_ref,
            commit_hash=result.commit_hash,
            diagnostic=result.diagnostic,
        )


def _default_map_requirements_ports(target_branch: str | None) -> TasksPorts:
    """Production port bundle for ``map_requirements`` (coord router bound to tasks.py)."""
    return TasksPorts(
        fs=RealFsReader(),
        coord=_MapReqCoordRouter(target_branch),
        git=RealGitOps(),
        render=RealRender(),
    )


class _StatusRender(RealRender):
    """Render adapter for ``status``: module ``console`` + ``indent=2`` JSON envelope.

    ``status``'s ``--json`` leg emits ``json.dumps(result, indent=2)`` (not the
    default-separators compact form the base :class:`RealRender` uses), so the
    envelope arm is overridden to preserve that byte-for-byte. Binding the module
    ``console`` (via ``super().__init__(console=console)`` at the call site) keeps
    the human render byte-identical AND keeps the ``@patch("...tasks.console.print")``
    seams intercepting. Scoped to ``status``'s own render sites (T031) — WP09 owns
    the broader render-seam sweep (incl. reconciling this indent divergence).
    """

    def json_envelope(self, payload: Mapping[str, object]) -> str:
        return json.dumps(payload, indent=2)


def _default_status_ports() -> TasksPorts:
    """Production port bundle for ``status`` (render bound to the module console)."""
    return TasksPorts(
        fs=RealFsReader(),
        coord=RealCoordCommitRouter(),
        git=RealGitOps(),
        render=_StatusRender(console=console),
    )


@dataclass
class _MoveTaskState:
    """Mutable orchestration state threaded through ``move_task``'s phases.

    The single-body command tracked ~30 loose locals across gather → decide →
    execute; the phase helpers exchange this one value object instead. Not frozen:
    each phase fills its own slice in the same order the original body did.
    """

    # --- raw command inputs ---
    task_id: str
    to: str
    mission: str | None
    agent: str | None
    assignee: str | None
    shell_pid: str | None
    note: str | None
    review_feedback_file: Path | None
    approval_ref: str | None
    reviewer: str | None
    self_review_fallback: bool
    intended_reviewer: str | None
    reviewer_failure_reason: str | None
    done_override_reason: str | None
    force: bool
    tracker_ref: list[str] | None
    skip_review_artifact_check: bool
    auto_commit: bool | None
    json_output: bool
    # --- phase A: resolved targets ---
    target_lane: Lane = Lane.PLANNED
    repo_root: Path = field(default_factory=Path)
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    mission_slug: str = ""
    tracker_ref_values: tuple[str, ...] = ()
    skip_target_branch_commit: bool = False
    resolved_auto_commit: bool = False
    feature_dir: Path = field(default_factory=Path)
    mt_feature_dir: Path = field(default_factory=Path)
    wp: WorkPackage | None = None
    old_lane: Lane = Lane.PLANNED
    current_agent: str | None = None
    # --- phase B: decision facts ---
    verdict_artifact_path: Path | None = None
    resolved_feedback_source: Path | None = None
    request: MoveTaskRequest | None = None
    # --- phase C: decision ---
    decision: Emit | None = None
    arb_review_ref: str | None = None
    # --- phase D: emit plan ---
    emit_plan: TransitionPlan | None = None
    evidence_dict: dict[str, Any] | None = None
    note_text: str | None = None
    actor: str = "user"
    canonical_lane: str | None = None
    review_feedback_pointer: str | None = None
    rejected_review_result: ReviewResult | None = None
    # --- phase E/F: emit + persist ---
    event: StatusEvent | None = None
    final_hop_actor: str | None = None


# --- phase A: resolve targets (I/O) -----------------------------------------


def _mt_warn_worktree_kitty_specs(st: _MoveTaskState) -> None:
    """Informational note when a worktree carries a stale ``kitty-specs/`` copy."""
    cwd = Path.cwd().resolve()
    if not (is_worktree_context(cwd) and not st.json_output and cwd != st.main_repo_root):
        return
    worktree_kitty = None
    current = cwd
    while current != current.parent and ".worktrees" in str(current):
        if (current / KITTY_SPECS_DIR).exists():
            worktree_kitty = current / KITTY_SPECS_DIR
            break
        current = current.parent
    if worktree_kitty and (worktree_kitty / st.mission_slug / "tasks").exists():
        console.print(
            f"[dim]Note: Using planning repo's kitty-specs/ on {st.target_branch} "
            "(worktree copy ignored)[/dim]"
        )


def _mt_resolve_targets(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Resolve roots/branch/feature-dir and load the WP + its canonical lane."""
    st.target_lane = ensure_lane(st.to)
    repo_root = locate_project_root()
    if repo_root is None:
        _output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root
    # FR-010 / FR-019: one-shot sparse-checkout warning before any read/mutate.
    _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks move-task")
    st.resolved_auto_commit = (
        get_auto_commit_default(repo_root) if st.auto_commit is None else st.auto_commit
    )
    st.mission_slug = _find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    st.skip_target_branch_commit = (
        _skip_target_branch_commit(st.main_repo_root, st.mission_slug, st.target_branch)
        if st.resolved_auto_commit
        else False
    )
    if st.resolved_auto_commit and not st.skip_target_branch_commit:
        protected_error = _protected_branch_status_commit_error(
            st.target_branch, st.main_repo_root, "spec-kitty agent tasks move-task"
        )
        if protected_error is not None:
            self_review_error = _self_review_fallback_option_error(
                enabled=st.self_review_fallback,
                target_lane=str(st.target_lane),
                force=st.force,
                intended_reviewer=st.intended_reviewer,
                failure_reason=st.reviewer_failure_reason,
            )
            if self_review_error is not None:
                _output_error(st.json_output, self_review_error)
                raise typer.Exit(1)
            _output_error(st.json_output, protected_error)
            raise typer.Exit(1)
    st.tracker_ref_values = tuple(
        t.strip() for t in (st.tracker_ref or []) if t and t.strip()
    )
    _mt_warn_worktree_kitty_specs(st)
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation.
    # WP06 FR-010 (T027): the shared coord-status dir STAYS on the coord husk.
    # ``feature_write_dir`` wraps ``resolve_feature_dir_for_mission`` (the kind-blind
    # coord-husk leg) — the SAME on-disk dir the pre-rewire body read; it feeds the
    # pre30 guard, the authoritative event-log lane read (``_read_transactional_wp_lane``),
    # and the coord override persist. It is NEVER repointed to a primary kind — that
    # would move the event-log read off the coord husk and reintroduce the split-brain
    # FR-010 closes.
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.mt_feature_dir = ports.coord.feature_write_dir(handle)
    try:
        check_pre30_layout(st.mt_feature_dir)
    except Pre30LayoutError as e:
        _output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    st.wp = locate_work_package(repo_root, st.mission_slug, st.task_id)
    # Lane is event-log-only; read from the canonical coord-husk event log.
    st.old_lane = _read_transactional_wp_lane(
        feature_dir=st.mt_feature_dir,
        mission_slug=st.mission_slug,
        wp_id=st.task_id,
        repo_root=st.main_repo_root,
    )
    st.current_agent = extract_scalar(st.wp.frontmatter, "agent")
    # Event-store write leg — the SAME coord husk as ``mt_feature_dir``.
    st.feature_dir = st.mt_feature_dir


# --- phase B: gather decision facts (I/O) -----------------------------------


def _mt_resolve_feedback(st: _MoveTaskState) -> tuple[str | None, bool, bool, str | None]:
    """Resolve the ``--review-feedback-file`` facts (+ planned-rollback content)."""
    if st.review_feedback_file is None:
        return None, False, False, None
    candidate = st.review_feedback_file.expanduser()
    candidate = (
        candidate.resolve()
        if candidate.is_absolute()
        else (Path.cwd() / candidate).resolve()
    )
    source_str = str(candidate)
    exists = candidate.exists()
    is_file = candidate.is_file()
    content: str | None = None
    if exists and is_file:
        st.resolved_feedback_source = candidate
        if st.target_lane == Lane.PLANNED:
            content = candidate.read_text(encoding="utf-8").strip()
    return source_str, exists, is_file, content


def _mt_build_request(
    st: _MoveTaskState,
    *,
    protected_error: str | None,
    review_verdict: str | None,
    review_artifact_name: str | None,
    feedback: tuple[str | None, bool, bool, str | None],
    unchecked_subtasks: tuple[str, ...],
    review_ready: bool,
    review_guidance: tuple[str, ...],
) -> MoveTaskRequest:
    """Assemble the pass-1 ``MoveTaskRequest`` (late facts default to skip-safe)."""
    feedback_source_str, feedback_exists, feedback_is_file, feedback_content = feedback
    return MoveTaskRequest(
        task_id=st.task_id,
        target_lane=str(st.target_lane),
        old_lane=str(st.old_lane),
        force=st.force,
        agent=st.agent,
        current_agent=st.current_agent,
        note=st.note,
        auto_commit=bool(st.resolved_auto_commit),
        target_branch=st.target_branch,
        skip_target_branch_commit=st.skip_target_branch_commit,
        tracker_ref_values=tuple(st.tracker_ref_values),
        assignee=st.assignee,
        shell_pid=st.shell_pid,
        self_review_fallback=st.self_review_fallback,
        intended_reviewer=st.intended_reviewer,
        reviewer_failure_reason=st.reviewer_failure_reason,
        protected_error=protected_error,
        review_verdict=review_verdict,
        review_artifact_name=review_artifact_name,
        skip_review_artifact_check=st.skip_review_artifact_check,
        feedback_provided=st.review_feedback_file is not None,
        feedback_source=feedback_source_str,
        feedback_exists=feedback_exists,
        feedback_is_file=feedback_is_file,
        feedback_content=feedback_content,
        unchecked_subtasks=unchecked_subtasks,
        review_ready=review_ready,
        review_guidance=review_guidance,
        done_execution_mode=None,
        done_merged=False,
        done_merge_msg="",
        done_override_reason=st.done_override_reason,
        issue_matrix_blocker=None,
        is_arbiter_override=False,
        effective_reviewer=None,
        effective_approval_ref=None,
    )


def _mt_gather_review_facts(st: _MoveTaskState) -> None:
    """Gather the early (guard-gating) facts and build the pass-1 request."""
    assert st.wp is not None
    protected_error: str | None = None
    if st.resolved_auto_commit and not st.skip_target_branch_commit:
        protected_error = _protected_branch_status_commit_error(
            st.target_branch, st.main_repo_root, "spec-kitty agent tasks move-task"
        )
    review_verdict: str | None = None
    review_artifact_name: str | None = None
    if st.target_lane in (Lane.APPROVED, Lane.DONE):
        _verdict_wp_dir = st.wp.path.parent / st.wp.path.stem
        review_verdict, st.verdict_artifact_path = _get_latest_review_cycle_verdict(
            _verdict_wp_dir
        )
        review_artifact_name = (
            st.verdict_artifact_path.name if st.verdict_artifact_path is not None else None
        )
    feedback = _mt_resolve_feedback(st)
    unchecked_subtasks: tuple[str, ...] = ()
    if st.target_lane in (Lane.FOR_REVIEW, Lane.APPROVED, Lane.DONE) and not st.force:
        unchecked_subtasks = tuple(
            _check_unchecked_subtasks(st.repo_root, st.mission_slug, st.task_id, st.force)
        )
    review_ready = True
    review_guidance: tuple[str, ...] = ()
    if st.target_lane in (Lane.FOR_REVIEW, Lane.APPROVED, Lane.DONE):
        is_valid, guidance = _validate_ready_for_review(
            st.repo_root,
            st.mission_slug,
            st.task_id,
            st.force,
            target_lane=str(st.target_lane),
        )
        review_ready = is_valid
        review_guidance = tuple(guidance)
    st.request = _mt_build_request(
        st,
        protected_error=protected_error,
        review_verdict=review_verdict,
        review_artifact_name=review_artifact_name,
        feedback=feedback,
        unchecked_subtasks=unchecked_subtasks,
        review_ready=review_ready,
        review_guidance=review_guidance,
    )


# --- phase C: two-pass decision + partial-write persists ---------------------


def _mt_fire_override_persist(st: _MoveTaskState) -> None:
    """OLD-timing review-artifact override (FR-004 partial-write-on-refusal).

    Fires before the guard sequence so a LATER guard's exit-1 refusal still leaves
    the override on disk — reproducing the un-refactored command's timing.
    """
    assert st.request is not None
    if not (override_persist_signal(st.request) and st.verdict_artifact_path is not None):
        return
    override_reason = st.note.strip() if isinstance(st.note, str) else ""
    _persist_review_artifact_override(
        st.verdict_artifact_path,
        repo_root=st.main_repo_root,
        wp_id=st.task_id,
        actor=st.agent or "operator",
        reason=override_reason,
    )
    _persist_review_artifact_override_in_coord(
        st.verdict_artifact_path,
        coord_feature_dir=st.mt_feature_dir,
        wp_id=st.task_id,
        actor=st.agent or "operator",
        reason=override_reason,
    )


def _mt_done_ancestry_facts(st: _MoveTaskState) -> tuple[str | None, bool, str]:
    """Late fact: done-transition execution mode + branch-merge ancestry."""
    if st.target_lane != Lane.DONE:
        return None, False, ""
    try:
        done_workspace = resolve_workspace_for_wp(
            st.main_repo_root, st.mission_slug, st.task_id
        )
        done_execution_mode: str | None = done_workspace.execution_mode
    except (ValueError, FileNotFoundError):
        done_execution_mode = "code_change"
    done_merged = False
    done_merge_msg = ""
    if done_execution_mode == "code_change":
        done_merged, done_merge_msg = _wp_branch_merged_into_target(
            repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            wp_id=st.task_id,
            target_branch=st.target_branch,
        )
    return done_execution_mode, done_merged, done_merge_msg


def _mt_issue_matrix_facts(st: _MoveTaskState) -> str | None:
    """Late fact: issue-matrix approval blocker.

    C-002: the canonicalizer fold + the blind primitive
    ``primary_feature_dir_for_mission`` stay co-located in the command module —
    NEVER routed through a port.
    """
    if st.target_lane not in (Lane.APPROVED, Lane.DONE):
        return None
    canonical_handle = _canonicalize_primary_read_handle(st.main_repo_root, st.mission_slug)
    return _issue_matrix_approval_blocker(
        st.feature_dir,
        target_lane=st.target_lane,
        primary_feature_dir=primary_feature_dir_for_mission(
            st.main_repo_root, canonical_handle
        ),
    )


def _mt_approval_facts(st: _MoveTaskState) -> tuple[str | None, str | None]:
    """Late fact: auto-detected reviewer + defaulted approval reference."""
    if st.target_lane not in (Lane.APPROVED, Lane.DONE):
        return None, None
    effective_reviewer = st.reviewer or _detect_reviewer_name()
    user_note = st.note.strip() if isinstance(st.note, str) else st.note
    effective_approval_ref = (
        st.approval_ref
        or (user_note if user_note else None)
        or f"auto-approval:{st.task_id}:{datetime.now(UTC).strftime('%Y%m%d')}"
    )
    return effective_reviewer, effective_approval_ref


def _mt_gather_late_facts(st: _MoveTaskState) -> None:
    """Gather pass-2 facts (allowed to raise) and rebuild the request."""
    assert st.request is not None
    done_execution_mode, done_merged, done_merge_msg = _mt_done_ancestry_facts(st)
    issue_matrix_blocker = _mt_issue_matrix_facts(st)
    effective_reviewer, effective_approval_ref = _mt_approval_facts(st)
    is_arbiter_override = _detect_arbiter_override(
        st.feature_dir, st.task_id, st.old_lane, resolve_lane_alias(st.target_lane), st.force
    )
    st.request = replace(
        st.request,
        done_execution_mode=done_execution_mode,
        done_merged=done_merged,
        done_merge_msg=done_merge_msg,
        issue_matrix_blocker=issue_matrix_blocker,
        is_arbiter_override=is_arbiter_override,
        effective_reviewer=effective_reviewer,
        effective_approval_ref=effective_approval_ref,
    )


def _mt_fire_arbiter_persist(st: _MoveTaskState) -> None:
    """OLD-timing arbiter-decision persist (FR-004 partial-write-on-refusal).

    Fires before pass 2 runs the issue-matrix guard, so an issue-matrix refusal
    still leaves the arbiter JSON on disk. ``arb_review_ref`` links the forward
    event to the rejection it overrides.
    """
    assert st.request is not None
    if not arbiter_persist_signal(st.request):
        return
    arb_note_text, _ = _effective_note_text(st.request)
    st.arb_review_ref = _run_arbiter_override(
        feature_dir=st.feature_dir,
        mission_slug=st.mission_slug,
        main_repo_root=st.main_repo_root,
        task_id=st.task_id,
        note_text=arb_note_text,
        agent=st.agent,
        json_output=st.json_output,
    )


def _mt_run_decision(st: _MoveTaskState) -> None:
    """Two-pass pure decision; RefuseExit1 short-circuits with the guard output."""
    assert st.request is not None
    # OLD-timing override persist BEFORE the guard sequence (pass 1).
    _mt_fire_override_persist(st)
    decision = decide_transition(st.request)
    if not isinstance(decision, RefuseExit1):
        # Early guards cleared — gather the late (possibly-raising) facts, fire the
        # OLD-timing arbiter persist ahead of the issue-matrix guard, then re-decide.
        _mt_gather_late_facts(st)
        _mt_fire_arbiter_persist(st)
        assert st.request is not None
        decision = decide_transition(st.request)
    if isinstance(decision, RefuseExit1):
        if not st.json_output:
            for warn_line in decision.console_warning:
                console.print(warn_line)
        _output_error(st.json_output, decision.error, diagnostic=decision.diagnostic)
        raise typer.Exit(1)
    st.decision = decision


# --- phase D: finalize emit plan --------------------------------------------


def _mt_finalize_plan(st: _MoveTaskState) -> None:
    """Execute the decision's authorised side-effect *inputs* and finalize the plan.

    The override/arbiter persists already fired at their OLD guard positions — they
    are NOT repeated here. Only the planned-rollback review cycle (which produces
    the feedback pointer) runs, then the plan is rebuilt when a side-effect produced
    a ``review_ref``.
    """
    assert st.decision is not None
    decision = st.decision
    st.emit_plan = decision.plan
    st.evidence_dict = decision.evidence_dict
    st.note_text = decision.note_text
    st.actor = st.agent or "user"
    st.canonical_lane = decision.plan.canonical_lane
    if decision.planned_rollback and st.resolved_feedback_source is not None:
        from specify_cli.review.cycle import create_rejected_review_cycle

        review_cycle = create_rejected_review_cycle(
            main_repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            wp_id=st.task_id,
            wp_slug=_resolve_wp_slug(st.main_repo_root, st.mission_slug, st.task_id),
            feedback_source=st.resolved_feedback_source,
            reviewer_agent=st.agent or "unknown",
        )
        st.review_feedback_pointer = review_cycle.pointer
        st.rejected_review_result = review_cycle.review_result
    if decision.done_override_note and not st.json_output:
        console.print(
            "[yellow]⚠️  Proceeding with done override; reason recorded in "
            "history/events.[/yellow]"
        )
    if decision.planned_rollback or decision.arbiter_forward:
        st.emit_plan = build_transition_plan(
            old_lane=str(st.old_lane),
            target_lane=str(st.target_lane),
            force=st.force,
            review_feedback_pointer=st.review_feedback_pointer,
            arb_review_ref=st.arb_review_ref,
            note_text=st.note_text,
        )


# --- phase E: emit the lane transition(s) via commit_status ------------------


def _mt_current_event_lane(st: _MoveTaskState) -> str:
    """The WP's current canonical lane (the emit chain's from-lane seed)."""
    current_event_lane: str | None = None
    for existing_event in reversed(
        read_events_transactional(
            feature_dir=st.feature_dir,
            mission_slug=st.mission_slug,
            repo_root=st.main_repo_root,
        )
    ):
        if existing_event.wp_id == st.task_id:
            current_event_lane = str(existing_event.to_lane)
            break
    if current_event_lane is None:
        # No canonical state — finalize-tasks must run first (#1589).
        from specify_cli.status import uninitialized_status_error

        raise RuntimeError(
            uninitialized_status_error(st.mission_slug, st.task_id, st.feature_dir)
        )
    return current_event_lane


def _mt_hop_review_result(
    st: _MoveTaskState,
    event: StatusEvent | None,
    current_event_lane: str,
    target: str,
    hop_actor: str,
) -> ReviewResult | None:
    """Auto-construct a ``ReviewResult`` when a hop leaves ``in_review``."""
    rejected = st.rejected_review_result
    in_review = (event is not None and event.to_lane == Lane.IN_REVIEW) or (
        event is None and current_event_lane == Lane.IN_REVIEW
    )
    if in_review and target == Lane.PLANNED and rejected is not None:
        return rejected
    if in_review and st.evidence_dict is not None:
        review_section = st.evidence_dict.get("review", {})
        return ReviewResult(
            reviewer=review_section.get("reviewer", hop_actor),
            verdict=review_section.get("verdict", Lane.APPROVED),
            reference=review_section.get("reference", f"auto-forward:{st.task_id}"),
        )
    return None


def _mt_hop_actor(
    st: _MoveTaskState, event: StatusEvent | None, current_event_lane: str, target: str
) -> str:
    """Resolve the actor for one emit hop (impl handoff preserves the WP agent)."""
    from_lane_for_hop = (
        event.to_lane if event is not None else resolve_lane_alias(current_event_lane)
    )
    return (
        st.agent
        or (
            st.current_agent
            if from_lane_for_hop == Lane.IN_PROGRESS and target == Lane.FOR_REVIEW
            else None
        )
        or "user"
    )


def _mt_emit_transitions(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Emit each lane hop through the coord WRITE ``commit_status`` capability."""
    assert st.emit_plan is not None
    emit_plan = st.emit_plan
    emit_force = emit_plan.emit_force
    emit_reason = emit_plan.emit_reason
    emit_review_ref = emit_plan.emit_review_ref
    current_event_lane = _mt_current_event_lane(st)
    event: StatusEvent | None = None
    final_hop_actor = st.actor
    for target in emit_plan.transition_targets:
        hop_actor = _mt_hop_actor(st, event, current_event_lane, target)
        hop_review_result = _mt_hop_review_result(
            st, event, current_event_lane, target, hop_actor
        )
        event = ports.coord.commit_status(
            TransitionRequest(
                feature_dir=st.feature_dir,
                mission_slug=st.mission_slug,
                wp_id=st.task_id,
                to_lane=target,
                actor=hop_actor,
                force=emit_force,
                reason=emit_reason,
                evidence=st.evidence_dict if target in (Lane.APPROVED, Lane.DONE) else None,
                review_ref=emit_review_ref,
                workspace_context=f"move-task:{st.main_repo_root}",
                subtasks_complete=(
                    True
                    if target in (Lane.FOR_REVIEW, Lane.APPROVED) and not emit_force
                    else None
                ),
                implementation_evidence_present=(
                    True
                    if target in (Lane.FOR_REVIEW, Lane.APPROVED) and not emit_force
                    else None
                ),
                repo_root=st.main_repo_root,
                review_result=hop_review_result,
            ),
            capability=GuardCapability.STANDARD,
        ).event
        final_hop_actor = hop_actor
        # review_ref only applies to the (first) rollback hop, never forward hops.
        emit_review_ref = None
    st.event = event
    st.final_hop_actor = final_hop_actor


# --- phase F: persist the WP file + primary commit via commit_artifact --------


def _mt_commit_wp_file(
    st: _MoveTaskState,
    ports: TasksPorts,
    updated_doc: str,
    agent_name: str,
    skip_target_commit: bool,
) -> None:
    """Auto-commit branch: write the WP file and route the primary commit.

    #2155 (FR-002 / T010): bundle ONLY primary-partition artifacts into the
    ``WORK_PACKAGE_TASK`` commit; the coord-owned status files are already committed
    to the coordination branch by the transactional emitter. A guard refusal folded
    into ``status="error"`` is surfaced, never swallowed.
    """
    assert st.wp is not None
    wp = st.wp
    spec_number = st.mission_slug.split("-")[0] if "-" in st.mission_slug else st.mission_slug
    commit_msg = f"chore: Move {st.task_id} to {st.target_lane} on spec {spec_number}"
    if agent_name != "unknown":
        commit_msg += f" [{agent_name}]"
    file_written = False
    try:
        actual_file_path = wp.path.resolve()
        router_result: CommitArtifactResult | None = None
        if skip_target_commit:
            if not st.json_output:
                console.print(
                    f"[dim]Note: WP file update not committed to '{st.target_branch}' "
                    "(protected branch, coord topology active). "
                    "The status transition is committed to the coordination branch "
                    "and is authoritative.[/dim]"
                )
            commit_success = False
        else:
            write_text_within_directory(
                wp.path, updated_doc, root=st.main_repo_root, encoding="utf-8"
            )
            file_written = True
            status_artifacts = _primary_bundle_status_artifacts(
                st.main_repo_root,
                st.mission_slug,
                _collect_status_artifacts(st.feature_dir),
            )
            # The WP file is WORK_PACKAGE_TASK (primary): route the commit through
            # the coord WRITE ``commit_artifact`` capability (over the ONE canonical
            # ``commit_for_mission`` entry point). The router owns placement
            # resolution AND the protected-primary refusal.
            router_result = ports.coord.commit_artifact(
                MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug),
                (actual_file_path, *status_artifacts),
                commit_msg,
                kind=MissionArtifactKind.WORK_PACKAGE_TASK,
                policy=ProtectionPolicy.resolve(st.main_repo_root),
            )
            commit_success = router_result.status == "committed"
        if commit_success:
            if not st.json_output:
                console.print(
                    f"[cyan]→ Committed status change to {st.target_branch} branch[/cyan]"
                )
        elif not skip_target_commit and router_result is not None:
            # #2155: do NOT swallow a router error as a soft "Failed to auto-commit".
            diagnostic = router_result.diagnostic
            detail = f": {diagnostic}" if diagnostic else ""
            if not st.json_output:
                console.print(
                    f"[yellow]Warning:[/yellow] WP-file auto-commit "
                    f"did not land ({router_result.status}){detail}"
                )
    except SafeCommitPathPolicyError:
        # #2155: a wrong-surface guard refusal is a real defect — re-raise, never hide.
        if not file_written:
            write_text_within_directory(
                wp.path, updated_doc, root=st.main_repo_root, encoding="utf-8"
            )
        raise
    except Exception as e:
        if not file_written:
            write_text_within_directory(
                wp.path, updated_doc, root=st.main_repo_root, encoding="utf-8"
            )
        if not st.json_output:
            console.print(f"[yellow]Warning:[/yellow] Auto-commit skipped: {e}")


def _mt_persist_tracker_refs(st: _MoveTaskState, skip_target_commit: bool) -> None:
    """T040 / FR-011: persist ``--tracker-ref`` values into the WP frontmatter."""
    assert st.wp is not None
    if not (st.tracker_ref_values and not skip_target_commit):
        return
    try:
        from specify_cli.frontmatter import write_frontmatter as _write_fm
        from specify_cli.status import read_wp_frontmatter as _read_wp_fm

        wp_meta, body = _read_wp_fm(st.wp.path)
        existing = list(wp_meta.tracker_refs or [])
        merged = sorted(set(existing) | set(st.tracker_ref_values))
        if merged != existing:
            updated = wp_meta.update(tracker_refs=merged)
            _write_fm(st.wp.path, updated.model_dump(exclude_none=True), body)
    except Exception as _tr_exc:  # pragma: no cover - defensive
        if not st.json_output:
            console.print(
                f"[yellow]Warning:[/yellow] Failed to persist --tracker-ref: {_tr_exc}"
            )


def _mt_persist_wp_file(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Apply operational frontmatter + history, then write/commit the WP file."""
    assert st.wp is not None and st.decision is not None
    wp = st.wp
    wp_content = wp.path.read_text(encoding="utf-8-sig")
    updated_front, updated_body, updated_padding = split_frontmatter(wp_content)
    if st.assignee:
        updated_front = set_scalar(updated_front, "assignee", st.assignee)
    if st.agent:
        updated_front = set_scalar(updated_front, "agent", st.agent)
    if st.shell_pid:
        updated_front = set_scalar(updated_front, "shell_pid", st.shell_pid)
    timestamp = datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)
    agent_name = st.final_hop_actor or "unknown"
    shell_pid_val = st.shell_pid or extract_scalar(updated_front, "shell_pid") or ""
    note_text = st.note_text or f"Moved to {st.target_lane}"
    shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
    history_entry = f"- {timestamp} – {agent_name} – {shell_part}{note_text}"
    updated_body = append_activity_log(updated_body, history_entry)
    updated_doc = build_document(updated_front, updated_body, updated_padding)
    # WP03: the primary-commit skip is DRIVEN by the core decision, not the raw fact.
    skip_target_commit = st.decision.skip_primary
    if st.resolved_auto_commit:
        _mt_commit_wp_file(st, ports, updated_doc, agent_name, skip_target_commit)
    else:
        write_text_within_directory(
            wp.path, updated_doc, root=st.main_repo_root, encoding="utf-8"
        )
    _mt_persist_tracker_refs(st, skip_target_commit)


# --- phase G/H: review-lock release + result output --------------------------


def _mt_release_review_lock(st: _MoveTaskState) -> None:
    """FR-017 / FR-018: release the review lock when review terminates.

    Placed AFTER the lane-transition commit so a failed release never rolls back
    the recorded transition; failures are logged, never fatal.
    """
    release_from = (Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.IN_PROGRESS)
    release_to = (Lane.APPROVED, Lane.PLANNED)
    if not (st.old_lane in release_from and st.target_lane in release_to):
        return
    try:
        from specify_cli.review.lock import ReviewLock

        lock_workspace = resolve_workspace_for_wp(
            st.main_repo_root, st.mission_slug, st.task_id
        )
        ReviewLock.release(Path(lock_workspace.worktree_path))
    except Exception as _release_exc:  # pragma: no cover - defensive
        logging.getLogger(__name__).warning(
            "Review lock release failed for %s in %s: %s",
            st.task_id,
            st.mission_slug,
            _release_exc,
        )


def _mt_execute(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Emit the transition(s) + persist the WP file under the status lock."""
    with feature_status_lock(st.main_repo_root, st.mission_slug):
        _mt_emit_transitions(st, ports)
        if st.self_review_fallback:
            from specify_cli.status import emit_reviewer_self_approval

            emit_reviewer_self_approval(
                st.feature_dir,
                mission_slug=st.mission_slug,
                wp_id=st.task_id,
                implementing_actor=st.final_hop_actor,
                intended_reviewer=(st.intended_reviewer or "").strip(),
                failure_reason=(st.reviewer_failure_reason or "").strip(),
                fallback_approved=True,
            )
        _mt_persist_wp_file(st, ports)
    _mt_release_review_lock(st)


def _mt_output(st: _MoveTaskState) -> None:
    """Emit the success envelope + dependent-WP warnings (coord skip arm aware)."""
    assert st.decision is not None and st.wp is not None
    event_fields = _status_event_result_fields(st.event)
    # WP03: the coord skip arm's polymorphic ``--json`` envelope is driven by the
    # core decision (``Emit.skip_primary``), not the raw fact.
    status_events_path = (
        _coord_status_events_path(st.main_repo_root, st.mission_slug)
        if st.decision.skip_primary
        else None
    )
    result: dict[str, object] = {
        "result": "success",
        "task_id": st.task_id,
        "old_lane": st.old_lane,
        "new_lane": st.target_lane,
        "path": str(st.wp.path),
        "event_id": event_fields["event_id"],
        "work_package_id": st.task_id,
        "to_lane": event_fields["to_lane"] or st.canonical_lane,
        "status_events_path": str(status_events_path or (st.feature_dir / EVENTS_FILENAME)),
    }
    if st.decision.skip_primary:
        result["wp_file_update"] = "skipped"
        result["wp_file_update_reason"] = (
            "protected branch with coordination topology; status event "
            "is authoritative on the coordination branch"
        )
        if st.agent:
            result["frontmatter_fields_skipped"] = ["agent"]
    if st.review_feedback_pointer is not None:
        result["review_feedback"] = st.review_feedback_pointer
    _output_result(
        st.json_output,
        result,
        f"[green]✓[/green] Moved {st.task_id} from {st.old_lane} to {st.target_lane}",
    )
    # Check for dependent WP warnings when moving to for_review (T083).
    _check_dependent_warnings(
        st.repo_root, st.mission_slug, st.task_id, st.target_lane, st.json_output
    )


def _do_move_task(
    task_id: str,
    to: str,
    mission: str | None,
    agent: str | None,
    assignee: str | None,
    shell_pid: str | None,
    note: str | None,
    review_feedback_file: Path | None,
    approval_ref: str | None,
    reviewer: str | None,
    self_review_fallback: bool,
    intended_reviewer: str | None,
    reviewer_failure_reason: str | None,
    done_override_reason: str | None,
    force: bool,
    tracker_ref: list[str] | None,
    skip_review_artifact_check: bool,
    auto_commit: bool | None,
    json_output: bool,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``move-task`` over the WP03 core + WP02 ports (C-005 seam).

    ``ports=None`` builds the production bundle (coord router bound to this
    module's patchable symbols). Tests inject a Fake bundle to observe the executed
    side-effects (T029). The phase helpers run in the SAME order as the original
    single body: resolve → gather → decide → finalize → execute → output.
    """
    ports = ports or _default_move_task_ports()
    st = _MoveTaskState(
        task_id=task_id,
        to=to,
        mission=mission,
        agent=agent,
        assignee=assignee,
        shell_pid=shell_pid,
        note=note,
        review_feedback_file=review_feedback_file,
        approval_ref=approval_ref,
        reviewer=reviewer,
        self_review_fallback=self_review_fallback,
        intended_reviewer=intended_reviewer,
        reviewer_failure_reason=reviewer_failure_reason,
        done_override_reason=done_override_reason,
        force=force,
        tracker_ref=tracker_ref,
        skip_review_artifact_check=skip_review_artifact_check,
        auto_commit=auto_commit,
        json_output=json_output,
    )
    try:
        _mt_resolve_targets(st, ports)
        _mt_gather_review_facts(st)
        _mt_run_decision(st)
        _mt_finalize_plan(st)
        _mt_execute(st, ports)
        _mt_output(st)
    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016).
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                wp_id=task_id,
                stack_trace=traceback.format_exc(),
                agent_id=agent,
            )
        diagnostic = e.to_diagnostic() if isinstance(e, EventPersistenceError) else None
        if diagnostic is not None and st.canonical_lane is not None:
            diagnostic["failed_event_to_lane"] = diagnostic.get("to_lane")
            diagnostic["to_lane"] = st.canonical_lane
            diagnostic["requested_lane"] = st.canonical_lane
        _output_error(json_output, str(e), diagnostic=diagnostic)
        raise typer.Exit(1) from None


@app.command(name="move-task")
def move_task(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    to: Annotated[str, typer.Option("--to", help="Target lane (planned/doing/for_review/approved/done)")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,
    agent: Annotated[str | None, typer.Option("--agent", help="Agent name")] = None,
    assignee: Annotated[str | None, typer.Option("--assignee", help="Assignee name (sets assignee when moving to doing)")] = None,
    shell_pid: Annotated[str | None, typer.Option("--shell-pid", help="Shell PID")] = None,
    note: Annotated[str | None, typer.Option("--note", help="History note")] = None,
    review_feedback_file: Annotated[
        Path | None, typer.Option("--review-feedback-file", help="Path to review feedback file (required for --to planned, including with --force)")
    ] = None,
    approval_ref: Annotated[str | None, typer.Option("--approval-ref", help="Approval reference for approval/done transitions (e.g., PR#42)")] = None,
    reviewer: Annotated[str | None, typer.Option("--reviewer", help="Reviewer name (auto-detected from git if omitted)")] = None,
    self_review_fallback: Annotated[
        bool,
        typer.Option(
            "--self-review-fallback",
            help="Record that approval is a self-review fallback after the intended reviewer failed.",
        ),
    ] = False,
    intended_reviewer: Annotated[
        str | None,
        typer.Option("--intended-reviewer", help="Reviewer that should have reviewed this WP before fallback."),
    ] = None,
    reviewer_failure_reason: Annotated[
        str | None,
        typer.Option("--reviewer-failure-reason", help="Reason the intended reviewer failed."),
    ] = None,
    done_override_reason: Annotated[
        str | None,
        typer.Option("--done-override-reason", help="Required when --to done and merge ancestry cannot be verified; recorded in history/event reason"),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Force move even with unchecked subtasks (does not bypass planned rollback feedback requirement)")] = False,
    tracker_ref: Annotated[
        list[str] | None,
        typer.Option(
            "--tracker-ref",
            help=(
                "External tracker reference (e.g., '#1298' or 'JIRA-123'). "
                "Repeatable; appended to the WP frontmatter tracker_refs."
            ),
        ),
    ] = None,
    skip_review_artifact_check: Annotated[
        bool,
        typer.Option(
            "--skip-review-artifact-check",
            help="Override a rejected latest review artifact when arbiter-approving; requires --note and records override evidence.",
        ),
    ] = False,
    auto_commit: Annotated[
        bool | None, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit WP file changes to target branch (default: from project config)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Move task between lanes (planned → doing → for_review → approved → done).

    Examples:
        spec-kitty agent tasks move-task WP01 --to doing --assignee claude --json
        spec-kitty agent tasks move-task WP02 --to for_review --agent claude --shell-pid $$
        spec-kitty agent tasks move-task WP03 --to approved --note "Review passed"
        spec-kitty agent tasks move-task WP03 --to done --done-override-reason "Branch deleted after hotfix merge"
        spec-kitty agent tasks move-task WP03 --to planned --review-feedback-file feedback.md
    """
    # WP06 (#2116): thin orchestrator. The Typer command declares the CLI surface
    # (WP01 golden byte-identity) and delegates to ``_do_move_task``, which runs the
    # WP03 decision core and executes it through the WP02 coord READ/WRITE ports.
    _do_move_task(
        task_id=task_id,
        to=to,
        mission=mission,
        agent=agent,
        assignee=assignee,
        shell_pid=shell_pid,
        note=note,
        review_feedback_file=review_feedback_file,
        approval_ref=approval_ref,
        reviewer=reviewer,
        self_review_fallback=self_review_fallback,
        intended_reviewer=intended_reviewer,
        reviewer_failure_reason=reviewer_failure_reason,
        done_override_reason=done_override_reason,
        force=force,
        tracker_ref=tracker_ref,
        skip_review_artifact_check=skip_review_artifact_check,
        auto_commit=auto_commit,
        json_output=json_output,
    )



def _resolve_inline_subtasks(
    task_id: str,
    tasks_content: str,
    status: str,
    feature_dir: Path,
) -> TaskIdResult | None:
    """
    Search tasks_content for 'Subtasks: T001, T002' lines containing task_id.

    Inline references are discovery hints only; this resolver reports updated
    only after materializing a durable checkbox row in tasks.md.
    """
    normalized_task_id = task_id.upper()
    for match in _INLINE_SUBTASKS_RE.finditer(tasks_content):
        ids = [value.strip().upper() for value in match.group("ids").split(",")]
        if normalized_task_id in ids:
            persisted = _persist_inline_subtask_status(task_id, status, feature_dir, tasks_content)
            if persisted:
                return TaskIdResult(
                    id=task_id,
                    outcome=TaskIdResolutionOutcome.UPDATED,
                    format=TaskIdResolutionFormat.INLINE_SUBTASKS,
                    message=f"Persisted status for inline Subtasks reference {task_id} as {status}.",
                )
            return TaskIdResult(
                id=task_id,
                outcome=TaskIdResolutionOutcome.NOT_FOUND,
                format=TaskIdResolutionFormat.INLINE_SUBTASKS,
                message=(
                    f"{task_id} appears only in an inline Subtasks reference. "
                    "Inline references are not durable status storage; materialize "
                    "a checkbox row or append a canonical status event before "
                    "reporting updated."
                ),
            )
    return None


def _mark_status_json_payload(results: list[TaskIdResult]) -> dict[str, object]:
    """Return the contracted mark-status --json payload."""
    summary = {
        "updated": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.UPDATED),
        "already_satisfied": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.ALREADY_SATISFIED),
        "not_found": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.NOT_FOUND),
    }
    return {
        "results": [
            {
                "id": result.id,
                "outcome": result.outcome.value,
                "format": result.format.value if result.format else None,
                "message": result.message,
            }
            for result in results
        ],
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# mark-status — coreless orchestrator (WP08 / FR-007)
# ---------------------------------------------------------------------------
# ``mark_status`` carries NO transition decision core: it resolves task IDs to
# durable rows, writes ``tasks.md``, and commits. It is thinned via the WP02
# capability ports (``FsReader`` read authority + ``commit_artifact`` write
# capability) and the existing resolver helpers — NOT by borrowing ``move_task``'s
# transition core (the deferred #2300 unification). The refuse-exit-1-on-protected
# behaviour (T005, the divergence from ``move_task``'s skip) is preserved exactly.


@dataclass
class _MarkStatusState:
    """Mutable orchestration state threaded through ``mark_status``'s phases.

    The single-body command tracked ~15 loose locals across validate → resolve →
    apply → history → output; the phase helpers exchange this one value object
    instead. Not frozen: each phase fills its own slice in the SAME order the
    original body did, so the ``tasks.md`` write still precedes the auto-commit.
    """

    # --- raw command inputs ---
    task_ids: list[str]
    status: str
    mission: str | None
    auto_commit: bool | None
    json_output: bool
    # --- phase A/B: resolved context ---
    repo_root: Path = field(default_factory=Path)
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    mission_slug: str = ""
    resolved_auto_commit: bool = False
    feature_dir: Path = field(default_factory=Path)
    tasks_md: Path = field(default_factory=Path)
    # --- phase C: apply results ---
    results: list[TaskIdResult] = field(default_factory=list)
    updated_tasks: list[str] = field(default_factory=list)
    not_found_tasks: list[str] = field(default_factory=list)
    resolved_tasks: list[str] = field(default_factory=list)
    artifact_mutated: bool = False


class _MarkStatusCoordRouter(RealCoordCommitRouter):
    """Coord WRITE router for ``mark_status``, bound to *this* module.

    Behaviour-identical to :meth:`RealCoordCommitRouter.commit_artifact`, but
    re-resolves ``commit_for_mission`` through the ``tasks`` module namespace so the
    established ``@patch("...agent.tasks.commit_for_mission")`` seam keeps
    intercepting after the WP08 port rewire. ``mark_status`` commits the
    ``TASKS_INDEX`` artifact WITHOUT a threaded ``target_branch`` (byte-parity with
    the pre-rewire inline ``commit_for_mission`` call), so this override — unlike
    ``_MapReqCoordRouter`` — does NOT thread one.
    """

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: MissionArtifactKind,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        result = commit_for_mission(
            mission.repo_root,
            mission.mission_slug,
            tuple(paths),
            message,
            policy,
            kind=kind,
        )
        return CommitArtifactResult(
            status=result.status,
            placement_ref=result.placement_ref,
            commit_hash=result.commit_hash,
            diagnostic=result.diagnostic,
        )


def _default_mark_status_ports() -> TasksPorts:
    """Production port bundle for ``mark_status`` (coord router bound to tasks.py)."""
    return TasksPorts(
        fs=RealFsReader(),
        coord=_MarkStatusCoordRouter(),
        git=RealGitOps(),
        render=RealRender(),
    )


def _ms_validate_inputs(st: _MarkStatusState) -> None:
    """Phase A: validate ``--status`` + non-empty task IDs, then normalize IDs."""
    if st.status not in ("done", "pending"):
        _output_error(st.json_output, f"Invalid status '{st.status}'. Must be 'done' or 'pending'.")
        raise typer.Exit(1)
    if not st.task_ids:
        _output_error(st.json_output, "At least one task ID is required")
        raise typer.Exit(1)
    # WP04/T022 (FR-017): accept both bare and mission-qualified task IDs
    # (``T001`` or ``<mission_slug>/T001`` / ``<mission_slug>:T001``). Normalize to
    # bare task IDs before validation. A garbage ID surfaces as "no task IDs found
    # in tasks.md" downstream — preserving the structured-error contract.
    st.task_ids = [_normalize_task_id_input(tid) for tid in st.task_ids]


def _ms_resolve_context(st: _MarkStatusState) -> None:
    """Phase B(i): repo/branch/auto-commit + the protected-branch refuse-exit-1 gate.

    The protected-branch guard fires unconditionally under ``auto_commit`` — it does
    NOT consult ``_skip_target_branch_commit``, so on a coord + protected-primary
    tree ``mark_status`` REFUSES (exit 1) where ``move_task`` SKIPS (exit 0). That
    divergence is deliberate (T005 / deferred #2300) and preserved here.
    """
    repo_root = locate_project_root()
    if repo_root is None:
        _output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root
    # FR-010 / FR-019: one-shot sparse-checkout session warning.
    _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks mark-status")
    st.resolved_auto_commit = (
        get_auto_commit_default(repo_root) if st.auto_commit is None else st.auto_commit
    )
    st.mission_slug = _find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    if st.resolved_auto_commit:
        protected_error = _protected_branch_status_commit_error(
            st.target_branch,
            st.main_repo_root,
            "spec-kitty agent tasks mark-status",
        )
        if protected_error is not None:
            _output_error(st.json_output, protected_error)
            raise typer.Exit(1)


def _ms_resolve_read_dir(st: _MarkStatusState, ports: TasksPorts) -> None:
    """Phase B(ii): resolve the TASKS_INDEX write surface (#2154) + pre30 guard.

    #2154 (FR-001 / T008): ``tasks.md`` is a TASKS_INDEX (primary-partition)
    artifact — resolve the WRITE leg through the SAME kind-aware authority the
    validation read and the commit leg use (now the ``FsReader`` port), so the
    subtask write lands on the PRIMARY surface a coord-topology mission reads back
    from. The kind-blind ``resolve_feature_dir_for_mission`` returns the ``-coord``
    husk under coord topology, so the write and the validation read would diverge.
    """
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.feature_dir = ports.fs.planning_read_dir(handle, kind=MissionArtifactKind.TASKS_INDEX)
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation
    try:
        check_pre30_layout(st.feature_dir)
    except Pre30LayoutError as e:
        _output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    st.tasks_md = st.feature_dir / TASKS_MD_FILENAME


def _ms_report_none_resolved(st: _MarkStatusState) -> None:
    """Emit the contracted 'no task IDs resolved' error and exit 1."""
    if st.json_output:
        print(json.dumps(_mark_status_json_payload(st.results)))
    elif any(result.format == TaskIdResolutionFormat.WP_ID for result in st.results):
        detail = "; ".join(result.message for result in st.results if result.message)
        _output_error(st.json_output, detail)
    else:
        _output_error(st.json_output, f"No task IDs found in tasks.md: {', '.join(st.not_found_tasks)}")
    raise typer.Exit(1)


def _ms_commit(st: _MarkStatusState, ports: TasksPorts) -> None:
    """Auto-commit the ``tasks.md`` mutation through the coord ``commit_artifact`` port.

    ``tasks.md`` is TASKS_INDEX (primary): route the commit through the coord WRITE
    ``commit_artifact`` capability (over the canonical ``commit_for_mission`` entry
    point). The router owns placement resolution AND the protected-primary refusal.
    """
    # Extract spec number from mission_slug (e.g., "014" from "014-feature-name").
    spec_number = st.mission_slug.split("-")[0] if "-" in st.mission_slug else st.mission_slug
    if len(st.updated_tasks) == 1:
        commit_msg = f"chore: Mark {st.updated_tasks[0]} as {st.status} on spec {spec_number}"
    else:
        commit_msg = f"chore: Mark {len(st.updated_tasks)} subtasks as {st.status} on spec {spec_number}"
    try:
        actual_tasks_path = st.tasks_md.resolve()
        router_result = ports.coord.commit_artifact(
            MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug),
            (actual_tasks_path,),
            commit_msg,
            kind=MissionArtifactKind.TASKS_INDEX,
            policy=ProtectionPolicy.resolve(st.main_repo_root),
        )
        if router_result.status == "committed":
            if not st.json_output:
                console.print(f"[cyan]→ Committed subtask changes to {st.target_branch} branch[/cyan]")
        elif not st.json_output:
            console.print("[yellow]Warning:[/yellow] Failed to auto-commit subtask changes")
    except Exception as e:
        if not st.json_output:
            console.print(f"[yellow]Warning:[/yellow] Auto-commit exception: {e}")


def _ms_apply_updates(st: _MarkStatusState, ports: TasksPorts) -> None:
    """Phase C: resolve each task ID to a durable row, write tasks.md, auto-commit.

    Holds the feature status lock across the read → resolve → write → commit span,
    exactly as the pre-rewire single body did.
    """
    with feature_status_lock(st.main_repo_root, st.mission_slug):
        if not st.tasks_md.exists():
            _output_error(st.json_output, f"tasks.md not found: {st.tasks_md}")
            raise typer.Exit(1)

        content = st.tasks_md.read_text(encoding="utf-8")
        lines = content.split("\n")
        results: list[TaskIdResult] = []
        artifact_mutated = False

        # Update all requested tasks in a single pass.
        for task_id in st.task_ids:
            before_content = "\n".join(lines)
            result = (
                _resolve_checkbox(task_id, lines, st.status)
                or _resolve_pipe_table(task_id, lines, st.status)
                or _resolve_inline_subtasks(task_id, before_content, st.status, st.feature_dir)
                or _resolve_wp_id(task_id, st.status, st.mission_slug, st.feature_dir)
                or TaskIdResult(
                    id=task_id,
                    outcome=TaskIdResolutionOutcome.NOT_FOUND,
                    format=None,
                    message=f"{task_id} was not found in any supported task format.",
                )
            )
            results.append(result)
            if result.format in {
                TaskIdResolutionFormat.CHECKBOX,
                TaskIdResolutionFormat.PIPE_TABLE,
            } and result.outcome == TaskIdResolutionOutcome.UPDATED:
                artifact_mutated = True
            if (
                result.format == TaskIdResolutionFormat.INLINE_SUBTASKS
                and result.outcome == TaskIdResolutionOutcome.UPDATED
            ):
                artifact_mutated = True
                lines = st.tasks_md.read_text(encoding="utf-8").split("\n")

        st.results = results
        st.updated_tasks = [r.id for r in results if r.outcome == TaskIdResolutionOutcome.UPDATED]
        st.not_found_tasks = [r.id for r in results if r.outcome == TaskIdResolutionOutcome.NOT_FOUND]
        st.resolved_tasks = [r.id for r in results if r.outcome != TaskIdResolutionOutcome.NOT_FOUND]
        st.artifact_mutated = artifact_mutated

        # Fail if no tasks were resolved.
        if not st.resolved_tasks:
            _ms_report_none_resolved(st)

        # Write updated content (single write for all changes).
        if artifact_mutated:
            st.tasks_md.write_text("\n".join(lines), encoding="utf-8")

        # Auto-commit to TARGET branch (detects from feature meta.json).
        if st.resolved_auto_commit and artifact_mutated:
            _ms_commit(st, ports)


def _ms_emit_history(st: _MarkStatusState) -> None:
    """Emit HistoryAdded events for the updated subtasks (T014)."""
    try:
        if st.updated_tasks:
            resolved_tasks_by_wp: dict[str, list[str]] = {}
            unresolved_tasks: list[str] = []
            tasks_content = st.tasks_md.read_text(encoding="utf-8")
            for task_id in st.updated_tasks:
                history_wp_id = _resolve_history_wp_id(tasks_content, task_id)
                if history_wp_id is None:
                    unresolved_tasks.append(task_id)
                else:
                    resolved_tasks_by_wp.setdefault(history_wp_id, []).append(task_id)

            for history_wp_id, task_ids_for_wp in resolved_tasks_by_wp.items():
                task_list_str = ", ".join(task_ids_for_wp)
                emit_history_added(
                    wp_id=history_wp_id,
                    entry_type="note",
                    entry_content=f"Subtask(s) {task_list_str} marked as {st.status}",
                    author="user",
                )
            if unresolved_tasks and not st.json_output:
                console.print(
                    "[yellow]Warning:[/yellow] Could not resolve owning WP for HistoryAdded event: "
                    + ", ".join(unresolved_tasks)
                )
    except Exception as e:
        if not st.json_output:
            console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")


def _ms_dossier_sync(st: _MarkStatusState) -> None:
    """Fire-and-forget dossier sync (best-effort)."""
    with contextlib.suppress(Exception):
        from specify_cli.sync.dossier_pipeline import (
            trigger_feature_dossier_sync_if_enabled,
        )

        trigger_feature_dossier_sync_if_enabled(
            st.feature_dir,
            st.mission_slug,
            st.repo_root,
        )


def _ms_output(st: _MarkStatusState) -> None:
    """Emit the mark-status success envelope + not-found warnings."""
    result = _mark_status_json_payload(st.results)
    if st.not_found_tasks and not st.json_output:
        console.print(f"[yellow]Warning:[/yellow] Not found: {', '.join(st.not_found_tasks)}")
    if len(st.updated_tasks) == 1:
        success_msg = f"[green]✓[/green] Marked {st.updated_tasks[0]} as {st.status}"
    elif not st.updated_tasks:
        success_msg = f"[green]✓[/green] Requested status already satisfied for: {', '.join(st.resolved_tasks)}"
    else:
        success_msg = f"[green]✓[/green] Marked {len(st.updated_tasks)} subtasks as {st.status}: {', '.join(st.updated_tasks)}"
    _output_result(st.json_output, result, success_msg)


def _do_mark_status(
    task_ids: list[str],
    status: str,
    mission: str | None,
    auto_commit: bool | None,
    json_output: bool,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``mark-status`` over the WP02 ports (C-005 seam), CORELESS.

    ``mark_status`` carries NO transition decision core (FR-007): it resolves task
    IDs to durable rows and writes/commits ``tasks.md``. It does NOT route through
    ``move_task``'s ``decide_transition`` core — that is the deferred #2300
    unification, guarded structurally by the T036 non-import gate. ``ports=None``
    builds the production bundle (coord router bound to this module's patchable
    ``commit_for_mission``). The phase helpers run in the SAME order as the original
    single body: validate → resolve → apply → history → dossier → output.
    """
    st = _MarkStatusState(
        task_ids=list(task_ids),
        status=status,
        mission=mission,
        auto_commit=auto_commit,
        json_output=json_output,
    )
    try:
        _ms_validate_inputs(st)
        _ms_resolve_context(st)
        ports = ports or _default_mark_status_ports()
        _ms_resolve_read_dir(st, ports)
        _ms_apply_updates(st, ports)
        _ms_emit_history(st)
        _ms_dossier_sync(st)
        _ms_output(st)
    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016).
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="mark-status")
def mark_status(
    task_ids: Annotated[list[str], typer.Argument(help="Task ID(s) - space-separated (e.g., T001 T002 T003)")],
    status: Annotated[str, typer.Option("--status", help="Status: done/pending")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    auto_commit: Annotated[
        bool | None, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit tasks.md changes to target branch (default: from project config)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Update task checkbox status in tasks.md for one or more tasks.

    Accepts MULTIPLE task IDs separated by spaces. All tasks are updated
    in a single operation with one commit.

    Examples:
        # Single task:
        spec-kitty agent tasks mark-status T001 --status done

        # Multiple tasks (space-separated):
        spec-kitty agent tasks mark-status T001 T002 T003 --status done

        # Many tasks at once:
        spec-kitty agent tasks mark-status T040 T041 T042 T043 T044 T045 --status done --mission 001-my-feature

        # With JSON output:
        spec-kitty agent tasks mark-status T001 T002 --status done --json
    """
    # WP08 (#2116): thin orchestrator. The Typer command declares the CLI surface
    # (WP01 golden byte-identity) and delegates to the CORELESS ``_do_mark_status``,
    # which resolves/writes/commits through the WP02 ports + existing resolver
    # helpers — with NO borrowed transition core (deferred #2300).
    _do_mark_status(
        task_ids=task_ids,
        status=status,
        mission=mission,
        auto_commit=auto_commit,
        json_output=json_output,
    )


@app.command(name="list-tasks")
def list_tasks(
    lane: Annotated[str | None, typer.Option("--lane", help="Filter by lane")] = None,
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """List tasks with optional lane filtering.

    Examples:
        spec-kitty agent tasks list-tasks --json
        spec-kitty agent tasks list-tasks --lane doing --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)

        # Find all task files — tasks/ is PRIMARY-partition (FR-001 / C-001 per-leg
        # split — WP03 T010): WP task files live on the primary checkout regardless
        # of topology; a coord-topology mission's STATUS-only husk has no tasks/.
        tasks_dir = resolve_planning_read_dir(
            main_repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        ) / "tasks"
        if not tasks_dir.exists():
            _output_error(json_output, f"Tasks directory not found: {tasks_dir}")
            raise typer.Exit(1)

        # Load canonical lanes from event log (STATUS-partition — stays coord-aware, C-001)
        _lt_feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
        try:
            from specify_cli.status import read_events as _lt_read_events
            from specify_cli.status import reduce as _lt_reduce

            _lt_events = _lt_read_events(_lt_feature_dir)
            _lt_snapshot = _lt_reduce(_lt_events) if _lt_events else None
            _lt_lanes: dict = {}
            if _lt_snapshot:
                for _lt_wp_id, _lt_state in _lt_snapshot.work_packages.items():
                    _lt_lanes[_lt_wp_id] = Lane(_lt_state.get("lane", Lane.PLANNED))
        except Exception:
            _lt_lanes = {}

        tasks = []
        for task_file in tasks_dir.glob("WP*.md"):
            if task_file.name.lower() == "readme.md":
                continue

            content = task_file.read_text(encoding="utf-8-sig")
            frontmatter, _, _ = split_frontmatter(content)

            task_wp_id = extract_scalar(frontmatter, "work_package_id") or task_file.stem
            task_title = extract_scalar(frontmatter, "title") or ""
            # Lane is event-log-only
            task_lane = _lt_lanes.get(task_wp_id, Lane.PLANNED)

            # Filter by lane if specified
            if lane and task_lane != lane:
                continue

            tasks.append({"work_package_id": task_wp_id, "title": task_title, "lane": task_lane, "path": str(task_file)})

        # Sort by work package ID
        tasks.sort(key=lambda t: t["work_package_id"])

        if json_output:
            print(json.dumps({"tasks": tasks, "count": len(tasks)}))
        else:
            if not tasks:
                console.print(f"[yellow]No tasks found{' in lane ' + lane if lane else ''}[/yellow]")
            else:
                console.print(f"[bold]Tasks{' in lane ' + lane if lane else ''}:[/bold]\n")
                for task in tasks:
                    console.print(f"  {task['work_package_id']}: {task['title']} [{task['lane']}]")

    except typer.Exit:
        raise
    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="add-history")
def add_history(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    note: Annotated[str, typer.Option("--note", help="History note")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    agent: Annotated[str | None, typer.Option("--agent", help="Agent name")] = None,
    shell_pid: Annotated[str | None, typer.Option("--shell-pid", help="Shell PID")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Append history entry to task activity log.

    Examples:
        spec-kitty agent tasks add-history WP01 --note "Completed implementation" --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        # FR-010 / FR-019: one-shot sparse-checkout session warning.
        _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks add-history")

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        _ah_main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)

        # Boundary guard — hard-reject pre-3.0 layout before any WP mutation.
        # Resolve through the kind-aware authority (resolution-authority gate:
        # add_history is a WRITE-classified function, so a kind-blind
        # resolve_feature_dir_for_mission here would be a coord-authority violation).
        _ah_feature_dir = resolve_planning_read_dir(
            _ah_main_repo_root, mission_slug, kind=MissionArtifactKind.TASKS_INDEX
        )
        try:
            check_pre30_layout(_ah_feature_dir)
        except Pre30LayoutError as e:
            _output_error(json_output, str(e))
            raise typer.Exit(1) from None

        # Load work package
        wp = locate_work_package(repo_root, mission_slug, task_id)

        # Build history entry
        timestamp = datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)
        agent_name = agent or extract_scalar(wp.frontmatter, "agent") or "unknown"
        shell_pid_val = shell_pid or extract_scalar(wp.frontmatter, "shell_pid") or ""

        shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
        history_entry = f"- {timestamp} – {agent_name} – {shell_part}{note}"

        # Add history entry to body
        updated_body = append_activity_log(wp.body, history_entry)

        # Build and write updated document
        updated_doc = build_document(wp.frontmatter, updated_body, wp.padding)
        wp.path.write_text(updated_doc, encoding="utf-8")

        # Emit HistoryAdded event (T015 - FR-021)
        try:
            emit_history_added(
                wp_id=task_id,
                entry_type="note",
                entry_content=note,
                author=agent or "user",
            )
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")

        result = {"result": "success", "task_id": task_id, "note": note}

        _output_result(json_output, result, f"[green]✓[/green] Added history entry to {task_id}")

    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016)
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                wp_id=task_id if "task_id" in dir() else None,
                stack_trace=traceback.format_exc(),
                agent_id=agent if "agent" in dir() else None,
            )
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# finalize-tasks — coreless orchestrator (WP08 / FR-007 / FR-010)
# ---------------------------------------------------------------------------
# ``finalize_tasks`` carries NO decision core: it parses ``tasks.md`` deps,
# validates coverage/cycles/conflicts through the existing ``tasks_finalize_validation``
# seam, applies the computed frontmatter writes, and bootstraps canonical status.
# It is thinned via the WP02 ``FsReader`` read port + the existing seams — NOT by
# borrowing any transition core (deferred #2300; guarded by the T036 non-import gate).


@dataclass
class _FinalizeState:
    """Mutable orchestration state threaded through ``finalize_tasks``'s phases.

    Not frozen: each phase fills its own slice in the SAME order the original body
    did (resolve → validate → apply → output), so the frontmatter writes still fire
    only after every validation gate has passed.
    """

    # --- raw command inputs ---
    mission: str | None
    json_output: bool
    validate_only: bool
    # --- phase A: resolved context ---
    repo_root: Path = field(default_factory=Path)
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    mission_slug: str = ""
    primary_feature_dir: Path = field(default_factory=Path)
    tasks_md: Path = field(default_factory=Path)
    tasks_dir: Path = field(default_factory=Path)
    # --- phase B: parsed/validated reads ---
    dependencies_map: dict[str, list[str]] = field(default_factory=dict)
    # --- phase C: applied writes + bootstrap ---
    update_plan: FrontmatterUpdatePlan | None = None
    would_modify: list[dict[str, object]] = field(default_factory=list)
    feature_dir: Path = field(default_factory=Path)
    bootstrap_result: BootstrapResult | None = None


def _default_finalize_ports() -> TasksPorts:
    """Production port bundle for ``finalize_tasks`` (FsReader read authority)."""
    return TasksPorts(
        fs=RealFsReader(),
        coord=RealCoordCommitRouter(),
        git=RealGitOps(),
        render=RealRender(),
    )


def _ft_resolve_context(st: _FinalizeState, ports: TasksPorts) -> None:
    """Phase A: repo/branch/read-dir resolution + the pre30 guard + existence checks.

    FR-010 / T035: the pre30-guard read is GUARD-ONLY (the coord-husk var fed ONLY
    ``check_pre30_layout`` before being reassigned to the primary read), so migrate
    it onto the kind-aware WORK_PACKAGE_TASK authority via the ``FsReader`` port.
    ``tasks.md`` and ``tasks/`` are PRIMARY-partition (FR-001 / C-001 per-leg split),
    so this single read feeds BOTH the guard and the parse. The WP02 T013 proof
    establishes the guard outcome is byte-identical across legs on a modern mission
    (SC-002/NFR-001). Only the STATUS artifacts (bootstrap, event log) use the
    coord-aware resolver in phase C.
    """
    repo_root = locate_project_root()
    if repo_root is None:
        _output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root
    # FR-010 / FR-019: one-shot sparse-checkout session warning.
    _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks finalize-tasks")
    st.mission_slug = _find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.primary_feature_dir = ports.fs.planning_read_dir(
        handle, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation (#1057)
    try:
        check_pre30_layout(st.primary_feature_dir)
    except Pre30LayoutError as e:
        _output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    st.tasks_md = st.primary_feature_dir / TASKS_MD_FILENAME
    st.tasks_dir = st.primary_feature_dir / "tasks"

    if not st.tasks_md.exists():
        _output_error(st.json_output, f"tasks.md not found: {st.tasks_md}")
        raise typer.Exit(1)
    if not st.tasks_dir.exists():
        _output_error(st.json_output, f"Tasks directory not found: {st.tasks_dir}")
        raise typer.Exit(1)


def _ft_validate(st: _FinalizeState) -> None:
    """Phase B: parse deps + WP04 coverage/cycle/disagree-loud conflict gates.

    Each gate is a PRE-write refusal — the frontmatter writes in phase C fire only
    after every gate below passes.
    """
    from specify_cli.core.dependency_parser import (
        parse_dependencies_from_tasks_md as _shared_parse_deps,
    )

    tasks_content = st.tasks_md.read_text(encoding="utf-8")
    st.dependencies_map = _shared_parse_deps(tasks_content)

    coverage = validate_wp_coverage(st.dependencies_map, st.tasks_dir)
    if not coverage.ok:
        _output_error(
            st.json_output,
            (
                "tasks.md work package coverage is incomplete. finalize-tasks could not match "
                "all WP files to parsed sections, so dependency lanes would be unreliable."
            ),
        )
        raise typer.Exit(1)

    cycles = detect_dependency_cycles(st.dependencies_map)
    if cycles:
        _output_error(st.json_output, f"Circular dependencies detected: {cycles}")
        raise typer.Exit(1)

    # --- Dependency conflict detection (T004: disagree-loud) ---
    existing_frontmatter = read_existing_frontmatter(st.tasks_dir)
    dep_conflict_errors = detect_dependency_conflicts(st.dependencies_map, existing_frontmatter)
    if dep_conflict_errors:
        error_msg = "Dependency disagreement detected:\n" + "\n".join(dep_conflict_errors)
        _output_error(st.json_output, error_msg)
        raise typer.Exit(1)


def _ft_apply_writes(st: _FinalizeState) -> None:
    """Phase C: apply the computed frontmatter writes (validate-only-gated) + bootstrap.

    The frontmatter updates are computed side-effect-free, then applied gating ALL
    writes on ``validate_only`` (T005/T006). Bootstrap reads the event log/meta.json
    via the topology-aware (STATUS-partition) resolver — it MUST stay coord-aware.
    """
    from specify_cli.frontmatter import write_frontmatter as _write_fm

    update_plan = compute_wp_frontmatter_updates(st.dependencies_map, st.tasks_dir)
    st.update_plan = update_plan
    for warning in update_plan.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    would_modify: list[dict[str, object]] = []
    for write in update_plan.writes:
        if not st.validate_only:
            _write_fm(write.wp_file, write.updated_meta.model_dump(exclude_none=True), write.body)
        else:
            would_modify.append({"wp_id": write.wp_id, "changes": {"dependencies": write.dependencies}})
    st.would_modify = would_modify

    # Bootstrap canonical status state for all WPs — STATUS-partition: reads the
    # event log and meta.json via the topology-aware resolver (C-001, coord-husk).
    st.feature_dir = resolve_feature_dir_for_mission(st.main_repo_root, st.mission_slug)
    st.bootstrap_result = bootstrap_canonical_state(
        st.feature_dir, st.mission_slug, dry_run=st.validate_only
    )


def _ft_output(st: _FinalizeState) -> None:
    """Phase D: build the validate-only / success envelope and emit it."""
    assert st.update_plan is not None and st.bootstrap_result is not None
    update_plan = st.update_plan
    bootstrap_result = st.bootstrap_result
    bootstrap_payload = {
        "total_wps": bootstrap_result.total_wps,
        "already_initialized": bootstrap_result.already_initialized,
        "newly_seeded": bootstrap_result.newly_seeded,
        "skipped": bootstrap_result.skipped,
        "wp_details": bootstrap_result.wp_details,
    }
    if st.validate_only:
        result: dict[str, object] = {
            "result": "validation_passed",
            "validate_only": True,
            "would_modify": st.would_modify,
            "would_preserve": update_plan.preserved_wps,
            "unchanged": update_plan.unchanged_wps,
            "updated_wp_count": update_plan.updated_count,
            "dependencies": st.dependencies_map,
            **_mission_identity_payload(st.feature_dir),
            "bootstrap": bootstrap_payload,
        }
    else:
        result = {
            "result": "success",
            "updated_wp_count": update_plan.updated_count,
            "modified_wps": update_plan.modified_wps,
            "unchanged_wps": update_plan.unchanged_wps,
            "preserved_wps": update_plan.preserved_wps,
            "dependencies": st.dependencies_map,
            **_mission_identity_payload(st.feature_dir),
            "bootstrap": bootstrap_payload,
        }

    _output_result(
        st.json_output,
        result,
        f"[green]✓[/green] Updated {update_plan.updated_count} WP files with dependencies"
        f" (bootstrap: {bootstrap_result.newly_seeded} seeded,"
        f" {bootstrap_result.already_initialized} existing)",
    )


def _do_finalize_tasks(
    mission: str | None,
    json_output: bool,
    validate_only: bool,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``finalize-tasks`` over the WP02 ``FsReader`` port, CORELESS.

    ``finalize_tasks`` carries NO decision core (FR-007): it parses/validates deps
    through the existing ``tasks_finalize_validation`` seam and applies the computed
    writes. It does NOT route through any transition core (deferred #2300; guarded by
    the T036 non-import gate). ``ports=None`` builds the production bundle. The phase
    helpers run in the SAME order as the original single body: resolve → validate →
    apply → output.
    """
    ports = ports or _default_finalize_ports()
    st = _FinalizeState(mission=mission, json_output=json_output, validate_only=validate_only)
    try:
        _ft_resolve_context(st, ports)
        _ft_validate(st)
        _ft_apply_writes(st)
        _ft_output(st)
    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016).
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="finalize-tasks")
def finalize_tasks(
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    validate_only: Annotated[bool, typer.Option("--validate-only", help="Validate without writing changes")] = False,
) -> None:
    """Parse tasks.md and inject dependencies into WP frontmatter.

    Scans tasks.md for "Depends on: WP##" patterns or phase groupings,
    builds dependency graph, validates for cycles, and writes dependencies
    field to each WP file's frontmatter.

    Examples:
        spec-kitty agent tasks finalize-tasks --mission 001-my-feature --json
        spec-kitty agent tasks finalize-tasks --mission 021-my-feature --json
    """
    # WP08 (#2116): thin orchestrator. The Typer command declares the CLI surface
    # (WP01 golden byte-identity) and delegates to the CORELESS ``_do_finalize_tasks``,
    # which validates through the existing ``tasks_finalize_validation`` seam and
    # reads through the WP02 ``FsReader`` port — with NO borrowed core (deferred #2300).
    _do_finalize_tasks(
        mission=mission,
        json_output=json_output,
        validate_only=validate_only,
    )


@dataclass
class _MapReqState:
    """Mutable orchestration state threaded through ``map_requirements``' phases.

    The single-body command tracked ~20 loose locals across resolve → plan →
    write → gate → finalize; the phase helpers exchange this one value object
    instead. Not frozen: each phase fills its own slice in the SAME order the
    original body did, so the frontmatter write still fires BEFORE the post-write
    stale gate (partial-write-on-refusal timing — NFR-001/WP04).
    """

    # --- raw command inputs ---
    wp: str | None
    refs: str | None
    batch: str | None
    replace: bool
    tracker_ref: list[str] | None
    mission: str | None
    json_output: bool
    auto_commit: bool | None
    # --- phase A: input-mode facts ---
    tracker_ref_values: list[str] = field(default_factory=list)
    tracker_only_mode: bool = False
    # --- phase B: resolved context ---
    repo_root: Path = field(default_factory=Path)
    mission_slug: str = ""
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    auto_commit_on: bool = False
    commit_target: CommitTarget = field(default_factory=lambda: CommitTarget(ref=""))
    # --- phase C: resolved read dirs + parsed reads ---
    feature_dir: Path = field(default_factory=Path)
    primary_dir: Path = field(default_factory=Path)
    tasks_dir: Path = field(default_factory=Path)
    all_spec_ids: set[str] = field(default_factory=set)
    functional_ids: set[str] = field(default_factory=set)
    new_mappings: dict[str, list[str]] = field(default_factory=dict)
    # --- phase D: pure decision ---
    mapping_plan: MappingPlan | None = None
    # --- phase F: finalize ---
    coverage: CoverageSummary | None = None
    committed: bool = False
    commit_sha: str | None = None
    commit_result_payload: dict[str, str] | None = None


def _mr_validate_modes(st: _MapReqState) -> None:
    """Phase A: the operator-mode gates (batch vs wp/refs vs tracker-only)."""
    # T040 / FR-011 (F-10): tracker_ref values are persisted alongside
    # requirement_refs.  --tracker-ref is repeatable and requires --wp.
    st.tracker_ref_values = [t.strip() for t in (st.tracker_ref or []) if t and t.strip()]

    if st.batch and (st.wp or st.refs):
        _output_error(st.json_output, "Cannot combine --batch with --wp/--refs. Use one mode.")
        raise typer.Exit(1)

    if st.tracker_ref_values and (st.batch or st.wp is None):
        _output_error(
            st.json_output,
            "--tracker-ref requires --wp (cannot be combined with --batch).",
        )
        raise typer.Exit(1)

    # When only --tracker-ref is supplied (no --refs), allow the persistence of
    # tracker refs without changing requirement_refs.  This is the primary usage
    # shape per the WP10 spec.
    st.tracker_only_mode = bool(st.tracker_ref_values and st.wp is not None and not st.refs)

    if not st.batch and not (st.wp and st.refs) and not st.tracker_only_mode:
        _output_error(
            st.json_output,
            "Provide either --wp + --refs (individual), --batch, or --wp + --tracker-ref.",
        )
        raise typer.Exit(1)


def _mr_resolve_context(st: _MapReqState) -> None:
    """Phase B: repo/mission/target-branch resolution + the protected-branch gate."""
    repo_root = locate_project_root()
    if repo_root is None:
        _output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root

    # FR-010 / FR-019: one-shot sparse-checkout session warning.
    _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks map-requirements")

    st.mission_slug = _find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    st.auto_commit_on = (
        get_auto_commit_default(st.main_repo_root) if st.auto_commit is None else st.auto_commit
    )
    st.commit_target = CommitTarget(ref=st.target_branch)
    if st.auto_commit_on:
        from specify_cli.coordination.commit_router import _resolve_planning_placement

        # map-requirements edits WP prompt files → WORK_PACKAGE_TASK (primary)
        # (write-surface-coherence WP02 / T009). Resolve the destination through
        # the kind authority instead of the hardcoded target_branch above.
        st.commit_target = _resolve_planning_placement(
            st.main_repo_root, st.mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        protected_error = _protected_branch_status_commit_error(
            st.commit_target.ref,
            st.main_repo_root,
            "spec-kitty agent tasks map-requirements",
        )
        if protected_error is not None:
            _output_error(st.json_output, protected_error)
            raise typer.Exit(1)


def _mr_build_new_mappings(st: _MapReqState) -> None:
    """Phase C(i): build the per-WP new-mapping dict from the active input mode."""
    if st.batch:
        try:
            parsed_batch = json.loads(st.batch)
        except json.JSONDecodeError as exc:
            _output_error(st.json_output, f"Invalid JSON in --batch: {exc}")
            raise typer.Exit(1) from None
        if not isinstance(parsed_batch, dict):
            _output_error(st.json_output, "--batch must be a JSON object {WP_ID: [refs]}")
            raise typer.Exit(1)
        for wp_id, ref_list in parsed_batch.items():
            if not isinstance(ref_list, list) or not all(isinstance(ref, str) for ref in ref_list):
                _output_error(
                    st.json_output,
                    f"Refs for {wp_id} must be a list of strings",
                )
                raise typer.Exit(1)
            st.new_mappings[wp_id.upper()] = [ref.upper() for ref in ref_list]
    elif st.tracker_only_mode:
        # Only --wp + --tracker-ref: no requirement refs to validate, but we still
        # register the WP key so the persistence loop visits it.
        assert st.wp is not None  # narrowed by tracker_only_mode
        st.new_mappings[st.wp.upper()] = []
    else:
        if st.wp is None or st.refs is None:
            _output_error(st.json_output, "Both --wp and --refs are required in individual mode.")
            raise typer.Exit(1)
        ref_list_parsed = [ref.strip() for ref in st.refs.split(",") if ref.strip()]
        st.new_mappings[st.wp.upper()] = [ref.upper() for ref in ref_list_parsed]


def _mr_unknown_wp_gate(st: _MapReqState) -> None:
    """Phase C(ii): reject WP ids the tasks/ dir does not carry."""
    existing_wps: set[str] = set()
    if st.tasks_dir.exists():
        for wp_file in st.tasks_dir.glob("WP*.md"):
            match = re.match(r"(WP\d{2})", wp_file.name)
            if match:
                existing_wps.add(match.group(1))

    unknown_wps = sorted(wp_id for wp_id in st.new_mappings if wp_id not in existing_wps)
    if not unknown_wps:
        return
    hint = f"Available WPs: {', '.join(sorted(existing_wps))}" if existing_wps else "No WP files found in tasks/"
    if st.json_output:
        print(
            json.dumps(
                {
                    "error": "Unknown WP IDs",
                    "unknown_wps": unknown_wps,
                    "hint": hint,
                }
            )
        )
    else:
        console.print(f"[red]Error:[/red] Unknown WP IDs: {', '.join(unknown_wps)}")
        console.print(f"  {hint}")
    raise typer.Exit(1)


def _mr_resolve_read_dirs(st: _MapReqState, ports: TasksPorts) -> None:
    """Phase C: resolve read dirs (fold via the FsReader port), parse spec ids, build mappings.

    T030: the co-located canonicalizer fold — ``primary_feature_dir_for_mission(
    _canonicalize_primary_read_handle(...))`` — routes through the WP02
    ``FsReader.primary_anchor_dir`` port (its named consumer per WP02 Note A); the
    blind primitive + the C-002 fold stay co-located INSIDE that adapter method.
    """
    from specify_cli.requirement_mapping import parse_requirement_ids_from_spec_md

    # #2064: resolve the WP ``tasks/`` dir through the SAME seam finalize uses.
    st.feature_dir = _map_requirements_feature_dir(st.main_repo_root, st.mission_slug)
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation.
    try:
        check_pre30_layout(st.feature_dir)
    except Pre30LayoutError as e:
        _output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    # PRIMARY-input invariant: ``spec.md`` is authored on PRIMARY — unchanged.
    # FR-011 / T012: fold the handle to its canonical dir NAME first so a bare
    # mid8 / human slug resolves the durable ``<slug>-<mid8>`` home (ambiguous
    # handle RAISES — no silent pick, C-002). Routed through the port (T030).
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.primary_dir = ports.fs.primary_anchor_dir(handle)

    if not st.feature_dir.exists():
        _output_error(st.json_output, f"Mission directory not found: {st.feature_dir}")
        raise typer.Exit(1)

    spec_md = st.primary_dir / SPEC_MD_FILENAME
    if not spec_md.exists():
        _output_error(st.json_output, f"spec.md not found: {spec_md}")
        raise typer.Exit(1)

    spec_ids = parse_requirement_ids_from_spec_md(spec_md.read_text(encoding="utf-8"))
    st.all_spec_ids = set(spec_ids["all"])
    st.functional_ids = set(spec_ids["functional"])

    _mr_build_new_mappings(st)

    # #2107 / FR-004 (gate-read-surface-completion WP04): the WP ``tasks/*.md``
    # files are WORK_PACKAGE_TASK — a PRIMARY-partition kind. Resolve the read dir
    # through the kind-aware seam (the SAME single authority WP01 routed the rest
    # of the gate reads onto) instead of the topology-routed ``feature_dir``.
    st.tasks_dir = (
        resolve_planning_read_dir(
            st.main_repo_root,
            st.mission_slug,
            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        )
        / "tasks"
    )
    _mr_unknown_wp_gate(st)


def _mr_plan(st: _MapReqState) -> None:
    """Phase D: freeze the reads and run the pure WP04 ``plan_mapping`` core."""
    from specify_cli.requirement_mapping import read_all_wp_requirement_refs

    # WP04 (FR-005 / FR-002): resolve the reads the pure mapping core consumes —
    # existing per-WP refs (the ONE read feeding BOTH the union-merge base and the
    # coverage projection) + the tasks.md union fallback — then let ``plan_mapping``
    # own the FR↔WP mapping, new-ref validation, and coverage decision.
    existing_all_refs = read_all_wp_requirement_refs(st.tasks_dir)
    tasks_md_refs: dict[str, list[str]] = {}
    tasks_md_file = st.feature_dir / TASKS_MD_FILENAME
    if tasks_md_file.exists():
        from specify_cli.cli.commands.agent.mission import (
            _parse_requirement_refs_from_tasks_md,
        )

        tasks_md_refs = _parse_requirement_refs_from_tasks_md(
            tasks_md_file.read_text(encoding="utf-8")
        )

    if st.tracker_only_mode:
        _mapping_mode = TRACKER_ONLY_MODE
    elif st.batch:
        _mapping_mode = "batch"
    else:
        _mapping_mode = "wp_refs"
    st.mapping_plan = plan_mapping(
        MappingRequest(
            spec_all_ids=frozenset(st.all_spec_ids),
            spec_functional_ids=frozenset(st.functional_ids),
            new_mappings=st.new_mappings,
            existing_all_refs=existing_all_refs,
            tasks_md_refs=tasks_md_refs,
            mode=_mapping_mode,
            replace=st.replace,
        )
    )


def _mr_gate_offenders(st: _MapReqState) -> None:
    """Phase D(ii): the PRE-write refusal gates driven by the core's offenders.

    Malformed FIRST, then unknown — the old inline validate_ref_format/validate_refs
    gate is deleted, not shadowed. Runs BEFORE the write loop, so a bad new ref
    refuses with NO write.
    """
    assert st.mapping_plan is not None
    if st.mapping_plan.offenders.malformed:
        malformed = list(st.mapping_plan.offenders.malformed)
        payload = {
            "error": "Invalid requirement ref format",
            "malformed_refs": malformed,
            "hint": "Refs must match FR-NNN, NFR-NNN, or C-NNN format",
        }
        if st.json_output:
            print(json.dumps(payload))
        else:
            console.print(f"[red]Error:[/red] Invalid ref format: {', '.join(malformed)}")
        raise typer.Exit(1)

    if st.mapping_plan.offenders.unknown_spec_id:
        unknown_refs = list(st.mapping_plan.offenders.unknown_spec_id)
        available_range = f"Available: {', '.join(sorted(st.all_spec_ids))}" if st.all_spec_ids else "No requirement IDs found in spec.md"
        payload = {
            "error": "Invalid requirement refs",
            "unknown_refs": sorted(set(unknown_refs)),
            "hint": f"Refs not found in spec.md. {available_range}",
        }
        if st.json_output:
            print(json.dumps(payload))
        else:
            console.print(f"[red]Error:[/red] Unknown refs: {', '.join(sorted(set(unknown_refs)))}")
            console.print(f"  {available_range}")
        raise typer.Exit(1)


def _mr_write_frontmatter(st: _MapReqState) -> None:
    """Phase E: apply the core's ``to_write`` (+ tracker refs) to WP frontmatter.

    Fires BEFORE the post-write stale gate — partial-write-on-refusal timing is
    preserved (NFR-001/WP04).
    """
    from specify_cli.frontmatter import write_frontmatter
    from specify_cli.status import read_wp_frontmatter

    assert st.mapping_plan is not None
    for wp_id in st.new_mappings:
        wp_file = next((wp_file for wp_file in st.tasks_dir.glob(f"{wp_id}*.md")), None)
        if wp_file is None:
            continue

        wp_meta, body = read_wp_frontmatter(wp_file)
        update_kwargs: dict[str, list[str]] = {}

        # Only update requirement_refs when refs were supplied; preserves backward
        # compatibility for the tracker-only invocation. The merged value is the
        # pure core's ``to_write`` (WP04) — the inline replace/union is deleted.
        if not st.tracker_only_mode:
            update_kwargs["requirement_refs"] = st.mapping_plan.to_write[wp_id]

        # T040 / FR-011 (F-10): merge tracker_refs (or replace if --replace).
        if st.tracker_ref_values and st.wp is not None and wp_id == st.wp.upper():
            if st.replace:
                merged_trackers = sorted(set(st.tracker_ref_values))
            else:
                existing_trackers = list(wp_meta.tracker_refs or [])
                merged_trackers = sorted(set(existing_trackers) | set(st.tracker_ref_values))
            update_kwargs["tracker_refs"] = merged_trackers

        if update_kwargs:
            updated_meta = wp_meta.update(**update_kwargs)
            write_frontmatter(wp_file, updated_meta.model_dump(exclude_none=True), body)


def _mr_stale_gate(st: _MapReqState) -> None:
    """Phase E(ii): post-write hard-fail on stale/invalid refs across ALL WPs.

    Runs AFTER the frontmatter write (original sequence position), so a pre-existing
    stale ref on an untouched WP still refuses (exit 1) with the partial write on
    disk — the exact partial-write-on-refusal behaviour WP04 preserved.
    """
    from specify_cli.requirement_mapping import (
        classify_stale_refs,
        read_all_wp_raw_requirement_refs,
        validate_ref_format,
        validate_refs,
    )

    all_wp_raw = read_all_wp_raw_requirement_refs(st.tasks_dir)
    all_raw_refs: list[str] = []
    for ref_list in all_wp_raw.values():
        all_raw_refs.extend(ref_list)

    # Raw tokens preserve case; uppercase for comparison.
    uppercased_raw = [r.upper() for r in all_raw_refs if not r.startswith("<")]
    _, post_merge_malformed = validate_ref_format(uppercased_raw)
    _, post_merge_unknown = validate_refs(uppercased_raw, st.all_spec_ids)
    stale_refs: dict[str, list[str]] = {}
    if post_merge_malformed or post_merge_unknown:
        bad = set(post_merge_malformed) | set(post_merge_unknown)
        for wp_id, ref_list in all_wp_raw.items():
            wp_bad = sorted(token for token in ref_list if token.upper() in bad or token.startswith("<"))
            if wp_bad:
                stale_refs[wp_id] = wp_bad

    if not stale_refs:
        return

    # Surface the parsed spec FR set and classify each offender so a simple format
    # mismatch (e.g. FR-003a) is obvious rather than looking like invented IDs (#2066).
    stale_ref_reasons = classify_stale_refs(stale_refs, post_merge_malformed)
    parsed_spec_ids = sorted(st.all_spec_ids)
    payload = {
        "error": "Stale or invalid refs in WP frontmatter",
        "stale_refs": stale_refs,
        "stale_ref_reasons": stale_ref_reasons,
        "parsed_spec_ids": parsed_spec_ids,
        "hint": (
            "Requirement IDs must match FR-NNN, NFR-NNN, or C-NNN "
            "(e.g. FR-003, not FR-003a). 'malformed' refs violate that format; "
            "'unknown_spec_id' refs are well-formed but not declared in spec.md "
            "(see parsed_spec_ids). Re-run with --replace to correct, "
            "e.g.: map-requirements --wp WP01 --refs FR-001 --replace"
        ),
    }
    if st.json_output:
        print(json.dumps(payload))
    else:
        console.print("[red]Error:[/red] Stale or invalid refs in WP frontmatter:")
        console.print("  IDs must match FR-NNN, NFR-NNN, or C-NNN (e.g. FR-003, not FR-003a).")
        for wp_id, bad_refs in sorted(stale_refs.items()):
            console.print(f"  {wp_id}: {', '.join(bad_refs)}")
        console.print(f"  Parsed spec IDs: {', '.join(parsed_spec_ids) or '(none)'}")
        console.print("  Use --replace to correct mappings")
    raise typer.Exit(1)


def _mr_auto_commit(st: _MapReqState, ports: TasksPorts) -> None:
    """Phase F(i): route the WP-file auto-commit through the WP02 ``commit_artifact`` port.

    map-requirements edits WP prompt files → WORK_PACKAGE_TASK (a primary kind,
    write-surface-coherence WP03 / T014). The coord router carries the resolved
    ``target_branch`` so the WP09 ff-advance fires for a coord write; the ``--json``
    ``commit_result`` envelope shape (#1891 / FR-013) is reconstructed byte-identically.
    """
    if not st.auto_commit_on:
        return
    written_files: list[Path] = []
    for wp_id in st.new_mappings:
        wp_file = next((f for f in st.tasks_dir.glob(f"{wp_id}*.md")), None)
        if wp_file is not None:
            written_files.append(wp_file.resolve())
    if not written_files:
        return
    spec_number = st.mission_slug.split("-")[0] if "-" in st.mission_slug else st.mission_slug
    commit_msg = f"chore: Map requirements for {', '.join(sorted(st.new_mappings))} on spec {spec_number}"
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    try:
        _router_result = ports.coord.commit_artifact(
            handle,
            tuple(written_files),
            commit_msg,
            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
            policy=ProtectionPolicy.resolve(st.main_repo_root),
        )
        if _router_result.status == "committed":
            st.committed = True
            st.commit_sha = _router_result.commit_hash
            st.commit_result_payload = {
                "sha": _router_result.commit_hash or "",
                "destination_ref": _router_result.placement_ref,
                "worktree_root": str(st.main_repo_root),
            }
    except Exception as exc_commit:
        if not st.json_output:
            console.print(f"[yellow]Warning:[/yellow] Auto-commit skipped: {exc_commit}")


def _mr_emit_output(st: _MapReqState) -> None:
    """Phase F(ii): reconstruct coverage from the core + emit the success envelope."""
    from specify_cli.requirement_mapping import read_all_wp_requirement_refs

    assert st.mapping_plan is not None
    # ``total_mappings`` reflects the post-write disk state (unchanged read). The
    # coverage summary is reconstructed from the core's ``unmapped_fr``: every
    # functional FR is either mapped or unmapped, so ``mapped = total - len(unmapped)``
    # is byte-identical to ``compute_coverage`` over the post-write state (WP04).
    all_wp_refs = read_all_wp_requirement_refs(st.tasks_dir)
    coverage: CoverageSummary = {
        "total_functional": len(st.functional_ids),
        "mapped_functional": len(st.functional_ids) - len(st.mapping_plan.unmapped_fr),
        "unmapped_functional": st.mapping_plan.unmapped_fr,
    }
    st.coverage = coverage

    payload = {
        "result": "success",
        **_mission_identity_payload(st.primary_dir),
        "mapped": {wp_id: sorted(refs) for wp_id, refs in st.new_mappings.items()},
        "total_mappings": {wp_id: sorted(refs) for wp_id, refs in all_wp_refs.items() if refs},
        "coverage": coverage,
        "committed": st.committed,
        "commit_sha": st.commit_sha,
        "commit_result": st.commit_result_payload,
    }
    if st.json_output:
        print(json.dumps(payload))
    else:
        console.print("[green]✓[/green] Requirement mappings saved")
        for wp_id, ref_list in sorted(st.new_mappings.items()):
            console.print(f"  {wp_id}: {', '.join(ref_list)}")
        console.print(f"\n  Coverage: {coverage['mapped_functional']}/{coverage['total_functional']} FRs mapped")
        if coverage["unmapped_functional"]:
            console.print(f"  [yellow]Unmapped:[/yellow] {', '.join(coverage['unmapped_functional'])}")
        if st.committed:
            console.print("[cyan]→ Committed mapping changes[/cyan]")


def _do_map_requirements(
    wp: str | None,
    refs: str | None,
    batch: str | None,
    replace: bool,
    tracker_ref: list[str] | None,
    mission: str | None,
    json_output: bool,
    auto_commit: bool | None,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``map-requirements`` over the WP04 core + WP02 ports (C-005 seam).

    ``ports=None`` builds the production bundle AFTER ``target_branch`` resolves
    (the coord router threads it for the ff-advance). Tests inject a Fake bundle to
    observe the executed side-effects (T032). The phase helpers run in the SAME
    order as the original single body: validate → resolve → plan → write → stale
    gate → finalize — so the frontmatter write still precedes the post-write stale
    gate (partial-write-on-refusal timing, NFR-001/WP04).
    """
    st = _MapReqState(
        wp=wp,
        refs=refs,
        batch=batch,
        replace=replace,
        tracker_ref=tracker_ref,
        mission=mission,
        json_output=json_output,
        auto_commit=auto_commit,
    )
    try:
        _mr_validate_modes(st)
        _mr_resolve_context(st)
        ports = ports or _default_map_requirements_ports(st.target_branch)
        _mr_resolve_read_dirs(st, ports)
        _mr_plan(st)
        _mr_gate_offenders(st)
        _mr_write_frontmatter(st)
        _mr_stale_gate(st)
        _mr_auto_commit(st, ports)
        _mr_emit_output(st)
    except typer.Exit:
        raise
    except Exception as exc:
        _output_error(json_output, str(exc))
        raise typer.Exit(1) from None


@app.command(name="map-requirements")
def map_requirements(
    wp: Annotated[str | None, typer.Option("--wp", help="WP ID (e.g., WP04)")] = None,
    refs: Annotated[
        str | None,
        typer.Option("--refs", help="Comma-separated requirement refs (e.g., FR-001,FR-002)"),
    ] = None,
    batch: Annotated[
        str | None,
        typer.Option(
            "--batch",
            help='JSON batch mapping (e.g., \'{"WP01":["FR-001"],"WP02":["FR-003"]}\')',
        ),
    ] = None,
    replace: Annotated[
        bool,
        typer.Option(
            "--replace",
            help="Replace existing refs instead of merging (default: merge/union)",
        ),
    ] = False,
    tracker_ref: Annotated[
        list[str] | None,
        typer.Option(
            "--tracker-ref",
            help=(
                "External tracker reference (e.g., '#1298' or 'JIRA-123'). "
                "Repeatable; requires --wp. Persists to the WP frontmatter as tracker_refs."
            ),
        ),
    ] = None,
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    auto_commit: Annotated[
        bool | None,
        typer.Option(
            "--auto-commit/--no-auto-commit",
            help="Automatically commit WP file changes (default: from project config)",
        ),
    ] = None,
) -> None:
    """Register requirement-to-WP mappings with immediate validation."""
    # WP07 (#2116): thin orchestrator. The Typer command declares the CLI surface
    # (WP01 golden byte-identity) and delegates to ``_do_map_requirements``, which
    # runs the WP04 ``plan_mapping`` core and executes the write/commit through the
    # WP02 ports (``FsReader.primary_anchor_dir`` fold, ``commit_artifact``).
    _do_map_requirements(
        wp=wp,
        refs=refs,
        batch=batch,
        replace=replace,
        tracker_ref=tracker_ref,
        mission=mission,
        json_output=json_output,
        auto_commit=auto_commit,
    )


@app.command(name="validate-workflow")
def validate_workflow(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Validate task metadata structure and workflow consistency.

    Examples:
        spec-kitty agent tasks validate-workflow WP01 --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        _vw_main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)

        # Boundary guard — hard-reject pre-3.0 layout before reading any WP.
        # Resolve through the kind-aware authority (resolution-authority gate:
        # validate_workflow is WRITE-classified, so a kind-blind resolver here
        # would be a coord-authority violation).
        _vw_guard_feature_dir = resolve_planning_read_dir(
            _vw_main_repo_root, mission_slug, kind=MissionArtifactKind.TASKS_INDEX
        )
        try:
            check_pre30_layout(_vw_guard_feature_dir)
        except Pre30LayoutError as e:
            _output_error(json_output, str(e))
            raise typer.Exit(1) from None

        # Load work package
        wp = locate_work_package(repo_root, mission_slug, task_id)

        # Validation checks
        errors = []
        warnings = []

        # Check required fields (lane is event-log-only, not required in frontmatter)
        required_fields = ["work_package_id", "title"]
        for field in required_fields:
            if not extract_scalar(wp.frontmatter, field):
                errors.append(f"Missing required field: {field}")

        # Get lane from event log (canonical source)
        _vw_feature_dir = resolve_feature_dir_for_mission(repo_root, mission_slug)
        try:
            from specify_cli.status import read_events as _vw_read_events
            from specify_cli.status import reduce as _vw_reduce

            _vw_events = _vw_read_events(_vw_feature_dir)
            _vw_snapshot = _vw_reduce(_vw_events) if _vw_events else None
            _vw_state = _vw_snapshot.work_packages.get(task_id) if _vw_snapshot else None
            lane_value = Lane(_vw_state.get("lane", Lane.PLANNED)) if _vw_state else Lane.PLANNED
        except Exception:
            lane_value = Lane.PLANNED

        # Check work_package_id matches filename
        wp_id = extract_scalar(wp.frontmatter, "work_package_id")
        if wp_id and not wp.path.name.startswith(wp_id):
            warnings.append(f"Work package ID '{wp_id}' doesn't match filename '{wp.path.name}'")

        # Check for activity log
        if "## Activity Log" not in wp.body:
            warnings.append("Missing Activity Log section")

        # Determine validity
        is_valid = len(errors) == 0

        result = {"valid": is_valid, "errors": errors, "warnings": warnings, "task_id": task_id, "lane": lane_value or "unknown"}

        if json_output:
            print(json.dumps(result))
        else:
            if is_valid:
                console.print(f"[green]✓[/green] {task_id} validation passed")
            else:
                console.print(f"[red]✗[/red] {task_id} validation failed")
                for error in errors:
                    console.print(f"  [red]Error:[/red] {error}")

            if warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in warnings:
                    console.print(f"  [yellow]•[/yellow] {warning}")

    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016)
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="validation",
                error_message=str(e),
                wp_id=task_id if "task_id" in dir() else None,
                stack_trace=traceback.format_exc(),
            )
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@dataclass
class _StatusState:
    """Mutable orchestration state threaded through ``status``'s phases.

    The single-body command tracked ~20 loose locals across resolve → load →
    flag → render; the phase helpers exchange this one value object instead. Not
    frozen: each phase fills its own slice in the SAME order the original body
    did, so the git/clock staleness I/O — and its exact sequence — stays inside
    the shell (WP05 aggregation parity, NFR-002).
    """

    # --- raw command inputs ---
    mission: str | None
    json_output: bool
    stale_threshold: int
    # --- phase A: resolved dirs ---
    cwd: Path = field(default_factory=Path)
    repo_root: Path = field(default_factory=Path)
    mission_slug: str = ""
    main_repo_root: Path = field(default_factory=Path)
    feature_dir: Path = field(default_factory=Path)
    tasks_dir: Path = field(default_factory=Path)
    # --- phase B: loaded work packages + reduced snapshot ---
    events: list[StatusEvent] = field(default_factory=list)
    snapshot: StatusSnapshot | None = None
    work_packages: list[dict[str, object]] = field(default_factory=list)
    wp_dependencies: dict[str, list[str]] = field(default_factory=dict)
    # --- phase C: review-status flags ---
    review_stall_threshold: int = 0
    stale_verdicts: list[dict[str, object]] = field(default_factory=list)
    stalled_wps: list[dict[str, object]] = field(default_factory=list)


def _st_resolve_dirs(st: _StatusState) -> None:
    """Phase A: repo/mission resolution + the CWD-independent read-dir resolution.

    Write path keeps main-repo-root resolution so canonical serialization pins to
    the primary checkout; the read path routes through the canonical resolver
    (WP08 T037, FR-030) with the legacy worktree-aware fallback preserved.
    """
    st.cwd = Path.cwd().resolve()
    repo_root = locate_project_root(st.cwd)
    if repo_root is None:
        raise typer.Exit(1)
    st.repo_root = repo_root

    st.mission_slug = _find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, _ = _ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )

    # Route through the single guarded read-side seam (WP01/IC-01; FR-002, C-007).
    from specify_cli.missions._read_path_resolver import (
        resolve_handle_to_read_path,
    )

    feature_dir = resolve_handle_to_read_path(st.main_repo_root, st.mission_slug)
    if not feature_dir.exists():
        # Last-ditch fallback to the original worktree-aware path so tests /
        # projects that stand up status files in unusual places still work.
        status_read_root = get_status_read_root(st.cwd)
        legacy_dir = candidate_feature_dir_for_mission(status_read_root, st.mission_slug)
        if legacy_dir.exists():
            feature_dir = legacy_dir
        else:
            console.print(f"[red]Error:[/red] Mission directory not found: {feature_dir}")
            raise typer.Exit(1)
    st.feature_dir = feature_dir

    # PRIMARY leg — tasks/ is PRIMARY-partition (FR-001 / C-001 per-leg split —
    # WP03 T009). The STATUS leg stays on the coord-aware ``feature_dir`` above.
    st.tasks_dir = resolve_planning_read_dir(
        st.main_repo_root, st.mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    ) / "tasks"
    if not st.tasks_dir.exists():
        console.print(f"[red]Error:[/red] Tasks directory not found: {st.tasks_dir}")
        raise typer.Exit(1)


def _st_resolve_execution_mode(
    front: str, main_repo_root: Path, mission_slug: str, wp_id: str | None
) -> tuple[str, str]:
    """Resolve ``(execution_mode, workspace_kind)`` for one WP row (verbatim fallbacks)."""
    try:
        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, wp_id)
        return workspace.execution_mode, workspace.resolution_kind
    except MissingLanesError:
        # Without lanes.json the resolver cannot return a workspace, but we still
        # want a meaningful execution_mode. Prefer the explicit frontmatter value,
        # then the normalized default, and only fall back to "code_change" if both
        # are missing — never blank.
        execution_mode = extract_scalar(front, "execution_mode") or ""
        if not execution_mode:
            try:
                normalized = get_normalized_wp(main_repo_root, mission_slug, wp_id)
                execution_mode = normalized.metadata.execution_mode or "code_change"
            except Exception:
                execution_mode = "code_change"
        return execution_mode, "unknown"
    except (ValueError, FileNotFoundError):
        # Resolver could not classify; fall back to frontmatter and default.
        return extract_scalar(front, "execution_mode") or "code_change", "unknown"


def _st_load_work_packages(st: _StatusState) -> None:
    """Phase B: reduce the event log + collect the per-WP status rows.

    Loads canonical lanes from the event log (lane is event-log-only), then reads
    each WP's frontmatter into a status row and freezes the declared dependencies
    for the pure ``build_status_view`` readiness map.
    """
    _st_lanes: dict[str, Lane] = {}
    try:
        from specify_cli.status import read_events as _st_read_events
        from specify_cli.status import reduce as _st_reduce

        st.events = _st_read_events(st.feature_dir)
        st.snapshot = _st_reduce(st.events) if st.events else None
        if st.snapshot:
            for _st_wp_id, _st_state in st.snapshot.work_packages.items():
                _st_lanes[_st_wp_id] = Lane(_st_state.get("lane", Lane.GENESIS))
    except Exception:
        st.events = []
        _st_lanes = {}

    # WP05: declared dependencies per WP id, frozen from the SAME frontmatter parse
    # already performed here (no extra file read).
    for wp_file in sorted(st.tasks_dir.glob("WP*.md")):
        front, body, padding = split_frontmatter(wp_file.read_text(encoding="utf-8"))

        wp_id = extract_scalar(front, "work_package_id")
        title = extract_scalar(front, "title")
        deps_raw = extract_scalar(front, "dependencies")
        if isinstance(deps_raw, list):
            wp_deps = [str(dep) for dep in deps_raw]
        elif deps_raw:
            wp_deps = [str(deps_raw)]
        else:
            wp_deps = []
        st.wp_dependencies[wp_id or wp_file.stem] = wp_deps
        lane = resolve_lane_alias(_st_lanes.get(wp_id or wp_file.stem, Lane.GENESIS))
        execution_mode, workspace_kind = _st_resolve_execution_mode(
            front, st.main_repo_root, st.mission_slug, wp_id
        )
        st.work_packages.append(
            {
                "id": wp_id,
                "title": title,
                "lane": lane,
                "phase": extract_scalar(front, "phase") or "Unknown Phase",
                "file": wp_file.name,
                "agent": extract_scalar(front, "agent") or "",
                "agent_profile": extract_scalar(front, "agent_profile") or "",
                "shell_pid": extract_scalar(front, "shell_pid") or "",
                "execution_mode": execution_mode,
                "workspace_kind": workspace_kind,
            }
        )

    if not st.work_packages:
        console.print(f"[yellow]No work packages found in {st.tasks_dir}[/yellow]")
        raise typer.Exit(0)


def _st_apply_review_flags(st: _StatusState) -> None:
    """Phase C: annotate rows with stale-verdict + stalled-review warnings."""
    st.review_stall_threshold = _review_stall_threshold_minutes(st.main_repo_root)
    st.stale_verdicts, st.stalled_wps = _apply_review_status_flags(
        st.work_packages,
        tasks_dir=st.tasks_dir,
        events=st.events,
        stall_threshold_minutes=st.review_stall_threshold,
    )


def _st_emit_json(st: _StatusState, ports: TasksPorts) -> None:
    """JSON leg: apply the git-staleness I/O, run the WP05 core, emit via the Render port.

    T031: the ``--json`` envelope is assembled from the pure ``build_status_view``
    aggregation and serialised through ``ports.render.json_envelope`` (``indent=2``
    for ``status``'s own render binding — byte-identical to the pre-rewire dump).
    """
    from specify_cli.core.stale_detection import check_doing_wps_for_staleness

    doing_wps = [wp for wp in st.work_packages if wp["lane"] == Lane.IN_PROGRESS]
    try:
        stale_results = check_doing_wps_for_staleness(
            main_repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            doing_wps=doing_wps,
            threshold_minutes=st.stale_threshold,
        )
    except MissingLanesError as exc:
        stale_results = build_stale_fallback_results(doing_wps, exc)

    for wp in st.work_packages:
        if wp["lane"] == Lane.IN_PROGRESS and wp["id"] in stale_results:
            _apply_stale_status_fields(wp, stale_results[wp["id"]])

    auto_commit_enabled = get_auto_commit_default(st.main_repo_root)
    # WP05: the pure aggregation core owns the kanban rollup + counts + percentages.
    view = build_status_view(
        StatusRequest(
            work_packages=st.work_packages,
            snapshot=st.snapshot,
            wp_dependencies=st.wp_dependencies,
        )
    )
    result: dict[str, object] = {
        **_mission_identity_payload(st.feature_dir),
        "total_wps": view.total_wps,
        "by_lane": dict(view.lane_counts),
        "work_packages": st.work_packages,
        "progress_percentage": view.progress_percentage,
        "progress_semantics": PROGRESS_SEMANTICS,
        "weighted_percentage": view.progress_percentage,
        "done_count": view.done_count,
        "done_percentage": view.done_percentage,
        "stale_wps": view.stale_count,
        "stale_verdicts": st.stale_verdicts,
        "stalled_wps": st.stalled_wps,
        "auto_commit": auto_commit_enabled,
    }
    print(ports.render.json_envelope(result))


def _st_board_cell(
    wp: Any, lane: Lane, main_repo_root: Path, profile_repo: object | None
) -> str:
    """Build one kanban cell string (marker + stale/claimed/review decoration)."""
    title_truncated = wp["title"][:22] + "..." if len(wp["title"]) > 22 else wp["title"]
    marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
    display_id = f"{marker}{wp['id']}"
    if wp.get("_stale_verdict"):
        return f"[yellow]⚠ {display_id}[/yellow]\n{title_truncated}"
    if lane == Lane.IN_PROGRESS and wp.get("is_stale"):
        return f"[red]⚠️ {display_id}[/red]\n{title_truncated}"
    if wp.get("_stall_label"):
        return f"[yellow]⚠ {display_id} (review)[/yellow]\n{title_truncated}"
    if wp.get("_display_claimed"):
        return f"[blue]{display_id} (claimed)[/blue]\n{title_truncated}"
    if wp.get("_display_in_review"):
        return f"[bright_cyan]{display_id} (review)[/bright_cyan]\n{title_truncated}"
    return f"{display_id}\n{title_truncated}"


def _st_render_overview(ports: TasksPorts, st: _StatusState, view: StatusView) -> None:
    """Render the title panel + done/weighted progress bar via the Render port."""
    from rich.panel import Panel
    from rich.text import Text

    title_text = Text()
    title_text.append("📊 Work Package Status: ", style="bold cyan")
    title_text.append(st.mission_slug, style="bold white")

    ports.render.human("")
    ports.render.human(Panel(title_text, border_style="cyan"))

    progress_text = Text()
    progress_text.append("Done progress: ", style="bold")
    progress_text.append(f"{view.done_count}/{view.total_wps}", style="bold green")
    progress_text.append(f" ({view.done_percentage}%)", style="dim")
    progress_text.append("\nWeighted readiness: ", style="bold")
    progress_text.append(f"{view.progress_percentage}%", style="bold cyan")

    bar_width = 40
    filled = int(bar_width * view.progress_percentage / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    progress_text.append(f"\n{bar}", style="green")

    ports.render.human(progress_text)
    ports.render.human("")


def _st_render_board(
    ports: TasksPorts, st: _StatusState, view: StatusView, profile_repo: object | None
) -> None:
    """Render the kanban board table via the Render port.

    Folds claimed + in_review WPs into the "Doing" column with markers; the row
    objects are the SAME ``view.lanes`` objects, so display-marker mutations
    propagate. GENESIS is excluded; off-board rows land in the "other" bucket.
    """
    from rich.table import Table

    by_lane = view.lanes
    display_in_progress = []
    for wp in by_lane[Lane.CLAIMED]:
        wp["_display_claimed"] = True
        display_in_progress.append(wp)
    display_in_progress.extend(by_lane[Lane.IN_PROGRESS])
    for wp in by_lane.get(Lane.IN_REVIEW, []):
        wp["_display_in_review"] = True
        display_in_progress.append(wp)

    table = Table(title="Kanban Board", show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("📋 Planned", style="yellow", no_wrap=False, width=25)
    table.add_column("🔄 Doing", style="blue", no_wrap=False, width=25)
    table.add_column("👀 For Review", style="cyan", no_wrap=False, width=25)
    table.add_column("👍 Approved", style="magenta", no_wrap=False, width=25)
    table.add_column("✅ Done", style="green", no_wrap=False, width=25)

    max_rows = max(len(by_lane[Lane.PLANNED]), len(display_in_progress), len(by_lane[Lane.FOR_REVIEW]), len(by_lane[Lane.APPROVED]), len(by_lane[Lane.DONE]))

    display_columns = [
        (Lane.PLANNED, by_lane[Lane.PLANNED]),
        (Lane.IN_PROGRESS, display_in_progress),
        (Lane.FOR_REVIEW, by_lane[Lane.FOR_REVIEW]),
        (Lane.APPROVED, by_lane[Lane.APPROVED]),
        (Lane.DONE, by_lane[Lane.DONE]),
    ]

    for i in range(max_rows):
        row = []
        for lane, lane_list in display_columns:
            if i < len(lane_list):
                row.append(_st_board_cell(lane_list[i], lane, st.main_repo_root, profile_repo))
            else:
                row.append("")
        table.add_row(*row)

    table.add_row(
        f"[bold]{len(by_lane[Lane.PLANNED])} WPs[/bold]",
        f"[bold]{len(display_in_progress)} WPs[/bold]",
        f"[bold]{len(by_lane[Lane.FOR_REVIEW])} WPs[/bold]",
        f"[bold]{len(by_lane[Lane.APPROVED])} WPs[/bold]",
        f"[bold]{len(by_lane[Lane.DONE])} WPs[/bold]",
        style="dim",
    )

    ports.render.human(table)
    ports.render.human("")


def _st_render_arbiter(ports: TasksPorts, st: _StatusState) -> None:
    """Render the arbiter-override history section via the Render port (T034)."""
    try:
        from specify_cli.review.arbiter import get_arbiter_overrides_for_wp

        arbiter_lines: list[str] = []
        for wp in st.work_packages:
            wp_id_val = wp.get("id") or ""
            if not wp_id_val:
                continue
            overrides = get_arbiter_overrides_for_wp(st.feature_dir, wp_id_val)
            for idx, override in enumerate(overrides, start=1):
                cat = override.get("category", "custom")
                arbiter_lines.append(f"  • {wp_id_val} Cycle {idx}: rejected → [yellow]overridden[/yellow] ({cat})")

        if arbiter_lines:
            ports.render.human("[bold yellow]⚖️  Arbiter Override History:[/bold yellow]")
            for line in arbiter_lines:
                ports.render.human(line)
            ports.render.human("")
    except ImportError:
        pass  # review package not yet available


def _st_render_review_queues(
    ports: TasksPorts, st: _StatusState, view: StatusView, profile_repo: object | None
) -> None:
    """Render the for_review / approved / done-with-stale-verdict sections."""
    by_lane = view.lanes
    if by_lane[Lane.FOR_REVIEW]:
        ports.render.human("[bold cyan]👀 Ready for Review:[/bold cyan]")
        for wp in by_lane[Lane.FOR_REVIEW]:
            marker = _get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            ports.render.human(f"  • {marker}{wp['id']} - {wp['title']}")
        ports.render.human("")

    if by_lane[Lane.APPROVED]:
        ports.render.human("[bold magenta]👍 Approved (merge when all WPs approved):[/bold magenta]")
        for wp in by_lane[Lane.APPROVED]:
            marker = _get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            line = f"  • {marker}{wp['id']} - {wp['title']}"
            if wp.get("_stale_verdict"):
                line += "  [bold yellow]⚠ review artifact: verdict=rejected[/bold yellow]"
            ports.render.human(line)
        ports.render.human("[dim]   Approved WPs stay here until feature merge. Dependents can start immediately.[/dim]")
        ports.render.human("")

    done_stale = [wp for wp in by_lane[Lane.DONE] if wp.get("_stale_verdict")]
    if done_stale:
        ports.render.human("[bold green]✅ Done (with stale verdict warnings):[/bold green]")
        for wp in done_stale:
            marker = _get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            ports.render.human(
                f"  • {marker}{wp['id']} - {wp['title']}"
                "  [bold yellow]⚠ review artifact: verdict=rejected[/bold yellow]"
            )
        ports.render.human("")


def _st_render_active(
    ports: TasksPorts,
    st: _StatusState,
    view: StatusView,
    stale_results: Any,
    profile_repo: object | None,
) -> None:
    """Render the claimed / in_progress / in_review sections via the Render port."""
    by_lane = view.lanes
    if by_lane[Lane.CLAIMED]:
        ports.render.human("[bold blue]🔄 Claimed (shown in Doing column):[/bold blue]")
        for wp in by_lane[Lane.CLAIMED]:
            marker = _get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            agent = wp.get("agent", "unknown")
            ports.render.human(f"  • {marker}{wp['id']} - {wp['title']} [dim](agent: {agent})[/dim]")
        ports.render.human("")

    if by_lane[Lane.IN_PROGRESS]:
        ports.render.human("[bold blue]🔄 In Progress:[/bold blue]")
        stale_wps = []
        for wp in by_lane[Lane.IN_PROGRESS]:
            marker = _get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            stale_label = _render_stale_status(stale_results.get(wp["id"]))
            agent = wp.get("agent", "unknown")
            if wp.get("is_stale"):
                ports.render.human(f"  • [red]⚠️ {marker}{wp['id']}[/red] - {wp['title']} [dim]({stale_label}, agent: {agent})[/dim]")
                stale_wps.append(wp)
            elif stale_label:
                ports.render.human(f"  • {marker}{wp['id']} - {wp['title']} [dim]({stale_label}, agent: {agent})[/dim]")
            else:
                ports.render.human(f"  • {marker}{wp['id']} - {wp['title']}")
        ports.render.human("")

        if stale_wps:
            ports.render.human(f"[yellow]⚠️  {len(stale_wps)} stale WP(s) detected - agents may have stopped without transitioning[/yellow]")
            ports.render.human("[dim]   Run: spec-kitty agent tasks move-task <WP_ID> --to for_review[/dim]")
            ports.render.human("")

    if by_lane.get(Lane.IN_REVIEW):
        ports.render.human("[bold bright_cyan]🔍 In Review (shown in Doing column):[/bold bright_cyan]")
        for wp in by_lane[Lane.IN_REVIEW]:
            marker = _get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            line = f"  • {marker}{wp['id']} - {wp['title']}"
            if wp.get("_stall_label"):
                line += f"  [bold yellow]⚠ {wp['_stall_label']}[/bold yellow]"
            ports.render.human(line)
        ports.render.human("")


def _st_render_planned(
    ports: TasksPorts, st: _StatusState, view: StatusView, profile_repo: object | None
) -> None:
    """Render the "Next Up (Planned)" section via the Render port."""
    by_lane = view.lanes
    if by_lane[Lane.PLANNED]:
        ports.render.human("[bold yellow]📋 Next Up (Planned):[/bold yellow]")
        for wp in by_lane[Lane.PLANNED][:3]:
            marker = _get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            ports.render.human(f"  • {marker}{wp['id']} - {wp['title']}")
        if len(by_lane[Lane.PLANNED]) > 3:
            ports.render.human(f"  [dim]... and {len(by_lane[Lane.PLANNED]) - 3} more[/dim]")
        ports.render.human("")


def _st_render_summary(ports: TasksPorts, st: _StatusState, view: StatusView) -> None:
    """Render the summary panel + the "Next action" hint via the Render port."""
    from rich.panel import Panel
    from rich.table import Table

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Total WPs:", str(view.total_wps))
    summary.add_row("Completed:", f"[green]{view.done_count}[/green] ({view.done_percentage}%)")
    summary.add_row("Weighted readiness:", f"[cyan]{view.progress_percentage}%[/cyan]")
    summary.add_row("In Progress:", f"[blue]{view.in_progress_count}[/blue]")
    summary.add_row("Planned:", f"[yellow]{view.planned_count}[/yellow]")

    auto_commit_enabled = get_auto_commit_default(st.main_repo_root)
    auto_commit_label = "[green]enabled[/green]" if auto_commit_enabled else "[yellow]disabled[/yellow]"
    summary.add_row("Auto-commit:", auto_commit_label)

    ports.render.human(Panel(summary, title="[bold]Summary[/bold]", border_style="dim"))

    ports.render.human("[bold]▶ Next action:[/bold]")
    ports.render.human(f"  [cyan]spec-kitty next --agent <your-name> --mission {st.mission_slug}[/cyan]")
    ports.render.human("[dim]  This command tells you exactly what to do next based on the dependency graph.[/dim]")
    ports.render.human("")


def _st_render_human(st: _StatusState, ports: TasksPorts) -> None:
    """Human leg: run the WP05 core, apply staleness, render the board via the Render port.

    T031: every emission routes through ``ports.render.human`` (bound to the module
    ``console`` in production — byte-identical + patch-seam-preserving). The pure
    ``build_status_view`` owns the rollup/counts; the shell owns only the
    git/clock staleness I/O and the drawing.
    """
    from specify_cli.core.stale_detection import check_doing_wps_for_staleness

    view = build_status_view(
        StatusRequest(
            work_packages=st.work_packages,
            snapshot=st.snapshot,
            wp_dependencies=st.wp_dependencies,
        )
    )
    by_lane = view.lanes

    try:
        stale_results = check_doing_wps_for_staleness(
            main_repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            doing_wps=by_lane[Lane.IN_PROGRESS],
            threshold_minutes=st.stale_threshold,
        )
    except MissingLanesError as exc:
        stale_results = build_stale_fallback_results(by_lane[Lane.IN_PROGRESS], exc)

    try:
        from doctrine.agent_profiles.repository import AgentProfileRepository

        profile_repo: object | None = AgentProfileRepository(
            built_in_dir=st.main_repo_root / "src" / "doctrine" / "agent_profiles" / "built-in"
        )
    except Exception:
        profile_repo = None

    for wp in by_lane[Lane.IN_PROGRESS]:
        wp_id = wp["id"]
        if wp_id in stale_results:
            _apply_stale_status_fields(wp, stale_results[wp_id])
        else:
            wp["is_stale"] = False

    _st_render_overview(ports, st, view)
    _st_render_board(ports, st, view, profile_repo)
    _st_render_arbiter(ports, st)
    _st_render_review_queues(ports, st, view, profile_repo)
    _st_render_active(ports, st, view, stale_results, profile_repo)
    _st_render_planned(ports, st, view, profile_repo)
    _st_render_summary(ports, st, view)


def _do_status(
    mission: str | None,
    json_output: bool,
    stale_threshold: int,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``status`` over the WP05 ``build_status_view`` core + the Render port.

    ``ports=None`` builds the production bundle (Render bound to the module
    ``console`` with an ``indent=2`` JSON envelope). Tests inject a Fake bundle to
    observe the rendered views/envelopes (T032). The phase helpers run in the SAME
    order as the original single body: resolve → load → flag → render — so the
    WP05 byte-identical aggregation and the git/clock staleness sequence are intact.
    """
    ports = ports or _default_status_ports()
    st = _StatusState(mission=mission, json_output=json_output, stale_threshold=stale_threshold)
    try:
        _st_resolve_dirs(st)
        _st_load_work_packages(st)
        _st_apply_review_flags(st)
        if st.json_output:
            _st_emit_json(st, ports)
            return
        _st_render_human(st, ports)
    except typer.Exit:
        raise
    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="status")
def status(
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    stale_threshold: Annotated[int, typer.Option("--stale-threshold", help="Minutes of inactivity before a WP is considered stale")] = 10,
) -> None:
    """Display kanban status board for all work packages in a feature.

    Shows a beautiful overview of work package statuses, progress metrics,
    and next steps based on dependencies.

    WPs in "doing" with no commits for --stale-threshold minutes are flagged
    as potentially stale (agent may have stopped).

    Example:
        spec-kitty agent tasks status
        spec-kitty agent tasks status --mission 012-documentation-mission
        spec-kitty agent tasks status --json
        spec-kitty agent tasks status --stale-threshold 15
    """
    # WP07 (#2116): thin orchestrator. The Typer command declares the CLI surface
    # (WP01 golden byte-identity) and delegates to ``_do_status``, which runs the
    # WP05 ``build_status_view`` core and renders through the WP02 Render port.
    _do_status(mission=mission, json_output=json_output, stale_threshold=stale_threshold)


@app.command(name="list-dependents")
def list_dependents(
    wp_id: Annotated[str, typer.Argument(help="Work package ID (e.g., WP01)")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Find all WPs that depend on a given WP (downstream dependents).

    This answers "who depends on me?" - useful when reviewing a WP to understand
    the impact of requested changes on downstream work packages.

    Also shows what the WP itself depends on (upstream dependencies).

    Examples:
        spec-kitty agent tasks list-dependents WP13
        spec-kitty agent tasks list-dependents WP01 --mission 001-my-feature --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)
        # WP08 (FR-010 / T035): the pre30 guard read is GUARD-ONLY — the variable was
        # reassigned to the primary WORK_PACKAGE_TASK read immediately after the guard,
        # so the kind-blind coord-husk resolve_feature_dir_for_mission probe here served
        # no purpose beyond the guard. Migrate it onto the kind-aware WORK_PACKAGE_TASK
        # authority (``tasks/`` is PRIMARY-partition), so this single resolve now feeds
        # BOTH the boundary guard and the graph builder. The WP02 T013 proof establishes
        # the guard outcome is byte-identical across legs on a modern mission
        # (SC-002/NFR-001); the redundant second reassignment is removed.
        feature_dir = resolve_planning_read_dir(
            main_repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
        # Boundary guard — hard-reject pre-3.0 layout before reading any WP (#1057)
        try:
            check_pre30_layout(feature_dir)
        except Pre30LayoutError as e:
            _output_error(json_output, str(e))
            raise typer.Exit(1) from None

        if not feature_dir.exists():
            _output_error(json_output, f"Mission directory not found: {feature_dir}")
            raise typer.Exit(1)

        # Build dependency graph and find dependents
        graph = build_dependency_graph(feature_dir)
        dependents = get_dependents(wp_id, graph)

        # Also get this WP's own dependencies for context
        try:
            wp = locate_work_package(repo_root, mission_slug, wp_id)
            own_deps_raw = extract_scalar(wp.frontmatter, "dependencies")
            # Handle both list and string formats
            if isinstance(own_deps_raw, list):
                own_deps = own_deps_raw
            elif own_deps_raw:
                own_deps = [own_deps_raw]
            else:
                own_deps = []
        except Exception:
            own_deps = []

        if json_output:
            print(json.dumps({"wp_id": wp_id, "depends_on": own_deps, "dependents": dependents}))
        else:
            console.print(f"\n[bold]{wp_id} Dependency Info:[/bold]")
            console.print(f"  Depends on: {', '.join(own_deps) if own_deps else '[dim](none)[/dim]'}")
            console.print(f"  Depended on by: {', '.join(dependents) if dependents else '[dim](none)[/dim]'}")

            if dependents:
                console.print(f"\n[yellow]⚠️  Changes to {wp_id} may impact: {', '.join(dependents)}[/yellow]")
            console.print()

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None
