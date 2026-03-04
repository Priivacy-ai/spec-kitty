# Work Packages: Agent Profile System (Remaining Scope)

**Inputs**: Design documents from `/kitty-specs/045-agent-profile-system/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md
**Tests**: Explicitly required by spec (ATDD/TDD); each WP includes test-first tasks.
**Organization**: Fine-grained subtasks (`Txxx`) roll up into independently deliverable work packages (`WPxx`).

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).

---

## Work Package WP05: Doctrine Package Distribution Foundation (Priority: P1) 🎯 MVP

**Goal**: Make `doctrine` reliably distributable/importable in wheel installs, unblocking all downstream doctrine-dependent work.
**Independent Test**: Build/install wheel in clean venv; `import doctrine` and shipped profile loading succeed.
**Prompt**: `/tasks/WP05-doctrine-package-distribution-foundation.md`
**Estimated Prompt Size**: ~320 lines

### Included Subtasks

- [ ] T001 Create/verify doctrine packaging metadata and package-data inclusion rules
- [ ] T002 [P] Update root package dependency wiring so CLI distribution resolves doctrine dependency
- [ ] T003 Replace fragile filesystem access with package-resource-safe loading paths
- [ ] T004 Add wheel smoke test for importability and shipped profile access
- [ ] T005 Validate build/install workflow and document distribution guardrails

### Implementation Notes

- Keep edits focused on distribution/import behavior; avoid mixing migration/interview/init logic in this WP.
- Ensure shipped YAML/templates/directives are included as package artifacts.

### Parallel Opportunities

- T002 and T004 can proceed once packaging shape from T001 is clear.

### Dependencies

- None.

### Risks & Mitigations

- Risk: Missing package data at install time. Mitigation: zipfile-based wheel assertions + runtime smoke tests.

---

## Work Package WP08: ToolConfig Migration and Compatibility (Priority: P1)

**Goal**: Deliver upgrade migration and runtime fallback for `agents` → `tools` rename without breaking existing projects.
**Independent Test**: Legacy configs load with warning; migration rewrites key; upgraded configs load cleanly.
**Prompt**: `/tasks/WP08-toolconfig-migration-and-compatibility.md`
**Estimated Prompt Size**: ~340 lines

### Included Subtasks

- [ ] T006 Add migration module for config key rename in `.kittify/config.yaml`
- [ ] T007 Register migration in upgrade pipeline and release migration manifest
- [ ] T008 Update ToolConfig loader/writer paths to prefer `tools` and fallback to legacy key with warning
- [ ] T009 [P] Add migration + compatibility tests (legacy, migrated, missing keys)
- [ ] T010 Update docs/help text and deprecation messaging for canonical terminology

### Implementation Notes

- Preserve backward compatibility while making `tools` canonical for writes.
- Migration should be idempotent and safe on partially upgraded repos.

### Parallel Opportunities

- T009 can run in parallel with T010 after T008 interface stabilizes.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Risk: Silent config regressions. Mitigation: fixture matrix for all key-state permutations.

---

## Work Package WP09: CI and Packaging Verification Alignment (Priority: P1)

**Goal**: Align CI to exercise doctrine packaging/import paths and guard against future distribution regressions.
**Independent Test**: CI executes doctrine tests, package smoke checks, and module-entry smoke checks consistently.
**Prompt**: `/tasks/WP09-ci-and-packaging-verification-alignment.md`
**Estimated Prompt Size**: ~260 lines

### Included Subtasks

- [ ] T011 Audit and update CI workflow test selection to include doctrine suite explicitly
- [ ] T012 Add install-time smoke test(s) for `python -m specify_cli` and doctrine imports
- [ ] T013 [P] Add wheel content verification assertions for shipped doctrine assets
- [ ] T014 Ensure local/CI command parity and document expected checks

### Implementation Notes

- Keep tests deterministic and fast enough for CI budget.

### Parallel Opportunities

- T013 can proceed in parallel with T012 once artifact names/paths are fixed.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Risk: CI-only failures due to path assumptions. Mitigation: run tests against installed wheel, not source tree only.

---

## Work Package WP10: Shipped Directives and Consistency Enforcement (Priority: P1)

**Goal**: Ship complete directive set (001-019) and enforce profile-to-directive reference integrity in tests.
**Independent Test**: Consistency test passes for all shipped profiles and directive files.
**Prompt**: `/tasks/WP10-shipped-directives-and-consistency-enforcement.md`
**Estimated Prompt Size**: ~380 lines

### Included Subtasks

- [ ] T015 Extract canonical directive code/name mapping from shipped profile references
- [ ] T016 Add missing directive YAML files in `src/doctrine/directives/` using schema-conformant structure
- [ ] T017 [P] Validate each directive file against `directive.schema.yaml`
- [ ] T018 Implement consistency test: referenced code exists and declared name/title match
- [ ] T019 Add negative-path fixtures for missing/mismatched directive references
- [ ] T020 Document directive consistency policy for contributors and reviewers

### Implementation Notes

- Unreferenced directives are allowed; missing referenced directives are not.

### Parallel Opportunities

- T017/T019 can run in parallel once initial directive files exist.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Risk: Drift between profile references and directive titles. Mitigation: strict assertion on both code and title.

---

## Work Package WP13: Doctrine Structure Templates and Init Integration (Priority: P2)

**Goal**: Ship `REPO_MAP`/`SURFACES` templates and wire `spec-kitty init` bootstrap prompt to generate them.
**Independent Test**: Fresh init flow offers generation; accepted path creates templated files with placeholders.
**Prompt**: `/tasks/WP13-doctrine-structure-templates-and-init-integration.md`
**Estimated Prompt Size**: ~320 lines

### Included Subtasks

- [ ] T021 Add shipped structure templates under `src/doctrine/templates/structure/`
- [ ] T022 [P] Validate template placeholders and formatting contract via tests
- [ ] T023 Integrate optional generation prompt into init/bootstrap workflow
- [ ] T024 Implement generation destination logic and overwrite safety behavior
- [ ] T025 Add integration tests for accept/decline paths in init flow

### Implementation Notes

- Preserve existing init UX patterns and avoid forcing file generation.

### Parallel Opportunities

- T022 can run in parallel with T023 once templates exist.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Risk: Template drift across doctrine/specify copies. Mitigation: source-of-truth assertions in tests.

---

## Work Package WP14: Mission Schema Agent-Profile Compatibility (Priority: P2)

**Goal**: Extend mission schemas/runtime format with optional `agent-profile` while preserving full backward compatibility.
**Independent Test**: Existing shipped missions still validate; new missions with valid `agent-profile` validate.
**Prompt**: `/tasks/WP14-mission-schema-agent-profile-compatibility.md`
**Estimated Prompt Size**: ~270 lines

### Included Subtasks

- [ ] T026 Update mission schema to allow optional `agent-profile` on states/steps with profile ID pattern validation
- [ ] T027 Update runtime DAG mission format schema for optional step-level `agent-profile`
- [ ] T028 [P] Add schema validation tests for valid/invalid/omitted `agent-profile` cases
- [ ] T029 Verify and lock backward compatibility for all shipped missions

### Implementation Notes

- Optional means no behavior change for existing mission definitions.

### Parallel Opportunities

- T028 can run parallel with T027 after schema draft is in place.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Risk: breaking older mission formats. Mitigation: explicit regression suite using shipped mission corpus.

---

## Work Package WP15: Profile Inheritance Resolution and Matching Integration (Priority: P2)

**Goal**: Implement `resolve_profile()` inheritance chain resolution (shallow merge) and use resolved profiles in matching.
**Independent Test**: Multi-level inheritance and matching behavior pass deterministic tests.
**Prompt**: `/tasks/WP15-profile-inheritance-resolution-and-matching-integration.md`
**Estimated Prompt Size**: ~360 lines

### Included Subtasks

- [ ] T030 Implement `resolve_profile(profile_id)` with ancestor traversal and cycle-safe semantics
- [ ] T031 Implement shallow merge logic (child overrides one level deep, preserve parent missing keys)
- [ ] T032 Handle orphaned parent references with warning + safe fallback behavior
- [ ] T033 Integrate resolved profiles into weighted matching path
- [ ] T034 [P] Add inheritance/matching test matrix (single-level, multi-level, orphan, cycle)

### Implementation Notes

- Keep merge semantics uniform across sections and deterministic for tests.

### Parallel Opportunities

- T034 can run parallel as logic solidifies; keep fixtures small and explicit.

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Risk: ambiguous merge semantics. Mitigation: codify with table-driven tests and edge-case fixtures.

---

## Work Package WP11: Agent Profile Interview Authoring Flow (Priority: P2)

**Goal**: Add interactive profile creation (`--interview`, `--defaults`) with role-based defaults and schema-validated output.
**Independent Test**: Guided interview writes valid `.agent.yaml`; fast path asks only required prompts.
**Prompt**: `/tasks/WP11-agent-profile-interview-authoring-flow.md`
**Estimated Prompt Size**: ~410 lines

### Included Subtasks

- [ ] T035 Design interview question flow and answer model aligned to AgentProfile schema sections
- [ ] T036 Implement `--interview` CLI path with structured Q&A and optional fields
- [ ] T037 Implement `--defaults` fast path with required-question-only behavior
- [ ] T038 Add role-capability prepopulation and schema validation before persist
- [ ] T039 [P] Add CLI tests (happy path, defaults path, validation failure, overwrite protection)
- [ ] T040 Add output messaging and file write safeguards for project profile directory

### Implementation Notes

- Follow constitution interview UX patterns for consistency.

### Parallel Opportunities

- T039 can be developed in parallel once CLI argument contract is stable.

### Dependencies

- Depends on WP10.

### Risks & Mitigations

- Risk: brittle interactive tests. Mitigation: isolate prompt/response adapter and mock cleanly.

---

## Work Package WP12: Agent Profile Initialization Command (Priority: P2)

**Goal**: Implement `spec-kitty agent profile init <profile-id>` to configure active tool context using resolved profile governance artifacts.
**Independent Test**: Init command writes correct tool-context fragment and reports applied governance context.
**Prompt**: `/tasks/WP12-agent-profile-initialization-command.md`
**Estimated Prompt Size**: ~340 lines

### Included Subtasks

- [ ] T041 Add `init` subcommand and argument validation/error handling
- [ ] T042 Resolve profile inheritance and construct normalized governance payload for initialization
- [ ] T043 Detect active tool/config target and write context fragment idempotently
- [ ] T044 [P] Add command tests for success, missing profile, inherited profile, and tool-target selection

### Implementation Notes

- Keep init stateless and parallel-safe; avoid global mutable session markers.

### Parallel Opportunities

- T044 can run in parallel once output contract is fixed.

### Dependencies

- Depends on WP11, WP15.

### Risks & Mitigations

- Risk: wrong base context for tool integrations. Mitigation: explicit per-tool path tests + payload snapshot assertions.

---

## Dependency & Execution Summary

- **Sequence**: `WP05` → parallel wave (`WP08`, `WP09`, `WP10`, `WP13`, `WP14`, `WP15`) → `WP11` → `WP12`.
- **Parallelization**: Six WPs can run concurrently after WP05; each includes additional `[P]` subtasks.
- **MVP Scope**: `WP05` (distribution unblocker), then `WP10` + `WP08` to secure correctness/compatibility baseline.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Doctrine package metadata + data inclusion | WP05 | P1 | No |
| T002 | Root dependency wiring updates | WP05 | P1 | Yes |
| T003 | Resource-safe loading paths | WP05 | P1 | No |
| T004 | Wheel smoke tests | WP05 | P1 | Yes |
| T005 | Build/install validation + docs | WP05 | P1 | No |
| T006 | Add migration module | WP08 | P1 | No |
| T007 | Register migration | WP08 | P1 | No |
| T008 | Loader/writer compatibility | WP08 | P1 | No |
| T009 | Migration compatibility tests | WP08 | P1 | Yes |
| T010 | Terminology/deprecation docs | WP08 | P1 | No |
| T011 | CI doctrine test coverage updates | WP09 | P1 | No |
| T012 | Install-time smoke checks | WP09 | P1 | No |
| T013 | Wheel content assertions | WP09 | P1 | Yes |
| T014 | CI/local parity documentation | WP09 | P1 | No |
| T015 | Extract directive reference map | WP10 | P1 | No |
| T016 | Add directive YAML files | WP10 | P1 | No |
| T017 | Directive schema validation checks | WP10 | P1 | Yes |
| T018 | Consistency cross-reference test | WP10 | P1 | No |
| T019 | Negative-path fixtures | WP10 | P1 | Yes |
| T020 | Contributor consistency guidance | WP10 | P1 | No |
| T021 | Add REPO_MAP/SURFACES templates | WP13 | P2 | No |
| T022 | Template contract tests | WP13 | P2 | Yes |
| T023 | Init flow prompt integration | WP13 | P2 | No |
| T024 | File generation and overwrite safety | WP13 | P2 | No |
| T025 | Init integration tests | WP13 | P2 | No |
| T026 | Mission schema optional agent-profile | WP14 | P2 | No |
| T027 | Runtime DAG schema updates | WP14 | P2 | No |
| T028 | Schema validation tests | WP14 | P2 | Yes |
| T029 | Backward compatibility verification | WP14 | P2 | No |
| T030 | Implement resolve_profile traversal | WP15 | P2 | No |
| T031 | Implement shallow merge semantics | WP15 | P2 | No |
| T032 | Orphan reference handling | WP15 | P2 | No |
| T033 | Matching integration uses resolved profiles | WP15 | P2 | No |
| T034 | Inheritance/matching test matrix | WP15 | P2 | Yes |
| T035 | Interview flow design and answer model | WP11 | P2 | No |
| T036 | Implement interactive interview path | WP11 | P2 | No |
| T037 | Implement defaults fast path | WP11 | P2 | No |
| T038 | Role prepopulation + schema validation | WP11 | P2 | No |
| T039 | Interview CLI test suite | WP11 | P2 | Yes |
| T040 | Output messaging + write safeguards | WP11 | P2 | No |
| T041 | Add init subcommand contract | WP12 | P2 | No |
| T042 | Build resolved governance payload | WP12 | P2 | No |
| T043 | Tool detection + fragment writing | WP12 | P2 | No |
| T044 | Init command test suite | WP12 | P2 | Yes |

<!-- status-model:start -->
## Canonical Status (Generated)

- WP05: done
- WP08: done
- WP09: done
- WP10: done
- WP11: done
- WP12: done
- WP13: done
- WP14: done
- WP15: done
<!-- status-model:end -->
