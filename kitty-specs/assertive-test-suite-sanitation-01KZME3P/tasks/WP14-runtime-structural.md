---
work_package_id: WP14
title: Runtime coordination structural sanitation
dependencies: [WP01]
requirement_refs: [FR-003, FR-006, FR-007, FR-008, FR-014, FR-016, NFR-002, NFR-003, NFR-007, NFR-009, NFR-010]
planning_base_branch: pr/assertive-test-suite-sanitation
merge_target_branch: pr/assertive-test-suite-sanitation
branch_strategy: Planning artifacts for this mission were generated on pr/assertive-test-suite-sanitation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/assertive-test-suite-sanitation unless the human explicitly redirects the landing branch.
subtasks: [T066, T067, T068, T069, T070]
history:
- status: planned
  at: '2026-08-10T01:00:00Z'
  actor: codex
  note: Added after analyze split mixed structural cohorts by authority family
authoritative_surface: tests/architectural/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP14.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp14-results.json
execution_mode: code_change
owned_files:
- tests/coordination/test_verdict_dir_co_resolution.py
- tests/mission_runtime/test_write_target_degrade.py
- tests/next/test_retrospective_terminus_wiring.py
- tests/runtime/test_bridge_compat_surface.py
- tests/runtime/test_bridge_decide_next.py
- tests/runtime/test_bridge_engine.py
- tests/runtime/test_bridge_retrospective.py
- tests/runtime/test_runtime_bridge_family_arch.py
- tests/runtime/test_setup_plan_sync_evidence.py
- tests/specify_cli/cli/commands/agent/test_record_analysis_double_resolution.py
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py
- tests/specify_cli/cli/commands/agent/test_tasks_coreless_orchestration.py
- tests/specify_cli/cli/commands/agent/test_workflow_placement_routing.py
- tests/specify_cli/cli/commands/test_coordination_doctor.py
- tests/specify_cli/cli/commands/test_daemon_doctor.py
- tests/specify_cli/cli/commands/test_mission_state_doctor.py
- tests/specify_cli/cli/commands/test_workspace_husk_doctor.py
- tests/specify_cli/coordination/test_commit_router_planning_residue.py
- tests/specify_cli/coordination/test_partition_authority_characterization.py
- tests/specify_cli/coordination/test_wp05_status_read_contract.py
- tests/specify_cli/status/test_inert_field_reduction.py
- tests/specify_cli/status/test_wp_state.py
- tests/specify_cli/test_clock_consolidation.py
- tests/specify_cli/workspace/test_context_worktree_routing.py
- tests/status/test_aggregate_surface_resolution.py
- tests/architectural/test_commit_target_kind_guard.py
- tests/architectural/test_coord_rollback_coherence_guard.py
- tests/architectural/test_events_tracker_public_imports.py
- tests/architectural/test_mission_runtime_surface.py
- tests/architectural/test_no_absolute_event_timestamp_mixture.py
- tests/architectural/test_no_phantom_worktree_repair.py
- tests/architectural/test_no_production_worktree_guard_bypass.py
- tests/architectural/test_no_raw_mission_spec_paths.py
- tests/architectural/test_no_tracked_test_feature_missions.py
- tests/architectural/test_no_worktree_name_guess.py
- tests/architectural/test_pre_review_scope_singlesource.py
- tests/architectural/test_resume_non_reemission_guard.py
- tests/architectural/test_safe_commit_import_boundary.py
- tests/architectural/test_session_reaper.py
- tests/architectural/test_status_command_guidance.py
- tests/architectural/test_status_module_boundary.py
- tests/architectural/test_status_sync_boundary.py
- tests/architectural/test_tasks_command_surface.py
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/test_verdict_vocab_single_source.py
- tests/architectural/test_worktrees_index_clean.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP14.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp14-results.json
tags: []
tracker_refs: ['#1931']
---

# WP14 — Runtime Coordination Structural Sanitation

## Do First

Load `architect-alphonso`; read FR-006/FR-007 and current runtime/mission/status/coordination authorities. Verify tracker state, reconcile WP01 manifest, claim WP14 canonically, use only its worktree.

## Objective

Adjudicate runtime, mission, status, event, worktree, and coordination structural guards as one coherent operational-authority family.

## T066 — Family Census

- Record current authority, live corpus, scanner/oracle, route, positive/negative shape, and consumers for every assigned file; terminalize all.
- Valid family grouping requires the same operational path, authority, corpus, oracle, and fault.

## T067 — Assertive Reduction

- Delete historical mission/WP artifacts, exact status prose/names, positive layout pins, and advisory-only checks.
- Reduce mixed files to smallest live negative invariant; no production behavior edits.

## T068 — Survivor Proof

- Every survivor/family needs nonzero corpus and a realistic prohibited runtime/coordination change that reaches Act and fails intended assertion.
- Require compliant control; collection/import/setup failure is invalid proof.

## T069 — Validation/Evidence

- Run focused survivors and lint/type checks; record terminal rows, commands, environments, faults, costs, and deltas.

## T070 — Integration Handoff

- Emit deleted/renamed paths for WP07; central map remains WP07-only. Commit owned files cleanly.

## Definition of Done

- [ ] 100% assigned-file terminal coverage.
- [ ] Every survivor has node/family causal proof.
- [ ] Focused validation and deterministic map handoff complete.

## Reviewer Guidance

Sample each operational subfamily. Reject exact event/status wording and completed-worktree history as current invariants.

## Commit

`git commit -m "test(WP14): sanitize runtime structural guards"`
