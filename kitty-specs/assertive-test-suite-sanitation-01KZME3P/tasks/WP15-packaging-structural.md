---
work_package_id: WP15
title: Packaging and CLI structural sanitation
dependencies: [WP01]
requirement_refs: [FR-003, FR-006, FR-007, FR-008, FR-014, FR-016, NFR-002, NFR-003, NFR-007, NFR-009, NFR-010]
planning_base_branch: pr/assertive-test-suite-sanitation
merge_target_branch: pr/assertive-test-suite-sanitation
branch_strategy: Planning artifacts for this mission were generated on pr/assertive-test-suite-sanitation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/assertive-test-suite-sanitation unless the human explicitly redirects the landing branch.
subtasks: [T071, T072, T073, T074, T075]
history:
- status: planned
  at: '2026-08-10T01:00:00Z'
  actor: codex
  note: Added after analyze split mixed structural cohorts by authority family
authoritative_surface: tests/architectural/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP15.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp15-results.json
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/test_command_surface_doctor.py
- tests/specify_cli/cli/commands/test_doctor_shared.py
- tests/specify_cli/tool_surface/providers/test_plugin_bundle.py
- tests/architectural/test_artifact_selection_completeness.py
- tests/architectural/test_cli_console_render_width.py
- tests/architectural/test_cli_console_single_seam.py
- tests/architectural/test_pyproject_shape.py
- tests/architectural/test_shared_package_boundary.py
- tests/architectural/test_template_governance_payload_contract.py
- tests/architectural/test_typer_compat_ci.py
- tests/architectural/test_uv_lock_pin_drift.py
- tests/architectural/tool_artifact_enrolment/test_enrolment_inventory.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP15.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp15-results.json
tags: []
tracker_refs: ['#1931']
---

# WP15 — Packaging and CLI Structural Sanitation

## Do First

Load `architect-alphonso`; read FR-006/FR-007 and current packaging/CLI/template/tool-artifact authorities. Verify tracker state, reconcile WP01 manifest, claim WP15 canonically, use only its worktree.

## Objective

Adjudicate the compact packaging, CLI, template, and artifact-enrolment structural family, including the nested AST/text inventory missed by the first plan.

## T071 — Family Census

- Record authority, consumer, corpus, scanner/oracle, route, and shape polarity for every file; terminalize all.
- Treat nested enrolment inventory as first-class; family proof cannot cross unrelated packaging contracts.

## T072 — Assertive Reduction

- Delete exact pyproject/template/CLI prose or positive-shape pins without current consumed authority.
- Reduce mixed files to smallest live negative invariant.

## T073 — Survivor Proof

- Every survivor/family requires nonzero corpus and realistic incompatible packaging/CLI/artifact change that reaches and fails intended oracle.
- Require compliant control; parse/import/collection failure is invalid.

## T074 — Validation/Evidence

- Run focused survivors, ruff, and focused mypy; record terminal rows, faults, commands/env/hashes, costs, and deltas.

## T075 — Integration Handoff

- Emit deterministic deleted/renamed paths to WP07; do not edit central shard map. Commit cleanly.

## Definition of Done

- [ ] All nine assigned files terminally adjudicated, including nested scanner.
- [ ] Every survivor has node/family proof; focused checks pass.
- [ ] WP07 handoff complete.

## Reviewer Guidance

Reject exact packaging text/layout as behavior, empty inventory, nested-path omission, and cross-contract family inheritance.

## Commit

`git commit -m "test(WP15): sanitize packaging structural guards"`
