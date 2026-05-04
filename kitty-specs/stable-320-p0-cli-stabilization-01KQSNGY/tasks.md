# Work Packages: 3.2.0 Stable P0 CLI Stabilization

**Mission**: `stable-320-p0-cli-stabilization-01KQSNGY`
**Inputs**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`
**Target branch**: `main`
**Planning/base branch**: `main`
**Merge target branch**: `main`

## Organization

Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each WP is scoped to a cohesive stabilization concern and has non-overlapping ownership metadata in its prompt file.

`[P]` marks subtasks that can proceed in parallel once their WP dependencies are satisfied.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Reproduce or characterize the #967 status bootstrap/emit hang under bounded timeout | WP01 | No | [D] |
| T002 | Isolate background sync, adapter, event-loop, file-lock, or fixture teardown involvement | WP01 | No | [D] |
| T003 | Implement the smallest deterministic status fixture/runtime boundary fix | WP01 | No | [D] |
| T004 | Add bounded regression tests and diagnostics for bootstrap and emit paths | WP01 | Yes | [D] |
| T005 | Capture #967 validation evidence for release closeout | WP01 | Yes | [D] |
| T006 | Add latest review-cycle artifact fixtures and tests for rejected/approved precedence | WP02 | No | [D] |
| T007 | Enforce rejected-verdict fail-closed checks before approved/done WP state mutation | WP02 | No | [D] |
| T008 | Add durable explicit override support for rejected verdict supersession | WP02 | No | [D] |
| T009 | Extend mission status, mission review, and merge preflight contradiction diagnostics | WP02 | Yes | [D] |
| T010 | Preserve JSON stdout cleanliness for touched review/task commands | WP02 | Yes | [D] |
| T011 | Add end-to-end review consistency regression coverage | WP02 | No | [D] |
| T012 | Inventory active command registries, packaged templates, diagnostics, and counts for retired checklist drift | WP03 | No | [D] |
| T013 | Remove retired checklist from active registry and generation surfaces | WP03 | No | [D] |
| T014 | Preserve manifest-owned stale checklist cleanup without deleting user-owned files | WP03 | No | [D] |
| T015 | Align runtime doctor/count diagnostics and docs/comments with active command reality | WP03 | Yes | [D] |
| T016 | Add fresh command surface inventory tests for #968 | WP03 | Yes | [D] |
| T017 | Reproduce #964 with fresh Codex/global skill generation, including `spec-kitty.advise` | WP04 | No | [D] |
| T018 | Ensure generated `SKILL.md` files include required YAML frontmatter | WP04 | No | [D] |
| T019 | Add generated-skill frontmatter tests across relevant host surfaces | WP04 | Yes | [D] |
| T020 | Update snapshots or verifier expectations only after generated output is fixed | WP04 | Yes | [D] |
| T021 | Run focused validation for WP01 status hang evidence | WP05 | No | [D] |
| T022 | Run focused validation for WP02 review consistency evidence | WP05 | No | [D] |
| T023 | Run focused validation for WP03/WP04 command and skill surface evidence | WP05 | No | [D] |
| T024 | Run ruff and selected broader regression suites | WP05 | No | [D] |
| T025 | Compile release evidence mapped to #967, #904, #968, and #964 | WP05 | No | [D] |

---

## Phase 1 - Status Determinism

## Work Package WP01: Status Test Hang Stabilization (Priority: P0)

**Goal**: Fix or deterministically isolate the #967 status bootstrap/emit hang without weakening status semantics.
**Independent Test**: `uv run pytest tests/status -q --timeout=30`
**Prompt**: `tasks/WP01-status-test-hang-stabilization.md`
**Requirement Refs**: FR-001, FR-002, NFR-001, NFR-002, NFR-003, SC-001
**Estimated Prompt Size**: ~260 lines

### Included Subtasks

- [x] T001 Reproduce or characterize the #967 status bootstrap/emit hang under bounded timeout (WP01)
- [x] T002 Isolate background sync, adapter, event-loop, file-lock, or fixture teardown involvement (WP01)
- [x] T003 Implement the smallest deterministic status fixture/runtime boundary fix (WP01)
- [x] T004 [P] Add bounded regression tests and diagnostics for bootstrap and emit paths (WP01)
- [x] T005 [P] Capture #967 validation evidence for release closeout (WP01)

### Implementation Notes

Start from current `tests/status` behavior under the required 30-second timeout. Patch the real hang cause or isolate it at the fixture/adapter boundary. Do not replace semantic assertions with sleep-based workarounds.

### Parallel Opportunities

T004 and T005 can proceed once T001-T003 identify the target boundary.

### Dependencies

None.

### Risks

Timeout-only fixes can hide the real nondeterminism. The WP must document the cause or the exact isolation rationale.

---

## Phase 2 - Review State Safety

## Work Package WP02: Review Verdict Consistency Gate (Priority: P0)

**Goal**: Implement the fail-closed #904 policy across WP completion, mission status, mission review, and merge preflight, with explicit durable override support.
**Independent Test**: A WP with latest `verdict: rejected` cannot move to approved/done, and mission status/review/merge cannot pass silently, unless an override is recorded.
**Prompt**: `tasks/WP02-review-verdict-consistency-gate.md`
**Requirement Refs**: FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-001, NFR-005, SC-002, SC-003
**Estimated Prompt Size**: ~390 lines

### Included Subtasks

- [x] T006 Add latest review-cycle artifact fixtures and tests for rejected/approved precedence (WP02)
- [x] T007 Enforce rejected-verdict fail-closed checks before approved/done WP state mutation (WP02)
- [x] T008 Add durable explicit override support for rejected verdict supersession (WP02)
- [x] T009 [P] Extend mission status, mission review, and merge preflight contradiction diagnostics (WP02)
- [x] T010 [P] Preserve JSON stdout cleanliness for touched review/task commands (WP02)
- [x] T011 Add end-to-end review consistency regression coverage (WP02)

### Implementation Notes

Reuse existing review artifact helpers where possible. If a new helper is needed, keep it small and shared by mutation/preflight paths to avoid divergent logic. Failed checks must happen before state mutation.

### Parallel Opportunities

T009 and T010 can proceed after the latest-artifact contract in T006 is clear.

### Dependencies

None, but implementation should avoid touching status hang files owned by WP01.

### Risks

An override flag without durable metadata would become an invisible bypass. Tests must assert durable evidence exists after override.

---

## Phase 3 - Command Surface Cleanup

## Work Package WP03: Retired Checklist Command Cleanup (Priority: P0)

**Goal**: Remove retired `checklist` from active registries/counts while preserving intentional stale-file cleanup for package-managed installations.
**Independent Test**: Fresh command generation contains no active `spec-kitty.checklist*`, and package-managed stale checklist files are cleaned without touching unknown user files.
**Prompt**: `tasks/WP03-retired-checklist-command-cleanup.md`
**Requirement Refs**: FR-009, FR-010, FR-011, FR-014, NFR-001, SC-004, SC-005
**Estimated Prompt Size**: ~330 lines

### Included Subtasks

- [x] T012 Inventory active command registries, packaged templates, diagnostics, and counts for retired checklist drift (WP03)
- [x] T013 Remove retired checklist from active registry and generation surfaces (WP03)
- [x] T014 Preserve manifest-owned stale checklist cleanup without deleting user-owned files (WP03)
- [x] T015 [P] Align runtime doctor/count diagnostics and docs/comments with active command reality (WP03)
- [x] T016 [P] Add fresh command surface inventory tests for #968 (WP03)

### Implementation Notes

The charter forbids broad name-only deletion of user-owned command files. Cleanup must rely on manifest/package ownership or intentionally preserve unknown files.

### Parallel Opportunities

T015 and T016 can proceed once T012 identifies the inventory sources.

### Dependencies

None.

### Risks

The retired command may appear through multiple surfaces. The fresh generation test is the acceptance gate, not a single registry edit.

---

## Phase 4 - Generated Skill Metadata

## Work Package WP04: Generated Skill Frontmatter (Priority: P0)

**Goal**: Fix generated skill frontmatter for #964, including the Codex/global `spec-kitty.advise` repro, and verify fresh generated host-visible files.
**Independent Test**: Fresh generated `SKILL.md` files include required YAML frontmatter and no missing-frontmatter warnings are produced.
**Prompt**: `tasks/WP04-generated-skill-frontmatter.md`
**Requirement Refs**: FR-012, FR-013, FR-014, NFR-001, SC-006
**Estimated Prompt Size**: ~280 lines

### Included Subtasks

- [x] T017 Reproduce #964 with fresh Codex/global skill generation, including `spec-kitty.advise` (WP04)
- [x] T018 Ensure generated `SKILL.md` files include required YAML frontmatter (WP04)
- [x] T019 [P] Add generated-skill frontmatter tests across relevant host surfaces (WP04)
- [x] T020 [P] Update snapshots or verifier expectations only after generated output is fixed (WP04)

### Implementation Notes

Patch the generator path, not only checked-in generated files. Tests must inspect generated output in a temporary surface.

### Parallel Opportunities

T019 and T020 can proceed after T018 defines the generated output shape.

### Dependencies

None, but coordinate with WP03 if both touch installer/generation tests.

### Risks

Snapshot-only updates can pass while fresh generation remains broken. The WP must prove generated files, not just templates, are correct.

---

## Phase 5 - Release Evidence

## Work Package WP05: Fresh Surface Smoke And Release Evidence (Priority: P0)

**Goal**: Run combined focused validation and compile release-ready evidence for all four scoped issues.
**Independent Test**: The quickstart validation commands either pass or have documented pre-existing failures reported according to the charter.
**Prompt**: `tasks/WP05-fresh-surface-smoke-and-release-evidence.md`
**Requirement Refs**: FR-015, NFR-001, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, SC-007
**Estimated Prompt Size**: ~240 lines

### Included Subtasks

- [x] T021 Run focused validation for WP01 status hang evidence (WP05)
- [x] T022 Run focused validation for WP02 review consistency evidence (WP05)
- [x] T023 Run focused validation for WP03/WP04 command and skill surface evidence (WP05)
- [x] T024 Run ruff, mypy, and selected broader regression suites (WP05)
- [x] T025 Compile release evidence mapped to #967, #904, #968, and #964 (WP05)

### Implementation Notes

This WP should not introduce product fixes except small test-harness or evidence-documentation repairs directly needed to validate the first four WPs. If any command path touches hosted SaaS/auth/tracker/sync on this computer, set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

### Parallel Opportunities

Validation can be split by issue class after WP01-WP04 are complete.

### Dependencies

Dependencies: WP01, WP02, WP03, WP04.

### Risks

Pre-existing failures must be reported as GitHub issues before they are treated as accepted baseline context.
