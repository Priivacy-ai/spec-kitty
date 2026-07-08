"""Task workflow commands for AI agents."""

# ⚠️ REGISTRATION SHIM (de-godded 4569→~1200 LOC by #2116/#2305 — keep it thin).
# This file owns ONLY: the @app.command wrappers, four small command bodies, and
# the seam-surface re-export block. New behavior goes in the sibling modules
# (tasks_shared / tasks_command_adapters / tasks_<family>), never here.
# Size/complexity regressions are Sonar's to flag (quality gate), not pytest's.

from __future__ import annotations

from specify_cli.core.constants import (
    KITTY_SPECS_DIR,
)
# ``primary_feature_dir_for_mission`` keeps an explicit ``as`` re-export: its
# direct call site relocated to ``tasks_move_task`` in WP05
# (tasks-py-degod-wave2-01KWH9EQ), but the module binding is a live patch seam
# (``@patch("...agent.tasks.primary_feature_dir_for_mission")``,
# test_pre30_guard_wiring) that the relocated ``_mt_issue_matrix_facts`` body
# routes back through ``_tasks.<attr>``.
# read-surface-ssot-closeout WP08 / FR-001 / NFR-001: the kind-blind
# ``resolve_feature_dir_for_mission`` re-export is RETIRED — its last two
# direct call sites (``list_tasks`` / ``validate_workflow``, below) now route
# through ``mission_runtime.placement_seam(...).read_dir(STATUS_STATE)``, and
# the relocated ``_ft_apply_writes`` (tasks_finalize.py) no longer proxies
# through ``_tasks.<attr>`` for this symbol either (routed the same way).
from specify_cli.missions._read_path_resolver import (
    primary_feature_dir_for_mission as primary_feature_dir_for_mission,
    resolve_planning_read_dir,
)
import contextlib
import logging
import subprocess
import traceback
from datetime import datetime, UTC
from pathlib import Path

import typer
from rich.console import Console
from typing import Annotated

# ``emit_error_logged`` keeps an explicit ``as`` re-export: its direct call
# site relocated to ``tasks_move_task`` in WP05 (tasks-py-degod-wave2), but the
# module binding is a live D7 patch seam routed back through ``_tasks.<attr>``.
# ``emit_history_added`` likewise (WP08): ``add_history`` still calls it
# directly here, AND the relocated ``_ms_emit_history`` (tasks_mark_status)
# routes it back through ``_tasks.<attr>`` — a live patch seam
# (``@patch("...agent.tasks.emit_history_added")``, ×10) that must stay an
# explicit module export under ``mypy --strict`` no-implicit-reexport.
from specify_cli.sync.events import (
    emit_history_added as emit_history_added,
    emit_error_logged as emit_error_logged,
)

# ``emit_status_transition_transactional`` keeps an explicit ``as`` re-export:
# its direct adapter call site relocated to ``tasks_command_adapters`` in WP03
# (tasks-py-degod-wave2-01KWH9EQ), but the module binding is a live D7 patch
# seam (``@patch("...agent.tasks.emit_status_transition_transactional")``)
# that the move_task coord router's ``commit_status`` body routes back through
# ``_tasks.<attr>`` (the ``seam_coord_router(route_emit=True)`` emit wrapper).
from specify_cli.coordination.status_transition import (
    emit_status_transition_transactional as emit_status_transition_transactional,
)
# ``read_events_transactional`` (D7 ×9) likewise: relocated move_task callers
# route back through ``_tasks.<attr>`` (WP05).
from specify_cli.coordination.status_transition import (
    read_events_transactional as read_events_transactional,
)
from specify_cli.status import Lane

from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
# ``get_main_repo_root`` / ``get_feature_target_branch`` / ``get_mission_type``
# keep explicit ``as`` re-exports: their direct call sites relocated to
# ``tasks_shared`` in WP02 (tasks-py-degod-wave2-01KWH9EQ), but each module
# binding is a live D7 patch seam (``@patch("...agent.tasks.<name>")``, 15/3/26
# sites) that the relocated bodies route back through ``_tasks.<attr>``.
# ``locate_project_root`` (top D7 seam, ×67) keeps an explicit ``as``
# re-export: the relocated move_task family routes it via ``_tasks.<attr>``
# (WP05); command bodies remaining here keep calling it directly.
from specify_cli.core.paths import locate_project_root as locate_project_root
from specify_cli.core.paths import get_main_repo_root as get_main_repo_root
from specify_cli.core.paths import get_feature_target_branch as get_feature_target_branch
# ``get_status_read_root`` keeps an explicit ``as`` re-export: its direct call
# site relocated to ``tasks_status_cmd`` in WP07 (tasks-py-degod-wave2), but
# the module binding is a live D7 patch seam
# (``@patch("...agent.tasks.get_status_read_root")``, ×3) that the relocated
# ``_st_resolve_dirs`` body routes back through ``_tasks.<attr>``.
from specify_cli.core.paths import get_status_read_root as get_status_read_root
from specify_cli.mission import get_mission_type as get_mission_type
from mission_runtime import (
    MissionArtifactKind,
    # Explicit ``as`` re-export: no direct call site remains in this module
    # after WP02 (tasks-py-degod-wave2-01KWH9EQ), but the module binding is a
    # live patch seam (``@patch("...agent.tasks.resolve_placement_only")``)
    # routed back through ``_tasks.<attr>`` by the relocated shared helpers.
    resolve_placement_only as resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
    # coord-primary-partition-lock WP05 (T024): live patch seam for
    # ``_mt_resolve_status_placement_ref`` — routed back through
    # ``_tasks.placement_seam`` by the relocated ``tasks_move_task`` body
    # (same D7 seam-bridge convention as the other ``mission_runtime`` names
    # above).
    placement_seam as placement_seam,
)
# ``commit_for_mission`` keeps an explicit ``as`` re-export: its direct
# adapter call sites relocated to ``tasks_command_adapters`` in WP03
# (tasks-py-degod-wave2-01KWH9EQ), but the module binding is a live D7 patch
# seam (``@patch("...agent.tasks.commit_for_mission")``, ~19 sites) that the
# relocated router ``commit_artifact`` bodies route back through
# ``_tasks.<attr>``.
from specify_cli.coordination.commit_router import commit_for_mission as commit_for_mission
from specify_cli.git.protection_policy import ProtectionPolicy
# ``feature_status_lock`` (D7 ×23) — the relocated ``_mt_execute`` (WP05) and
# ``_ms_apply_updates`` (WP08) route it via ``_tasks.<attr>``.
from specify_cli.status import feature_status_lock as feature_status_lock
# ``get_auto_commit_default`` (D7 ×7) — the relocated ``_mt_resolve_targets``
# (WP05) and ``_ms_resolve_context`` (WP08) route it via ``_tasks.<attr>``.
from specify_cli.core.agent_config import get_auto_commit_default as get_auto_commit_default
# ``bootstrap_canonical_state`` keeps an explicit ``as`` re-export: its direct
# call site relocated to ``tasks_finalize`` in WP08 (tasks-py-degod-wave2), but
# the module binding is a live patch seam
# (``@patch("...agent.tasks.bootstrap_canonical_state")``, ×7,
# test_tasks_canonical_cleanup / test_tasks_coreless_orchestration) that the
# relocated ``_ft_apply_writes`` body routes back through ``_tasks.<attr>``.
from specify_cli.status import bootstrap_canonical_state as bootstrap_canonical_state
from specify_cli.workspace.context import resolve_workspace_for_wp
from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout


# ``locate_work_package`` (D7 ×16) keeps an explicit ``as`` re-export: the
# relocated move_task family routes it via ``_tasks.<attr>`` (WP05).
from specify_cli.task_utils import (
    append_activity_log,
    build_document,
    extract_scalar,
    locate_work_package as locate_work_package,
    split_frontmatter,
)

# WP02 (#2058): tasks.md/manifest parsing + WP-id resolution helpers and the
# shared result vocabulary live in the ``tasks_outline`` seam. Imported here so
# existing ``from ...agent.tasks import <name>`` call sites keep working.
from specify_cli.cli.commands.agent.tasks_outline import (
    # WP09 (tasks-py-degod-wave2-01KWH9EQ): the ``TaskIdResult`` vocabulary and
    # ``_INLINE_SUBTASKS_RE`` left this module with ``_resolve_inline_subtasks``
    # (now in ``tasks_mark_status``); zero external ``from tasks import`` sites
    # (per-symbol reference check in the WP09 sweep).
    # WP03 (#2058): the pipe-table row parsers moved to ``tasks_materialization``
    # along with their only former internal caller. They remain re-exported here
    # (explicit ``as`` form) because existing tests import them from ``tasks``.
    _is_pipe_table_task_row as _is_pipe_table_task_row,
    # ``_normalize_task_id_input`` keeps an explicit ``as`` re-export: its
    # direct call site relocated to ``tasks_mark_status`` in WP08
    # (tasks-py-degod-wave2), but ``tests/contract/test_mark_status_input_shapes.py``
    # imports it from ``tasks`` (×7).
    _normalize_task_id_input as _normalize_task_id_input,
    _parse_pipe_table_header as _parse_pipe_table_header,
)

# WP03 (#2058): frontmatter/file persistence + markdown-row mutation helpers
# live in the ``tasks_materialization`` seam. Re-exported here (out-of-map edit:
# tasks.py is owned by WP07) so existing ``from ...agent.tasks import <name>``
# call sites (workflow.py, implement.py, tests) keep working unchanged. Names not
# referenced inside this module use the explicit ``as`` re-export form so ruff
# recognizes the intentional public re-export and does not flag F401.
# ``_resolve_wp_slug`` / ``_issue_matrix_approval_blocker`` (below) keep
# explicit ``as`` re-exports: their direct call sites relocated to
# ``tasks_move_task`` in WP05, but ``tests/agent/cli/commands/test_tasks_helpers.py``
# imports both from ``tasks``.
from specify_cli.cli.commands.agent.tasks_materialization import (
    _collect_status_artifacts as _collect_status_artifacts,
    _resolve_wp_slug as _resolve_wp_slug,
    _materialize_inline_subtask_status as _materialize_inline_subtask_status,
    # WP09: ``_persist_inline_subtask_status`` left with ``_resolve_inline_subtasks``
    # (now imported directly by ``tasks_mark_status``); zero external refs via ``tasks``.
    _persist_review_artifact_override_in_coord as _persist_review_artifact_override_in_coord,
    _persist_review_feedback as _persist_review_feedback,
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
    # Explicit ``as`` re-export (WP02 mypy campsite fold): ``test_tasks.py``
    # imports this from ``tasks``; the implicit re-export is an
    # ``attr-defined`` error under ``mypy --strict``.
    _get_latest_review_cycle_verdict as _get_latest_review_cycle_verdict,
    _issue_matrix_approval_blocker as _issue_matrix_approval_blocker,
)

# WP04: dependency/cycle validation, lane-metadata helpers, and the
# finalize_tasks validation core live in the ``tasks_finalize_validation`` seam.
# The lane helpers are re-imported here so existing
# ``from ...agent.tasks import <name>`` call sites keep working. The
# finalize-only gate names (``compute_wp_frontmatter_updates`` etc.) moved to
# ``tasks_finalize`` in WP08 — zero-patch-site symbols with a canonical home,
# imported there directly (per-symbol external-reference checks: no test or
# src imports them from ``tasks``).
from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    _lane_targets_for_emit,
    _wp_lane_from_status_events,
)

# WP03: the pure ``move_task`` transition decision core lives in
# ``tasks_transition_core``; the orchestration moved to ``tasks_move_task``
# (WP05). ``decide_transition`` keeps an explicit ``as`` re-export: its module
# binding is a live seam (``monkeypatch.setattr(tasks, "decide_transition", …)``
# sentinel tests, test_tasks_transition_core.py) that the relocated
# ``_mt_run_decision`` body routes back through ``_tasks.<attr>``.
from specify_cli.cli.commands.agent.tasks_transition_core import (
    decide_transition as decide_transition,
)

# WP04: the pure ``map_requirements`` FR↔WP mapping decision core. The command
# orchestration relocated to ``tasks_map_requirements`` in WP06
# (tasks-py-degod-wave2-01KWH9EQ); ``plan_mapping`` keeps an explicit ``as``
# re-export: its module binding is a live sentinel seam
# (``monkeypatch.setattr(tasks_module, "plan_mapping", …)``,
# test_tasks_mapping_core.py ×2) that the relocated ``_mr_plan`` body routes
# back through ``_tasks.<attr>``.
from specify_cli.cli.commands.agent.tasks_mapping_core import (
    plan_mapping as plan_mapping,
)

# WP05: the pure ``status`` compute/aggregation core. The command orchestration
# relocated to ``tasks_status_cmd`` in WP07 (tasks-py-degod-wave2-01KWH9EQ);
# ``build_status_view`` keeps an explicit ``as`` re-export: its module binding
# is a live sentinel seam (``monkeypatch.setattr(tasks_module,
# "build_status_view", …)``, test_tasks_status_view.py ×2) that the relocated
# ``_st_emit_json`` / ``_st_render_human`` bodies route back through
# ``_tasks.<attr>``.
from specify_cli.cli.commands.agent.tasks_status_view import (
    build_status_view as build_status_view,
)

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

# WP06 (#2116): the move_task orchestrator (now in ``tasks_move_task``, WP05)
# consumes the WP02 capability ports — the coord READ authority (``FsReader``)
# and the coord WRITE authority's two disjoint capabilities (``commit_status``
# over the transactional emitter / ``commit_artifact`` over the mission commit
# router). See ``agent_tasks_ports`` for the stratification rationale.
# ``RealFsReader`` / ``RealGitOps`` keep explicit ``as`` re-exports alongside
# ``RealRender``: the moved ``_default_move_task_ports`` (WP05) constructs the
# port bundle via the ``tasks`` bindings so construction stays patchable.
from specify_cli.agent_tasks_ports import (
    # ``RealCoordCommitRouter`` keeps an explicit ``as`` re-export: the moved
    # ``_default_status_ports`` (WP07) and ``_default_finalize_ports`` (WP08)
    # construct the port bundle via the ``tasks`` bindings so construction
    # stays patchable.
    RealCoordCommitRouter as RealCoordCommitRouter,
    RealFsReader as RealFsReader,
    RealGitOps as RealGitOps,
    RealRender,
)

# WP03 (tasks-py-degod-wave2-01KWH9EQ / FR-004): the three coord WRITE router
# the coord-router seam factory lives in ``tasks_command_adapters`` (imports
# downward only — never ``tasks`` at module scope, breaking the ports↔commands
# cycle risk). The explicit ``as`` re-export keeps ``tasks.seam_coord_router`` a
# module attribute: the ``_default_*_ports`` factories below construct the
# single production ``RealCoordCommitRouter`` via this binding, so
# ``@patch("...agent.tasks.seam_coord_router")`` / ``monkeypatch.setattr`` on the
# ``tasks`` namespace keeps intercepting construction. The factory injects seam
# wrappers that route ``emit_status_transition_transactional`` /
# ``commit_for_mission`` back through ``_tasks.<attr>`` (research.md D1), so the
# module bindings of those two seam symbols above stay live patch targets.
from specify_cli.cli.commands.agent.tasks_command_adapters import (
    seam_coord_router as seam_coord_router,
)

# ---------------------------------------------------------------------------
# WP02 (tasks-py-degod-wave2-01KWH9EQ / FR-002, FR-003): the cross-family
# shared helpers live in ``tasks_shared``. Every moved symbol is re-imported
# here in the explicit ``as`` re-export form so ``tasks.<name>`` stays a module
# attribute — the seam surface (NFR-002). Relocated bodies route their calls to
# patched seam symbols back through ``_tasks.<attr>`` (lazy in-function import),
# so ``@patch("...agent.tasks.<name>")`` / ``monkeypatch.setattr(tasks, ...)``
# keep INTERCEPTING, not merely resolving. Per-symbol evidence:
# kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md; interception
# pins: tests/.../agent/test_tasks_shared_seam.py.
# ---------------------------------------------------------------------------
from specify_cli.cli.commands.agent.tasks_shared import (
    _RUNTIME_STATE_DENY_LIST as _RUNTIME_STATE_DENY_LIST,
    _check_unchecked_subtasks as _check_unchecked_subtasks,
    _coord_topology_active as _coord_topology_active,
    _emit_sparse_session_warning as _emit_sparse_session_warning,
    _ensure_target_branch_checked_out as _ensure_target_branch_checked_out,
    _filter_by_planning_tip_content as _filter_by_planning_tip_content,
    _filter_runtime_state_paths as _filter_runtime_state_paths,
    _find_mission_slug as _find_mission_slug,
    _list_wp_branch_mission_specs_changes as _list_wp_branch_mission_specs_changes,
    _list_wp_branch_specs_changes_for_guard as _list_wp_branch_specs_changes_for_guard,
    _mark_status_json_payload as _mark_status_json_payload,
    _mission_identity_payload as _mission_identity_payload,
    _output_error as _output_error,
    _output_result as _output_result,
    _protected_branch_status_commit_error as _protected_branch_status_commit_error,
    _resolve_git_common_dir as _resolve_git_common_dir,
    _review_currency_check_branch as _review_currency_check_branch,
    _skip_target_branch_commit as _skip_target_branch_commit,
    _validate_ready_for_review as _validate_ready_for_review,
    _wp_branch_merged_into_target as _wp_branch_merged_into_target,
    resolve_primary_branch as resolve_primary_branch,
)

# Re-exported lane helpers consumed by tests via
# ``from ...agent.tasks import <name>`` even though tasks.py uses them only
# indirectly; listed in ``__all__`` so the re-export is explicit (C-007).
# The D7 seam infra names (``ProtectionPolicy``, ``resolve_topology``,
# ``routes_through_coordination``, ``resolve_workspace_for_wp``,
# ``subprocess``) are declared too (WP02, tasks-py-degod-wave2-01KWH9EQ):
# they are patched as ``tasks.<name>`` by the historical test contracts and
# read back through ``_tasks.<attr>`` by the relocated ``tasks_shared``
# bodies, so the module bindings are deliberate exports, not incidental
# imports.
__all__ = [
    "ProtectionPolicy",
    "RealRender",
    "_behind_commits_touch_only_planning_artifacts",
    "_check_dependent_warnings",
    "_lane_targets_for_emit",
    "_wp_lane_from_status_events",
    "app",
    "compute_incomplete_dependents",
    "resolve_topology",
    "resolve_workspace_for_wp",
    "routes_through_coordination",
    "subprocess",
]

logger = logging.getLogger(__name__)
# ``SPEC_MD_FILENAME`` stays a ``tasks.py``-owned constant: its only consumer
# (``_mr_resolve_read_dirs``) relocated to ``tasks_map_requirements`` in WP06
# and reads it back through ``_tasks.SPEC_MD_FILENAME`` (the WP05
# ``UTC_SECOND_TIMESTAMP_FORMAT`` precedent).
SPEC_MD_FILENAME = "spec.md"
UTC_SECOND_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


app = typer.Typer(name="tasks", help="Task workflow commands for AI agents", no_args_is_help=True)

console = Console()


globals()["_list_wp_branch_" + KITTY_SPECS_DIR.replace("-", "_") + "_changes"] = (
    _list_wp_branch_mission_specs_changes
)


# ===========================================================================
# WP05 (tasks-py-degod-wave2-01KWH9EQ / FR-001, FR-002): the ``move-task``
# family — ``_do_move_task``, the 23 ``_mt_*`` phase helpers, ``_MoveTaskState``
# and ``_default_move_task_ports`` — lives in ``tasks_move_task`` (moved
# VERBATIM). Every moved symbol is re-imported here in the explicit ``as``
# re-export form so ``tasks.<name>`` stays a module attribute — the seam
# surface (NFR-002). The relocated bodies route every patched seam symbol back
# through ``_tasks.<attr>`` (lazy in-function import, research.md D1/D7), so
# ``@patch("...agent.tasks.<sym>")`` / ``monkeypatch.setattr(tasks, ...)``
# keep INTERCEPTING (incl. ``decide_transition``, ``_skip_target_branch_commit``
# (C-001), ``ProtectionPolicy`` and the port adapters constructed by the moved
# ``_default_move_task_ports``). The ``@app.command`` Typer wrapper below stays
# here: the CLI surface (byte-frozen ``--help``) belongs to the registration
# shim. Per-symbol evidence:
# kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md.
# ===========================================================================
from specify_cli.cli.commands.agent.tasks_move_task import (
    _MoveTaskState as _MoveTaskState,
    # WP09 (FR-008, IC-07): the six family stragglers that stayed behind at
    # WP05 — the arbiter override pair, the #2155 mixed-bundle partition, the
    # coord event-path probe, the event-field shaper and the reviewer detector
    # — relocated here in the final registration-shim sweep. Explicit ``as``
    # re-exports: each is a live ``@patch("...agent.tasks.<name>")`` /
    # direct-import seam (test_tasks_move_task_seam.py,
    # test_coord_status_commit_2155.py, test_move_task_guard.py,
    # test_review_feedback_pointer_2x_unit.py, test_tasks_helpers.py).
    _coord_status_events_path as _coord_status_events_path,
    _default_move_task_ports as _default_move_task_ports,
    _detect_arbiter_override as _detect_arbiter_override,
    _detect_reviewer_name as _detect_reviewer_name,
    _do_move_task as _do_move_task,
    # #2335: the for_review deliverable-recovery pair (lane porcelain parser +
    # pre-guard auto-commit) joins the family surface like every other def.
    _lane_deliverable_paths as _lane_deliverable_paths,
    _mt_approval_facts as _mt_approval_facts,
    _mt_build_request as _mt_build_request,
    _mt_commit_lane_deliverables as _mt_commit_lane_deliverables,
    _mt_commit_wp_file as _mt_commit_wp_file,
    _mt_current_event_lane as _mt_current_event_lane,
    _mt_done_ancestry_facts as _mt_done_ancestry_facts,
    _mt_emit_transitions as _mt_emit_transitions,
    # WP02 (review-regression-gate-01KWX6DF, T004/T005): the for_review
    # pre-review regression-gate hook + its precedence/messaging helpers join
    # the family surface like every other def — same seam-bridge rule.
    _mt_empty_scope_verdict as _mt_empty_scope_verdict,
    _mt_execute as _mt_execute,
    _mt_finalize_plan as _mt_finalize_plan,
    _mt_fire_arbiter_persist as _mt_fire_arbiter_persist,
    _mt_fire_override_persist as _mt_fire_override_persist,
    _mt_gather_late_facts as _mt_gather_late_facts,
    _mt_gather_review_facts as _mt_gather_review_facts,
    _mt_hop_actor as _mt_hop_actor,
    _mt_hop_review_result as _mt_hop_review_result,
    _mt_issue_matrix_facts as _mt_issue_matrix_facts,
    _mt_output as _mt_output,
    _mt_persist_tracker_refs as _mt_persist_tracker_refs,
    _mt_persist_wp_file as _mt_persist_wp_file,
    _mt_pre_review_block_enabled as _mt_pre_review_block_enabled,
    _mt_pre_review_changed_files as _mt_pre_review_changed_files,
    _mt_pre_review_gate_block_message as _mt_pre_review_gate_block_message,
    _mt_pre_review_gate_console_warning as _mt_pre_review_gate_console_warning,
    _mt_pre_review_gate_metadata as _mt_pre_review_gate_metadata,
    _mt_pre_review_gate_verdict as _mt_pre_review_gate_verdict,
    _mt_pre_review_gate_with_override_scope as _mt_pre_review_gate_with_override_scope,
    _mt_pre_review_scope_override as _mt_pre_review_scope_override,
    _mt_release_review_lock as _mt_release_review_lock,
    # coord-primary-partition-lock WP05 (T023/T024): the STATUS_STATE seam
    # lookup + the extracted write/commit core + the enriched success message
    # join the family surface like every other def — same seam-bridge rule.
    _mt_resolve_status_placement_ref as _mt_resolve_status_placement_ref,
    _mt_write_and_commit_wp_file as _mt_write_and_commit_wp_file,
    _mt_wp_commit_success_message as _mt_wp_commit_success_message,
    _mt_resolve_feedback as _mt_resolve_feedback,
    _mt_resolve_pre_review_workspace as _mt_resolve_pre_review_workspace,
    _mt_resolve_targets as _mt_resolve_targets,
    _mt_review_config_section as _mt_review_config_section,
    _mt_run_decision as _mt_run_decision,
    _mt_run_pre_review_gate as _mt_run_pre_review_gate,
    _mt_warn_worktree_kitty_specs as _mt_warn_worktree_kitty_specs,
    _pre_review_gate_composite_routing as _pre_review_gate_composite_routing,
    _pre_review_gate_filter_groups as _pre_review_gate_filter_groups,
    _primary_bundle_status_artifacts as _primary_bundle_status_artifacts,
    _run_arbiter_override as _run_arbiter_override,
    _status_event_result_fields as _status_event_result_fields,
)


# ===========================================================================
# WP06 (tasks-py-degod-wave2-01KWH9EQ / FR-001, FR-002): the
# ``map-requirements`` family — ``_do_map_requirements``, the 11 ``_mr_*``
# phase helpers, ``_MapReqState`` and ``_default_map_requirements_ports`` —
# lives in ``tasks_map_requirements`` (moved VERBATIM). Every moved symbol is
# re-imported here in the explicit ``as`` re-export form so ``tasks.<name>``
# stays a module attribute — the seam surface (NFR-002). The relocated bodies
# route every patched seam symbol back through ``_tasks.<attr>`` (lazy
# in-function import, research.md D1/D7), so ``@patch("...agent.tasks.<sym>")``
# / ``monkeypatch.setattr(tasks, ...)`` keep INTERCEPTING (incl. the
# ``plan_mapping`` sentinel seam, ``_protected_branch_status_commit_error``
# (C-001 REFUSE arm — no skip pre-gate, harness label T005) and the port
# adapters constructed by the moved ``_default_map_requirements_ports``). The
# ``@app.command`` Typer wrapper stays here: the CLI surface (byte-frozen
# ``--help``) belongs to the registration shim. Per-symbol evidence:
# kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md.
# ===========================================================================
from specify_cli.cli.commands.agent.tasks_map_requirements import (
    _MapReqState as _MapReqState,
    _default_map_requirements_ports as _default_map_requirements_ports,
    _do_map_requirements as _do_map_requirements,
    # WP09 (FR-008, IC-07): the family straggler that stayed behind at WP06 —
    # the kind-aware ``tasks/`` read resolver — relocated in the final
    # registration-shim sweep. Explicit ``as`` re-export: a live
    # ``@patch("...agent.tasks._map_requirements_feature_dir")`` seam
    # (test_pre30_guard_wiring.py, test_map_requirements_read_surface.py,
    # test_tasks_map_requirements_seam.py) and a direct-import surface
    # (test_coord_loop_tasks.py, test_requirement_mapping_coord_surface.py).
    _map_requirements_feature_dir as _map_requirements_feature_dir,
    _mr_auto_commit as _mr_auto_commit,
    _mr_build_new_mappings as _mr_build_new_mappings,
    _mr_emit_output as _mr_emit_output,
    _mr_gate_offenders as _mr_gate_offenders,
    _mr_plan as _mr_plan,
    _mr_resolve_context as _mr_resolve_context,
    _mr_resolve_read_dirs as _mr_resolve_read_dirs,
    _mr_stale_gate as _mr_stale_gate,
    _mr_unknown_wp_gate as _mr_unknown_wp_gate,
    _mr_validate_modes as _mr_validate_modes,
    _mr_write_frontmatter as _mr_write_frontmatter,
)


# ===========================================================================
# WP07 (tasks-py-degod-wave2-01KWH9EQ / FR-001, FR-012): the ``status`` family
# — ``_do_status``, the 14 ``_st_*`` phase helpers, ``_StatusState`` and
# ``_default_status_ports`` — lives in ``tasks_status_cmd`` (moved VERBATIM;
# the ``_cmd`` suffix keeps it distinct from the WP05 pure aggregation core in
# ``tasks_status_view``). Every moved symbol is re-imported here in the
# explicit ``as`` re-export form so ``tasks.<name>`` stays a module attribute —
# the seam surface (NFR-002). The relocated bodies route every patched seam
# symbol back through ``_tasks.<attr>`` (lazy in-function import, research.md
# D1/D7), so ``@patch("...agent.tasks.<sym>")`` / ``monkeypatch.setattr(tasks,
# ...)`` keep INTERCEPTING (incl. the ``build_status_view`` sentinel seam, the
# conftest ``console`` rebinding, ``get_status_read_root`` and the port
# adapters constructed by the moved ``_default_status_ports`` — the ONE
# indent=2 ``--json`` envelope, byte-frozen). The ``@app.command`` Typer
# wrapper below stays here: the CLI surface (byte-frozen ``--help``) belongs
# to the registration shim. Per-symbol evidence:
# kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md.
# ===========================================================================
from specify_cli.cli.commands.agent.tasks_status_cmd import (
    _StatusState as _StatusState,
    # WP09 (FR-008, IC-07): the four family stragglers that stayed behind at
    # WP07 — the review-stall threshold reader, the human-in-charge marker and
    # the staleness shapers — relocated in the final registration-shim sweep.
    # Explicit ``as`` re-exports: each is a live
    # ``@patch("...agent.tasks.<name>")`` / direct-import seam
    # (test_tasks_status_cmd_seam.py, test_human_in_charge_profile.py).
    _apply_stale_status_fields as _apply_stale_status_fields,
    _default_status_ports as _default_status_ports,
    _do_status as _do_status,
    _get_hic_marker as _get_hic_marker,
    _render_stale_status as _render_stale_status,
    _review_stall_threshold_minutes as _review_stall_threshold_minutes,
    _st_apply_review_flags as _st_apply_review_flags,
    _st_board_cell as _st_board_cell,
    _st_emit_json as _st_emit_json,
    _st_load_work_packages as _st_load_work_packages,
    _st_render_active as _st_render_active,
    _st_render_arbiter as _st_render_arbiter,
    _st_render_board as _st_render_board,
    _st_render_human as _st_render_human,
    _st_render_overview as _st_render_overview,
    _st_render_planned as _st_render_planned,
    _st_render_review_queues as _st_render_review_queues,
    _st_render_summary as _st_render_summary,
    _st_resolve_dirs as _st_resolve_dirs,
    _st_resolve_execution_mode as _st_resolve_execution_mode,
)


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


# ===========================================================================
# WP08 (tasks-py-degod-wave2-01KWH9EQ / FR-001, FR-002): the ``mark-status``
# family — ``_do_mark_status``, the 9 ``_ms_*`` phase helpers,
# ``_MarkStatusState`` and ``_default_mark_status_ports`` — lives in
# ``tasks_mark_status`` (moved VERBATIM). Every moved symbol is re-imported
# here in the explicit ``as`` re-export form so ``tasks.<name>`` stays a
# module attribute — the seam surface (NFR-002). The relocated bodies route
# every patched seam symbol back through ``_tasks.<attr>`` (lazy in-function
# import, research.md D1/D7), so ``@patch("...agent.tasks.<sym>")`` /
# ``monkeypatch.setattr(tasks, ...)`` keep INTERCEPTING (incl. the heavy
# ``feature_status_lock`` and ``emit_history_added`` seams,
# ``_protected_branch_status_commit_error`` (C-001 REFUSE arm — no skip
# pre-gate, harness label T005), ``_resolve_inline_subtasks`` (which stays
# ``tasks.py``-resident below) and the port adapters constructed by the moved
# ``_default_mark_status_ports``). The ``@app.command`` Typer wrapper below
# stays here: the CLI surface (byte-frozen ``--help``) belongs to the
# registration shim. Per-symbol evidence:
# kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md.
# ===========================================================================
from specify_cli.cli.commands.agent.tasks_mark_status import (
    _MarkStatusState as _MarkStatusState,
    _default_mark_status_ports as _default_mark_status_ports,
    _do_mark_status as _do_mark_status,
    _ms_apply_updates as _ms_apply_updates,
    _ms_commit as _ms_commit,
    _ms_dossier_sync as _ms_dossier_sync,
    _ms_emit_history as _ms_emit_history,
    _ms_output as _ms_output,
    _ms_report_none_resolved as _ms_report_none_resolved,
    _ms_resolve_context as _ms_resolve_context,
    _ms_resolve_read_dir as _ms_resolve_read_dir,
    _ms_validate_inputs as _ms_validate_inputs,
    # WP09 (FR-008, IC-07): the family straggler that stayed behind at WP08 —
    # the inline-Subtasks resolver — relocated in the final registration-shim
    # sweep. Explicit ``as`` re-export: a live
    # ``@patch("...agent.tasks._resolve_inline_subtasks")`` seam
    # (test_tasks_mark_status_seam.py) that ``_ms_apply_updates`` routes back
    # through ``_tasks.<attr>``.
    _resolve_inline_subtasks as _resolve_inline_subtasks,
)


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

        # Load canonical lanes from event log (STATUS-partition — stays coord-aware, C-001).
        # read-surface-ssot-closeout WP08 / FR-001 / NFR-001: routed through the
        # kind-aware placement seam instead of the kind-blind
        # resolve_feature_dir_for_mission (same coord-aware STATUS_STATE resolution).
        _lt_feature_dir = placement_seam(main_repo_root, mission_slug).read_dir(
            MissionArtifactKind.STATUS_STATE
        )
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
            render = RealRender()
            print(render.json_envelope({"tasks": tasks, "count": len(tasks)}))
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


# ===========================================================================
# WP08 (tasks-py-degod-wave2-01KWH9EQ / FR-001, FR-010): the ``finalize-tasks``
# family — ``_do_finalize_tasks``, the 4 ``_ft_*`` phase helpers,
# ``_FinalizeState`` and ``_default_finalize_ports`` — lives in
# ``tasks_finalize`` (moved VERBATIM; the squad-recovered FIFTH family — after
# this move ALL five command families are out of this module). Every moved
# symbol is re-imported here in the explicit ``as`` re-export form so
# ``tasks.<name>`` stays a module attribute — the seam surface (NFR-002). The
# relocated bodies route every patched seam symbol back through
# ``_tasks.<attr>`` (lazy in-function import, research.md D1/D7), so
# ``@patch("...agent.tasks.<sym>")`` / ``monkeypatch.setattr(tasks, ...)``
# keep INTERCEPTING (incl. ``bootstrap_canonical_state``, the conftest
# ``console`` rebinding and the port adapters constructed by the moved
# ``_default_finalize_ports`` — the plain ``RealCoordCommitRouter``; finalize
# has ZERO direct emission sites, research.md D3). read-surface-ssot-closeout
# WP08: the former ``resolve_feature_dir_for_mission`` pre30-guard-wiring seam
# is RETIRED — ``_ft_apply_writes`` now calls
# ``mission_runtime.placement_seam(...).read_dir(STATUS_STATE)`` directly
# (no ``_tasks.<attr>`` proxy for this symbol). The
# ``@app.command`` Typer wrapper below stays here: the CLI surface
# (byte-frozen ``--help``) belongs to the registration shim. Per-symbol
# evidence: kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md.
# ===========================================================================
from specify_cli.cli.commands.agent.tasks_finalize import (
    _FinalizeState as _FinalizeState,
    _default_finalize_ports as _default_finalize_ports,
    _do_finalize_tasks as _do_finalize_tasks,
    _ft_apply_writes as _ft_apply_writes,
    _ft_output as _ft_output,
    _ft_resolve_context as _ft_resolve_context,
    _ft_validate as _ft_validate,
    _ft_validate_occurrence_map_ready as _ft_validate_occurrence_map_ready,
)


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

        # Get lane from event log (canonical source).
        # read-surface-ssot-closeout WP08 / FR-001 / NFR-001: routed through the
        # kind-aware placement seam instead of the kind-blind
        # resolve_feature_dir_for_mission (same coord-aware STATUS_STATE resolution;
        # ``repo_root`` — not ``_vw_main_repo_root`` — is preserved unchanged, matching
        # the pre-existing call's argument).
        _vw_feature_dir = placement_seam(repo_root, mission_slug).read_dir(
            MissionArtifactKind.STATUS_STATE
        )
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
            render = RealRender()
            print(render.json_envelope(result))
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
            render = RealRender()
            print(render.json_envelope({"wp_id": wp_id, "depends_on": own_deps, "dependents": dependents}))
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
