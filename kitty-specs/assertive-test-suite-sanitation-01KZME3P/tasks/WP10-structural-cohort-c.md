---
work_package_id: WP10
title: Boundary and safety structural sanitation
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-006
- FR-007
- FR-008
- FR-014
- FR-016
- NFR-002
- NFR-003
- NFR-007
- NFR-009
- NFR-010
planning_base_branch: pr/assertive-test-suite-sanitation
merge_target_branch: pr/assertive-test-suite-sanitation
branch_strategy: Planning artifacts for this mission were generated on pr/assertive-test-suite-sanitation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/assertive-test-suite-sanitation unless the human explicitly redirects the landing branch.
subtasks:
- T056
- T057
- T058
- T059
- T060
history:
- status: planned
  at: '2026-08-10T00:06:32Z'
  actor: codex
  note: Added after /spec-kitty.analyze exposed incomplete structural ownership
authoritative_surface: tests/architectural/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP10.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp10-results.json
execution_mode: code_change
owned_files:
- tests/git/test_guard_capability_regression.py
- tests/integration/test_cross_seam_consumers.py
- tests/specify_cli/cli/commands/test_identity_audit.py
- tests/specify_cli/cli/commands/test_sparse_checkout_doctor.py
- tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py
- tests/specify_cli/core/test_load_meta_fail_closed_authority.py
- tests/specify_cli/decisions/test_ownership_3111.py
- tests/specify_cli/saas_client/test_client_consent_gate_3030.py
- tests/specify_cli/test_egress_consolidation_3110.py
- tests/specify_cli/test_meta_fail_closed_full_census_contract.py
- tests/specify_cli/test_meta_reader_sweep.py
- tests/sync/test_consent_resolver_3030.py
- tests/sync/test_project_identity_resolver_3030.py
- tests/sync/test_sync_action_gate.py
- tests/sync/tracker/test_saas_client_consent_gate_3030.py
- tests/architectural/test_2093_authority_invariant.py
- tests/architectural/test_all_declarations_required.py
- tests/architectural/test_auth_transport_singleton.py
- tests/architectural/test_batch_split_single_authority.py
- tests/architectural/test_compat_shims.py
- tests/architectural/test_dossier_sync_boundary.py
- tests/architectural/test_drg_writer_discovery.py
- tests/architectural/test_egress_consent_boundary.py
- tests/architectural/test_git_matrix_paths_resolve.py
- tests/architectural/test_guard_capability_call_sites.py
- tests/architectural/test_innerstatechanged_invariants.py
- tests/architectural/test_integration_boundary.py
- tests/architectural/test_layer_rules.py
- tests/architectural/test_merge_reconciliation_class_guard.py
- tests/architectural/test_no_authored_applies_edge.py
- tests/architectural/test_no_inert_schema_slots.py
- tests/architectural/test_no_invalid_windows_filenames.py
- tests/architectural/test_no_op_stable_writes.py
- tests/architectural/test_no_prompt_filtering_added.py
- tests/architectural/test_no_read_side_bypass.py
- tests/architectural/test_no_runtime_pypi_dep.py
- tests/architectural/test_no_shipped_layer_label.py
- tests/architectural/test_no_tmp_paths_in_tests.py
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_patch_seam_census_control.py
- tests/architectural/test_read_surface_placement_guard.py
- tests/architectural/test_real_home_isolation_guard.py
- tests/architectural/test_safety_registry_completeness.py
- tests/architectural/test_same_tier_uniqueness.py
- tests/architectural/test_serial_port_preservation.py
- tests/architectural/test_shared_module_object_patches.py
- tests/architectural/test_tid251_enforcement.py
- tests/architectural/test_trio_seam_only.py
- tests/architectural/test_unfiltered_journal_read_boundary.py
- tests/architectural/test_unregistered_shim_scanner.py
- tests/architectural/test_untrusted_path_containment.py
- tests/architectural/test_wp_owned_files_no_kitty_specs.py
- tests/architectural/test_wp_prompt_build_latency.py
- tests/architectural/test_write_surface_placement_guard.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP10.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp10-results.json
tags: []
tracker_refs:
- '#1931'
---

# WP10 — Boundary and Safety Structural Sanitation

## Do First

Load `architect-alphonso`. Read FR-006/FR-007, current boundary/security/path/import authorities referenced by assigned files, WP01's structural manifest, and WP05's survival rule. Claim through `spec-kitty agent action implement WP10 --mission assertive-test-suite-sanitation-01KZME3P --agent codex --profile architect-alphonso` and use only its worktree.

## Objective

Terminally adjudicate the coherent boundary/safety/path/import structural family. These include high-authority guards, so deletion remains assertive but evidence-led: remove stale positive shape/history/prose/count scaffolds; retain only live negative invariants with plausible controlled-fault bite.

## T056 — Complete Machine Screening

- Reconcile every owned path against WP01's structural candidate manifest; unowned discoveries trigger pre-dispatch task replan.
- Capture scanner kind, corpus, asserted oracle, positive/negative shape, named current authority, current consumer/route, historical tokens, and count/name/prose pins.
- Every assigned file receives a terminal verdict. Every survivor references node-level or valid-family causal proof; group only guards with the same production path, authority, corpus, oracle, and fault.
- Explicitly distinguish active security/governance boundaries from assertions that merely demand exact module names or completed migration layout.

## T057 — Delete Spent Scaffolds

- Delete advisory-only, historical report/WP, positive implementation-shape, exact prose/name/count, and self-presence checks without current authority.
- Preserve useful negative checks from mixed files by reducing to the smallest behaviorally meaningful oracle.
- Do not edit route-owned `test_ci_quality_path_filters.py`/`test_suite_jobs_gate_blocking.py`, WP04-owned shim registry, or WP05-owned migration clusters; their exact owners terminalize them.
- Remove only owned dead helpers/imports; no product behavior changes.

## T058 — Controlled Fault Proof

- For each survivor or valid equivalent family, record authority, nonzero corpus, a realistic prohibited change, Act reached, and intended assertion failure.
- Require compliant control green and prohibited control red. A parser error, missing import, collection failure, or pasted literal is invalid proof.
- Prefer narrow fault injection; use focused mutation only where it adds non-equivalent causal evidence.
- If a current high-authority invariant cannot be proven cheaply, preserve it provisionally only by escalating to HiC before terminal verdict; do not silently delete or mark temporary.

## T059 — Focused Validation and Ledger

- Run focused collection/tests for every surviving assigned file, `ruff` changed files, and focused mypy for changed helpers.
- `WP10.yaml` maps every assigned file to a terminal verdict; `wp10-results.json` stores commands/env/hash/outcomes/costs/corpus/fault deltas.
- No masking markers, retry-to-green, assertion weakening, or baseline-only count reductions.

## T060 — Integration Handoff

- Emit a deterministic deleted/renamed path list and expected `_arch_shard_map.py` removals.
- Do not edit the central map. WP07 integrates all cohort handoffs and runs complete architectural route validation.
- Commit owned files and leave worktree clean.

## Definition of Done

- [ ] Every assigned cohort-C file has a terminal verdict.
- [ ] Spent structural scaffolds removed while live governance/security boundaries remain protected.
- [ ] Every survivor has nonzero corpus, current authority, and node-level or valid-family two-sided controlled-fault bite.
- [ ] Focused survivors pass; deleted paths are in deterministic map handoff.
- [ ] No edits outside exact ownership.

## Reviewer Guidance

Sample both deletions and survivors. Reject historical prestige as authority, positive exact shape disguised as architecture, literal-paste probes, empty-corpus gates, and weakening of active security/governance contracts. Confirm assigned-file/ledger coverage is exactly 100%.

## Commit

`git commit -m "test(WP10): sanitize structural cohort c"`
