# Tasks: Charter-Mediated Doctrine Selection (Mission B)

**Mission**: `charter-mediated-doctrine-selection-01KRTZCA`
**Branch**: `feat/org-doctrine-layer` → `feat/org-doctrine-layer`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data model**: [data-model.md](data-model.md)
**Total WPs**: 9 | **Total subtasks**: 51

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Extend `DoctrineSelectionConfig` with 5 new `selected_<kind>` fields | WP01 | |
| T002 | Extend `OrgCharterPolicy` with 7 new `required_<kind>` fields + `activations` field | WP01 | [P] |
| T003 | Add `ActivationEntry`, `ALLOWED_MISSION_TYPES`, `ALLOWED_ACTIONS`, `resolve_for_context` in `src/charter/activations.py` | WP01 | [P] |
| T004 | Extend `_OPTIONAL_EMPTY_OMIT_KEYS` in `src/charter/schemas.py` with 5 new keys for NFR-005 byte-stability | WP01 | |
| T005 | Unit tests for new schema fields (round-trip empty, round-trip populated, parity) | WP01 | [P] |
| T006 | Extend `charter.extractor._apply_selection_row` to read the 5 new `selected_<kind>` fields | WP02 | |
| T007 | Add `_apply_activations_block` handler reading top-level `activations:` from charter.md fenced YAML | WP02 | |
| T008 | Add `activations` field to `GovernanceConfig` (sibling of `doctrine`); round-trip through `governance.yaml` | WP02 | |
| T009 | Unit tests for extractor: round-trip selected_styleguides; round-trip activations block; mixed-fields fixture | WP02 | [P] |
| T010 | Create `src/charter/profiles.py` re-exporting `AgentProfile`, `AgentProfileRepository`, `Role`, `DEFAULT_ROLE_CAPABILITIES` | WP03 | [P] |
| T011 | Create `src/charter/mission_steps.py` re-exporting `MissionStep`, `MissionStepContract`, `MissionStepContractRepository` | WP03 | [P] |
| T012 | Create `src/charter/drg.py` re-exporting DRG types + functions (`DRGEdge`, `DRGGraph`, `DRGNode`, `Relation`, `NodeKind`, `load_graph`, `merge_layers`, `resolve_context`, `ResolvedContext`) | WP03 | [P] |
| T013 | Create `src/charter/primitives.py` re-exporting `PrimitiveExecutionContext`, `execute_with_glossary` | WP03 | [P] |
| T014 | Create `src/charter/resolution.py` re-exporting `ResolutionResult`, `ResolutionTier` | WP03 | [P] |
| T015 | Create `src/charter/versioning.py` re-exporting `check_bundle_compatibility`, `get_bundle_schema_version` | WP03 | [P] |
| T016 | Add `tests/architectural/test_charter_facades_reexport_doctrine.py` asserting each facade re-exports the named doctrine symbols | WP03 | [P] |
| T017 | Add `_render_selected_styleguides` helper in `src/charter/context.py` | WP04 | |
| T018 | Add `_render_selected_toolguides`, `_render_selected_procedures`, `_render_selected_agent_profiles`, `_render_selected_mission_step_contracts` helpers | WP04 | |
| T019 | Wire all 5 new render helpers into `build_charter_context` after existing directive/tactic renderers | WP04 | |
| T020 | Carry provenance metadata (`source: org` / pack name) through new renderers for org-distributed artifacts | WP04 | |
| T021 | Unit tests: each new renderer emits ID + body (or fetch + when-doing under overflow); provenance line present for org artifacts | WP04 | [P] |
| T022 | Add `_render_activation_stanza` helper in `src/charter/context.py` producing the "When you `<action>` in a `<mission_type>` mission, run ..." line | WP05 | |
| T023 | Wire activation resolver call (`charter.activations.resolve_for_context`) into `build_charter_context` and render matching entries | WP05 | |
| T024 | Populate `tests/architectural/test_trigger_registry_coverage.py::_REGISTERED_TRIGGERS` with the 15-token frozenset per plan §2.10 | WP05 | [P] |
| T025 | Unit tests: activation stanza emitted on context match; wildcard match works; multiple matches concatenate in declaration order | WP05 | [P] |
| T026 | Extend `apply_org_charter_to_interview` in `src/specify_cli/doctrine/org_charter.py` to union every `required_<kind>` (7 new) into `interview_data.selected_<kind>` | WP06 | |
| T027 | Extend `load_org_charter_policies` merge to handle all 8 `required_<kind>` lists with union-preserving-first-seen-order semantics | WP06 | |
| T028 | Extend org-pack merge for `activations` field (concatenate; last-duplicate-wins on identity 4-tuple) | WP06 | |
| T029 | Extend `DoctrineLayerCollisionWarning` emission to cover styleguides, toolguides, paradigms, procedures, mission_step_contracts (FR-014) | WP06 | |
| T030 | Implement strict missing-pack policy (FR-015): hard-fail with named-pack-and-path error when `local_path` does not exist | WP06 | |
| T031 | Unit tests: org charter union for each kind; collision warning for each kind; missing-pack hard-fail | WP06 | [P] |
| T032 | Migrate `src/specify_cli/invocation/registry.py` to `from charter.profiles import ...`; remove from allowlist | WP07 | |
| T033 | Migrate `src/specify_cli/invocation/router.py` to `from charter.profiles import ...`; remove from allowlist | WP07 | [P] |
| T034 | Migrate `src/specify_cli/mission_loader/registry.py` and `mission_loader/contract_synthesis.py` to `from charter.mission_steps import ...`; remove both from allowlist | WP07 | [P] |
| T035 | Migrate `src/specify_cli/mission_step_contracts/executor.py` to `from charter.mission_steps import ...` + `from charter.drg import ...`; remove from allowlist | WP07 | [P] |
| T036 | Migrate `src/specify_cli/calibration/walker.py` and `glossary/drg_builder.py` to `from charter.drg import ...`; remove both from allowlist | WP07 | [P] |
| T037 | Migrate `src/specify_cli/missions/__init__.py` to `from charter.primitives import ...`; remove from allowlist | WP07 | [P] |
| T038 | Migrate `src/specify_cli/runtime/resolver.py` to `from charter.resolution import ...`; remove from allowlist | WP07 | [P] |
| T039 | Migrate `src/specify_cli/cli/commands/charter.py`, `charter_bundle.py`, and `upgrade/migrations/m_3_2_6_charter_bundle_v2.py` to `from charter.versioning import ...`; remove from allowlist (or document as ≤ 2 exceptions per C-004) | WP07 | [P] |
| T040 | Promote `SchemaUtilities` to `src/kernel/schema_utils.py`; migrate `bulk_edit/occurrence_map.py`; remove from allowlist | WP07 | [P] |
| T041 | Add `MissionTypeProfile` Pydantic model + `load_profile` + `resolve_governance` in `src/charter/mission_type_profiles.py` | WP08 | |
| T042 | Ship `src/doctrine/missions/software-dev/governance-profile.yaml` mirroring today's `software-dev-default` selections | WP08 | [P] |
| T043 | Ship `src/doctrine/missions/documentation/governance-profile.yaml` with documentation-flavoured defaults | WP08 | [P] |
| T044 | Ship `src/doctrine/missions/research/governance-profile.yaml` with minimal defaults | WP08 | [P] |
| T045 | Ship `src/doctrine/missions/plan/governance-profile.yaml` with minimal defaults | WP08 | [P] |
| T046 | Wire `resolve_governance` into the mission-context pipeline (read meta.json mission_type; union with project + org) | WP08 | |
| T047 | Hard-fail on unknown mission_type with no project override; message names the unknown value | WP08 | |
| T048 | Add `spec-kitty doctrine new <kind> <name>` CLI command + `--pack <path>` flag in `src/specify_cli/cli/commands/doctrine.py` | WP09 | |
| T049 | Add `spec-kitty doctrine validate <path>` CLI command for project-layer validation | WP09 | [P] |
| T050 | Extend `spec-kitty doctor doctrine` with a "Selections" section listing per-kind active artifacts + resolved pack source | WP09 | [P] |
| T051 | Promote 10 glossary entries in `glossary/contexts/doctrine.md` from `Status: candidate` to `Status: canonical` (C-007); add user-doc note for missing-pack policy change (C-006) | WP09 | [P] |

---

## Work Packages

### WP01 — Schema extensions

**Priority**: P0 (everything depends on these schemas)
**Dependencies**: none
**Enables**: WP02, WP04, WP06, WP08, WP09

Extend `DoctrineSelectionConfig` with the 5 new `selected_<kind>` fields and `OrgCharterPolicy` with the 7 new `required_<kind>` fields. Add the new `charter.activations` module with `ActivationEntry`, vocabularies, and resolver. Extend `_OPTIONAL_EMPTY_OMIT_KEYS` for NFR-005 byte-stability.

**ATDD turns green:**
- `tests/architectural/test_artifact_selection_completeness.py` — 3/3
- `tests/architectural/test_activation_registry_schema.py` — 4/4 (import-level)

---

### WP02 — Charter sync extensions

**Priority**: P0 (selection rendering needs extraction)
**Dependencies**: WP01
**Enables**: WP04

Extend `charter.extractor` to read the 5 new `selected_<kind>` fields and the new top-level `activations:` block from `charter.md`. Round-trip through `governance.yaml`.

**ATDD turns green:**
- `tests/integration/test_user_doctrine_artifact_lifecycle.py::test_case_1_selected_styleguides_field_round_trips`

---

### WP03 — Charter facade modules

**Priority**: P1 (preparation for boundary migration)
**Dependencies**: none (independent of schema work)
**Enables**: WP07

Create the 6 re-export-only modules under `src/charter/` per the facade table in plan §1.3.

**ATDD turns green:**
- `tests/architectural/test_charter_facades_reexport_doctrine.py` (NEW — added by T016)
- `tests/architectural/test_layer_rules.py` — 8/8 stays green

---

### WP04 — Global selection rendering

**Priority**: P0 (Case 1 / Case 2 global selection happy path)
**Dependencies**: WP02
**Enables**: WP05 (re-uses fetch stanza helper)

Add 5 new `_render_selected_<kind>` helpers in `src/charter/context.py`, wire them into `build_charter_context`, carry provenance.

**ATDD turns green:**
- `tests/integration/test_user_doctrine_artifact_lifecycle.py::test_case_1_project_styleguide_appears_in_implement_prompt`

---

### WP05 — Activation registry rendering + trigger registry

**Priority**: P0 (Case 1 step 5 — context-scoped activation)
**Dependencies**: WP04
**Enables**: WP08

Add `_render_activation_stanza` helper, wire `resolve_for_context` into `build_charter_context`, populate `_REGISTERED_TRIGGERS` with the 15-token frozenset.

**ATDD turns green:**
- `tests/integration/test_user_doctrine_artifact_lifecycle.py::test_case_1_styleguide_render_includes_trigger_stanza`
- `tests/architectural/test_trigger_registry_coverage.py` — 2/2 (non-vacuous)

---

### WP06 — Org-charter pre-fill union + collision + missing-pack policy

**Priority**: P0 (Case 2 end-to-end)
**Dependencies**: WP01
**Enables**: WP09

Extend `apply_org_charter_to_interview` for all 7 new `required_<kind>` fields. Extend `DoctrineLayerCollisionWarning` to all 8 kinds. Implement FR-015 hard-fail policy.

**ATDD turns green:**
- `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_org_pack_styleguide_appears_in_consumer_prompt`
- `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_required_styleguides_in_org_charter_pre_fills`
- `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_org_styleguide_collision_with_builtin_warns`
- `tests/integration/test_org_pack_artifact_lifecycle.py::test_case_2_consumer_without_fetched_pack_fails_loudly`

---

### WP07 — Runtime → charter boundary migration

**Priority**: P0 (boundary ratchet must drop to ≤ 2 per C-004)
**Dependencies**: WP03
**Enables**: nothing further

Migrate the 13 runtime files in the boundary allowlist to import from charter facades. Promote `SchemaUtilities` to `kernel/`.

**ATDD turns green:**
- `tests/architectural/test_runtime_charter_doctrine_boundary.py` — allowlist drops from 13 to ≤ 2

---

### WP08 — Mission-type governance profiles

**Priority**: P0 (Journey 4)
**Dependencies**: WP04, WP05
**Enables**: WP09

Ship 4 `governance-profile.yaml` files, add the loader + resolver, hard-fail on unknown.

**ATDD turns green:**
- `tests/missions/test_mission_type_profile_resolution.py` — 14/14

---

### WP09 — Operator UX + glossary promotion

**Priority**: P1 (operator-facing, after the engine works)
**Dependencies**: WP04, WP06
**Enables**: mission acceptance

Add `doctrine new`, `doctrine validate`, extended `doctor doctrine` Selections section. Promote 10 glossary entries to canonical. Update user docs for missing-pack policy change (C-006).

**Acceptance gates:**
- New CLI commands have unit + integration tests
- Glossary entries flip to `Status: canonical`
- User docs call out the FR-015 behaviour change
