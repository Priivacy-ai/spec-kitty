# Tasks: Implement Review Retrospect Reliability

**Mission**: `01KQQSCWP7HAJRR93F98AESKH4` (mid8: `01KQQSCW`)  
**Spec**: [./spec.md](./spec.md) · **Plan**: [./plan.md](./plan.md) · **Quickstart**: [./quickstart.md](./quickstart.md)  
**Branch contract**: planning base `main` -> final merge `main` (matches target: yes)  
**Date**: 2026-05-03

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add the narrow `specify_cli.review.cycle` boundary and result types | WP01 |  | [D] |
| T002 | Implement canonical `review-cycle://` pointer builder and validator | WP01 |  | [D] |
| T003 | Implement pointer resolver with legacy `feedback://` normalization warnings | WP01 |  | [D] |
| T004 | Add review artifact required-frontmatter validation and fail-closed errors | WP01 |  | [D] |
| T005 | Add focused unit tests for artifact, pointer, and result invariants | WP01 |  | [D] |
| T006 | Replace `move-task` rejection artifact creation with the shared boundary | WP02 |  | [D] |
| T007 | Derive rejected `ReviewResult` before outbound `in_review` mutation | WP02 |  | [D] |
| T008 | Add fail-before-mutation CLI regressions for missing, empty, and invalid feedback | WP02 |  | [D] |
| T009 | Add `in_review -> planned` rejection integration coverage for #960 | WP02 |  | [D] |
| T010 | Run targeted status transition and emit regression tests | WP02 |  | [D] |
| T011 | Route fix-mode feedback resolution through the shared pointer resolver | WP03 |  | [D] |
| T012 | Preserve sentinel handling while warning on legacy or missing pointers | WP03 |  | [D] |
| T013 | Add fix-mode prompt tests for canonical and legacy review pointers | WP03 |  | [D] |
| T014 | Add regression coverage that focused rejection context loads from the canonical pointer | WP03 |  | [D] |
| T015 | Add a finalized-task routing fixture with stale discovery runtime state | WP04 |  | [D] |
| T016 | Make `spec-kitty next` prefer finalized task/WP lane state over stale phase state | WP04 |  | [D] |
| T017 | Cover implement, review, approved/done, blocked, and terminal routing outcomes | WP04 |  | [D] |
| T018 | Preserve existing `Decision` JSON contract and prompt-file invariant | WP04 |  | [D] |
| T019 | Add structured missing-record outcomes for `agent retrospect synthesize --json` | WP05 |  |
| T020 | Add explicit retrospective capture/init path or deterministic auto-initialization | WP05 |  |
| T021 | Distinguish missing mission, insufficient artifacts, record created, and synthesized states | WP05 |  |
| T022 | Add retrospective JSON and Rich/JSON compatibility regressions | WP05 |  |
| T023 | Build one focused end-to-end smoke fixture for reject -> fix -> approve -> next -> retrospect | WP06 |  |
| T024 | Verify #967, #966, #964, and #968 remain explicitly deferred unless adjacent | WP06 |  |
| T025 | Run the mission acceptance test set and update quickstart if commands differ | WP06 |  |
| T026 | Record local-sync-disabled verification rationale for purely local fixtures | WP06 |  |

---

## Work Packages

### WP01 - Shared Review-Cycle Boundary

**Goal**: Create the narrow shared invariant boundary for rejected review cycles.  
**Priority**: P0 foundation.  
**Independent Test**: `uv run pytest tests/review/test_cycle.py -q` proves artifact creation, frontmatter validation, pointer generation/resolution, legacy normalization, and rejected `ReviewResult` derivation without calling CLI commands.  
**Prompt**: `tasks/WP01-shared-review-cycle-boundary.md`  
**Requirement Refs**: FR-003, FR-004, FR-006, FR-007, NFR-001, NFR-003, NFR-004, C-003

#### Included Subtasks
- [x] T001 Add the narrow `specify_cli.review.cycle` boundary and result types (WP01)
- [x] T002 Implement canonical `review-cycle://` pointer builder and validator (WP01)
- [x] T003 Implement pointer resolver with legacy `feedback://` normalization warnings (WP01)
- [x] T004 Add review artifact required-frontmatter validation and fail-closed errors (WP01)
- [x] T005 Add focused unit tests for artifact, pointer, and result invariants (WP01)

#### Implementation Sketch
Create `src/specify_cli/review/cycle.py` and reuse `ReviewCycleArtifact` from `src/specify_cli/review/artifacts.py`. The new module should produce a single validated result object containing the artifact path, canonical pointer, and rejected `ReviewResult`. It must validate before returning data that callers can persist.

#### Parallel Opportunities
None inside this WP; it defines the boundary used by WP02 and WP03.

#### Dependencies
None.

#### Risks
Risk: the boundary grows into a review runtime. Mitigation: keep it limited to artifact, pointer, and rejected-result invariants.

---

### WP02 - Rejection Transition Adapter

**Goal**: Make normal `move-task` rejection from `in_review` work through the shared boundary and fail before mutation on invalid feedback.  
**Priority**: P0.  
**Independent Test**: CLI integration proves `agent tasks move-task WP01 --to planned --review-feedback-file <file>` from `in_review` persists a canonical pointer and rejected `ReviewResult` without lower-level repair.  
**Prompt**: `tasks/WP02-rejection-transition-adapter.md`  
**Requirement Refs**: FR-001, FR-002, FR-003, FR-006, FR-007, NFR-001, NFR-003, NFR-004

#### Included Subtasks
- [x] T006 Replace `move-task` rejection artifact creation with the shared boundary (WP02)
- [x] T007 Derive rejected `ReviewResult` before outbound `in_review` mutation (WP02)
- [x] T008 Add fail-before-mutation CLI regressions for missing, empty, and invalid feedback (WP02)
- [x] T009 Add `in_review -> planned` rejection integration coverage for #960 (WP02)
- [x] T010 Run targeted status transition and emit regression tests (WP02)

#### Implementation Sketch
Modify `src/specify_cli/cli/commands/agent/tasks.py` so rejection rollback calls the WP01 boundary before `emit_status_transition`. Pass both `review_ref` and `review_result` into the transition request. Add tests that inspect the event log after failure to prove no partial state was written.

#### Parallel Opportunities
Can run after WP01. WP04 and WP05 are independent.

#### Dependencies
Depends on WP01.

#### Risks
Risk: approval paths accidentally change. Mitigation: keep changes conditional on rejected planned rollback and run existing status tests.

---

### WP03 - Fix-Mode Pointer Resolution

**Goal**: Make fix-mode load rejection context through the same canonical pointer resolver used by rejection persistence.  
**Priority**: P1.  
**Independent Test**: Implement/fix-mode prompt tests load `review-cycle://...` feedback content, tolerate legacy `feedback://...` with warning, and ignore operational sentinels.  
**Prompt**: `tasks/WP03-fix-mode-pointer-resolution.md`  
**Requirement Refs**: FR-004, FR-005, NFR-001, NFR-002, NFR-003

#### Included Subtasks
- [x] T011 Route fix-mode feedback resolution through the shared pointer resolver (WP03)
- [x] T012 Preserve sentinel handling while warning on legacy or missing pointers (WP03)
- [x] T013 Add fix-mode prompt tests for canonical and legacy review pointers (WP03)
- [x] T014 Add regression coverage that focused rejection context loads from the canonical pointer (WP03)

#### Implementation Sketch
Modify `src/specify_cli/cli/commands/agent/workflow.py` to call the WP01 pointer resolver for feedback context. Keep `force-override` and `action-review-claim` sentinel behavior. Update or replace the current pointer tests with active 3.x coverage where needed.

#### Parallel Opportunities
Can run after WP01 and in parallel with WP02 once the boundary API is stable.

#### Dependencies
Depends on WP01.

#### Risks
Risk: old prompt tests are branch-gated or still assert legacy "feature" wording. Mitigation: add new 3.x-focused tests rather than weakening the canonical terminology rule.

---

### WP04 - Finalized Task Routing for `next`

**Goal**: Ensure `spec-kitty next` routes from finalized task/WP state instead of stale discovery phase state.  
**Priority**: P1.  
**Independent Test**: A fixture mission with finalized WPs and stale discovery runtime state routes to implement, review, merge/completion, terminal, or blocked decisions, never discovery.  
**Prompt**: `tasks/WP04-finalized-task-next-routing.md`  
**Requirement Refs**: FR-008, NFR-001, NFR-002, NFR-003, C-003

#### Included Subtasks
- [x] T015 Add a finalized-task routing fixture with stale discovery runtime state (WP04)
- [x] T016 Make `spec-kitty next` prefer finalized task/WP lane state over stale phase state (WP04)
- [x] T017 Cover implement, review, approved/done, blocked, and terminal routing outcomes (WP04)
- [x] T018 Preserve existing `Decision` JSON contract and prompt-file invariant (WP04)

#### Implementation Sketch
Modify the existing `src/specify_cli/next/runtime_bridge.py` and, only if necessary, helper logic in `src/specify_cli/next/decision.py`. Keep the runtime package boundary intact. Tests should assert public `Decision` JSON shape rather than private runtime internals.

#### Parallel Opportunities
Independent of WP02/WP03 after artifacts are available.

#### Dependencies
None.

#### Risks
Risk: changing next routing destabilizes custom missions. Mitigation: test only finalized software-dev task/WP override and preserve existing non-finalized behavior.

---

### WP05 - Retrospective Missing-Record Path

**Goal**: Give completed missions a first-class `agent retrospect` path when `retrospective.yaml` is missing.  
**Priority**: P1.  
**Independent Test**: `spec-kitty agent retrospect synthesize --mission <mission> --json` returns parseable JSON distinguishing record-created, synthesized, insufficient-artifacts, and mission-not-found outcomes.  
**Prompt**: `tasks/WP05-retrospective-missing-record-path.md`  
**Requirement Refs**: FR-009, FR-010, NFR-001, NFR-003

#### Included Subtasks
- [ ] T019 Add structured missing-record outcomes for `agent retrospect synthesize --json` (WP05)
- [ ] T020 Add explicit retrospective capture/init path or deterministic auto-initialization (WP05)
- [ ] T021 Distinguish missing mission, insufficient artifacts, record created, and synthesized states (WP05)
- [ ] T022 Add retrospective JSON and Rich/JSON compatibility regressions (WP05)

#### Implementation Sketch
Modify `src/specify_cli/cli/commands/agent_retrospect.py` and use existing `src/specify_cli/retrospective/reader.py`, `writer.py`, and schema models. Prefer explicit `capture` or `init` when records cannot be synthesized deterministically; allow synthesize to initialize only when completed mission artifacts are sufficient.

#### Parallel Opportunities
Independent of review-cycle WPs.

#### Dependencies
None.

#### Risks
Risk: fabricated retrospective data. Mitigation: fail with `insufficient_mission_artifacts` unless the completed mission evidence is adequate.

---

### WP06 - Focused Smoke and Acceptance Coverage

**Goal**: Prove the complete implement-review-retrospect control loop works as specified and keep optional issues scoped.  
**Priority**: P2 acceptance.  
**Independent Test**: One temporary mission fixture exercises reject -> canonical artifact/pointer -> fix-mode context -> approve/complete -> next routing -> retrospective path.  
**Prompt**: `tasks/WP06-focused-smoke-and-acceptance.md`  
**Requirement Refs**: FR-011, NFR-001, NFR-002, NFR-005, NFR-006, C-001, C-002, C-004, C-005, C-006, C-007

#### Included Subtasks
- [ ] T023 Build one focused end-to-end smoke fixture for reject -> fix -> approve -> next -> retrospect (WP06)
- [ ] T024 Verify #967, #966, #964, and #968 remain explicitly deferred unless adjacent (WP06)
- [ ] T025 Run the mission acceptance test set and update quickstart if commands differ (WP06)
- [ ] T026 Record local-sync-disabled verification rationale for purely local fixtures (WP06)

#### Implementation Sketch
Add a focused integration smoke test after WP02-WP05 land. Keep this package limited to end-to-end coverage and acceptance documentation; do not add new production behavior unless a small adjacent #967/#966/#964/#968 fix falls out naturally and is approved by the existing scope.

#### Parallel Opportunities
None; this is the final integration package.

#### Dependencies
Dependencies: WP02, WP03, WP04, WP05.

#### Risks
Risk: smoke coverage turns into a broad test-runner rewrite. Mitigation: keep #967 deferred unless a small proven root cause is discovered.

---

## Dependency & Execution Summary

- **Sequence**: WP01 first; WP02 and WP03 follow WP01; WP04 and WP05 can run independently; WP06 runs last.
- **Parallelization**: WP04 and WP05 are parallel-safe immediately. WP02 and WP03 are parallel-safe after WP01 defines the shared API.
- **MVP Scope**: WP01 + WP02 + WP03 close the highest-risk rejection and fix-mode trust path. WP04 and WP05 complete the other core bugs. WP06 proves acceptance.

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|---|---|
| FR-001 | WP02 |
| FR-002 | WP02 |
| FR-003 | WP01, WP02 |
| FR-004 | WP01, WP03 |
| FR-005 | WP03 |
| FR-006 | WP01, WP02 |
| FR-007 | WP01, WP02 |
| FR-008 | WP04 |
| FR-009 | WP05 |
| FR-010 | WP05 |
| FR-011 | WP06 |
| NFR-001 | WP01, WP02, WP03, WP04, WP05, WP06 |
| NFR-002 | WP03, WP04, WP06 |
| NFR-003 | WP01, WP02, WP03, WP04, WP05 |
| NFR-004 | WP01, WP02 |
| NFR-005 | WP06 |
| NFR-006 | WP06 |
| C-001 | WP06 |
| C-002 | WP06 |
| C-003 | WP01, WP04 |
| C-004 | WP06 |
| C-005 | WP06 |
| C-006 | WP06 |
| C-007 | WP06 |
