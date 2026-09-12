---
work_package_id: WP12
title: Sync status and upgrade duplicate consolidation
dependencies: [WP01]
requirement_refs: [FR-003, FR-005, FR-008, FR-014, FR-016, NFR-002, NFR-007, NFR-010]
planning_base_branch: pr/assertive-test-suite-sanitation
merge_target_branch: pr/assertive-test-suite-sanitation
branch_strategy: Planning artifacts for this mission were generated on pr/assertive-test-suite-sanitation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/assertive-test-suite-sanitation unless the human explicitly redirects the landing branch.
subtasks: [T081, T082, T083, T084, T085]
history:
- status: planned
  at: '2026-08-10T01:00:00Z'
  actor: codex
  note: Added after analyze enumerated the complete strict duplicate manifest
authoritative_surface: tests/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP12.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp12-results.json
execution_mode: code_change
owned_files:
- tests/status/test_doctor.py
- tests/status/test_store.py
- tests/sync/test_auth.py
- tests/sync/test_batch_error_surfacing.py
- tests/sync/test_dossier_trigger.py
- tests/sync/test_event_emission.py
- tests/sync/test_events.py
- tests/sync/test_git_metadata.py
- tests/sync/tracker/test_config.py
- tests/sync/tracker/test_service.py
- tests/upgrade/test_activate_builtin_types_migration.py
- tests/upgrade/test_charter_rename_migration.py
- tests/upgrade/test_charter_template_migration.py
- tests/upgrade/test_m_0_12_0_documentation_mission_unit.py
- tests/upgrade/test_migration_charter_cleanup_unit.py
- tests/upgrade/test_migration_python_only_unit.py
- tests/upgrade/test_op_record_schema_v2_migration.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP12.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp12-results.json
tags: []
tracker_refs: ['#1931']
---

# WP12 — Sync, Status, and Upgrade Duplicate Consolidation

## Do First

Load `randy-reducer`; read FR-003/FR-005, current sync/status/upgrade authorities, both WP01 fingerprints, and platform/version policy. Verify tracker state, claim WP12 canonically, use only its worktree.

## Objective

Adjudicate strict/normalized duplicate families in status, sync/tracker, and upgrade migrations while preserving unique network, persistence, platform, and version boundaries.

## T081 — Manifest Reconciliation

- Map every owned member/group and split on path/oracle/input/route/platform/outcome divergence.

## T082 — Status/Sync Families

- Compare actual store/service/event/transport boundaries; delete copied setup/oracles dominated by deeper current seams.
- Preserve unique teardown, persistence, auth, and error propagation.

## T083 — Upgrade Families

- Consolidate migration test bodies only when supported input/version matrix and post-state oracle match exactly.
- Historical migration names are not proof of a supported boundary.

## T084 — Causal Validation

- Every deletion names survivor/no unique kill; every changed/cited survivor gets node/family proof.
- Run focused tests, targeted fault/mutation probes, platform/version cases, and ruff; record costs/deltas.

## T085 — Ledger/Handoff

- WP12 artifacts terminally cover all owned groups/members; emit deleted paths for WP07 and commit cleanly.

## Definition of Done

- [ ] Complete terminal coverage and named survivors.
- [ ] No unique sync/status/version/platform boundary lost.
- [ ] Focused validation, handoff, and clean commit complete.

## Reviewer Guidance

Reject same-body claims across different migration versions, network/persistence seams, or teardown behavior. Verify actual source path and oracle.

## Commit

`git commit -m "test(WP12): consolidate sync and upgrade duplicates"`
