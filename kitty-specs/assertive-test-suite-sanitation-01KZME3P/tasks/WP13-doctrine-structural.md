---
work_package_id: WP13
title: Doctrine and resolver structural sanitation
dependencies:
- WP01
requirement_refs: [FR-003, FR-006, FR-007, FR-008, FR-014, FR-016, NFR-002, NFR-003, NFR-007, NFR-009, NFR-010]
planning_base_branch: pr/assertive-test-suite-sanitation
merge_target_branch: pr/assertive-test-suite-sanitation
branch_strategy: Planning artifacts for this mission were generated on pr/assertive-test-suite-sanitation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/assertive-test-suite-sanitation unless the human explicitly redirects the landing branch.
subtasks: [T061, T062, T063, T064, T065]
history:
- status: planned
  at: '2026-08-10T01:00:00Z'
  actor: codex
  note: Added after analyze split mixed structural cohorts by authority family
authoritative_surface: tests/architectural/
create_intent:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP13.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp13-results.json
execution_mode: code_change
owned_files:
- tests/charter/test_append_promotion_primitive.py
- tests/charter/test_charter_ownership_invariant.py
- tests/charter/test_chokepoint_coverage.py
- tests/charter/test_context_decomposition_completion.py
- tests/charter/test_mission_type_key.py
- tests/charter/test_operational_context.py
- tests/charter/test_surface_calibration.py
- tests/cli/test_charter_mission_type_commands.py
- tests/doctrine/drg/test_kind_mapping_totality.py
- tests/doctrine/test_activation_parity_guard.py
- tests/doctrine/test_pack_root_resolver.py
- tests/specify_cli/cli/commands/test_doctrine_collect.py
- tests/specify_cli/test_doctrine_service_factory.py
- tests/architectural/test_activation_registry_schema.py
- tests/architectural/test_built_in_location_authority.py
- tests/architectural/test_builtin_override_policy.py
- tests/architectural/test_charter_facades_reexport_doctrine.py
- tests/architectural/test_charter_no_specify_cli_import.py
- tests/architectural/test_charter_path_literal_authority.py
- tests/architectural/test_charter_references_resolve.py
- tests/architectural/test_charter_runtime_canonical_paths.py
- tests/architectural/test_charter_sole_door_agent_profile_repository.py
- tests/architectural/test_charter_sole_door_doctrine_service.py
- tests/architectural/test_charter_sole_door_hardcoded_paths.py
- tests/architectural/test_charter_sole_door_inner_reacharound.py
- tests/architectural/test_charter_sole_door_resolver_imports.py
- tests/architectural/test_doctrine_artefact_layout.py
- tests/architectural/test_doctrine_wheel_closure.py
- tests/architectural/test_glossary_canonical_terms.py
- tests/architectural/test_glossary_pack_boundary.py
- tests/architectural/test_glossary_pack_no_regression.py
- tests/architectural/test_glossary_pack_urn.py
- tests/architectural/test_kernel_no_doctrine_import.py
- tests/architectural/test_org_activation_seam.py
- tests/architectural/test_profile_load_resolver_guidance.py
- tests/architectural/test_protection_resolver_call_sites.py
- tests/architectural/test_resolution_activation_foundation.py
- tests/architectural/test_runtime_charter_doctrine_boundary.py
- tests/architectural/test_single_mission_surface_resolver.py
- tests/architectural/test_surface_resolution_audit.py
- tests/architectural/test_topology_resolution_boundary.py
- tests/architectural/test_urn_resolver_scalar_fence.py
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP13.yaml
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp13-results.json
tags: []
tracker_refs: ['#1931']
---

# WP13 — Doctrine and Resolver Structural Sanitation

## Do First

Load `architect-alphonso`; read FR-006/FR-007, current charter/doctrine/glossary/resolution authorities, and WP01's manifest. Verify tracker assignment/comment, claim WP13 canonically, and use only its worktree.

## Objective

Adjudicate the coherent doctrine/charter/glossary/resolver structural family. Delete retired names, exact layout/prose, and positive-shape comparisons; preserve only current authority boundaries with executable two-sided bite.

## T061 — Family Census

- Reconcile every owned path to WP01. Record authority, corpus, scanner kind, oracle, positive/negative shape, consumers, and route.
- Give every assigned file a terminal verdict. Group proof only for identical authority, production path, corpus, oracle, platform, and fault.

## T062 — Assertive Reduction

- Delete historical shape/name/prose/layout checks and advisory-only output without current authority.
- Reduce mixed files to the smallest live negative boundary; remove local dead helpers/imports only.

## T063 — Survivor Proof

- Every survivor or valid family must scan nonzero live corpus and fail its intended assertion under a realistic prohibited doctrine/resolver change.
- Require compliant control green; import/collection/parser failure and literal pasting do not count.

## T064 — Validation/Evidence

- Focused collection/pytest for every survivor; `ruff` changed files and focused mypy where needed.
- Record terminal rows, commands/env/hashes, corpus, fault, costs, and node deltas in WP13 artifacts.

## T065 — Integration Handoff

- Emit deterministic deleted/renamed architectural paths for WP07; do not edit the central shard map.
- Commit exact ownership only; complete architecture gate follows WP07 integration.

## Definition of Done

- [ ] All assigned files terminally adjudicated.
- [ ] Every survivor has node/family two-sided causal proof.
- [ ] Deleted paths are in the WP07 handoff; focused validation passes.

## Reviewer Guidance

Reject historical doctrine prestige, exact resolver layout, empty corpora, literal-paste probes, and cross-family proof inheritance. Sample each family independently.

## Commit

`git commit -m "test(WP13): sanitize doctrine structural guards"`
