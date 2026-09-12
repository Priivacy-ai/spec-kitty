---
work_package_id: WP06
title: 'US3: context.py service extraction + residual + completion (#2532)'
dependencies:
- WP05
requirement_refs:
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-002
- NFR-005
planning_base_branch: feat/charter-delivery-finish-context-degod
merge_target_branch: feat/charter-delivery-finish-context-degod
branch_strategy: Planning artifacts for this mission were generated on feat/charter-delivery-finish-context-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-delivery-finish-context-degod unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
history:
- at: '2026-07-30'
  actor: planner-priti
  note: WP authored from plan IC-05 + decomposition map (service cluster + completion).
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- src/charter/context_json.py
- src/charter/org_pack_discovery.py
- src/charter/action_doctrine_bundle.py
- src/charter/profile_resolution.py
- src/charter/doctrine_service_builder.py
- tests/charter/test_context_decomposition_completion.py
- tests/charter/test_context_service_seams.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/charter/context.py
- src/charter/context_json.py
- src/charter/org_pack_discovery.py
- src/charter/action_doctrine_bundle.py
- src/charter/profile_resolution.py
- src/charter/doctrine_service_builder.py
- tests/architectural/test_no_dead_symbols.py
- tests/charter/test_context_decomposition_completion.py
- tests/charter/test_context_service_seams.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```
Apply the resolved initialization/boundaries/directives/tactics; confirm which in one line, then proceed.

## Objective

Finish #2532: extract the **service / profile-resolution seams LAST** (they carry the US1-frozen activation-wrapper region and the module-global caches), thin `context.py` to a residual orchestration surface, and wire the **non-fakeable completion test**. Depends on **WP05**.

Design authority: [`../data-model.md`](../data-model.md), [`../research.md`](../research.md) (Decisions 7, 8, 9, 11, 12), [`../contracts/context-decomposition-parity.md`](../contracts/context-decomposition-parity.md).

## Critical context (verified)
- This WP **owns `context.py`** and is the ONLY WP that lists it in owned_files. It absorbs the residual orchestration + FR-009 re-export block + FR-007 note.
- **US1-frozen region**: `_build_activation_aware_doctrine_service` (~`context.py:1550-1566`) is the region WP02/WP03 (US1) touched. Extract it LAST, into `doctrine_service_builder.py`, against the now-frozen US1 code.
- **Globals relocation (verified safe)**: `_DEFAULT_AGENT_PROFILE_REPO`, `_ACTIVATION_AWARE_PROFILE_MAPS`, and `_reset_agent_profile_cache` (imported by 4 test files) relocate as a unit to `profile_resolution.py`; the `context.py` re-export binds the function object by reference (single-source cache — no dual-cache trap). Each new module needing `DoctrineService` adds its own `import doctrine.service as _doctrine_service_module`.
- Reuse the WP04 parity fixture as the byte-parity guard.

## Subtasks

### T029 — `context_json.py` + `org_pack_discovery.py` + `action_doctrine_bundle.py`
Move the JSON-builder privates (`_bundle_root_for_json`, `_relative_json_path`, `_project_charter_json_block`, `_project_directive_entries`, `_load_project_directives`, `_local_directive_entry`, `_maybe_build_doctrine_service`, `_EMPTY_ORG_CHARTER`, `_DirectiveLike`, `_DirectivesConfigLike`) to `src/charter/context_json.py`; the org-pack-discovery cluster to `org_pack_discovery.py`; the action-doctrine-bundle cluster (`_load_action_doctrine_bundle`, `_resolve_action_bundle`, `_ActionDoctrineBundle`) to `action_doctrine_bundle.py`. `__all__` each. Thin `build_charter_context_json` to delegate.

### T030 — `profile_resolution.py` (caches — LAST cluster)
Move the profile-resolution cluster + module-global caches + `_reset_agent_profile_cache` (+ `_default_agent_profile_repository`, `_activation_aware_profile_map`, `_resolve_agent_profile_record`, `_load_agent_profile`, `_existing_org_roots`, `_profiles_dict_from_service`, `_normalize_directive_id`). Keep the `context.py` FR-009 re-export binding `_reset_agent_profile_cache` by reference. `__all__`.

### T031 — `doctrine_service_builder.py` (US1-frozen region)
Move `_build_doctrine_service` + `_build_activation_aware_doctrine_service` into `doctrine_service_builder.py`, each with its own `import doctrine.service as _doctrine_service_module`. This is the US1-frozen region — extract against the frozen code, byte-parity preserved. `__all__`.

### T032 — Thin `context.py` to residual
Reduce `context.py` to: the 3 public orchestrators + `CharterContextResult` + `BOOTSTRAP_ACTIONS` + imports + the `# FR-009 preserved surface` re-export block + a top-of-file **retrospective** decomposition note (`# Decomposed into cohesive sibling modules — see #2532`, matching the `doctor.py:10` precedent). `__all__` current.

### T033 — Wire the completion test + full verify (+ mission-fallout allowlist fix)
**Mission-fallout campsite (required):** WP02 added a caller (`src/specify_cli/invocation/empty_charter.py:56`) for `charter_activated_urns`, which was previously uncalled and grandfathered in `_SYMBOL_ALLOWLIST` in `tests/architectural/test_no_dead_symbols.py`. That allowlist entry is now stale (the symbol has a real caller), so the shrink-only dead-symbol ratchet fails. **Remove the `charter_activated_urns` line from `_SYMBOL_ALLOWLIST`** (a shrink is allowed) so `test_no_dead_symbols.py` goes green with all lanes coexisting. This is confirmed NOT pre-existing at the upstream base (no caller there) — it is this mission's fallout and MUST be fixed here.

Create `tests/charter/test_context_decomposition_completion.py` asserting BOTH:
1. **primary (un-fakeable)**: a seam-existence manifest — each named seam module exists AND is imported by ≥1 non-`context` caller;
2. **secondary**: `wc -l src/charter/context.py ≤ 600`.
Add `tests/charter/test_context_service_seams.py` (focused unit tests). Then:
```
uv run pytest tests/charter/ -q
uv run pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_runtime_charter_doctrine_boundary.py -q
uv run ruff check src/charter/ && uv run mypy src/charter/
```
Byte-parity + all gates green. If `context.py` cannot reach ≤600, STOP and escalate to the operator (it is a BLOCKER needing re-sign-off, not an implementer ceiling tweak).

## Branch strategy
Planning base `feat/charter-delivery-finish-context-degod`; merge target `main` (PR). Depends on WP05 — enter via `spec-kitty agent action implement WP06 --agent claude`.

## Definition of Done
- [ ] Service/profile-resolution/doctrine-service-builder seams extracted (US1-frozen region last); each declares `__all__`.
- [ ] `context.py` ≤ 600 LOC, residual orchestration + FR-009 shim + FR-007 note only.
- [ ] Completion test green (seam manifest primary + LOC gate); layer-rule/`__all__`/dead-symbol green; byte-parity green.
- [ ] `_reset_agent_profile_cache` + all test-imported privates still resolve.
- [ ] ruff + mypy --strict clean.

## Risks
- Cache dual-source trap on the profile globals (re-export by reference — verify).
- Missing the ≤600 ceiling (escalate, do not silently re-negotiate).
- Perturbing the US1-frozen region (extract byte-parity, do not refactor its logic).

## Reviewer guidance
Confirm the completion test's seam manifest is real (each seam imported from its own home, not just re-exported); confirm `wc -l context.py ≤ 600`; confirm byte-parity + all arch gates; verify `_reset_agent_profile_cache` re-export binds by reference (single cache).
