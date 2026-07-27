# Tasks: Templates as Mission Configuration

**Mission**: `templates-as-config-01KXMS1G`  
**Planning branch**: `feat/templates-as-config`  
**Mission merge target**: `feat/templates-as-config`  
**Generated**: 2026-07-16T06:39:25Z

## Planning Inputs

- [Specification](spec.md)
- [Implementation plan](plan.md)
- [Research decisions](research.md)
- [Data model](data-model.md)
- [Internal resolution contract](contracts/template-resolution-contract.md)
- [Developer quickstart](quickstart.md)
- `issue-matrix.md` on the coordination branch (issue #2658 claim/evidence ledger)

## Delivery Strategy

The implementation is divided at file-ownership and review boundaries. WP01 projects doctrine configuration through the activated resolved context. WP02 builds the shared two-stage selection seam. WP03 and WP04 then migrate the independent specification and planning readers in parallel. WP05 joins both paths for compatibility proof, integration coverage, architectural enforcement, and final quality evidence.

```text
WP01 → WP02 ─┬→ WP03 ─┐
             └→ WP04 ─┴→ WP05
```

No WP may broaden the mission into activation enumeration, runtime mission discovery, meta-less fallback removal, doctrine copy removal, derived mission-tree deletion, or release/version changes owned by issues #2659–#2661.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Campsite-clean WP01-owned context/repository surfaces before feature edits | WP01 | — |
| T002 | Add red doctrine/context tests for exact mapping and explicit null values | WP01 | — |
| T003 | Replace the reserved resolved-context slot with a typed lazy/cached mapping projection | WP01 | — |
| T004 | Source the projection only from the activated doctrine mission-type artifact | WP01 | — |
| T005 | Prove immutability/determinism and protect the 100 ms hot-path budget | WP01 | [P] |
| T006 | Run focused context/repository type, style, behavior, and ≥90% changed-code coverage gates | WP01 | — |
| T007 | Campsite-clean WP02-owned resolver/shim surfaces before feature edits | WP02 | — |
| T008 | Add red happy-path and override-precedence tests for artifact-key selection | WP02 | — |
| T009 | Add red null, missing-key, and unresolved-file diagnostic tests | WP02 | [P] |
| T010 | Implement the typed two-stage mapped-template resolution seam | WP02 | — |
| T011 | Preserve the isolated legacy/typeless boundary without new inference | WP02 | — |
| T012 | Expose the shared seam through the maintained CLI patch boundary and run ≥90% changed-code coverage gates | WP02 | — |
| T013 | Campsite-clean WP03-owned mission-creation surfaces before feature edits | WP03 | — |
| T014 | Add red mission-creation tests for doctrine-mapped specification templates | WP03 | — |
| T015 | Add red mission-creation tests for absent and invalid configuration | WP03 | [P] |
| T016 | Migrate specification scaffolding to the shared mapped-template seam | WP03 | — |
| T017 | Preserve creation transaction, event, metadata, and created-file behavior | WP03 | — |
| T018 | Run focused mission-creation regression, style, type, and ≥90% changed-code coverage gates | WP03 | — |
| T019 | Campsite-clean WP04-owned plan-command surfaces before feature edits | WP04 | — |
| T020 | Add red plan-scaffold tests for mapped filenames and override winners | WP04 | — |
| T021 | Add red plan tests for null, missing-key, and unresolved-file diagnostics | WP04 | [P] |
| T022 | Migrate plan scaffolding to the shared mapped-template seam | WP04 | — |
| T023 | Make pristine comparison use the same effective resolved template | WP04 | — |
| T024 | Preserve plan commit, branch, JSON, and lifecycle semantics | WP04 | [P] |
| T025 | Run focused plan-phase, commit-boundary, and ≥90% changed-code coverage gates | WP04 | — |
| T026 | Campsite-clean WP05-owned integration/e2e/architecture surfaces before feature edits | WP05 | — |
| T027 | Build, run, record, and delete the transitional software-development parity scaffold | WP05 | — |
| T028 | Add enduring activated-mission integration coverage for exact mappings and failures | WP05 | [P] |
| T029 | Extend CLI smoke coverage across specification and planning template outcomes | WP05 | [P] |
| T030 | Strengthen the architectural gate against magic defaults and surviving parity code | WP05 | — |
| T031 | Run the cross-WP targeted quality, ≥90% changed-code coverage, performance, terminology, and scope sweep | WP05 | — |
| T032 | Produce tracer-ready closeout evidence and obtain coordinator append acknowledgment | WP05 | — |

## Phase 1 — Canonical Configuration Foundation

### WP01 — Project Doctrine Template Mapping into Resolved Context

**Prompt**: [tasks/WP01-project-template-mapping.md](tasks/WP01-project-template-mapping.md)  
**Priority**: P0  
**Independent test**: Resolving every activated built-in mission type yields a mapping exactly equal to its doctrine artifact, including explicit null, without loading the new slot on the action-sequence hot path.  
**Dependencies**: None  
**Estimated prompt size**: ~260 lines

- [x] T001 Campsite-clean WP01-owned context/repository surfaces before feature edits (WP01)
- [x] T002 Add red doctrine/context tests for exact mapping and explicit null values (WP01)
- [x] T003 Replace the reserved resolved-context slot with a typed lazy/cached mapping projection (WP01)
- [x] T004 Source the projection only from the activated doctrine mission-type artifact (WP01)
- [x] T005 Prove immutability/determinism and protect the 100 ms hot-path budget (WP01)
- [x] T006 Run focused context/repository type, style, behavior, and ≥90% changed-code coverage gates (WP01)

**Implementation sketch**: First campsite-clean the owned context/repository surfaces with behavior-preserving focused tests or a frozen-baseline record. Then lock the observable contract in repository and resolved-context tests, add a deferred repository-backed mapping thunk/property, preserve null exactly, and demonstrate that action-sequence-only resolution does not trigger the mapping read.

**Parallel opportunities**: T005's performance/determinism fixture can be prepared independently after T002 defines expected values.
**Risks**: Accidentally reading a governance profile string, eagerly loading doctrine, or returning a mutable repository dictionary would violate the authority and performance contracts.

## Phase 2 — Shared Selection Contract

### WP02 — Resolve Artifact Keys through Activated Template Configuration

**Prompt**: [tasks/WP02-resolve-mapped-template.md](tasks/WP02-resolve-mapped-template.md)  
**Priority**: P0  
**Independent test**: A requested artifact kind resolves its doctrine-mapped filename through all existing file tiers, while null/missing/unresolved cases fail actionably and never select software-development content.  
**Dependencies**: WP01  
**Estimated prompt size**: ~300 lines

- [x] T007 Campsite-clean WP02-owned resolver/shim surfaces before feature edits (WP02)
- [x] T008 Add red happy-path and override-precedence tests for artifact-key selection (WP02)
- [x] T009 Add red null, missing-key, and unresolved-file diagnostic tests (WP02)
- [x] T010 Implement the typed two-stage mapped-template resolution seam (WP02)
- [x] T011 Preserve the isolated legacy/typeless boundary without new inference (WP02)
- [x] T012 Expose the shared seam through the maintained CLI patch boundary and run ≥90% changed-code coverage gates (WP02)

**Implementation sketch**: First campsite-clean the resolver/shim surfaces. Then define one typed selector that accepts a non-neutral activated context plus artifact kind, rejects neutral context with `TemplateConfigurationError`, validates configuration, and delegates the mapped filename to the unchanged five-tier resolver. Existing typeless readers stay on the explicit legacy branch outside this seam.

**Parallel opportunities**: T008 and T009 can be authored as separate red test groups before the implementation seam exists.
**Risks**: Conflating mapping with path precedence, retaining a default `mission="software-dev"` at the new API boundary, or changing existing resolver tier order.

## Phase 3 — Production Reader Migration

### WP03 — Scaffold Specifications from Mission Configuration

**Prompt**: [tasks/WP03-migrate-specification-reader.md](tasks/WP03-migrate-specification-reader.md)  
**Priority**: P0  
**Independent test**: Mission creation for activated software-development copies the mapped effective spec template, honors overrides, and refuses absent/invalid template configuration instead of creating an empty or borrowed spec.  
**Dependencies**: WP02  
**Estimated prompt size**: ~280 lines

- [x] T013 Campsite-clean WP03-owned mission-creation surfaces before feature edits (WP03)
- [x] T014 Add red mission-creation tests for doctrine-mapped specification templates (WP03)
- [x] T015 Add red mission-creation tests for absent and invalid configuration (WP03)
- [x] T016 Migrate specification scaffolding to the shared mapped-template seam (WP03)
- [x] T017 Preserve creation transaction, event, metadata, and created-file behavior (WP03)
- [x] T018 Run focused mission-creation regression, style, type, and ≥90% changed-code coverage gates (WP03)

**Implementation sketch**: First campsite-clean the owned mission-creation surfaces. Then drive `create_mission_core` red-first in the canonical core tests, replace its two hard-coded local file checks and empty-file fallback with the shared selector, and keep the CLI mission-create suites as read-only adjacent regression coverage.

**Parallel opportunities**: WP03 can execute in parallel with WP04 after WP02 is approved; within WP03, positive and failure fixtures can be authored separately.  
**Risks**: Changing when the mission directory/event stream is created, leaving partial state on configuration failure, or testing only a helper rather than the real creation path.

### WP04 — Scaffold and Compare Plans from Mission Configuration

**Prompt**: [tasks/WP04-migrate-plan-reader.md](tasks/WP04-migrate-plan-reader.md)  
**Priority**: P0  
**Independent test**: Plan setup resolves the activated mission type's `plan` mapping for both scaffold and pristine comparison, honors overrides, and reports actionable absent/invalid configuration without changing commit or branch behavior.  
**Dependencies**: WP02  
**Estimated prompt size**: ~320 lines

- [x] T019 Campsite-clean WP04-owned plan-command surfaces before feature edits (WP04)
- [x] T020 Add red plan-scaffold tests for mapped filenames and override winners (WP04)
- [x] T021 Add red plan tests for null, missing-key, and unresolved-file diagnostics (WP04)
- [x] T022 Migrate plan scaffolding to the shared mapped-template seam (WP04)
- [x] T023 Make pristine comparison use the same effective resolved template (WP04)
- [x] T024 Preserve plan commit, branch, JSON, and lifecycle semantics (WP04)
- [x] T025 Run focused plan-phase, commit-boundary, and ≥90% changed-code coverage gates (WP04)

**Implementation sketch**: First campsite-clean the owned plan-command surfaces. Then extend phase tests through the maintained patch seam, route both `_scaffold_plan_template` and `_is_plan_pristine` through one effective resolution result, and run the existing plan commit-boundary integration cases unchanged.

**Parallel opportunities**: WP04 can execute in parallel with WP03 after WP02; T024's unchanged-boundary assertions can be audited while T020/T021 are written.
**Risks**: Scaffold and pristine logic resolving different winners, duplicate resolution changing warnings, or disturbing the setup-plan two-pass lifecycle.

## Phase 4 — Compatibility and Merge-Ready Gates

### WP05 — Prove Parity and Enforce the Authority Swap

**Prompt**: [tasks/WP05-prove-template-authority-swap.md](tasks/WP05-prove-template-authority-swap.md)  
**Priority**: P1  
**Independent test**: End-to-end specification and planning flows retain exact shipped software-development content and override behavior, all absent-configuration cases fail closed, and no transitional scaffold or magic default selection survives.  
**Dependencies**: WP03, WP04  
**Estimated prompt size**: ~340 lines

- [x] T026 Campsite-clean WP05-owned integration/e2e/architecture surfaces before feature edits (WP05)
- [x] T027 Build, run, record, and delete the transitional software-development parity scaffold (WP05)
- [x] T028 Add enduring activated-mission integration coverage for exact mappings and failures (WP05)
- [x] T029 Extend CLI smoke coverage across specification and planning template outcomes (WP05)
- [x] T030 Strengthen the architectural gate against magic defaults and surviving parity code (WP05)
- [x] T031 Run the cross-WP targeted quality, ≥90% changed-code coverage, performance, terminology, and scope sweep (WP05)
- [x] T032 Produce tracer-ready closeout evidence and obtain coordinator append acknowledgment (WP05)

**Implementation sketch**: First campsite-clean the owned quality surfaces. Create and delete the parity scaffold, extend enduring integration/e2e/architecture coverage, run the scoped gates including ≥90% changed-code coverage, audit non-goals, and block WP approval until the primary-checkout coordinator acknowledges appending the evidence to all three traces.

**Parallel opportunities**: T028 and T029 touch different test files and may be developed in parallel once both reader WPs are merged into the lane.
**Risks**: Leaving the old path as a permanent oracle, writing a vacuous text-only architecture check, or allowing final QA to mask a reader-specific regression with mocks.

## Requirement Coverage

Requirement references are registered in WP frontmatter through `spec-kitty agent tasks map-requirements`. Final validation must report no unmapped functional requirements. NFR and constraint coverage is carried explicitly in prompt success criteria and review guidance.

## Execution Notes

- Every implementation WP uses the `python-pedro` profile and must load it before reading the prompt body.
- Runtime worktrees and branches are assigned from finalized `lanes.json`; do not create implementation worktrees during task authoring.
- `finalize-tasks` forbids WP ownership under `kitty-specs/`; implementers record tracer-ready evidence in Activity Logs, and WP05 cannot be approved until the mission coordinator appends it to all three primary-checkout traces and records acknowledgment.
- Issue #2658 is assigned to the operator, has a coordination-owned `issue-matrix.md` row, and must have a tracker comment naming `templates-as-config-01KXMS1G` before implementation starts.
- Reviewer and implementer roles remain distinct during the later implement/review loop.
- Work-package status is event-owned; do not invent task-status subdirectories or edit status in WP frontmatter.
