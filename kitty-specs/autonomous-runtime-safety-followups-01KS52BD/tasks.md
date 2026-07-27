# Work Packages: Autonomous Runtime Safety Follow-ups

**Inputs**: Design documents from `/kitty-specs/autonomous-runtime-safety-followups-01KS52BD/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md  
**Tests**: Focused affected packages per WP; no full-suite run required per WP.  
**Organization**: Six issue-aligned work packages. WP01-WP05 are code/runtime workstreams. WP06 is docs-only and should be implemented after runtime behavior is settled, but it intentionally has no metadata dependency so current lane collapse does not serialize the mission.

## Work Package WP01: Retrospect schema reconciliation (Priority: P1)

**Goal**: Make `agent retrospect synthesize` accept records written by `retrospect create`.  
**Independent Test**: A create-shaped `retrospective.yaml` passes synthesize dry-run and `--apply`.  
**Prompt**: `/tasks/WP01-retrospect-schema-reconciliation.md`  
**Requirement Refs**: FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, NFR-004, NFR-006, C-001, C-005, C-007, C-008

### Included Subtasks
- [ ] T001 Reproduce the pydantic `extra_forbidden` failure with a create-shaped retrospective record.
- [ ] T002 Align synthesize reader schema with create writer output.
- [ ] T003 Cover dry-run/default synthesize against the create-shaped record.
- [ ] T004 Cover `--apply` synthesize against the create-shaped record.
- [ ] T005 Run focused retrospective tests and mypy on touched modules.

### Implementation Notes
- Prefer a shared pydantic model if local impact is small; otherwise configure the synthesize reader to ignore informational extras.
- Preserve existing missing-record, malformed-YAML, and I/O error behavior.

### Parallel Opportunities
- Independent from WP02-WP06.

### Dependencies
- None.

### Risks & Mitigations
- Risk: schema widening hides invalid records. Mitigation: keep findings/proposal fields strict where they drive behavior.

---

## Work Package WP02: Decision deferred closure (Priority: P1)

**Goal**: Allow deferred decisions to close cleanly when plan defaults are accepted.  
**Independent Test**: Open -> defer -> resolve succeeds; marker removal no longer reports verifier drift.  
**Prompt**: `/tasks/WP02-decision-deferred-closure.md`  
**Requirement Refs**: FR-004, FR-005, FR-006, NFR-001, NFR-002, NFR-003, NFR-004, NFR-006, C-001, C-002, C-005, C-007, C-008

### Included Subtasks
- [ ] T006 Add regression coverage for `deferred -> resolved` conflict.
- [ ] T007 Update decision service/state handling for explicit closure.
- [ ] T008 Update verifier rules for closed deferred decisions without markers.
- [ ] T009 Update acceptance clarification handling for closed decisions.
- [ ] T010 Run focused decision/acceptance tests and mypy on touched modules.

### Implementation Notes
- Prefer allowing `deferred -> resolved`; add `close-with-default` only if the state model makes direct resolution unsafe.
- Do not change `open`, `defer`, or `cancel` public contracts.

### Parallel Opportunities
- Independent from WP01, WP03, WP04, WP05, and WP06.

### Dependencies
- None.

### Risks & Mitigations
- Risk: unresolved deferred decisions become invisible. Mitigation: require explicit final answer or explicit default-closure action.

---

## Work Package WP03: owned_files validator for `kitty-specs/` paths (Priority: P1)

**Goal**: Make `finalize-tasks` reject `kitty-specs/` entries in WP `owned_files` before lane work starts.  
**Independent Test**: Validate-only and full finalization fail with a structured WP/path error.  
**Prompt**: `/tasks/WP03-owned-files-validator.md`  
**Requirement Refs**: FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, C-001, C-003, C-005, C-007, C-008

### Included Subtasks
- [ ] T011 Add finalize-tasks fixture with `kitty-specs/` in `owned_files`.
- [ ] T012 Implement shared validation for validate-only and mutating finalization.
- [ ] T013 Return structured JSON details naming offending WP and path.
- [ ] T014 Add architectural regression coverage for WP frontmatter ownership.
- [ ] T015 Run focused finalize/architectural tests and mypy on touched modules.

### Implementation Notes
- Preferred stable error code: `OWNED_FILES_KITTY_SPECS_PATH`.
- Do not implement mission-branch auto-routing unless existing architecture makes it straightforward and testable.

### Parallel Opportunities
- Independent from WP01, WP02, WP04, WP05, and WP06.

### Dependencies
- None.

### Risks & Mitigations
- Risk: planning-artifact missions need a different route. Mitigation: WP04 handles planning-artifact pre-flight classification separately; this WP only fixes the contract split.

---

## Work Package WP04: Bulk-edit planning pre-flight refinement (Priority: P2)

**Goal**: Treat WPs authoring `occurrence_map.yaml` as bulk-edit planning instead of blocking false positives.  
**Independent Test**: A claimed occurrence-map WP passes without `--acknowledge-not-bulk-edit`; active rewrite WPs still block.  
**Prompt**: `/tasks/WP04-bulk-edit-planning-preflight.md`  
**Requirement Refs**: FR-010, FR-011, NFR-001, NFR-002, NFR-003, NFR-004, NFR-006, C-001, C-003, C-004, C-005, C-007, C-008

### Included Subtasks
- [ ] T016 Add regression test for inferred bulk-edit text plus occurrence-map-owned WP.
- [ ] T017 Add WP frontmatter inspection to implementation pre-flight.
- [ ] T018 Downgrade planning-artifact inference to informational for that WP.
- [ ] T019 Preserve blocking behavior for active rewrite WPs and invalid `bulk_edit` state.
- [ ] T020 Run focused implement/bulk-edit tests and mypy on touched modules.

### Implementation Notes
- Do not change the bulk-edit skill.
- Keep `--acknowledge-not-bulk-edit` behavior for true non-bulk-edit cases.

### Parallel Opportunities
- Independent from WP01, WP02, WP03, WP05, and WP06.

### Dependencies
- None.

### Risks & Mitigations
- Risk: safety gate weakens for active rewrites. Mitigation: include negative tests for rewrite WPs.

---

## Work Package WP05: Lane-collapse disjoint-ownership refinement (Priority: P2)

**Goal**: Preserve parallel lanes for disjoint upstream workstreams that only meet at a fan-in WP.  
**Independent Test**: Six disjoint workstreams plus one fan-in WP produce parallel lanes rather than one collapsed lane.  
**Prompt**: `/tasks/WP05-lane-collapse-disjoint-ownership.md`  
**Requirement Refs**: FR-012, FR-013, NFR-001, NFR-002, NFR-003, NFR-004, NFR-006, C-001, C-005, C-007, C-008

### Included Subtasks
- [ ] T021 Add fan-in lane fixture with disjoint `owned_files`.
- [ ] T022 Refine lane collapse to consider ownership overlap and lane dependency ordering.
- [ ] T023 Preserve collapse for overlapping owned-file dependencies.
- [ ] T024 Improve `collapse_report` evidence for dependency/overlap decisions.
- [ ] T025 Run focused lane/finalize tests and mypy on touched modules.

### Implementation Notes
- The fan-in WP is the synchronization point; upstream workstreams should not collapse solely due to transitive relationships.
- Keep existing merge consumer compatibility with `lanes.json`.

### Parallel Opportunities
- Independent from WP01, WP02, WP03, WP04, and WP06.

### Dependencies
- None.

### Risks & Mitigations
- Risk: new parallelism creates conflicts. Mitigation: keep overlap collapse conservative and assert lane dependencies.

---

## Work Package WP06: Focused-PR workflow documentation (Priority: P3)

**Goal**: Document the focused-PR fallback for autonomous local runs that hit `TARGET_BRANCH_NOT_SYNCHRONIZED`.  
**Independent Test**: Docs include trigger, focused branch commands, direct mission-branch PR path, and squash-merge guidance.  
**Prompt**: `/tasks/WP06-focused-pr-workflow-docs.md`  
**Requirement Refs**: FR-014, FR-015, NFR-001, NFR-004, C-001, C-005, C-007, C-008

### Included Subtasks
- [ ] T026 Locate or create the standing mission workflow documentation target.
- [ ] T027 Update official autonomous-run docs with focused-PR fallback.
- [ ] T028 Cite `TARGET_BRANCH_NOT_SYNCHRONIZED` and runtime remediation commands.
- [ ] T029 Add direct mission-branch PR and squash-merge guidance from PR #1251.
- [ ] T030 Run applicable docs/toc tests or document why none apply.

### Implementation Notes
- Implement after WP01-WP05 so docs reflect final behavior, even though metadata has no dependency to avoid current lane-collapse serialization.
- If `spec-kitty-mission-workflow.md` is absent, create the closest standing workflow doc approved by existing docs structure.

### Parallel Opportunities
- Can draft in parallel, but final wording should be checked after runtime WPs land.

### Dependencies
- None in metadata; operationally run after runtime WPs.

### Risks & Mitigations
- Risk: docs target ambiguity. Mitigation: update existing how-to pages and create `docs/how-to/run-an-autonomous-mission.md` if no exact page exists.

---

## Dependency & Execution Summary

- **Recommended sequence**: WP01 -> WP02 -> WP03/WP04 -> WP05 -> WP06.
- **Metadata dependencies**: none, to avoid current fan-in collapse behavior.
- **Parallelization**: WP01-WP05 can run as separate workstreams because their `owned_files` are disjoint.
- **MVP Scope**: WP01 alone unblocks retrospective synthesis; WP01 + WP02 unblock terminus learning and decision closure.

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP02 |
| FR-005 | WP02 |
| FR-006 | WP02 |
| FR-007 | WP03 |
| FR-008 | WP03 |
| FR-009 | WP03 |
| FR-010 | WP04 |
| FR-011 | WP04 |
| FR-012 | WP05 |
| FR-013 | WP05 |
| FR-014 | WP06 |
| FR-015 | WP06 |

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Reproduce retrospective schema mismatch | WP01 | P1 | Yes |
| T002 | Align retrospective reader schema | WP01 | P1 | No |
| T003 | Dry-run synthesize regression | WP01 | P1 | Yes |
| T004 | Apply synthesize regression | WP01 | P1 | Yes |
| T005 | Retrospective focused verification | WP01 | P1 | No |
| T006 | Decision transition regression | WP02 | P1 | Yes |
| T007 | Decision closure implementation | WP02 | P1 | No |
| T008 | Verifier closure awareness | WP02 | P1 | No |
| T009 | Acceptance closure awareness | WP02 | P1 | No |
| T010 | Decision focused verification | WP02 | P1 | No |
| T011 | Invalid owned-files fixture | WP03 | P1 | Yes |
| T012 | Finalize ownership validation | WP03 | P1 | No |
| T013 | Structured ownership error | WP03 | P1 | No |
| T014 | Architectural ownership test | WP03 | P1 | Yes |
| T015 | Ownership focused verification | WP03 | P1 | No |
| T016 | Bulk-edit planning regression | WP04 | P2 | Yes |
| T017 | WP frontmatter pre-flight inspection | WP04 | P2 | No |
| T018 | Informational planning warning | WP04 | P2 | No |
| T019 | Active rewrite gate preservation | WP04 | P2 | No |
| T020 | Bulk-edit focused verification | WP04 | P2 | No |
| T021 | Fan-in lane fixture | WP05 | P2 | Yes |
| T022 | Ownership-aware lane collapse | WP05 | P2 | No |
| T023 | Overlap collapse regression | WP05 | P2 | Yes |
| T024 | Collapse report evidence | WP05 | P2 | No |
| T025 | Lane focused verification | WP05 | P2 | No |
| T026 | Docs target discovery | WP06 | P3 | Yes |
| T027 | Official autonomous docs update | WP06 | P3 | No |
| T028 | Runtime error remediation citation | WP06 | P3 | No |
| T029 | Direct PR and squash guidance | WP06 | P3 | No |
| T030 | Docs verification | WP06 | P3 | No |
