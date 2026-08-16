---
work_package_id: WP09
title: CI gate and route structural sanitation
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
- T051
- T052
- T053
- T054
- T055
history:
- status: planned
  at: '2026-08-10T00:06:32Z'
  actor: codex
  note: Added after /spec-kitty.analyze exposed incomplete structural ownership
authoritative_surface: tests/architectural/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP09.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp09-results.json
execution_mode: code_change
owned_files:
- tests/merge/test_push_preflight.py
- tests/review/test_pre_review_gate_sole_caller_audit.py
- tests/specify_cli/cli/commands/test_merge_residue_gate_single_authority_wp13.py
- tests/architectural/test_arch_pole_deserialized.py
- tests/architectural/test_arch_shard_marker_completeness.py
- tests/architectural/test_arch_unblind_matrix.py
- tests/architectural/test_ci_architectural_gate_coverage.py
- tests/architectural/test_ci_collection_completeness.py
- tests/architectural/test_ci_fast_jobs_have_timeout.py
- tests/architectural/test_ci_topology_worklist.py
- tests/architectural/test_coverage_consumer_needs.py
- tests/architectural/test_coverage_root_collisions.py
- tests/architectural/test_cross_gate_churn_agreement.py
- tests/architectural/test_cross_grain_builtin_gate.py
- tests/architectural/test_docs_scoped_arch_coverage.py
- tests/architectural/test_gate_coverage.py
- tests/architectural/test_gate_coverage_parse_model.py
- tests/architectural/test_gate_read_literal_ban.py
- tests/architectural/test_inline_meta_read_gate.py
- tests/architectural/test_job_count_ceiling.py
- tests/architectural/test_marker_baseline.py
- tests/architectural/test_marker_registry_single_source.py
- tests/architectural/test_mission_resolver_walker_gate.py
- tests/architectural/test_next_shard_marker_completeness.py
- tests/architectural/test_no_primary_anchored_gates.py
- tests/architectural/test_plugin_validate_workflow.py
- tests/architectural/test_pytest_marker_convention.py
- tests/architectural/test_pytest_marker_correctness.py
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/test_shard_universe_bounded.py
- tests/architectural/test_src_filter_coverage.py
- tests/architectural/test_tasks_domain_gate_visibility.py
- tests/architectural/test_trigger_registry_coverage.py
- tests/architectural/test_ui_e2e_coverage_discovered.py
- tests/architectural/test_unit_contract_residual_gate.py
- tests/architectural/test_workflow_coherence.py
- tests/architectural/test_workflow_dist_lint.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP09.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp09-results.json
tags: []
tracker_refs:
- '#1931'
---

# WP09 — CI Gate and Route Structural Sanitation

## Do First

Load `architect-alphonso`. Read FR-006/FR-007, the current ADR/contract authorities named by assigned files, WP01's structural candidate manifest, and WP05's survival rule. Claim through `spec-kitty agent action implement WP09 --mission assertive-test-suite-sanitation-01KZME3P --agent codex --profile architect-alphonso` and use only its worktree.

## Objective

Terminally adjudicate the coherent CI/gate/coverage/marker/shard structural family. Delete advisory-only and positive-shape route scaffolds that cannot catch a plausible current CI ownership bug. Preserve a negative route/gate invariant only with live corpus and realistic authority-violating fault proof.

## T051 — Complete Machine Screening

- Reconcile every owned path against WP01's generated structural manifest; missing/unowned paths stop for task replan before edits.
- Record scanner kind, corpus, positive vs negative shape, asserted oracle, referenced authority/issue, historical mission tokens, count/prose/name pins, and current CI role.
- Every assigned file gets a terminal verdict. Every survivor references node-level or valid-family causal proof; group only guards with the same production path, authority, corpus, oracle, and fault.
- Import/collection failure, an empty corpus, or pasting a searched literal does not prove causal bite.

## T052 — Delete Spent Scaffolds

- Delete files/tests whose only observable is historical layout, exact prose/token/name/count, completed migration shape, test self-presence, or non-failing advisory output.
- Remove file-local dead helpers/imports. Do not edit production behavior, shared shard maps, workflows, or another WP's surfaces.
- When a file mixes useful and spent checks, retain/rehome the smallest current negative invariant and delete the rest.
- Record deleted nodeids, authority absence, runtime/collection cost, and why no unique live boundary remains.

## T053 — Controlled Fault Proof

- For each survivor or valid equivalent family, name current authority, assert a nonzero corpus floor, and introduce a realistic prohibited source/AST/dependency change in a disposable copy.
- The Act must execute and intended assertion must fail. Collection/import/setup failures do not count.
- Use two-sided controls: compliant change remains green; prohibited change reds. Prefer focused deterministic fault injection to mutation theater.
- A survivor lacking proof is deleted unless HiC supplies a current authority and executable probe.

## T054 — Focused Validation and Ledger

- Run focused collection/tests for every surviving assigned file, `ruff` changed files, and focused mypy where helpers change.
- `WP09.yaml` gives every assigned file a terminal verdict and every survivor node-level or valid-family structural evidence.
- Store commands, environment/hash, outcomes, costs, corpus size, fault result, and deleted/survivor node deltas in `wp09-results.json`.
- No skip/xfail/quarantine/flaky marker may be introduced to make a structural guard pass.

## T055 — Integration Handoff

- Emit a deterministic list of cohort-B deleted/renamed paths and required `_arch_shard_map.py` removals.
- Do not edit the central shard map. WP07 owns integration after WP03/WP04/WP05/WP09/WP10 complete.
- Commit owned changes and handoff. Full architectural hard-gate execution follows WP07 integration and repeats in WP08.

## Definition of Done

- [ ] Every assigned cohort-B file has a terminal structural verdict.
- [ ] Spent scaffolds are removed; no positive-shape implementation pin is renamed as an invariant.
- [ ] Every survivor has live corpus, current authority, and node-level or valid-family two-sided controlled-fault bite.
- [ ] Focused survivors pass; all deleted paths appear in deterministic integration handoff.
- [ ] Worktree clean after focused commit.

## Reviewer Guidance

Independently sample deletions and survivors. Reject “architectural” as authority, literal-paste probes, empty-corpus success, historical mission reports in pytest, count baselines without current budgets, and any edit outside owned files. Verify all owned paths reconcile to the ledger.

## Commit

`git commit -m "test(WP09): sanitize structural cohort b"`
