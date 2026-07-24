"""Consolidated re-export identity guard for the ``tasks`` compat surface
(mission ``dev-assist-retire-path-hardening-01KXAVR0``, WP05a / #2565).

The ``tasks.py`` wave-2 decomposition (mission ``tasks-py-degod-wave2-01KWH9EQ``)
left 6 sibling ``test_tasks_*_seam.py`` files, each carrying its own
``test_tasks_binding_is_<seam>_object`` identity battery (parametrized over a
private ``_MOVE_SET``) plus an exact-set ``test_move_set_matches_<seam>_defs``
completeness pin. The identity coverage is the one piece of that scaffolding
with no golden-file duplicate elsewhere — it is the only thing standing
between a future extraction and a silently dropped ``tasks.<name>`` re-export
(a historical ``@patch("...agent.tasks.<name>")`` or
``from ...agent.tasks import <name>`` edge going stale). This module folds
all 6 batteries into ONE guard so that coverage lives in a single place next
to the compat surface it protects, instead of scattered across 6 files that
are being retired piecemeal (WP05a here; WP05b/WP06 retires the remaining 3
heavy seams' batteries against the coverage this guard already provides).

Shape mirrors ``test_mission_shim_reexports.py`` (grouped required-symbol
tuples + a ``hasattr``/identity parametrized gate) and
``tests/runtime/test_bridge_compat_surface.py`` (a re-derived-from-source
completeness check rather than a hand-maintained list trusted on faith).
Self-contained: no import of the 6 seam test files' internal ``_MOVE_SET``
tuples (those files are being retired around this guard) — the map below is
this file's own literal data, and the completeness check re-derives the
seams' surface straight from the production ``tasks_*.py`` modules.

Two guarantees:

1. **Identity re-export.** For every ``(symbol, residual_module)`` pair,
   ``tasks.<symbol> is <residual_module>.<symbol>`` — the SAME object, not a
   coincidental native redefinition on ``tasks`` that happens to compare
   equal.
2. **Genuine origin + superset coverage.** Every mapped symbol is confirmed
   to be natively defined in its claimed residual module (catches a
   mis-mapped row), and the union of all 6 residual modules' natively
   defined symbols is re-derived from source and asserted to be a SUBSET of
   this guard's key-set — so a symbol dropped from the map here, while still
   defined in the seam module, fails loudly right next to the guard instead
   of silently losing coverage.
"""

from __future__ import annotations

import pytest

from specify_cli.cli.commands.agent import (
    tasks,
    tasks_finalize,
    tasks_map_requirements,
    tasks_mark_status,
    tasks_move_task,
    tasks_shared,
    tasks_status_cmd,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Per-seam symbol groups — one tuple per residual module, mirroring each
# retired seam file's own ``_MOVE_SET`` (grouped for readability; the guard
# treats the union as one required key-set). Counts noted per group for
# traceability against the seam files' own docstring counts at authoring
# time (finalize=8, map_requirements=15, shared=20, status_cmd=21,
# move_task=65, mark_status=13 — 142 total). WP04 (#2684) added two net-new
# natively-defined symbols atop that baseline: ``_legacy_unchecked_subtask_ids``
# (shared=21) and ``_ms_emit_subtask_state`` (mark_status=14) — 144 total. #2816
# WP13 (IC-10) then retired ``_legacy_unchecked_subtask_ids`` (shared 21 -> 20)
# when the guard stopped reading checkbox rows.
# ---------------------------------------------------------------------------

_TASKS_FINALIZE: tuple[str, ...] = (  # WP08 (wave2) — 8 symbols
    "_FinalizeState",
    "_default_finalize_ports",
    "_ft_resolve_context",
    "_ft_validate",
    "_ft_validate_occurrence_map_ready",
    "_ft_apply_writes",
    "_ft_output",
    "_do_finalize_tasks",
)

_TASKS_MAP_REQUIREMENTS: tuple[str, ...] = (  # WP06 (wave2) — 15 symbols
    "_default_map_requirements_ports",
    "_MapReqState",
    "_mr_validate_modes",
    "_mr_resolve_context",
    "_mr_build_new_mappings",
    "_mr_unknown_wp_gate",
    "_mr_resolve_read_dirs",
    "_mr_plan",
    "_mr_gate_offenders",
    "_mr_write_frontmatter",
    "_mr_stale_gate",
    "_mr_auto_commit",
    "_mr_emit_output",
    "_do_map_requirements",
    "_map_requirements_feature_dir",
)

_TASKS_SHARED: tuple[str, ...] = (  # WP02 (wave2) — 20 symbols
    # ``resolve_primary_branch`` removed by FR-007 (mission
    # primary-merge-vocabulary, WP04): the delegating shim was retired so the
    # canonical ``core.git_ops.resolve_primary_branch`` is the single source
    # (21 -> 20; total 141 -> 140).
    "_review_currency_check_branch",
    "_RUNTIME_STATE_DENY_LIST",
    "_filter_runtime_state_paths",
    "_emit_sparse_session_warning",
    "_ensure_target_branch_checked_out",
    "_find_mission_slug",
    "_output_result",
    "_output_error",
    "_protected_branch_status_commit_error",
    "_coord_topology_active",
    "_skip_target_branch_commit",
    "_mission_identity_payload",
    "_resolve_git_common_dir",
    "_check_unchecked_subtasks",
    "_validate_ready_for_review",
    "_wp_branch_merged_into_target",
    "_filter_by_planning_tip_content",
    "_list_wp_branch_mission_specs_changes",
    "_list_wp_branch_specs_changes_for_guard",
    "_mark_status_json_payload",
)

_TASKS_STATUS_CMD: tuple[str, ...] = (  # WP07 (wave2) — 23 symbols (#2816: +gated runtime seam, +reconstruct-reader row)
    "_default_status_ports",
    "_StatusState",
    "_st_resolve_dirs",
    "_st_gated_runtime_fields",
    "_st_runtime_row",
    "_st_resolve_execution_mode",
    "_st_load_work_packages",
    "_st_apply_review_flags",
    "_st_emit_json",
    "_st_board_cell",
    "_st_render_overview",
    "_st_render_board",
    "_st_render_arbiter",
    "_st_render_review_queues",
    "_st_render_active",
    "_st_render_planned",
    "_st_render_summary",
    "_st_render_human",
    "_do_status",
    "_review_stall_threshold_minutes",
    "_get_hic_marker",
    "_apply_stale_status_fields",
    "_render_stale_status",
)

_TASKS_MOVE_TASK: tuple[str, ...] = (  # WP05 (wave2); grown to 75 via WP09, +1 (_binding_role_for_lane) = 76, -1 (_mt_pre_review_gate_verdict retired, WP04) = 75
    # (#2513/#2160: +uncheck/clear-markers/reset-rollback; #2573: +gate
    # skip-reason pair; WP07 #2649: +param-object + commit/uncheck degod helpers;
    # #2639: +complete-deferred-readiness + pre-review-dirty-paths;
    # coord-commit-integrity #2861: +_binding_role_for_lane role-map dedup)
    "_binding_role_for_lane",
    "_default_move_task_ports",
    "_MoveTaskState",
    "_MoveTaskArgs",
    "_mt_warn_worktree_kitty_specs",
    "_mt_resolve_targets",
    "_mt_resolve_feedback",
    "_mt_build_request",
    "_lane_deliverable_paths",
    "_mt_commit_lane_deliverables",
    "_mt_complete_deferred_for_review_readiness",
    "_mt_gather_review_facts",
    "_mt_fire_override_persist",
    "_mt_done_ancestry_facts",
    "_mt_issue_matrix_facts",
    "_mt_approval_facts",
    "_mt_gather_late_facts",
    "_mt_fire_arbiter_persist",
    "_mt_run_decision",
    "_mt_finalize_plan",
    "_mt_current_event_lane",
    "_mt_hop_review_result",
    "_mt_hop_actor",
    "_mt_emit_transitions",
    # WP10 (wp-runtime-state-eviction, closeout reconciliation): the god-write
    # cut (WP06/WP07, FR-006/FR-007/FR-008) DELETED the frontmatter-writing
    # runtime-state family — ``_mt_persist_tracker_refs`` (tracker refs now an
    # off-axis union delta), ``_mt_clear_rollback_claim_markers`` /
    # ``_mt_uncheck_rollback_subtasks`` / ``_mt_attempt_uncheck_write`` /
    # ``_mt_commit_uncheck_tasks_md`` / ``_mt_reset_for_planned_rollback`` (the
    # rollback-to-planned reset is now an event-sourced ``InnerStateChanged``
    # ``subtasks`` delta). Their rows are removed from this guard; the six
    # event-sourcing helpers that REPLACED them are added below. The unit test
    # modules that imported the deleted symbols are reconciled in the same
    # closeout.
    "_mt_persist_wp_file",
    "_mt_release_review_lock",
    # WP10 closeout: the event-sourcing helpers WP06/WP07 added to the move_task
    # seam (off-axis runtime-state emit, claim-triple policy_metadata packer,
    # review planner, rollback subtask-reset delta builder, shell-pid baseline
    # reader, current-agent resolver). Each is a genuine native def with an
    # identity re-export on ``tasks``, so it joins the compat surface like every
    # other def. #2816/IC-04 (runtime-state-corpus-cutover, WP05) deleted the
    # flag-OFF ``_mt_dual_write_wp_file`` bridge (the last dual-write path was
    # cut) and added ``_mt_resolve_current_agent`` (the ownership-read reroute
    # onto the snapshot seam) — reconciled here (net 0).
    "_mt_emit_runtime_state",
    "_mt_reassignment_binding_fields",
    "_mt_resolve_current_agent",
    "_mt_hop_policy_metadata",
    "_mt_plan_review_result",
    "_mt_rollback_subtasks_reset",
    "_mt_shell_pid_baseline",
    "_mt_execute",
    "_mt_output",
    "_do_move_task",
    "_coord_status_events_path",
    "_status_event_result_fields",
    "_detect_reviewer_name",
    "_detect_arbiter_override",
    "_run_arbiter_override",
    "_mt_run_pre_review_gate",
    # WP09 (doctrine-controlled-transition-gates-01KY51Z7): the inverted,
    # doctrine-resolved transition gate + its thin-orchestrator helpers. Barrel
    # lines + tuple entries move together (P-F1); the forwarder
    # ``_mt_run_pre_review_gate`` above stays a real symbol delegating to
    # ``_mt_run_transition_gates``.
    "_mt_run_transition_gates",
    "_TransitionGateInputs",
    "_TransitionGateEffect",
    "_mt_warn_pre_review_test_command_deprecated",
    "_mt_resolve_scope_source",
    "_mt_resolve_active_gate_bindings",
    "_mt_resolve_gate_baseline",
    "_mt_build_transition_gate_context",
    "_mt_cancelled_verdict",
    "_mt_fail_open_gate",
    "_mt_resolve_transition_gate_verdicts",
    "_mt_dispatch_one_gate",
    "_mt_dispatch_transition_gates",
    "_mt_collect_transition_gate_verdicts",
    "_mt_resolve_transition_gate_inputs",
    "_mt_gate_representative",
    "_mt_translate_gate_verdicts",
    "_mt_emit_skipped_gate",
    "_mt_emit_transition_gate_effect",
    "_mt_resolve_pre_review_workspace",
    "_mt_pre_review_changed_files",
    "_mt_pre_review_dirty_paths",
    "_mt_pre_review_gate_with_override_scope",
    "_mt_empty_scope_verdict",
    # WP16 (lifecycle-gate-execution-context-01KY72GQ, IC-07f): the retired
    # new_checkout_paths byproduct-diff now enrols the gate subprocess's
    # created paths into the tool-artifact owner compensator.
    "_mt_enrol_gate_byproducts",
    "_mt_pre_review_gate_metadata",
    "_mt_pre_review_gate_console_warning",
    "_mt_pre_review_gate_block_message",
    "_mt_review_config_section",
    "_mt_pre_review_block_enabled",
    # #2573 fast-follow: the --skip-pre-review-gate flag + disable-env seam.
    "_mt_pre_review_gate_env_disable_reason",
    "_mt_pre_review_gate_skip_reason",
    "_mt_pre_review_scope_override",
    "_pre_review_gate_filter_groups",
    "_pre_review_gate_composite_routing",
)

_TASKS_MARK_STATUS: tuple[str, ...] = (  # WP08 (wave2) — 13 symbols
    "_MarkStatusState",
    "_default_mark_status_ports",
    "_ms_validate_inputs",
    "_ms_resolve_context",
    "_ms_resolve_read_dir",
    "_ms_report_none_resolved",
    "_ms_commit",
    "_ms_apply_updates",
    "_ms_emit_subtask_state",
    "_ms_emit_history",
    "_ms_dossier_sync",
    "_ms_output",
    "_do_mark_status",
    "_resolve_inline_subtasks",
)

#: seam-module-name -> imported module object, and -> that seam's required
#: symbol tuple. Both keyed by the same short name used in the seam test
#: files' own module names (``test_tasks_<name>_seam.py``) for easy
#: cross-reference.
_SEAM_MODULES = {
    "tasks_finalize": tasks_finalize,
    "tasks_map_requirements": tasks_map_requirements,
    "tasks_shared": tasks_shared,
    "tasks_status_cmd": tasks_status_cmd,
    "tasks_move_task": tasks_move_task,
    "tasks_mark_status": tasks_mark_status,
}

_SEAM_GROUPS: dict[str, tuple[str, ...]] = {
    "tasks_finalize": _TASKS_FINALIZE,
    "tasks_map_requirements": _TASKS_MAP_REQUIREMENTS,
    "tasks_shared": _TASKS_SHARED,
    "tasks_status_cmd": _TASKS_STATUS_CMD,
    "tasks_move_task": _TASKS_MOVE_TASK,
    "tasks_mark_status": _TASKS_MARK_STATUS,
}

#: symbol -> residual (seam) module name. Built explicitly (not via a dict
#: comprehension over possibly-colliding keys) so a future accidental symbol
#: collision across two seams' tuples raises HERE at import time rather than
#: silently overwriting one seam's mapping with another's.
SYMBOL_TO_MODULE: dict[str, str] = {}
for _module_name, _symbols in _SEAM_GROUPS.items():
    for _symbol in _symbols:
        if _symbol in SYMBOL_TO_MODULE:
            raise AssertionError(
                f"symbol {_symbol!r} claimed by both {SYMBOL_TO_MODULE[_symbol]!r} "
                f"and {_module_name!r} — seam groups must be disjoint."
            )
        SYMBOL_TO_MODULE[_symbol] = _module_name

#: Non-callable natively-defined symbols per seam that the callable-based
#: native-def scan below would otherwise miss (module-level constants, not
#: functions/classes). Mirrors ``test_tasks_shared_seam.py``'s
#: ``module_defs.add("_RUNTIME_STATE_DENY_LIST")`` precedent.
_EXTRA_NON_CALLABLE_NATIVE_DEFS: dict[str, frozenset[str]] = {
    "tasks_shared": frozenset({"_RUNTIME_STATE_DENY_LIST"}),
}


def _native_module_defs(module_name: str) -> set[str]:
    """Re-derive a seam module's natively-defined public/private surface.

    Same technique each retired seam file used for its own completeness pin
    (``getattr(obj, "__module__", None) == module.__name__ and callable(obj)``),
    generalized across all 6 modules plus the one known non-callable
    constant exception, so this guard's coverage claim is checked against
    production source rather than trusted on faith.
    """
    module = _SEAM_MODULES[module_name]
    callable_defs = {
        name
        for name, obj in vars(module).items()
        if getattr(obj, "__module__", None) == module.__name__ and callable(obj)
    }
    return callable_defs | set(_EXTRA_NON_CALLABLE_NATIVE_DEFS.get(module_name, frozenset()))


# ===========================================================================
# Guard 1 — identity re-export
# ===========================================================================


@pytest.mark.parametrize(
    "symbol,module_name",
    sorted(SYMBOL_TO_MODULE.items()),
    ids=[f"{mod}.{sym}" for sym, mod in sorted(SYMBOL_TO_MODULE.items())],
)
def test_tasks_binding_is_seam_object(symbol: str, module_name: str) -> None:
    """``tasks.<symbol>`` resolves and is the SAME object as
    ``<residual_module>.<symbol>`` — a genuine identity re-export, not a
    coincidental native redefinition on ``tasks``."""
    seam_module = _SEAM_MODULES[module_name]
    assert hasattr(tasks, symbol), (
        f"tasks.{symbol} no longer resolves — a re-export from {module_name} "
        "was dropped."
    )
    assert getattr(tasks, symbol) is getattr(seam_module, symbol), (
        f"tasks.{symbol} is NOT the same object as {module_name}.{symbol} — "
        "the compat re-export is a copy, not an identity re-export (breaks "
        "monkeypatch/mocker.patch interception on tasks.<name>)."
    )


# ===========================================================================
# Guard 2 — genuine origin + superset coverage
# ===========================================================================


@pytest.mark.parametrize(
    "symbol,module_name",
    sorted(SYMBOL_TO_MODULE.items()),
    ids=[f"{mod}.{sym}" for sym, mod in sorted(SYMBOL_TO_MODULE.items())],
)
def test_guard_symbol_is_genuinely_native_to_its_seam(symbol: str, module_name: str) -> None:
    """Every mapped symbol is confirmed to actually originate in the seam
    module the guard claims — catches a mis-mapped row (e.g. a symbol
    attributed to the wrong seam) that a bare identity check alone would not
    reliably surface."""
    assert symbol in _native_module_defs(module_name), (
        f"{symbol!r} is mapped to {module_name!r} in the guard but is not "
        f"natively defined there — check SYMBOL_TO_MODULE / the seam group."
    )


def test_guard_keyset_is_superset_of_all_six_seams_native_defs() -> None:
    """The guard's key-set must be a superset of the union of all 6 residual
    modules' natively-defined symbols, re-derived straight from production
    source — so a symbol dropped from this guard (while still defined in its
    seam module) fails HERE, loudly, instead of silently losing coverage.

    This is the guard that satisfies coverage-before-deletion for the
    remaining heavy seams' scaffolding retirement.
    """
    union_of_native_defs: set[str] = set()
    for module_name in _SEAM_MODULES:
        union_of_native_defs |= _native_module_defs(module_name)

    guard_keys = set(SYMBOL_TO_MODULE)
    missing = union_of_native_defs - guard_keys
    assert not missing, (
        "Symbols natively defined in a seam module but missing from the "
        f"consolidated compat guard: {sorted(missing)}"
    )
    assert union_of_native_defs <= guard_keys


def test_no_required_symbol_duplicated_in_survey() -> None:
    """The 6 seam groups must stay disjoint (catches copy-paste across
    groups; ``SYMBOL_TO_MODULE`` construction above already raises on a
    collision, this pins the resulting invariant directly)."""
    total_declared = sum(len(symbols) for symbols in _SEAM_GROUPS.values())
    assert total_declared == len(SYMBOL_TO_MODULE)


def test_guard_covers_full_142_symbol_surface() -> None:
    """Traceability pin: the guard's total symbol count matches the sum of
    the 6 seams' counts recorded in the seam files' own docstrings at
    authoring time (8 + 15 + 20 + 21 + 65 + 13 = 142). A change here is
    expected when a future WP relocates symbols; it should be a deliberate,
    reviewed edit — not a silent drift. #2513/#2160 added
    ``_mt_uncheck_rollback_subtasks``, ``_mt_clear_rollback_claim_markers`` and
    ``_mt_reset_for_planned_rollback`` to the tasks_move_task seam (51 -> 54).
    #2573 fast-follow added ``_mt_pre_review_gate_env_disable_reason`` and
    ``_mt_pre_review_gate_skip_reason`` (54 -> 56). WP07
    (loop-friction-quickwins-2-01KXBWA4, T025, #2555.1) added
    ``_mt_untracked_planning_artifact_paths`` and ``_write_wp_fallback``
    (56 -> 58). WP07 (implement-loop-commit-hardening-01KXJ1ZX, #2649) added
    the ``_MoveTaskArgs`` param object plus the ``_mt_commit_wp_file`` /
    ``_mt_uncheck_rollback_subtasks`` degod helpers (``_mt_wp_commit_message``,
    ``_mt_report_commit_outcome``, ``_mt_attempt_uncheck_write``,
    ``_mt_commit_uncheck_tasks_md``) (58 -> 63). FR-007
    (primary-merge-vocabulary, WP04) retired the ``tasks_shared``
    ``resolve_primary_branch`` delegating shim (tasks_shared 21 -> 20). #2639
    (pre-review transitions observable/interruption-safe) added
    ``_mt_complete_deferred_for_review_readiness`` and
    ``_mt_pre_review_dirty_paths`` (63 -> 65). Net tasks-surface total
    141 -> 142. WP04 (#2684, subtask-emit + reader-delegate) added
    ``_legacy_unchecked_subtask_ids`` (tasks_shared 20 -> 21) and
    ``_ms_emit_subtask_state`` (tasks_mark_status 13 -> 14): 142 -> 144.
    #2816 Phase B (bypass-reader gating) added ``_st_gated_runtime_fields``
    (tasks_status_cmd 21 -> 22): 144 -> 145. #2816 WP11 (IC-07 reconstruction
    reader) added ``_st_runtime_row`` — the board's snapshot read routed through
    the one ``reconstruct_wp_view`` reader (tasks_status_cmd 22 -> 23): 145 -> 146.
    #2816/IC-04 (runtime-state-corpus-cutover, WP05) then swapped the
    tasks_move_task seam's ``_mt_dual_write_wp_file`` (deleted with the last
    dual-write path) for ``_mt_resolve_current_agent`` (the ownership-read
    snapshot reroute): net 0, still 146. #2816/IC-06 (runtime-state-corpus-cutover,
    WP07) then deleted the now production-dead WP-file write/commit closure that
    WP05 orphaned when it removed ``_mt_dual_write_wp_file`` (the last caller):
    ``_mt_commit_wp_file``, ``_mt_write_and_commit_wp_file``,
    ``_mt_wp_commit_message``, ``_mt_report_commit_outcome``,
    ``_mt_wp_commit_success_message``, ``_write_wp_fallback``,
    ``_mt_untracked_planning_artifact_paths``, ``_mt_resolve_status_placement_ref``
    and ``_primary_bundle_status_artifacts`` (tasks_move_task 65 -> 56):
    146 -> 137. #2816 WP13 (IC-10, subtask-completion event-sourced) then retired
    ``_legacy_unchecked_subtask_ids`` — the guard's only live caller stopped
    reading checkbox rows (tasks_shared 21 -> 20): 137 -> 136. The resolved-
    binding reassignment helper is a native move-task seam and therefore joins
    the registration-shim compatibility surface: 136 -> 137. WP09
    (doctrine-controlled-transition-gates-01KY51Z7) inverted the pre-review gate
    into ``_mt_run_transition_gates`` and its thin-orchestrator extraction: two
    dataclasses (``_TransitionGateInputs``/``_TransitionGateEffect``) and 13 new
    ``_mt_*`` helpers join the tasks_move_task seam (56 -> 71): 137 -> 152. WP09
    remediation (metadata-fidelity fix) then extracted ``_mt_resolve_gate_baseline``
    — the shared baseline loader the restored FR-004 override tier and the handler
    context both call — a native move-task seam def (71 -> 72): 152 -> 153. WP09
    closeout (CI compat-surface remediation) then registered the three remaining
    natively-defined move-task seam defs the extraction left unregistered —
    ``_mt_cancelled_verdict``, ``_mt_fail_open_gate`` and
    ``_mt_resolve_transition_gate_verdicts`` (72 -> 75): 153 -> 156. coord-commit-
    integrity (#2861, FR-005) added ``_binding_role_for_lane`` — the lane->role
    map dedup extracted from the two duplicate role maps at the move-task emit
    seam (tasks_move_task 75 -> 76): 156 -> 157. scopesource-gate-followup-01KY6S9P
    (WP04, #2873) then retired ``_mt_pre_review_gate_verdict`` — the census-derived
    composition helper had no production call site (the sole live ``for_review``
    path always injects a ``scope_source``, never omits it) — and its ``tasks.py``
    compat re-export (tasks_move_task 76 -> 75): 157 -> 156. WP16
    (lifecycle-gate-execution-context-01KY72GQ, IC-07f) retired
    ``new_checkout_paths`` and added ``_mt_enrol_gate_byproducts`` — the gate
    subprocess's created-path diff now enrols into the tool-artifact owner
    compensator (commit-on-pass via no-op, revert-on-abort via
    ``restore_generated_artifact_snapshots``) instead of being detected and
    warned about (tasks_move_task 75 -> 76): 156 -> 157."""
    assert len(SYMBOL_TO_MODULE) == 157  # golden-count: cardinality-is-contract
