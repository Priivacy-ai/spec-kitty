# Work Packages: Responsive Pre-Review Gate Operator Flow

**Inputs**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`
**Planning / merge branch**: `fix/pre-review-gate-operator-flow`
**Issue / release**: #2573 on the path to 3.2.6; release-ready closeout remains downstream of #3127.

**Organization**: Five independently reviewable work packages. File ownership does not overlap. WP03 and WP04 form the parallel verification wave after the engine foundation.

---

## WP01: Deterministic Scope-Budget Policy (Priority: P0, Foundation)

**Goal**: Add the immutable, source-controlled authority that classifies normalized candidate-head target sets as `bounded`, `oversized`, or `unknown`.
**Independent Test**: Pure policy tests prove exact-atom matching for `tests/architectural`, stable order-independent identity, descendant fallback to `unknown`, and no mutation/learning API.
**Prompt**: `tasks/WP01-deterministic-scope-budget-policy.md`
**Requirement refs**: FR-008, FR-009, FR-010, NFR-007, C-004, C-007
**Depends on**: None

### Included Subtasks
- [x] T025 Verify/assign tracker issue #2573 to the Human-in-Charge before implementation starts.
- [x] T001 Write red-first normalization and classification contracts.
- [x] T002 Implement immutable policy and assessment types.
- [x] T003 Add the exact `tests/architectural` oversized rule and stable identity.
- [x] T004 Prove unknown/declared-command compatibility and absence of runtime mutation.

---

## WP02: Engine Verdict and Pre-Launch Refusal (Priority: P0)

**Goal**: Apply the policy before candidate-head launch, add typed status/verdict evidence, and make oversized refusal terminal without disturbing existing timeout, cancellation, or aggregation behavior.
**Independent Test**: Engine and integration tests prove `SCOPE_OVERSIZED`/`NOT_STARTED` returns before the launch seam, while unknown scopes run and unknown timeouts carry candidate diagnostics.
**Prompt**: `tasks/WP02-engine-verdict-and-prelaunch-refusal.md`
**Requirement refs**: FR-002, FR-006, FR-007, FR-008, FR-009, FR-010, NFR-003, NFR-007, C-004, C-007
**Depends on**: WP01

### Included Subtasks
- [x] T005 Write red-first engine/verdict contracts.
- [x] T006 Extend typed outcomes, head-run states, status events, and verdict evidence.
- [x] T007 Assess derived and explicit-override scopes before launch.
- [x] T008 Add unknown-timeout diagnostic evidence using the monotonic observer clock.
- [x] T009 Update aggregation and run focused engine/integration regression gates.

---

## WP03: Public Operator Output and Observer Wiring (Priority: P0)

**Goal**: Deliver scope assessment and continuing heartbeat events through both public review-submission paths, render them only in human mode, and preserve one final JSON document and existing precedence.
**Independent Test**: Exact Typer-entry tests observe assessment before launch, start within one second, two heartbeats in a controlled 60-second run, terminal refusal/candidate guidance, and singular structured output.
**Prompt**: `tasks/WP03-public-operator-output-and-observer-wiring.md`
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-007, FR-008, FR-009, FR-010, NFR-001, NFR-002, NFR-003, NFR-004, NFR-006, NFR-007, C-002, C-003, C-004, C-005, C-006
**Depends on**: WP02

### Included Subtasks
- [x] T010 Replace the public liveness gap with red-first exact-entry tests.
- [x] T011 Carry the typed observer through the registered handler context.
- [x] T012 Wire the same observer through registry and explicit-override paths.
- [x] T013 Render human assessment, heartbeats, refusal, and candidate guidance.
- [x] T014 Extend final metadata while keeping top-level transition authority and one JSON document.
- [x] T015 Re-prove skip/disable ordering, daemon exception, and warn/block compatibility.

---

## WP04: Interruption and Cross-Platform Integrity Evidence (Priority: P1)

**Goal**: Supply the real-process and deterministic platform evidence required for timeout, cancellation, Windows tree termination, and abrupt parent death without promising orphan cleanup after `SIGKILL`.
**Independent Test**: Dedicated tests prove POSIX owned-tree cleanup for catchable exits, Windows `taskkill /T` contract behavior, and unchanged lane/event state after a real CLI parent is killed while candidate validation is running.
**Prompt**: `tasks/WP04-interruption-and-cross-platform-integrity.md`
**Requirement refs**: FR-002, FR-006, FR-007, NFR-003, NFR-005, C-004
**Depends on**: WP02

### Included Subtasks
- [x] T016 Add focused real-process interruption fixtures.
- [x] T017 Prove POSIX timeout and catchable-cancellation cleanup.
- [x] T018 Pin the Windows tree-termination command contract.
- [x] T019 Prove abrupt-parent-death lane/event integrity and document the cleanup boundary.

---

## WP05: Traceability, Retrospective Handoff, and Release Gate (Priority: P1)

**Goal**: Produce complete scenario-to-test evidence, audit durable operational candidates, hand them to the canonical post-merge retrospective, and define the executable #3127/rebase/checks release gate for #2573.
**Independent Test**: The traceability matrix has no blank evidence cells for FR-001–FR-010; the handoff inventories every operational candidate or explicit absence; release evidence cannot claim readiness before the upstream gate is satisfied.
**Prompt**: `tasks/WP05-traceability-feedback-and-release-closeout.md`
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, NFR-003, NFR-005, NFR-006, NFR-007, C-001, C-002, C-003, C-004, C-005, C-006, C-007
**Depends on**: WP03, WP04

### Included Subtasks
- [x] T020 Build the exact-node traceability matrix and verify every cell.
- [x] T021 Run targeted and relevant full regression gates and record trustworthy evidence.
- [x] T022 Audit immediate operational-candidate tracer entries and distinguish synthetic evidence.
- [x] T023 Produce the canonical post-merge retrospective handoff.
- [x] T024 Re-evaluate #2573 and record the executable #3127 release-gate resume point.

---

## Dependency and Parallelization Summary

```text
WP01 deterministic policy
  -> WP02 engine/verdict integration
       -> WP03 public output ---------\
       -> WP04 interruption evidence --+-> WP05 traceability and release closeout
```

- Wave 1: WP01
- Wave 2: WP02
- Wave 3 (parallel): WP03 and WP04
- Wave 4: WP05

No package may edit another package's `owned_files`. If verification in WP04 exposes a production defect in WP02-owned code, reject/escalate that evidence back to WP02 rather than expanding WP04's surface.

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: planned
- WP02: planned
- WP03: planned
- WP04: planned
- WP05: planned
<!-- status-model:end -->
