# Work Packages: 3.2.0 Workflow Reliability Blockers

**Inputs**: Design documents from `/Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty/kitty-specs/release-320-workflow-reliability-01KQKV85/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required. This mission exists to close release blockers with deterministic regression coverage.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently reviewable and carries explicit owned-file boundaries.

**Prompt Files**: Each work package references a matching prompt file in `/Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty/kitty-specs/release-320-workflow-reliability-01KQKV85/tasks/`.

## Work Package WP01: Regression Harness and Workflow Fixtures (Priority: P0)

**Goal**: Create the shared deterministic fixture layer and smoke tests that all blocker fixes can reuse.
**Independent Test**: Reliability fixture smoke tests can create a temporary mission, status event log, work package files, and optional lane/workspace context without real network calls.
**Prompt**: `/tasks/WP01-regression-harness-and-workflow-fixtures.md`
**Requirement Refs**: NFR-001, NFR-002, NFR-003, NFR-004, C-001, C-002, C-003, C-006

### Included Subtasks
- [x] T001 Create shared reliability fixture helpers under `tests/reliability/fixtures/`.
- [x] T002 Add mission/work-package fixture builders for event logs, review artifacts, lane context, and merge state.
- [x] T003 [P] Add sync-failure fakes that do not perform real hosted network calls.
- [x] T004 [P] Add review prompt collision fixtures for two repos, two missions, and same-second invocations.
- [x] T005 Add a fixture smoke test proving the harness can support every linked blocker scenario.
- [x] T006 Document the fixture contracts and machine sync flag rule for implementers.

### Implementation Notes
- Keep this package limited to fixture and helper surfaces. Do not fix production behavior here.
- Fixture APIs should be small and explicit enough for later WPs to use without depending on hidden global state.
- Use `tmp_path` repositories and local files; avoid the dev SaaS deployment.

### Parallel Opportunities
- T003 and T004 can proceed in parallel after T001 defines shared helper layout.

### Dependencies
- None.

### Risks & Mitigations
- Risk: Fixture helpers become a second implementation of workflow logic. Mitigate by using existing public CLI helpers where possible and keeping fixtures focused on setup/verification.

---

## Work Package WP02: Status Transition Atomicity (Priority: P1)

**Goal**: Make successful status transitions provably durable and verify #944 claimed-state recovery.
**Independent Test**: Transition commands either append and read back the expected status event or fail non-zero with a precise diagnostic.
**Prompt**: `/tasks/WP02-status-transition-atomicity.md`
**Requirement Refs**: FR-001, FR-002, FR-003, NFR-001, NFR-003, NFR-005

### Included Subtasks
- [x] T007 Add focused regression tests for `move-task` approval event persistence and missing event readback failure.
- [x] T008 Add verification coverage for backgrounded, interrupted, or slow implement/review paths not stranding WPs in `claimed`.
- [x] T009 Implement post-write event readback invariants in status transition command paths.
- [x] T010 Ensure worktree/subagent transition paths resolve the canonical mission event log.
- [x] T011 Harden dirty/unowned-file handling so blocked event emission is reported as a hard transition failure.
- [x] T012 Run targeted status/task lifecycle tests and update diagnostics for reviewer clarity.

### Implementation Notes
- Prefer helpers in `src/specify_cli/status/` for readback and invariant checks.
- Keep command success tied to durable local event evidence, not frontmatter or derived snapshots alone.

### Parallel Opportunities
- T007 and T008 can be drafted in parallel because they exercise different failure modes.

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- Risk: Adding readback at the wrong layer duplicates transition semantics. Mitigate by centralizing readback in status helpers and calling it from command surfaces.

---

## Work Package WP03: Review Prompt Isolation and Canonical Diff Refs (Priority: P1)

**Goal**: Make generated review prompts collision-proof and prevent reviewer dispatch when prompt metadata points at the wrong work.
**Independent Test**: Concurrent review prompt fixtures generate unique prompts whose metadata matches repo, mission, WP, worktree, and canonical diff refs.
**Prompt**: `/tasks/WP03-review-prompt-isolation-and-canonical-diff-refs.md`
**Requirement Refs**: FR-004, FR-005, FR-006, FR-014, NFR-001, NFR-005, C-004, C-005

### Included Subtasks
- [x] T013 Add concurrent review prompt tests for two repos, two missions, and repeated invocations.
- [x] T014 Add a regression for mission slugs beginning with `mission-` and canonical review diff refs.
- [x] T015 Implement invocation-specific review prompt paths and structured prompt metadata.
- [x] T016 Add fail-closed validation before reviewer dispatch.
- [x] T017 Move review diff command construction to canonical mission/lane refs.
- [x] T018 Add latest-review-artifact verdict helper coverage for approved/done versus rejected contradictions.

### Implementation Notes
- Keep review prompt identity logic under review/workflow surfaces, not ad hoc shell string assembly.
- Expose a small helper for latest review artifact verdict so WP06 can consume it from merge/ship gates without owning review internals.

### Parallel Opportunities
- T013 and T014 are parallel-safe after WP01 fixture helpers exist.

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- Risk: Metadata validation blocks valid legacy prompts. Mitigate by applying fail-closed behavior only to newly generated prompt dispatch paths and documenting fallback errors.

---

## Work Package WP04: Active WP Ownership Guard (Priority: P1)

**Goal**: Ensure commit and workflow guards validate against the active WP's `owned_files`, not stale shared-lane context.
**Independent Test**: A shared-lane fixture moves from one WP to another with disjoint owned files and the guard switches ownership context correctly.
**Prompt**: `/tasks/WP04-active-wp-ownership-guard.md`
**Requirement Refs**: FR-007, FR-008, NFR-001, NFR-005, C-004

### Included Subtasks
- [x] T019 Add shared-lane sequential-WP tests with disjoint `owned_files`.
- [x] T020 Add guard-output tests distinguishing stale context from true scope violations.
- [x] T021 Resolve active WP id at guard invocation time from workspace/status context.
- [x] T022 Update commit guard ownership detection to read the active WP's frontmatter.
- [x] T023 Add diagnostics for stale or ambiguous active-WP context.
- [x] T024 Run targeted policy/workspace tests and document guard expectations.

### Implementation Notes
- Keep the guard conservative: if the active WP cannot be proven, report context ambiguity rather than pretending a stale ownership set is authoritative.
- Avoid widening ownership globs to silence failures.

### Parallel Opportunities
- T019 and T020 can be written in parallel.

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- Risk: Guard changes affect every commit path. Mitigate with narrow tests for existing happy paths plus the shared-lane regression.

---

## Work Package WP05: Sync Finalization Output Hygiene (Priority: P2)

**Goal**: Preserve successful local command surfaces when final SaaS/sync cleanup fails non-fatally.
**Independent Test**: Forced final-sync failures after local success keep stdout parseable and render a non-fatal diagnostic without red command-failure styling.
**Prompt**: `/tasks/WP05-sync-finalization-output-hygiene.md`
**Requirement Refs**: FR-009, FR-010, FR-011, NFR-002, NFR-004, C-002

### Included Subtasks
- [ ] T025 Add strict JSON stdout tests for final-sync warning paths.
- [ ] T026 Add duplicate sync-lock/interpreter-shutdown diagnostic tests.
- [ ] T027 Implement structured non-fatal sync diagnostics after local mutation success.
- [ ] T028 Route diagnostics to stderr or explicit JSON fields according to command contracts.
- [ ] T029 Deduplicate repeated sync diagnostics per invocation.
- [ ] T030 Run targeted sync tests with mocked external services and the machine sync flag where applicable.

### Implementation Notes
- The local mutation result remains authoritative once durable local state is written.
- Do not suppress sync diagnostics; make them explicit and machine-readable where command contracts allow.

### Parallel Opportunities
- T025 and T026 can proceed in parallel.

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- Risk: JSON command contracts differ by command. Mitigate by validating the exact command surfaces changed with a JSON parser.

---

## Work Package WP06: Merge/Ship Preflight and Review Artifact Consistency (Priority: P2)

**Goal**: Detect unsafe release state before merge/ship signoff, including diverged local `main` and stale rejected review artifacts.
**Independent Test**: Merge/ship preflight blocks a diverged target branch and prevents approved/done WPs with latest `verdict: rejected` from passing silently.
**Prompt**: `/tasks/WP06-merge-ship-preflight-and-review-artifact-consistency.md`
**Requirement Refs**: FR-012, FR-013, FR-014, NFR-001, NFR-005, C-004, C-005

### Included Subtasks
- [ ] T031 Add preflight tests for local `main` diverged from `origin/main`.
- [ ] T032 Add tests for approved/done WPs with latest rejected review-cycle frontmatter.
- [ ] T033 Implement merge/ship target-branch divergence detection.
- [ ] T034 Provide deterministic focused PR branch synthesis guidance from mission-owned changes.
- [ ] T035 Integrate review artifact consistency checks before mission-review or ship signoff.
- [ ] T036 Run merge/post-merge/integration tests and verify final smoke expectations.

### Implementation Notes
- Use the actual branch values from canonical state; for this mission the helper resolved current `main`, planning/base `main`, and merge target `main`.
- Consume review artifact helpers from WP03 rather than reimplementing review-cycle parsing in merge code.

### Parallel Opportunities
- T031 and T032 can be developed in parallel after WP01 fixtures exist.

### Dependencies
- Dependencies: WP01, WP02, WP03.

### Risks & Mitigations
- Risk: Branch preflight blocks legitimate local release work. Mitigate by producing deterministic remediation instead of a generic failure.

---

## Dependency & Execution Summary

- **Sequence**: WP01 first, then WP02-WP05 can proceed in parallel; WP06 depends on WP01 plus status/review helper work from WP02 and WP03.
- **Parallelization**: WP02, WP03, WP04, and WP05 own distinct code surfaces and can run concurrently after WP01.
- **MVP Scope**: WP01 + WP02 + WP03 prove the highest-risk implement/review trust path; WP04-WP06 complete stable-release readiness.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02 |
| FR-002 | WP02 |
| FR-003 | WP02 |
| FR-004 | WP03 |
| FR-005 | WP03 |
| FR-006 | WP03 |
| FR-007 | WP04 |
| FR-008 | WP04 |
| FR-009 | WP05 |
| FR-010 | WP05 |
| FR-011 | WP05 |
| FR-012 | WP06 |
| FR-013 | WP06 |
| FR-014 | WP03, WP06 |
| NFR-001 | WP01, WP02, WP03, WP04, WP06 |
| NFR-002 | WP01, WP05 |
| NFR-003 | WP01, WP02 |
| NFR-004 | WP01, WP05 |
| NFR-005 | WP02, WP03, WP04, WP06 |
| NFR-006 | WP02, WP03, WP04, WP05, WP06 |
| C-001 | WP01 |
| C-002 | WP01, WP05 |
| C-003 | WP01 |
| C-004 | WP03, WP04, WP06 |
| C-005 | WP03, WP06 |
| C-006 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create shared reliability fixture helpers | WP01 | P0 | No | [D] |
| T002 | Add mission/work-package fixture builders | WP01 | P0 | No | [D] |
| T003 | Add sync-failure fakes | WP01 | P0 | Yes | [D] |
| T004 | Add review prompt collision fixtures | WP01 | P0 | Yes | [D] |
| T005 | Add fixture smoke test | WP01 | P0 | No | [D] |
| T006 | Document fixture contracts and sync flag rule | WP01 | P0 | No | [D] |
| T007 | Add move-task event persistence tests | WP02 | P1 | No | [D] |
| T008 | Add #944 claimed recovery coverage | WP02 | P1 | Yes | [D] |
| T009 | Implement transition event readback invariants | WP02 | P1 | No | [D] |
| T010 | Resolve canonical event log from worktrees | WP02 | P1 | No | [D] |
| T011 | Harden dirty/unowned-file transition diagnostics | WP02 | P1 | No | [D] |
| T012 | Run status/task lifecycle tests | WP02 | P1 | No | [D] |
| T013 | Add concurrent prompt tests | WP03 | P1 | Yes | [D] |
| T014 | Add mission-prefixed slug diff test | WP03 | P1 | Yes | [D] |
| T015 | Implement invocation-specific prompt metadata | WP03 | P1 | No | [D] |
| T016 | Add fail-closed prompt validation | WP03 | P1 | No | [D] |
| T017 | Use canonical refs for review diffs | WP03 | P1 | No | [D] |
| T018 | Add latest review artifact helper coverage | WP03 | P1 | No | [D] |
| T019 | Add shared-lane ownership tests | WP04 | P1 | Yes | [D] |
| T020 | Add stale-context diagnostic tests | WP04 | P1 | Yes | [D] |
| T021 | Resolve active WP id at guard time | WP04 | P1 | No | [D] |
| T022 | Update commit guard ownership detection | WP04 | P1 | No | [D] |
| T023 | Add stale/ambiguous context diagnostics | WP04 | P1 | No | [D] |
| T024 | Run policy/workspace tests | WP04 | P1 | No | [D] |
| T025 | Add strict JSON sync warning tests | WP05 | P2 | Yes |
| T026 | Add sync diagnostic dedupe tests | WP05 | P2 | Yes |
| T027 | Implement non-fatal sync diagnostics | WP05 | P2 | No |
| T028 | Route diagnostics correctly | WP05 | P2 | No |
| T029 | Deduplicate sync diagnostics | WP05 | P2 | No |
| T030 | Run targeted sync tests | WP05 | P2 | No |
| T031 | Add diverged target branch tests | WP06 | P2 | Yes |
| T032 | Add rejected review artifact consistency tests | WP06 | P2 | Yes |
| T033 | Implement merge/ship branch divergence detection | WP06 | P2 | No |
| T034 | Add focused PR branch remediation guidance | WP06 | P2 | No |
| T035 | Integrate review artifact consistency checks | WP06 | P2 | No |
| T036 | Run merge/post-merge integration tests | WP06 | P2 | No |
