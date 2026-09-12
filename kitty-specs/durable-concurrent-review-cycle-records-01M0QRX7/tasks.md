---
description: Work packages for durable concurrent review-cycle records
updated: 2026-08-23
---

# Work Packages: Durable Concurrent Review-Cycle Records

**Inputs**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/verdict-save-queue.md`, and `quickstart.md`

**Organization**: Thirty-two fine-grained subtasks roll up into seven independently reviewable work packages. Subtask completion is event-sourced; use `spec-kitty agent tasks mark-status`, not Markdown checkbox edits.

## Work Package WP01: Production-Path Durability Oracle (Priority: P0) 🎯 MVP Proof

**Goal**: Replace the false-green concurrency reproduction with a portable, production-command acceptance oracle that independently proves event and committed-evidence durability.
**Independent Test**: The issue-pinned test runs at least 50 synchronized rounds with two persistent spawned processes and accepts only two durable successes or one durable success plus a causally proven 10-second queue timeout or independently valid state refusal. A deterministic concurrent round proves the second writer waits and succeeds when the first releases within 10 seconds; each protection mutant turns the test red through the intended production seam.
**Prompt**: `tasks/WP01-production-path-durability-oracle.md`
**Requirement Refs**: FR-003, FR-006, FR-008, NFR-001, NFR-002, NFR-005, C-003, C-004
**Estimated Prompt Size**: ~330 lines

### Included Subtasks

T001 Replace the helper/manual-event worker with persistent `spawn` workers invoking the real reviewer command (WP01)
T002 Build a two-authority oracle over event history and `git show` at the governed destination ref (WP01)
T003 Enforce the allowed per-round outcomes; deterministic busy non-vacuity is deferred to post-integration command tests (WP01)
T004 Add a causally isolated event-serialization mutation control without adding a test-only lock (WP01)
T005 Add an independent mutation control that fabricates evidence-commit success without changing Git (WP01)

### Implementation Notes

- Preserve the honest red signal until production packages close it.
- Do not trust the command's durability flag as the oracle.
- Use top-level pickleable workers and no POSIX-only `fork`, signals, or paths.

### Parallel Opportunities

- Can proceed in parallel with WP02 because ownership is disjoint.

### Dependencies

- None.

### Risks & Mitigations

- Natural scheduling may never exercise refusal; WP04 must force a deterministic queue-timeout case after the queue is integrated.
- Same-WP state transitions may reject the second writer legitimately; treat an explicit nonzero refusal as valid, never a warning-success.

---

## Work Package WP02: Checkout-Wide Verdict Queue (Priority: P0)

**Goal**: Provide the small cross-process queue primitive that serializes automatic verdict evidence commits across a Git common directory.
**Independent Test**: Queue tests prove common-dir keying, exact 10-second default, typed timeout, exception/process-death release, cross-platform behavior, and the absence of daemon lifecycle.
**Prompt**: `tasks/WP02-checkout-wide-verdict-queue.md`
**Requirement Refs**: FR-002, FR-007, NFR-004, C-002, C-006
**Estimated Prompt Size**: ~300 lines

### Included Subtasks

T006 Implement the mission-independent queue key from canonical Git common-directory resolution (WP02)
T007 Implement bounded acquisition with the exact 10-second default and typed busy failure (WP02)
T008 Define context-manager cleanup, exception safety, process-death recovery, and explicit reentrancy behavior (WP02)
T009 Test same-checkout, linked-worktree, cross-mission, and independent-clone keying (WP02)
T010 Add lock-order and no-daemon structural guards without changing generic status locking (WP02)

### Implementation Notes

- Reuse `filelock`; add no dependency.
- The queue may span evidence Git, but the review-cycle allocation/status lock used by the new evidence path must not span that Git invocation. Existing authoritative status-transaction locking remains out of scope.
- WP04 command orchestration is the sole verdict-queue acquisition owner. WP03 exposes a non-acquiring evidence operation invoked inside that lease and must never reacquire it.
- Keep the primitive in the review bounded context.

### Parallel Opportunities

- Can proceed in parallel with WP01.

### Dependencies

- None.

### Risks & Mitigations

- A mission-scoped filename would miss cross-mission collisions; tests must compare resolved paths.
- Silent reentrant acquisition can deadlock; choose and pin one behavior explicitly.

---

## Work Package WP03: Retained Evidence and Identical Adoption (Priority: P1)

**Goal**: Make review-cycle persistence return typed truth, retain failed artifacts, adopt identical retries, and verify committed content at the governed destination.
**Independent Test**: Returned failures, raised failures, interruption, staged states, unverified `unchanged`, and already-committed retry cases all produce the specified retained/adopted outcome without duplicate cycles.
**Prompt**: `tasks/WP03-retained-evidence-and-adoption.md`
**Requirement Refs**: FR-001, FR-003, FR-005, FR-006, NFR-002, C-001, C-006
**Estimated Prompt Size**: ~390 lines

### Included Subtasks

T011 Introduce the typed verdict-persistence outcome and eliminate warning-only Boolean ambiguity (WP03)
T012 Retain byte-identical evidence on returned errors, wrong-surface results, exceptions, and interruptions (WP03)
T013 Discover and adopt an identical pending record using canonical evidence content without adding verdict authority (WP03)
T014 Verify committed or already-committed adopted evidence from the placement-selected destination ref (WP03)
T015 Preserve unrelated clean, staged, and partially staged state throughout failure and retry (WP03)
T016 Invert and extend cycle tests for the complete commit-result and recovery truth table (WP03)

### Implementation Notes

- Match mission, WP, reviewer, rendered body, and affected files; ignore allocation timestamp/cycle only.
- A non-identical submission never adopts or overwrites a retained record.
- Do not add a persisted verdict or fingerprint that becomes a second authority.

### Parallel Opportunities

- Internal test cases can be developed alongside implementation after WP02 is available.

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- `unchanged` is not inherently durable; verify exact governed-ref content.
- A retained file may already be staged; use existing safe-commit isolation and assert unrelated staging remains untouched.

---

## Work Package WP04: Truthful Verdict Command Orchestration (Priority: P1)

**Goal**: Integrate the queue and persistence outcome into the real reviewer command so automatic saves succeed only after evidence and event durability, while local-only mode remains explicit.
**Independent Test**: Real command tests distinguish durable success, busy refusal, persistence failure, event failure, and `no_auto_commit`, with coherent exit codes and JSON/human output.
**Prompt**: `tasks/WP04-truthful-verdict-command.md`
**Requirement Refs**: FR-001, FR-002, FR-004, FR-005, FR-006, NFR-002, C-001, C-002
**Estimated Prompt Size**: ~400 lines

### Included Subtasks

T017 Acquire the verdict queue only for automatic evidence persistence and release it before event emission (WP04)
T018 Propagate typed evidence outcomes through `move-task` instead of inferring durability from configuration (WP04)
T019 Gate authoritative event emission on verified evidence and keep compensation under the same verdict queue when it invokes Git (WP04)
T020 Preserve `--no-auto-commit` as queue-free, successful local-only behavior with false durability (WP04)
T021 Add command tests for returned/raised commit failures, timeout, event failure, retained retry, and idempotence (WP04)
T022 Align JSON, human output, exit codes, evidence reference, destination ref, and stable failure reasons (WP04)

### Implementation Notes

- Global order: queue → short allocation status lock → release status lock → Git → release queue → status event lock.
- No path may acquire the verdict queue while holding the status lock.
- A non-durable automatic outcome must never be wrapped in `result: success`.

### Parallel Opportunities

- Output-contract tests and orchestration wiring can be developed in parallel within one lane after WP03 lands.

### Dependencies

- Depends on WP02 and WP03.

### Risks & Mitigations

- Existing compensation can perform another Git operation; route it through the same queue to avoid recreating contention.
- Event failure reports command failure and attempts serialized evidence compensation; successful compensation removes the evidence, while only a loud compensation failure may leave explicit non-current history.

---

## Work Package WP05: Governed Topology Contract (Priority: P2)

**Goal**: Prove the completed production-command contract across every governed placement topology and automatic-commit mode.
**Independent Test**: A separate matrix verifies the event and evidence destinations for all four topologies, both commit modes, and event-failure compensation semantics.
**Prompt**: `tasks/WP05-governed-topology-contract.md`
**Requirement Refs**: FR-004, FR-007, FR-008, NFR-002, C-001, C-004, C-006
**Estimated Prompt Size**: ~220 lines

### Included Subtasks

T023 Create a real-command topology matrix for single-branch, lanes, coordination, and lanes-with-coordination (WP05)
T024 Cross every topology with automatic and local-only modes and verify the actual placement-selected refs (WP05)
T025 Verify approval/rejection scenarios and serialized compensation behavior after event failure (WP05)

### Implementation Notes

- Do not infer destination from topology flags; query placement and use `git show`.
- A failed event first attempts serialized compensation; non-current evidence is allowed only after a loud compensation failure or explicit future policy change.

### Parallel Opportunities

- Matrix cases may be parameterized and developed together within the lane.

### Dependencies

- Depends on WP01 and WP04.

### Risks & Mitigations

- Mocked topology can create false confidence; build real Git topology and inspect actual refs.
- Compensation policy can drift; assert the exact serialized attempt and loud-failure branch.

---

## Work Package WP06: Uncontended Verdict Performance (Priority: P2)

**Goal**: Measure the complete uncontended verdict operation statistically and prove the under-two-second requirement without timing fixture setup.
**Independent Test**: The repository performance harness benchmarks a real reviewer command including queue, evidence commit/read-back, and event persistence.
**Prompt**: `tasks/WP06-uncontended-verdict-performance.md`
**Requirement Refs**: FR-001, FR-004, NFR-003, NFR-006
**Estimated Prompt Size**: ~200 lines

### Included Subtasks

T026 Build a reusable real-command benchmark fixture with setup/reset outside the timed callable (WP06)
T027 Add a statistical end-to-end benchmark covering queue, evidence commit/read-back, and event persistence (WP06)
T028 Validate benchmark marker/workflow selection and record the reproducible baseline and environment (WP06)

### Implementation Notes

- Use `pytest-benchmark` and current performance policy.
- Do not benchmark the direct cycle writer or event-only path.

### Parallel Opportunities

- Can proceed in parallel with WP05 after WP04.

### Dependencies

- Depends on WP04.

### Risks & Mitigations

- Fixture and process startup can dominate; exclude them from the timed callable.
- One-shot timing is noisy; statistical median is the primary signal.

---

## Work Package WP07: Native CI and Quality Closeout (Priority: P2)

**Goal**: Execute the issue-pinned production proof natively on Linux, macOS, and Windows and close the targeted quality gates with reproducible evidence.
**Independent Test**: A narrow three-OS workflow invokes the exact baseline and both mutation nodes with `-n0`; successful completed Linux, macOS, and Windows jobs are linked, and the completed repository diff-coverage gate proves at least 90% changed-line coverage alongside focused pytest, Ruff, and strict mypy evidence.
**Prompt**: `tasks/WP07-native-ci-quality-closeout.md`
**Requirement Refs**: FR-008, NFR-001, NFR-004, NFR-005, NFR-006, C-003, C-004
**Estimated Prompt Size**: ~220 lines

### Included Subtasks

T029 Add and register a narrow native Ubuntu/macOS/Windows workflow using repository setup/cache, two-layer CI-quality routing, and fail-closed architecture-model conventions (WP07)
T030 Invoke the exact issue-pinned production node with persistent `spawn` workers and serial pytest execution (WP07)
T031 Run the complete targeted pytest, Ruff, strict mypy, and 90% changed-line coverage gates (WP07)
T032 Record exact results, pre-existing failures, platform evidence, and tooling friction in the WP Activity Log (WP07)

### Implementation Notes

- Native jobs must run the exact production node, not a queue-only smoke test.
- Implementation WPs cannot own `kitty-specs/`; the Activity Log carries evidence for later mission tracer curation.

### Parallel Opportunities

- Workflow authoring and its fail-closed architecture-model registration can begin after WP01; Definition of Done waits for successful completed native jobs and the enforced diff-coverage result after WP05 and WP06.

### Dependencies

- Depends on WP01, WP05, and WP06.

### Risks & Mitigations

- Windows startup cost is bounded with two persistent workers across the 50 rounds.
- External CI wait is explicit; local completion must still validate workflow syntax and exact node selection.

---

## Dependency & Execution Summary

- **Wave 1**: WP01 and WP02 in parallel.
- **Wave 2**: WP03 after WP02.
- **Wave 3**: WP04 after WP02 and WP03.
- **Wave 4**: WP05 and WP06 in parallel after their prerequisites.
- **Wave 5**: WP07 after WP01, WP05, and WP06.
- **MVP proof**: WP01 establishes the honest, non-fakeable acceptance signal; durable behavior requires WP01–WP04.

## Requirements Coverage Summary

| Requirement | Covered By |
|---|---|
| FR-001 | WP03, WP04 |
| FR-002 | WP02, WP04 |
| FR-003 | WP01, WP03 |
| FR-004 | WP04, WP05, WP06 |
| FR-005 | WP03, WP04 |
| FR-006 | WP01, WP03, WP04 |
| FR-007 | WP02, WP05 |
| FR-008 | WP01, WP05, WP07 |

## Subtask Index (Reference)

| ID | Summary | WP | Priority | Parallel? |
|---|---|---|---|---|
| T001 | Real production-command spawn workers | WP01 | P0 | No |
| T002 | Two-authority durability oracle | WP01 | P0 | No |
| T003 | Allowed concurrent outcome contract | WP01 | P0 | No |
| T004 | Serialization mutation control | WP01 | P0 | Yes |
| T005 | Evidence-commit mutation control | WP01 | P0 | Yes |
| T006 | Canonical checkout-wide queue key | WP02 | P0 | No |
| T007 | Ten-second typed timeout | WP02 | P0 | No |
| T008 | Cleanup and reentrancy contract | WP02 | P0 | No |
| T009 | Topology/keying unit tests | WP02 | P0 | Yes |
| T010 | Lock-order and no-daemon guards | WP02 | P0 | Yes |
| T011 | Typed persistence outcome | WP03 | P1 | No |
| T012 | Retain failed evidence | WP03 | P1 | No |
| T013 | Identical pending adoption | WP03 | P1 | No |
| T014 | Governed-ref read-back | WP03 | P1 | No |
| T015 | Preserve staging state | WP03 | P1 | Yes |
| T016 | Cycle recovery truth-table tests | WP03 | P1 | Yes |
| T017 | Automatic-only queue integration | WP04 | P1 | No |
| T018 | Typed outcome propagation | WP04 | P1 | No |
| T019 | Event gate and compensation | WP04 | P1 | No |
| T020 | Preserve local-only mode | WP04 | P1 | Yes |
| T021 | Command failure/retry tests | WP04 | P1 | Yes |
| T022 | Machine/human result alignment | WP04 | P1 | No |
| T023 | Real-command topology matrix | WP05 | P2 | No |
| T024 | Topology × commit-mode assertions | WP05 | P2 | No |
| T025 | Scenario and compensation semantics | WP05 | P2 | No |
| T026 | Real-command benchmark fixture | WP06 | P2 | No |
| T027 | Statistical end-to-end benchmark | WP06 | P2 | No |
| T028 | Benchmark selection and baseline | WP06 | P2 | No |
| T029 | Native three-OS workflow and architecture registration | WP07 | P2 | Yes |
| T030 | Exact production-node execution | WP07 | P2 | No |
| T031 | Targeted quality gates | WP07 | P2 | No |
| T032 | Reproducible evidence record | WP07 | P2 | No |
