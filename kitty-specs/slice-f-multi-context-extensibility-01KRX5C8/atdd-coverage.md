# ATDD Coverage — Slice F

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Companion: [plan.md §3 ATDD landing plan](plan.md#3-atdd-landing-plan-per-lane), [spec.md §"Development Discipline: ATDD-First"](spec.md)

This file is the **canonical executable contract** for Slice F per NFR-008 and C-011. Every in-scope Scenario and operator-observable AC has at least one acceptance test that pins it. The planner pre-populates each row at `/spec-kitty.plan` time with the planned test file + test function + the WP IDs that land the RED commit and turn it GREEN.

Reviewers consult this file to know which test pins which scenario — and which WP delivers the red→green transition.

---

## Coverage table

| ID | Type | Test file | Test function name | RED commit (lane-opening WP) | GREEN WP | Status |
|---|---|---|---|---|---|---|
| Scenario 1 | Scenario | `tests/integration/test_three_layer_drg_end_to_end.py` | `test_org_drg_fragment_merges_through_three_layers_with_provenance` | WP06 | WP06 | planned |
| Scenario 1 (exception) | Scenario | `tests/integration/test_org_pack_missing_path_hard_fails.py` | `test_org_pack_with_missing_local_path_raises_named_error` | WP06 | WP06 | planned |
| Scenario 2 | Scenario | `tests/integration/test_monorepo_charter_scope.py` | `test_nearest_enclosing_charter_resolves_from_deep_subdirectory` | WP09 | WP09 | planned |
| Scenario 2 (exception) | Scenario | `tests/integration/test_monorepo_charter_scope.py` | `test_malformed_monorepo_config_reports_conflicting_paths` | WP09 | WP09 | planned |
| Scenario 3 | Scenario | `tests/integration/test_workflow_sequence_runtime.py` | `test_non_default_workflow_id_produces_extra_design_review_step` | WP11 | WP11 | planned |
| Scenario 3 (exception) | Scenario | `tests/specify_cli/next/test_workflow_registry.py` | `test_unknown_workflow_id_hard_fails_with_available_list` | WP10 | WP10 | planned |
| Scenario 4 | Scenario | `tests/charter/test_alias_deleted_regression.py` | `test_resolve_governance_import_raises_import_error` | WP04 | WP04 | planned |
| Scenario 5 | Scenario | `tests/integration/test_catalog_miss_cli_visibility.py` | `test_typoed_styleguide_produces_visible_stderr_warning` | WP05 | WP05 | planned |
| Scenario 6 | Scenario | `tests/architectural/test_ratchet_baselines.py` | `test_growing_an_allowlist_above_baseline_fails` | WP01 | WP01 | planned |
| AC-1 | AC | `tests/integration/test_three_layer_drg_end_to_end.py` | `test_charter_lint_lints_all_three_layers_with_provenance` | WP06 | WP06 | planned |
| AC-2 | AC | `tests/cli/test_doctrine_org_commands.py` | `test_doctrine_org_init_scaffolds_minimal_pack` AND `test_doctor_doctrine_surfaces_org_layer_state` | WP08 | WP08 | planned |
| AC-3 | AC | `tests/specify_cli/next/test_wp_prompt_governance_contract.py` (regression) + `tests/integration/test_monorepo_charter_scope.py` (new behaviour) | (all 23 existing) + `test_default_scope_is_byte_identical_to_today` | WP09 | WP09 | planned |
| AC-4 | AC | `tests/integration/test_workflow_sequence_runtime.py` | `test_fixture_mission_with_workflow_id_produces_documented_step_diff` | WP11 | WP11 | planned |
| AC-5 | AC | `tests/charter/test_alias_deleted_regression.py` | `test_resolve_governance_import_raises_import_error` AND `test_no_test_fixture_still_imports_legacy_alias` | WP04 | WP04 | planned |
| AC-6 | AC | `tests/architectural/test_ratchet_baselines.py` | `test_baseline_file_exists_with_required_keys` AND `test_growth_fails_shrinkage_warns` | WP01 | WP01 | planned |
| AC-7 | AC | `tests/architectural/test_no_dead_modules.py` | `test_category_7_grandfathered_at_most_seven_entries` | WP01 | WP01 | planned |
| AC-8 | AC | `tests/architectural/test_all_declarations_required.py` + `tests/architectural/test_no_dead_symbols.py` | `test_every_charter_module_declares_all` AND `test_every_kernel_module_declares_all` AND `test_no_public_symbol_in_all_is_unimported` | WP02 | WP02 | planned |
| AC-9 | AC | `tests/integration/test_catalog_miss_cli_visibility.py` | `test_typoed_styleguide_produces_visible_stderr_warning` | WP05 | WP05 | planned |
| AC-10 | AC | `tests/contract/test_example_round_trip.py` | `test_contract_example_round_trip[*]` (parameterised over every tagged codeblock in `kitty-specs/*/contracts/*.md`) | WP03 | WP03 | planned |
| AC-11 | AC | `tests/glossary/test_canonical_promotion.py` | `test_all_slice_f_terms_are_canonical_in_doctrine_context` | WP12 | WP12 | planned |
| AC-17 | AC (regression) | `tests/specify_cli/next/test_wp_prompt_governance_contract.py` + `tests/architectural/test_wp_prompt_build_latency.py` + `tests/architectural/test_layer_rules.py` + full architectural sweep | (all existing pass unchanged) | WP12 | WP12 (verification) | planned |
| AC-18 | AC | (manual) `spec-kitty analyze` report at mission close | analyze verdict READY FOR IMPLEMENTATION; 0 CRITICAL / 0 HIGH | WP12 | WP12 | planned |

---

## Existence-only ACs (covered by file/issue presence per NFR-008 slack)

These ACs do NOT follow red→green discipline because the deliverable is a pure-documentation artefact whose existence IS the test:

| ID | What exists | WP | Verification |
|---|---|---|---|
| AC-12 | `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` | WP12 | File exists; ADR sections present per FR-200; "deleted in commit X" field reserved |
| AC-13 | GitHub ticket open against Priivacy-ai/spec-kitty (labelled for Robert's queue) | WP12 | Ticket URL pinned in the WP12 close-out commit message |
| AC-14 | `tests/architectural/README.md` documents the 5-axis model | WP12 | File exists; lists every gate with its axis (per ratchet-coherence-audit §3) |
| AC-15 | Forward-staged migrations convention documented in `src/specify_cli/upgrade/migrations/README.md` | WP12 | File exists; convention paragraph present (per Q7 / FR-301) |
| AC-16 | Charter amendments landed in `.kittify/charter/charter.md` | WP12 | Charter contains: burn-down policy section (FR-303a / C-004), `__all__` declaration convention (FR-303b / C-007), ATDD-first discipline note (FR-303c / C-011) |

For these, the WP12 reviewer confirms each file / issue exists with the required sections. No RED→GREEN transition applies.

---

## Reviewer protocol (per spec §"Reviewer obligation")

For every row above with a non-trivial RED→GREEN transition, the reviewer of the GREEN WP MUST:

```bash
# Confirm the test was RED on the WP's planning base:
git checkout <wp.planning_base_branch>
pytest <test_file>::<test_function>     # MUST FAIL

# Confirm the test is GREEN on the WP's final commit:
git checkout <wp_branch>
pytest <test_file>::<test_function>     # MUST PASS
```

If the test was already green on the planning base, the WP did not follow ATDD discipline — the reviewer rejects with feedback per spec §"Reviewer obligation".

---

## Per-WP FR-304 commit-message obligation

Per FR-304, every commit that lands an ATDD acceptance test MUST declare in its commit message:

1. Which Scenario or AC the test covers (e.g. "covers: Scenario 1, AC-1").
2. The expected red→green transition (e.g. "expected GREEN at: WP06 final commit").

The GREEN WP's frontmatter pins the SHA-or-WP of the RED commit so the audit trail is complete.

---

## Coverage summary

- **In-scope ACs requiring red→green:** AC-1 through AC-11, AC-17, AC-18 = 13 ACs
- **In-scope Scenarios:** Scenarios 1-6 (with several having exception-path counterparts) = 6 Scenarios, 9 distinct tests
- **Existence-only ACs:** AC-12, AC-13, AC-14, AC-15, AC-16 = 5 ACs (within the 10% NFR-008 slack)
- **Total rows in coverage table:** 22 (above) + 5 (existence-only) = **27 distinct test/artefact anchors**

Coverage threshold per NFR-008 is ≥ 90% of in-scope ACs. With 13/13 in-scope ACs and 9/9 Scenario tests covered, Slice F satisfies the threshold (100% in-scope coverage; the 10% slack is held in reserve for the existence-only ACs).
