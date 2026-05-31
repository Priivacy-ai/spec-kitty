# Tasks: Charter Pack Activation Layer

**Mission**: `charter-pack-activation-layer-01KSYE4V`
**Mission ID**: `01KSYE4VZ9V0S14NRC87XX92BP`
**Branch**: `pr/charter-doctrine-mission-type-configuration` → `pr/charter-doctrine-mission-type-configuration`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)
**Date**: 2026-05-31
**Total WPs**: 11 | **Total subtasks**: 51

---

## Work Package Summary

| WP | Title | Priority | Dependencies | Subtasks | Est. Size |
|----|-------|----------|--------------|----------|-----------|
| WP01 | Foundational Fixes: Architectural Tests + DRG + C-004 | High | — | T001–T006 | ~320 lines |
| WP02 | PackContext Three-State Extension | High | — (parallel with WP01) | T007–T010 | ~350 lines |
| WP03 | ProjectContext + Invocation Context Module | High | WP02 | T011–T014 | ~300 lines |
| WP04 | Default Charter Pack + CharterPackManager | High | WP02, WP03 | T015–T019 | ~450 lines |
| WP05 | Upgrade Migration m_3_2_8 | High | WP04 | T020–T023 | ~280 lines |
| WP06 | Charter CLI: Activate / Deactivate / List / Pack | High | WP03, WP04 | T024–T029 | ~480 lines |
| WP07 | Consistency Check Implementation | High | WP03, WP04 | T030–T033 | ~350 lines |
| WP08 | Pattern A: DRG Filter Wiring (4 call sites + `_node_is_activated`) | High | WP02, WP03 | T034–T038 | ~400 lines |
| WP09 | Pattern B+C: Flat Catalog + Direct Repository Wiring | High | WP02, WP08 | T039–T043 | ~420 lines |
| WP10 | WP Lifecycle Gates | High | WP02, WP04 | T044–T047 | ~350 lines |
| WP11 | Test Quality Improvements | Should | WP02, WP08 | T048–T051 | ~280 lines |

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Fix `test_legacy_subpackage_is_gone` namespace-package false positive (FR-021) | WP01 | [P] |
| T002 | Fix 8 broken `test_template_governance_payload_contract` tests (FR-022) | WP01 | [P] |
| T003 | Add m_3_2_7 and m_3_2_8 to dead-modules allowlist; bump baseline 71→73 (FR-023) | WP01 | [P] |
| T004 | Remove tracked test fixture files from `kitty-specs/` (FR-025) | WP01 | [P] |
| T005 | Fix `_SINGULAR_TO_PLURAL["mission_step_contract"]` in `drg.py` (FR-028) | WP01 | [P] |
| T006 | Fix C-004: replace TYPE_CHECKING charter import with `_PackContextLike` protocol in `mission_step_repository.py` (FR-020) | WP01 | [P] |
| T007 | Add 8 new `activated_*` fields to `PackContext` dataclass | WP02 | |
| T008 | Add 8 per-kind reader functions in `pack_context.py` and hook into `from_config()` | WP02 | |
| T009 | Fix FR-039: remove `and raw` guard from `_read_activated_kinds` + `_read_activated_mission_types`; delete `test_empty_activated_kinds_uses_builtin_fallback` | WP02 | |
| T010 | Write/extend `test_pack_context.py` to cover all three-state variants for new per-kind fields | WP02 | |
| T011 | Create `src/charter/invocation_context.py` with `ProjectContext`, `OperationalContext`, `ContextPreconditionError` class bodies | WP03 | |
| T012 | Implement `from_repo()` factory and `require_*()` guard methods on `ProjectContext` | WP03 | |
| T013 | Add 4 `OperationalContext`-family symbols to `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE`; update `_baselines.yaml` (FR-024 / FR-040) | WP03 | |
| T014 | Write `tests/charter/test_invocation_context.py` covering `from_repo()`, guards, and `ContextPreconditionError` | WP03 | |
| T015 | Create `src/charter/packs/default.yaml` with all 9 activation kinds fully populated with built-in IDs | WP04 | |
| T016 | Create `src/charter/pack_manager.py` with `ActivationResult`, `MergeResult` value objects and `YAML_KEY_MAP` constant | WP04 | |
| T017 | Implement `CharterPackManager.activate()` and `deactivate()` with cascade logic | WP04 | |
| T018 | Implement `CharterPackManager.list_activated()`, `list_available()`, and `merge_defaults()` | WP04 | |
| T019 | Write `tests/charter/test_pack_manager.py` | WP04 | |
| T020 | Create `m_3_2_8_default_charter_pack.py` with `detect()`, `can_apply()`, `apply()` | WP05 | |
| T021 | Implement backup-before-write pattern in `apply()` (C-008, NFR-002) | WP05 | |
| T022 | Write tests for `detect()` and `apply()` called directly (not via upgrade pipeline) | WP05 | |
| T023 | Register migration so `test_no_dead_modules` recognizes it; verify baseline includes both migrations | WP05 | |
| T024 | Refactor `activate.py` CLI to call `CharterPackManager.activate()` for all 9 kinds + `--cascade` | WP06 | |
| T025 | Fix reader gap (FR-014): refactor `charter_activate.py` `activate_mission_type_override()` to write `mission_type_activations` to `config.yaml` instead of override files | WP06 | |
| T026 | Create `deactivate.py` with all 9 kinds and shared-artifact cascade protection | WP06 | |
| T027 | Create `list.py` with `charter list` and `--show-available` Rich table output (FR-009, FR-010) | WP06 | |
| T028 | Create `pack.py` `charter pack consistency-check` subcommand; register all new commands in `_app.py` | WP06 | |
| T029 | Update/write CLI tests for activate (all 9 kinds), deactivate, list, and pack consistency-check | WP06 | |
| T030 | Create `src/charter/consistency_check.py` with `ConsistencyReport` and unknown-reference algorithm | WP07 | |
| T031 | Implement cross-kind DRG-edge reference validation in `consistency_check.py` | WP07 | |
| T032 | Implement kind-level duplicate-detection and kind-violation checks | WP07 | |
| T033 | Write `tests/charter/test_consistency_check.py` with at least one planted violation per check type | WP07 | |
| T034 | Extend `_node_is_activated` in `drg.py` with per-artifact-ID frozenset checks (FR-038) | WP08 | |
| T035 | Wire `filter_graph_by_activation` in `context.py:_load_action_doctrine_bundle()` | WP08 | |
| T036 | Wire in `reference_resolver.py:resolve_references_transitively()` | WP08 | |
| T037 | Wire in `compiler.py:_resolve_transitive_reference_graph()` | WP08 | |
| T038 | Wire in `executor.py` step contract execution path | WP08 | |
| T039 | Wire Pattern B: `generate.py:47` — construct `DoctrineService` with `pack_context` | WP09 | |
| T040 | Wire `org_charter.py:660, 710` callers of `load_org_charter_policies()` to pass `pack_context` | WP09 | |
| T041 | Wire `doctor.py:2332` + `org_layer.py:218,236` to pass/accept `pack_context` (FR-037) | WP09 | |
| T042 | Wire Pattern C: `DoctrineService.agent_profiles` via `charter/resolver.py` with activation filter | WP09 | |
| T043 | Add `MissionStepRepository` to `charter/mission_steps.py` re-exports; wire to production call site (FR-016) | WP09 | |
| T044 | Add charter profile gate to `spec-kitty agent mission finalize-tasks` (FR-017) | WP10 | |
| T045 | Add charter profile precondition to `spec-kitty agent action implement` before worktree creation (FR-018) | WP10 | |
| T046 | Wire hard-fail on non-activated artifact lookup in DRG/tactic resolution paths (FR-019) | WP10 | |
| T047 | Write tests for lifecycle gates: finalize-tasks hard-fail + implement hard-fail scenarios | WP10 | |
| T048 | Extend NFR-001 test to real filesystem I/O, multi-run p99 methodology (FR-026) | WP11 | [P] |
| T049 | Add FR-027 test: `mission_type_activations: [software-dev]` → documentation/research/plan excluded | WP11 | [P] |
| T050 | Fix FR-029: move subprocess call from fast-marked unit test to integration mark | WP11 | [P] |
| T051 | Fix FR-030: replace vacuous assertion in decision dispatch test with meaningful invariant | WP11 | [P] |

---

## Critical Path

`WP01 (parallel with WP02) → WP03 → WP04 → WP06`

Secondary chain: `WP04 → WP05` (upgrade migration, can follow WP06 in parallel)

Wiring chain: `WP02 + WP03 → WP08 → WP09`

Gates chain: `WP02 + WP04 → WP10`

Test quality: `WP02 + WP08 → WP11`

Total critical-path length: 4 sequential WPs on the CLI path (WP02 → WP03 → WP04 → WP06).

---

## Parallel Opportunities

| After landing | Can run in parallel |
|---------------|---------------------|
| Start | WP01 + WP02 (no dependencies on each other) |
| WP02 | WP03 starts; WP01 subtasks are independent of each other within WP01 |
| WP03 | WP04 starts |
| WP02 + WP03 | WP08 starts |
| WP04 | WP05, WP06, WP07, WP10 can all start in parallel |
| WP08 | WP09 and WP11 start |
| WP06 + WP07 | Final integration testing |

WP01 subtasks T001–T006 are fully independent and can be executed in any order within the WP.
WP11 subtasks T048–T051 are fully independent and can be executed in any order within the WP.

---

## Work Packages

### WP01 — Foundational Fixes: Architectural Tests + DRG + C-004

**Goal**: Make all 6 architectural ratchets pass on the branch before any new code lands. Fix the drg.py MSC plural bug and the C-004 boundary violation independently.
**Priority**: High
**Dependencies**: none
**Estimated size**: ~320 lines
**Subtasks**: T001–T006
**Agent profile**: python-pedro

- [x] T001 Fix `test_legacy_subpackage_is_gone` find_spec (FR-021)
- [x] T002 Fix 8 `test_template_governance_payload_contract` tests (FR-022)
- [x] T003 Add m_3_2_7/m_3_2_8 to dead-modules allowlist; bump baseline 71→73 (FR-023)
- [x] T004 Remove tracked test fixture files from `kitty-specs/` (FR-025)
- [x] T005 Fix `_SINGULAR_TO_PLURAL["mission_step_contract"]` in `drg.py` (FR-028)
- [x] T006 Fix C-004 TYPE_CHECKING import in `mission_step_repository.py` (FR-020)

**Implementation Notes**:
- T001: `test_legacy_subpackage_is_gone` uses `importlib.util.find_spec()` which returns non-None for namespace packages; fix by checking for `__file__` attribute on the returned spec or using a more precise check.
- T002: The 8 broken tests reference deleted template paths; update to the current template file locations or remove stale path assertions.
- T003: `m_3_2_7` and `m_3_2_8` are new migrations added by this mission; pre-register them in the `test_no_dead_modules.py` allowlist and bump the baseline counter from 71 to 73.
- T004: Remove any test fixture markdown files accidentally committed under `kitty-specs/` that should live under `tests/fixtures/`.
- T005: `_SINGULAR_TO_PLURAL` in `drg.py` is missing the `"mission_step_contract"` → `"mission_step_contracts"` mapping; this causes silent key errors in DRG traversal when MSC nodes are present.
- T006: `mission_step_repository.py` imports `PackContext` under `TYPE_CHECKING` creating a C-004 violation (`doctrine.*` importing from `charter.*`); replace with a structural `_PackContextLike` protocol defined locally or in `doctrine.drg.models`.

**Parallel Opportunities**: All 6 subtasks are independent and can be fixed concurrently.

**Risks**:
- T001 requires verifying actual `find_spec` behavior for namespace packages to avoid false green.
- T006 must not break mypy strict; validate the protocol covers all attribute accesses used in the repository.

---

### WP02 — PackContext Three-State Extension

**Goal**: Add 8 per-kind `activated_*` fields to `PackContext` and enforce the three-state semantics (`None` = all built-ins available, `frozenset()` = nothing available, non-empty frozenset = exactly those IDs) for all activation readers. Delete `test_empty_activated_kinds_uses_builtin_fallback` because that fallback is explicitly removed.
**Priority**: High
**Dependencies**: none (can run parallel with WP01)
**Estimated size**: ~350 lines
**Subtasks**: T007–T010
**Agent profile**: python-pedro

- [x] T007 Add 8 `activated_*` fields to `PackContext` dataclass
- [x] T008 Add 8 per-kind reader functions + hook into `from_config()`
- [x] T009 Fix FR-039: remove `and raw` guard from `_read_activated_kinds` + `_read_activated_mission_types`; delete `test_empty_activated_kinds_uses_builtin_fallback`
- [x] T010 Write/extend `test_pack_context.py` for three-state coverage

**Implementation Notes**:
- T007: The 8 new fields are `activated_directives`, `activated_tactics`, `activated_styleguides`, `activated_toolguides`, `activated_paradigms`, `activated_procedures`, `activated_agent_profiles`, `activated_mission_step_contracts`. All are `frozenset[str] | None` with default `None` (None = all built-ins available).
- T008: Mirror the existing `_read_activated_mission_types()` pattern for each kind. Each reader reads the corresponding `activated_<kind>s` key from config.yaml. Hook all 8 readers into `PackContext.from_config()`.
- T009: The `and raw` guard in `_read_activated_kinds` and `_read_activated_mission_types` silently converts an explicit `[]` (empty list) into `None` (all), violating hard-restriction semantics. Remove the guard so `[]` → `frozenset()` (nothing). Delete the test that asserted the old fallback behavior.
- T010: Test matrix for each field: (a) key absent from config → `None`; (b) key present with empty list → `frozenset()`; (c) key present with IDs → `frozenset` of those IDs.

**Risks**: Removing the `and raw` guard is a behavior change that existing tests may rely on; audit all tests touching `activated_kinds` and `activated_mission_types` before deleting.

---

### WP03 — ProjectContext + Invocation Context Module

**Goal**: Create `src/charter/invocation_context.py` with `ProjectContext`, `OperationalContext`, and `ContextPreconditionError`. Pre-allowlist 4 `OperationalContext`-family dead symbols so the architectural ratchet does not reject the new module on first commit.
**Priority**: High
**Dependencies**: WP02
**Estimated size**: ~300 lines
**Subtasks**: T011–T014
**Agent profile**: python-pedro

- [x] T011 Create `invocation_context.py` with `ProjectContext`, `OperationalContext`, `ContextPreconditionError` class bodies
- [x] T012 Implement `from_repo()` factory and `require_*()` guard methods on `ProjectContext`
- [x] T013 Add 4 `OperationalContext`-family symbols to `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE`; update `_baselines.yaml` (FR-024 / FR-040)
- [x] T014 Write `tests/charter/test_invocation_context.py` covering `from_repo()`, guards, and `ContextPreconditionError`

**Implementation Notes**:
- T011: `ProjectContext` is a dataclass holding `repo_root: Path`, `pack_context: PackContext`, and `charter_loaded: bool`. `OperationalContext` is a lightweight wrapper that adds the current WP state (claimed WP ID, agent profile). `ContextPreconditionError` is a `RuntimeError` subclass raised by guard methods when preconditions fail.
- T012: `from_repo(repo_root)` loads `PackContext.from_config(repo_root)` and sets `charter_loaded = True` if `.kittify/charter/charter.md` exists. `require_charter_loaded()`, `require_mission_type_activated(mt)`, and `require_artifact_activated(kind, artifact_id)` raise `ContextPreconditionError` with structured messages on failure.
- T013: The 4 symbols are `ProjectContext`, `OperationalContext`, `ContextPreconditionError`, and the `from_repo` factory symbol. Add them to the `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` list in `test_no_dead_symbols.py` so the test does not fail while the module is being wired.
- T014: Test `from_repo()` with (a) no charter file, (b) charter file present; test each `require_*()` raises on failure and passes on success; test `ContextPreconditionError` message format.

**Risks**: `_baselines.yaml` bumps must be coordinated with WP01 T003 bump to avoid rebase conflicts.

---

### WP04 — Default Charter Pack + CharterPackManager

**Goal**: Ship `src/charter/packs/default.yaml` with all 9 activation kinds fully populated with built-in IDs. Implement `CharterPackManager` with `activate()`, `deactivate()`, `list_activated()`, `list_available()`, and `merge_defaults()`.
**Priority**: High
**Dependencies**: WP02, WP03
**Estimated size**: ~450 lines
**Subtasks**: T015–T019
**Agent profile**: python-pedro

- [x] T015 Create `src/charter/packs/default.yaml` with all 9 activation kinds fully populated
- [x] T016 Create `src/charter/pack_manager.py` with `ActivationResult`, `MergeResult` value objects and `YAML_KEY_MAP`
- [x] T017 Implement `CharterPackManager.activate()` and `deactivate()` with cascade logic
- [x] T018 Implement `CharterPackManager.list_activated()`, `list_available()`, and `merge_defaults()`
- [x] T019 Write `tests/charter/test_pack_manager.py`

**Implementation Notes**:
- T015: `default.yaml` must enumerate every built-in artifact ID for all 9 kinds. This is a static shipped file under `src/charter/packs/`; it is never written at runtime. IDs come from the doctrine package.
- T016: `YAML_KEY_MAP` is a `dict[str, str]` mapping CLI kind names to their `config.yaml` keys (e.g. `"mission-type"` → `"mission_type_activations"`, `"directive"` → `"activated_directives"`). `ActivationResult` holds `kind`, `artifact_id`, `was_already_active: bool`, and `cascade_results: list[ActivationResult]`. `MergeResult` holds per-kind counts of written vs skipped entries.
- T017: `activate(kind, artifact_id, cascade_scope)` reads config.yaml via ruamel.yaml round-trip, appends the ID to the appropriate list, emits cascade activations for kinds in `cascade_scope`, returns `ActivationResult`. `deactivate()` mirrors activate; includes shared-artifact cascade protection (does not cascade-deactivate artifacts referenced by other still-active artifacts).
- T018: `list_activated()` returns current state per kind from config.yaml. `list_available()` loads `default.yaml` and returns all IDs not already activated. `merge_defaults()` adds any missing kind entries from `default.yaml` to config.yaml without overwriting existing entries.
- T019: Cover activate/deactivate round-trip, cascade scope, `merge_defaults()` idempotency, and `list_available()` exclusion of already-activated IDs.

**Risks**: Cascade deactivation shared-artifact protection requires knowing the full activation graph; ensure `deactivate()` reads the full current state before computing which cascade IDs are exclusively owned.

---

### WP05 — Upgrade Migration m_3_2_8

**Goal**: Write and register the `m_3_2_8_default_charter_pack` upgrade migration. It writes default activation keys to `config.yaml` with backup-before-write semantics for existing charter files.
**Priority**: High
**Dependencies**: WP04
**Estimated size**: ~280 lines
**Subtasks**: T020–T023
**Agent profile**: python-pedro

- [ ] T020 Create `m_3_2_8_default_charter_pack.py` with `detect()`, `can_apply()`, `apply()`
- [ ] T021 Implement backup-before-write pattern in `apply()` (C-008, NFR-002)
- [ ] T022 Write tests for `detect()` and `apply()` called directly (not via upgrade pipeline)
- [ ] T023 Register migration + verify baseline includes both m_3_2_7 and m_3_2_8

**Implementation Notes**:
- T020: `detect()` returns `True` if `.kittify/config.yaml` exists but lacks one or more `activated_*` keys (i.e., not yet migrated). `can_apply()` returns `True` if `.kittify/` directory exists. `apply()` calls `CharterPackManager.merge_defaults()` to populate missing keys.
- T021: In `apply()`, before any write, if `.kittify/charter/charter.md` exists: copy it to `.kittify/charter/backups/charter-{timestamp}.md`; write a `CharterBackup` metadata record; print a prominent warning about the backup. Use `ruamel.yaml` round-trip for `config.yaml` writes to preserve existing comments and formatting.
- T022: Tests must cover: (a) project with no `activated_*` keys → migration applies; (b) project with all keys present → migration skips; (c) project with charter file → backup created before write; (d) backup is a byte-for-byte copy of the original.
- T023: Add `"m_3_2_8_default_charter_pack"` to the migration registry and the `test_no_dead_modules.py` allowlist. Confirm both `m_3_2_7` and `m_3_2_8` appear in the baseline.

**Risks**: `ruamel.yaml` round-trip must preserve inline comments in config.yaml; validate with a real config.yaml fixture that contains comments.

---

### WP06 — Charter CLI: Activate / Deactivate / List / Pack

**Goal**: Refactor `activate.py` for all 9 kinds, create `deactivate.py` and `list.py` as first-class commands, create `pack.py` with consistency-check subcommand, and fix the reader gap (FR-014). All existing activate tests must be updated to cover all 9 kinds.
**Priority**: High
**Dependencies**: WP03, WP04
**Estimated size**: ~480 lines
**Subtasks**: T024–T029
**Agent profile**: python-pedro

- [ ] T024 Refactor `activate.py` CLI to call `CharterPackManager.activate()` for all 9 kinds + `--cascade`
- [ ] T025 Fix reader gap (FR-014): refactor `charter_activate.py` `activate_mission_type_override()` to write `mission_type_activations` to `config.yaml` instead of override files
- [ ] T026 Create `deactivate.py` with all 9 kinds and shared-artifact cascade protection
- [ ] T027 Create `list.py` with `charter list` and `--show-available` Rich table output (FR-009, FR-010)
- [ ] T028 Create `pack.py` `charter pack consistency-check` subcommand; register all new commands in `_app.py`
- [ ] T029 Update/write CLI tests for activate (all 9 kinds), deactivate, list, and pack consistency-check

**Implementation Notes**:
- T024: Replace current per-kind dispatch in `activate.py` with a unified `activate <kind> <artifact-id> [--cascade <scope>]` command backed by `CharterPackManager.activate()`. The `--cascade` flag accepts `all` or a comma-separated list of kind names.
- T025: `charter_activate.py:activate_mission_type_override()` currently writes `.kittify/overrides/mission-types/<id>.yaml`. Change it to update the `mission_type_activations` list in `config.yaml` via `CharterPackManager`. The override-files write path is retired.
- T026: `deactivate <kind> <artifact-id> [--cascade <scope>]` mirrors `activate`; shared-artifact cascade protection surfaces as a printed warning listing which cascade-target IDs were skipped because they are referenced by other active artifacts.
- T027: `charter list` prints a Rich table with columns: Kind | Activated IDs | Available (if `--show-available`). Empty activation (frozenset) shown as `(none)`. `None` (all) shown as `(all built-ins)`.
- T028: `charter pack consistency-check` calls `ConsistencyReport` from WP07 and formats the result as a Rich table with exit code 1 if violations are found.
- T029: Test all 9 kinds through the activate/deactivate CLI surface via `typer.testing.CliRunner`. Cover cascade scope parsing, error messages for unknown artifact IDs, and `list --show-available` output format.

**Risks**: Retiring the override-files write path (T025) may break callers in `resolve_action_sequence()` that currently read override files; audit all readers before removing the write path.

---

### WP07 — Consistency Check Implementation

**Goal**: Implement `src/charter/consistency_check.py` with `ConsistencyReport` and the full validation algorithm: unknown-reference detection, cross-kind DRG-edge reference validation, kind-level duplicate detection, and kind-violation checks.
**Priority**: High
**Dependencies**: WP03, WP04
**Estimated size**: ~350 lines
**Subtasks**: T030–T033
**Agent profile**: python-pedro

- [ ] T030 Create `consistency_check.py` with `ConsistencyReport` and unknown-reference algorithm
- [ ] T031 Implement cross-kind DRG-edge reference validation in `consistency_check.py`
- [ ] T032 Implement kind-level duplicate-detection and kind-violation checks
- [ ] T033 Write `tests/charter/test_consistency_check.py` with at least one planted violation per check type

**Implementation Notes**:
- T030: `ConsistencyReport` is a dataclass with `violations: list[ConsistencyViolation]`, `passed: bool`, and `summary: str`. Unknown-reference check: for each artifact ID in the charter pack, verify the ID exists in the loaded doctrine catalog for its kind.
- T031: Cross-kind edge validation: for each DRG edge from an activated artifact to a referenced artifact of another kind, verify the referenced artifact is also activated. This surfaces implicit cascade requirements that the user did not explicitly activate.
- T032: Duplicate-detection: check that no artifact ID appears twice within the same kind's activation list. Kind-violation: check that artifact IDs are assigned to the correct kind (e.g., a directive ID does not appear in `activated_tactics`).
- T033: Plant one violation of each type in a synthetic fixture pack: one unknown reference, one missing cross-kind reference, one duplicate, one kind violation. Assert that `ConsistencyReport.violations` contains exactly those violations and `passed` is False.

**Risks**: Cross-kind edge validation requires loading the DRG for the activated mission types; this adds a dependency on `PackContext.activated_mission_types` being set, which requires WP04 to be complete.

---

### WP08 — Pattern A: DRG Filter Wiring (4 call sites + `_node_is_activated`)

**Goal**: Wire `filter_graph_by_activation` into all 4 Pattern A production call sites and extend `_node_is_activated` with per-artifact-ID frozenset checks. All tests mocking these call paths must be updated to pass a `PackContext`.
**Priority**: High
**Dependencies**: WP02, WP03
**Estimated size**: ~400 lines
**Subtasks**: T034–T038
**Agent profile**: python-pedro

- [x] T034 Extend `_node_is_activated` in `drg.py` with per-artifact-ID frozenset checks (FR-038)
- [x] T035 Wire `filter_graph_by_activation` in `context.py:_load_action_doctrine_bundle()`
- [x] T036 Wire in `reference_resolver.py:resolve_references_transitively()`
- [x] T037 Wire in `compiler.py:_resolve_transitive_reference_graph()`
- [x] T038 Wire in `executor.py` step contract execution path

**Implementation Notes**:
- T034: Current `_node_is_activated` checks only kind-level activation (`activated_kinds`). Extend it to additionally check whether the specific artifact ID is in the per-kind frozenset (e.g., `activated_directives`). When the per-kind frozenset is `None`, all IDs pass. When empty, no IDs pass. When non-empty, only listed IDs pass.
- T035: `context.py:_load_action_doctrine_bundle()` (line ~523) receives a `PackContext`. After loading and merging the DRG, call `filter_graph_by_activation(merged, pack_context)` before passing to `resolve_context()`.
- T036: `reference_resolver.py:resolve_references_transitively()` (line ~40) — add `pack_context: PackContext` parameter and call `filter_graph_by_activation` before `resolve_transitive_refs()`.
- T037: `compiler.py:_resolve_transitive_reference_graph()` (line ~499) — add `pack_context` parameter and apply filter after DRG load.
- T038: `executor.py` (line ~170) — pass `pack_context` through the step execution path and apply filter before `resolve_context()`.
- All 4 wiring changes must be grep-verifiable production call sites per DIR-013 (FR-031–FR-034).

**Risks**: Adding `pack_context` parameter to 4 functions may require updating call chains; trace each function's callers to avoid introducing `None` defaults that silently bypass filtering.

---

### WP09 — Pattern B+C: Flat Catalog + Direct Repository Wiring

**Goal**: Wire activation filtering for Pattern B kinds (paradigm/procedure via flat catalog and DRG) and Pattern C kinds (agent-profile, mission-step-contract via direct repository). Wire `MissionStepRepository` to a production call site. All tests for wired call sites must be updated.
**Priority**: High
**Dependencies**: WP02, WP08
**Estimated size**: ~420 lines
**Subtasks**: T039–T043
**Agent profile**: python-pedro

- [ ] T039 Wire Pattern B: `generate.py:47` — construct `DoctrineService` with `pack_context`
- [ ] T040 Wire `org_charter.py:660, 710` callers of `load_org_charter_policies()` to pass `pack_context`
- [ ] T041 Wire `doctor.py:2332` + `org_layer.py:218,236` to pass/accept `pack_context` (FR-037)
- [ ] T042 Wire Pattern C: `DoctrineService.agent_profiles` via `charter/resolver.py` with activation filter
- [ ] T043 Add `MissionStepRepository` to `charter/mission_steps.py` re-exports; wire to production call site (FR-016)

**Implementation Notes**:
- T039: `generate.py:47` constructs a `DoctrineService`. Extend the constructor to accept `pack_context: PackContext | None = None` and filter `.paradigms`/`.procedures` properties when non-None. Pass `pack_context` from the generate command's invocation context.
- T040: `org_charter.py:load_org_charter_policies()` already has a `pack_context` parameter; its 3 callers at lines 660 and 710 (and the 4th at `doctor.py:2332`) pass nothing. Thread `pack_context` from the call site.
- T041: `doctor.py:2332` is a 4th caller of `load_org_charter_policies()` that currently passes only `repo_root`. Wire `pack_context` here so `spec-kitty doctor` shows a filtered policy picture. `org_layer.py:218,236` needs `pack_context` parameter added to its linter check functions.
- T042: `charter/resolver.py:~257` accesses `DoctrineService.agent_profiles`. Filter the result by `pack_context.activated_agent_profiles` — if the frozenset is non-None, return only profiles whose IDs are in the frozenset.
- T043: `charter/mission_steps.py` is currently a stub. Add `MissionStepRepository` to its `__all__` / re-exports. Wire `MissionStepRepository.resolve()` at one verified production call site (the most natural is the step contract executor already touched in WP08 T038).

**Risks**: `DoctrineService` changes affect many consumers; keep the `pack_context=None` default to avoid breaking existing callers, and ensure that `None` means "no filtering" (not "filter everything").

---

### WP10 — WP Lifecycle Gates

**Goal**: Add charter activation gates to `finalize-tasks` (profile availability check) and `agent action implement` (precondition check before worktree creation). Add hard-fail to non-activated artifact lookup in DRG/tactic resolution paths (FR-019). Update existing lifecycle tests to match new behavior.
**Priority**: High
**Dependencies**: WP02, WP04
**Estimated size**: ~350 lines
**Subtasks**: T044–T047
**Agent profile**: python-pedro

- [ ] T044 Add charter profile gate to `spec-kitty agent mission finalize-tasks` (FR-017)
- [ ] T045 Add charter profile precondition to `spec-kitty agent action implement` before worktree creation (FR-018)
- [ ] T046 Wire hard-fail on non-activated artifact lookup in DRG/tactic resolution paths (FR-019)
- [ ] T047 Write tests for lifecycle gates: finalize-tasks hard-fail + implement hard-fail scenarios

**Implementation Notes**:
- T044: In `finalize-tasks`, after loading the WP metadata, call `ProjectContext.from_repo()` and then `require_artifact_activated("agent-profile", wp_meta.agent_profile)` if the WP declares an `agent_profile`. Raise `ContextPreconditionError` with a message that names the missing profile and suggests running `charter activate agent-profile <id>`.
- T045: In `agent action implement`, before creating the worktree, call `ProjectContext.from_repo()` and verify the WP's declared agent profile is activated. This is the last enforcement point before environment creation.
- T046: Create `src/charter/exceptions.py` (WP10-owned) with `CharterActivationError(RuntimeError)`. When a charter-aware resolution path receives a filtered DRG and the requested artifact is absent from the filtered graph, the caller raises `CharterActivationError` with the artifact identifier, activated set, and resolution command.
- T047: Tests cover: (a) `finalize-tasks` raises on unactivated agent profile; (b) `finalize-tasks` passes when profile is activated; (c) `implement` raises on unactivated profile; (d) `implement` does not raise when no profile declared; (e) DRG hard-fail raises `CharterActivationError` for direct reference to non-activated artifact.

**Risks**: Hard-fail (T046) must distinguish between direct references (hard-fail) and incidental traversal (skip); clarify the distinction in comments before implementing.

---

### WP11 — Test Quality Improvements

**Goal**: Extend NFR-001 to real filesystem I/O with p99 multi-run methodology; add FR-027 activation filter test; fix subprocess test mark (FR-029); replace vacuous assertion with meaningful invariant (FR-030).
**Priority**: Should
**Dependencies**: WP02, WP08
**Estimated size**: ~280 lines
**Subtasks**: T048–T051
**Agent profile**: python-pedro

- [x] T048 Extend NFR-001 test to real filesystem I/O, multi-run p99 methodology (FR-026)
- [x] T049 Add FR-027 test: `mission_type_activations: [software-dev]` → documentation/research/plan excluded
- [x] T050 Fix FR-029: move subprocess call from fast-marked unit test to integration mark
- [x] T051 Fix FR-030: replace vacuous assertion in decision dispatch test with meaningful invariant

**Implementation Notes**:
- T048: The existing NFR-001 test uses an in-memory mock and measures a single wall-clock run. Replace with a temp-directory fixture that creates a real `.kittify/config.yaml` and measures 20 runs; compute p99 and assert ≤ 100ms. Use `pytest-benchmark` or `timeit` with explicit percentile logic.
- T049: Create a config fixture with `mission_type_activations: [software-dev]`. Assert that `PackContext.activated_mission_types` is `frozenset({"software-dev"})` and that `"documentation"`, `"research"`, and `"plan"` are not in the frozenset. This tests the hard-restriction behavior end-to-end.
- T050: The offending test is marked `@pytest.mark.fast` but calls a subprocess. Move it to `@pytest.mark.integration` so CI fast-test passes don't include I/O-heavy subprocess calls.
- T051: The vacuous assertion is likely `assert result is not None` or `assert True` in the decision dispatch test. Replace with an assertion on the actual dispatch outcome (e.g., the correct handler was called, or the returned object has the expected type and non-default field values).

**Parallel Opportunities**: All 4 subtasks are independent and can be executed in any order within the WP.

**Risks**: p99 threshold of 100ms is tight on slow CI runners; use `pytest.mark.slow` and skip in fast-CI if needed, while keeping the methodology correct.

---

## Execution Notes

### Agent Profile Assignment

All WPs use `python-pedro` (Python implementer). No curator or documentation-only WPs in this mission.

### Branch Strategy

Planning artifacts were generated on `pr/charter-doctrine-mission-type-configuration`. All implementation changes must be committed to `pr/charter-doctrine-mission-type-configuration`. This is both the planning branch and the merge target.

### Test Marks

- `@pytest.mark.fast` — unit tests with no I/O (default for new tests)
- `@pytest.mark.doctrine` — tests that load doctrine artifacts from the filesystem
- `@pytest.mark.architectural` — pytestarch layer-rule tests (run via `pytest tests/architectural/`)
- `@pytest.mark.integration` — tests involving subprocess, worktrees, or multi-process I/O

### Key Constraints (from charter)

- `doctrine.*` must **never** import `charter.*` (DIR-001 domain isolation; enforced by `test_layer_rules.py`)
- All activation state reads and writes go through `charter.*` APIs (DIR-001)
- Empty activation list = nothing available — no reader-side fallback (DIR-002 hard restriction)
- Default charter pack is the sole backward-compatibility safety net (DIR-004)
- Backup-before-write for all charter upgrade operations (DIR-006)
- Every new module must have a verified production call site before the WP is done (DIR-013)

### Three-State Semantics Summary

| Config value | Python value | Meaning |
|---|---|---|
| Key absent from config.yaml | `None` | All built-in artifacts available (unmanaged project) |
| `activated_directives: []` | `frozenset()` | Nothing available — hard restriction with empty set |
| `activated_directives: [DIRECTIVE_001]` | `frozenset({"DIRECTIVE_001"})` | Only `DIRECTIVE_001` available |

The `and raw` guard that converted `[]` → `None` is removed in WP02 T009. The default charter pack (WP04 T015) ensures that existing projects receive a fully populated activation set after running `spec-kitty upgrade`, preserving all previously available behavior.

### Wiring Verification

Per DIR-013, the following FRs are verified by grep-checking production call sites:

| FR | Call site | File |
|----|-----------|------|
| FR-031 | `filter_graph_by_activation` in `_load_action_doctrine_bundle` | `src/charter/context.py` |
| FR-032 | `filter_graph_by_activation` in `resolve_references_transitively` | `src/charter/reference_resolver.py` |
| FR-033 | `filter_graph_by_activation` in `_resolve_transitive_reference_graph` | `src/charter/compiler.py` |
| FR-034 | `filter_graph_by_activation` in step execution | `src/specify_cli/mission_step_contracts/executor.py` |
| FR-035 | `DoctrineService` constructed with `pack_context` | `src/specify_cli/cli/commands/charter/generate.py` |
| FR-036 | `load_org_charter_policies` called with `pack_context` | `src/specify_cli/doctrine/org_charter.py` |
| FR-037 | `doctor.py` passes `pack_context` to org charter linter | `src/specify_cli/cli/commands/doctor.py` |
| FR-016 | `MissionStepRepository` wired to production call site | `src/charter/mission_steps.py` |

### References

- `spec.md` — full FR/NFR list and user journeys
- `plan.md` — architecture decisions, complexity tracking, and project structure
- `research.md` — confirmed wiring table (kind → resolution pattern → call site), storage decision, upgrade algorithm
- `data-model.md` — `PackContext` field definitions, `ActivationKind` enum, `YAML_KEY_MAP` canonical mapping
- `contracts/charter-activate-cli.md` — activate CLI contract
- `contracts/charter-deactivate-cli.md` — deactivate CLI contract
- `contracts/charter-list-cli.md` — list CLI contract
- `contracts/charter-pack-consistency-check-cli.md` — pack consistency-check CLI contract
- `quickstart.md` — operator runbook: upgrade, activate/deactivate, consistency-check, lifecycle gate failures
