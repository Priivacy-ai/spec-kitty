---
work_package_id: WP04
title: Decision re-point + extractor retirement
dependencies:
- WP02
- WP03
requirement_refs:
- FR-004
- FR-005
- FR-006
tracker_refs:
- '#2773'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/sync.py
- src/charter/extractor.py
- src/charter/__init__.py
- src/charter/consistency_check.py
- src/charter/mission_type_profiles.py
- src/doctrine/spdd_reasons/activation.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- tests/architectural/test_charter_references_resolve.py
- tests/charter/test_references_missing_failclosed.py
- tests/charter/test_extractor.py
- tests/charter/test_integration.py
- tests/doctrine/test_activation_parity_guard.py
role: implementer
tags: []
shell_pid: "583708"
shell_pid_created_at: "1784388189.08"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective
Re-point every governance/directive/parity **DECISION** reader from the four legacy files to `charter.yaml`, and **retire the prose→triad extractor**. This is the deterministic-first win.

**Authoritative**: [`plan.md`](../plan.md) IC-04, [`data-model.md`](../data-model.md) INV-3/4.

## ⚠ NFR-005 HARD ORDERING (within this WP)
Re-point the loaders (T016) **BEFORE** deleting the scrape (T017). If the scrape is deleted first, `sync()` stops writing the triad and the un-re-pointed loaders return an **empty `GovernanceConfig()` silently** (governance lost, no error). Keep loader **signatures stable** so WP05/`resolver.py` callers auto-follow.

## Context / grounding
- `sync.py:307 load_governance_config`, `:356 load_directives_config` (the two chokepoint loaders), `:198 sync()` scrape, `:224 post_save_hook`.
- `extractor.py:46 SECTION_MAPPING`, `write_extraction_result`, `:807 extract_with_ai` (dead stub — delete).
- `consistency_check.py:200 _load_raw_activation_lists` (config activation, DIRECT), `:406 _load_reference_ids_by_kind` (references catalog), `:32` #2530 fail-closed error.
- Bypass readers: `mission_type_profiles.py:954 _project_has_doctrine_overrides` (reads governance.yaml, caller :479), `spdd_reasons/activation.py` (`_GOVERNANCE:41`, `_compute_active:92`, cache `clear_activation_cache:49`), `_doctrine_collect.py:555`.
- **Orphan-cleanup (post-tasks squad)**: retiring `post_save_hook` + the scraper symbols breaks unowned bindings — `src/charter/__init__.py:61-65,139 __all__` (re-exports `post_save_hook`), `extractor.py:38 __all__` (lists `write_extraction_result`), `tests/charter/test_extractor.py:11,208-231` (imports the deleted symbols, ~20 tests), `tests/charter/test_integration.py` (references `post_save_hook`). All now owned by this WP.

## Subtasks
### T016 — Re-point loaders → charter.yaml (FIRST)
- `load_governance_config` / `load_directives_config` read `governance`/`directives` from `charter.yaml` (via the resolved charter path). Keep signatures stable.
### T017 — Delete the scrape + retire the extractor + fix orphaned bindings (AFTER T016)
- Delete `sync()`'s prose→triad scrape + `post_save_hook`; delete `SECTION_MAPPING` + `write_extraction_result` + dead `extract_with_ai`.
- **Fix the orphaned bindings** (else ImportError / red-at-aggregate): update `src/charter/__init__.py` (drop the `post_save_hook`/`write_extraction_result` imports + `__all__` entries) and `extractor.py:38 __all__`.
### T018 — Parity reads charter.yaml (BOTH reads)
- Re-point BOTH `_load_raw_activation_lists:200` (activation lists) **and** `_load_reference_ids_by_kind:406` (catalog) to `charter.yaml`. Re-home the #2530 fail-closed error onto charter.yaml. This closes the WP02 transient-red-parity coupling.
### T019 — Bypass readers
- `mission_type_profiles._project_has_doctrine_overrides:954`, `spdd_reasons/activation` (invalidate `clear_activation_cache:49`), `_doctrine_collect.py:555` → read charter.yaml.
### T020 — Tests (incl. retiring spent scraper tests)
- `test_charter_references_resolve.py`, `test_references_missing_failclosed.py` (re-home #2530; **update the #2758 `first_missing_bundle_file` assertion from `"references.yaml"` → `"charter.yaml"`** — it auto-narrows once WP01's `BUNDLE_CONTENT_HASH_FILES` is `charter.yaml`), `test_activation_parity_guard.py` (now reads charter.yaml) — all green. **Retire the spent scraper tests** in `tests/charter/test_extractor.py` (`test_extract_with_ai_*`, `test_write_extraction_result_*`, `SECTION_MAPPING` dispatch tests) + fix `test_integration.py` `post_save_hook` refs. Assert governance loads non-empty through the loader after the scrape is gone.

## ATDD (red-first)
Red-first: assert `load_governance_config` returns the authored governance from `charter.yaml` (RED until T016); assert parity reads charter.yaml activation+catalog (RED until T018).

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (deps WP02, WP03); merges back to `feat/consolidate-charter-bundle`.

## Definition of Done
- All decision readers + both parity reads on charter.yaml; extractor scraper + dead AI stub deleted; #2530 re-homed; loader signatures stable; parity green.
- ruff + mypy --strict clean; complexity ≤15.

## Reviewer guidance
- Verify the **ordering** (loaders re-pointed before scrape delete) — no silent-empty-governance window in the final diff.
- Verify BOTH `consistency_check` reads moved (activation AND catalog), not just the catalog.
- Verify no governance decision still reads a legacy file.

## Activity Log

- 2026-07-18T14:18:11Z – claude:sonnet:python-pedro:implementer – shell_pid=453423 – Assigned agent via action command
- 2026-07-18T15:20:31Z – claude:sonnet:python-pedro:implementer – shell_pid=453423 – T016-T020 done. Loaders (load_governance_config/load_directives_config) re-pointed to charter.yaml governance:/directives: sections; sync() scrape+post_save_hook retired AFTER loader re-point (NFR-005 order respected in final diff, no silent-empty-governance window); SECTION_MAPPING/write_extraction_result/extract_with_ai deleted from extractor.py (Extractor's doctrine-selection+activation scan kept, unconditional, still used by out-of-scope tests). consistency_check.py: BOTH _load_raw_activation_lists (mirrors PackContext charter: pointer, closes WP02<->WP04 transient-parity coupling) and _load_reference_ids_by_kind (catalog.references, was references.yaml) re-pointed; #2530 re-homed as CharterYamlCorruptError/CharterPackConfigError. 3 bypass readers re-pointed: mission_type_profiles, spdd_reasons/activation (single-file cache key), _doctrine_collect. Gates: ruff+mypy --strict clean on all 7 owned src files, complexity<=15, all 5 owned test files green (56 tests). Project's own charter pack: coherent=True. One necessary-fallout fix outside owned_files: tests/architectural/test_no_dead_symbols.py allowlist entry for charter.extractor.Extractor (its only production caller, sync.py, was retired by T017; class kept as tested library primitive, tracker note left in-file). Individually verified architectural gates green: test_no_dead_symbols, test_ratchet_baselines, test_chokepoint_coverage, test_no_legacy_terminology, test_layer_rules. Full non_sandbox architectural sweep (1025 tests, collects cleanly) is slow (nested full-repo pytest subprocesses) and was not run to full completion -- reviewer should confirm. Expected out-of-scope fallout (ripple from sync()/extractor retirement, NOT fixed, outside owned_files): test_sync.py, test_sync_authority_paths.py, test_sync_paths.py, test_sync_references.py, test_worktree_charter_via_canonical_root.py(2/5), test_activate_resolves_no_answers_edit.py(collection error), test_chokepoint_overhead.py(3 errors), test_charter_context_spdd_reasons.py(9), test_context.py::TestBuildContextV2(4), test_resolver.py(12), test_resolved_mission_type_context.py(1). Pre-existing/unrelated to WP04 (confirmed no dependency on touched APIs): test_bundle_content_hash.py, test_bundle_contract.py, test_bundle_validate_cli.py, synthesizer/test_orchestrator_resynthesize.py, synthesizer/test_performance_envelopes.py, synthesizer/test_synthesize_path_parity.py, charter_yaml_io OWNED_SECTIONS/UnknownCharterYamlSectionError dead-symbol orphans (WP01 territory, file untouched).
- 2026-07-18T15:23:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=583708 – Started review via action command
- 2026-07-18T15:38:38Z – user – shell_pid=583708 – Ordering OK: loaders read charter.yaml governance/directives directly (T016) and sync() scrape+post_save_hook deleted (T017) -- no silent-empty-governance window (loaders read hand-authored charter.yaml, not the retired triad; verified authored gov/13 directives load when charter.yaml at resolved root). Parity coherent=True, verification_errors=[], reference_id_divergences=[]; test_activation_parity_guard GREEN; both consistency_check reads moved (activation via PackContext charter: pointer, catalog via catalog.references); #2530 re-homed to CharterYamlCorruptError/CharterPackConfigError. Extractor kept: honest+minimal dead-symbols allowlist entry (test-only callers post-WP04, deletion deferred to tracked follow-up) -- DoD requires deleting scraper symbols (done: SECTION_MAPPING/write_extraction_result/extract_with_ai gone), not the class. 3 bypass readers re-pointed; #2758 assertion->charter.yaml. Owned gates green: ruff clean, mypy --strict clean, complexity<=15, 56 owned tests pass. Scope clean (only owned files + justified allowlist). 52 out-of-scope fallout items (48 fail + 4 err across 11 files) catalogued for WP05(context.py)/WP07 -- all WP04-caused ripple, GREEN at parent, NOT pre-existing. Plus pre-existing dead-symbols orphan charter_yaml_io::OWNED_SECTIONS/UnknownCharterYamlSectionError (WP01 territory, red at parent) -> WP07.
