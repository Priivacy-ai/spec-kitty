---
work_package_id: WP11
title: Specify CLI duplicate consolidation
dependencies: [WP01]
requirement_refs: [FR-003, FR-005, FR-008, FR-014, FR-016, NFR-002, NFR-007, NFR-010]
planning_base_branch: pr/assertive-test-suite-sanitation
merge_target_branch: pr/assertive-test-suite-sanitation
branch_strategy: Planning artifacts for this mission were generated on pr/assertive-test-suite-sanitation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/assertive-test-suite-sanitation unless the human explicitly redirects the landing branch.
subtasks: [T076, T077, T078, T079, T080]
history:
- status: planned
  at: '2026-08-10T01:00:00Z'
  actor: codex
  note: Added after analyze enumerated the complete strict duplicate manifest
authoritative_surface: tests/specify_cli/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP11.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp11-results.json
execution_mode: code_change
owned_files:
- tests/specify_cli/acceptance/test_trio_read_seam_migration.py
- tests/specify_cli/bulk_edit/test_moves.py
- tests/specify_cli/bulk_edit/test_occurrence_map.py
- tests/specify_cli/bulk_edit/test_structural_targets.py
- tests/specify_cli/cli/commands/agent/test_tasks.py
- tests/specify_cli/cli/commands/agent/test_tasks_materialization.py
- tests/specify_cli/cli/commands/agent/test_tasks_outline.py
- tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py
- tests/specify_cli/cli/commands/agent/test_wp05_mission_coordination_routing.py
- tests/specify_cli/cli/commands/review/test_existing_matrix_remediation.py
- tests/specify_cli/cli/commands/test_charter_generate_autotrack.py
- tests/specify_cli/cli/commands/test_charter_widen.py
- tests/specify_cli/cli/commands/test_charter_widen_integration.py
- tests/specify_cli/cli/commands/test_implement_cores.py
- tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py
- tests/specify_cli/cli/commands/test_merge.py
- tests/specify_cli/compat/test_cache.py
- tests/specify_cli/compat/test_install_events.py
- tests/specify_cli/compat/test_planner.py
- tests/specify_cli/compat/test_registry.py
- tests/specify_cli/compat/test_remediation_index_url.py
- tests/specify_cli/compat/test_runtime.py
- tests/specify_cli/compat/test_upgrade_hint_chk028.py
- tests/specify_cli/context/test_resolver.py
- tests/specify_cli/contracts/test_registry.py
- tests/specify_cli/coordination/test_worktree_topology.py
- tests/specify_cli/core/test_config_registry.py
- tests/specify_cli/dashboard/test_glossary_handler.py
- tests/specify_cli/dashboard/test_lint_tile_handler.py
- tests/specify_cli/invocation/cli/test_invocations.py
- tests/specify_cli/migration/test_runtime_state_cutover.py
- tests/specify_cli/migration/test_runtime_state_cutover_placement.py
- tests/specify_cli/mission_step_contracts/test_executor.py
- tests/specify_cli/ownership/test_audit_scope.py
- tests/specify_cli/ownership/test_validation.py
- tests/specify_cli/regression/test_twelve_agent_parity.py
- tests/specify_cli/session_presence/test_agents_md_writer.py
- tests/specify_cli/session_presence/test_claude_code_hook.py
- tests/specify_cli/session_presence/test_content.py
- tests/specify_cli/session_presence/test_skills_preamble_writer.py
- tests/specify_cli/shims/test_direct_commands.py
- tests/specify_cli/shims/test_registry.py
- tests/specify_cli/test_feature_metadata.py
- tests/specify_cli/test_lane_regression_guard.py
- tests/specify_cli/test_mid8_caller_routing.py
- tests/specify_cli/test_mid8_contract_sensitive_routing.py
- tests/specify_cli/test_template_lane_guard.py
- tests/specify_cli/test_wp18_meta_reader_contracts.py
- tests/specify_cli/tool_surface/test_plugin_build_claude.py
- tests/specify_cli/tool_surface/test_plugin_build_codex.py
- tests/test_dashboard/test_glossary_handler.py
- tests/test_dashboard/test_lint_tile_handler.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP11.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp11-results.json
tags: []
tracker_refs: ['#1931']
---

# WP11 — Specify CLI Duplicate Consolidation

## Do First

Load `randy-reducer`; read FR-003/FR-005, current Specify CLI public/compatibility authorities, and both WP01 duplicate fingerprints. Verify tracker state, claim WP11 canonically, use only its worktree.

## Objective

Terminally adjudicate every strict/normalized duplicate family touching owned Specify CLI/dashboard files. Keep unique entry-point, compatibility, migration, or error boundaries; delete copied or dominated oracles.

## T076 — Manifest Reconciliation

- Map every owned member to all strict/normalized groups and a named owner/survivor. Unowned members trigger replan.
- Split family on production path, oracle, input, route, platform, outcome, or public-import divergence.

## T077 — CLI/Compatibility Families

- Adjudicate command, compat, context, contracts, migration, ownership, session, shim, and tool-surface groups.
- Prefer current live entry points; retain incompatible consumer/import/platform boundaries.

## T078 — Dashboard/Lane Families

- Consolidate glossary/lint dashboard twins and lane/template/mid8 guards after live-route comparison.
- Exact token/name pinning is not a distinct oracle.

## T079 — Causal Validation

- Every deletion names survivor and proves no unique non-equivalent fault kill; every changed/cited survivor has node/family causal proof.
- Run focused pytest, targeted mutation/fault probes, ruff, and store costs/deltas.

## T080 — Ledger/Handoff

- WP11 artifacts cover every owned group/member terminally; commit only owned files. WP07 consumes path deletions before routing.

## Definition of Done

- [ ] Every owned duplicate member/group terminally covered.
- [ ] No unique CLI/compatibility boundary lost; focused validation passes.
- [ ] Deterministic path handoff and clean commit exist.

## Reviewer Guidance

Independently trace live entry points. Reject syntax-only consolidation, mocked survivor replacing real CLI boundary, or family inheritance across compatibility paths.

## Commit

`git commit -m "test(WP11): consolidate specify cli duplicates"`
