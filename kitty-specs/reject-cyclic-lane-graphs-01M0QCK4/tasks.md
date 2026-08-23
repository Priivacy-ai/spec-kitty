# Tasks: Reject Cyclic Lane Graphs

**Mission**: `reject-cyclic-lane-graphs-01M0QCK4`  
**Mission ID**: `01M0QCK4D9D65AVNC15HKWAQZ7`  
**Planning base / local merge target**: `fix/reject-cyclic-lane-graphs`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add red-first unit cases for deterministic lane-cycle detection | WP01 | |
| T002 | Define immutable structured cycle diagnostic types | WP01 | [P] |
| T003 | Implement deterministic directed-cycle selection and normalization | WP01 | |
| T004 | Enforce the cycle gate inside `compute_lanes` before depth calculation | WP01 | |
| T005 | Reconcile legacy cycle-safety coverage and run focused domain gates | WP01 | |
| T006 | Add red-first JSON and human diagnostic parity tests | WP02 | [P] |
| T007 | Add absent/existing `lanes.json` preservation tests | WP02 | [P] |
| T008 | Render typed cycle failures through the shared finalization boundary | WP02 | |
| T009 | Verify planning-lane participation and validate-only zero mutation | WP02 | |
| T010 | Run CLI/finalization regression and quality gates | WP02 | |
| T011 | Lock valid-DAG output compatibility in existing computation tests | WP03 | [P] |
| T012 | Add insertion-order and multiple-cycle determinism matrices | WP03 | [P] |
| T013 | Add cross-process hash-seed determinism proof | WP03 | |
| T014 | Add the fixed 100-lane/500-edge p95 benchmark | WP03 | [P] |
| T015 | Run broad lane regressions and verify the diagnostic contract | WP03 | |

## Work Package WP01: Authoritative Domain Cycle Gate

**Goal**: Make `compute_lanes` reject every cyclic final execution-lane graph with deterministic structured facts before it can calculate accepted depths or return a manifest.

**Priority**: P0 — foundational and MVP

**Independent test**: Directly call `compute_lanes` with an authored acyclic WP graph whose ownership collapse yields a lane cycle; assert `LaneDependencyCycleError`, a normalized closed path, sorted lane membership, and no returned manifest.

**Dependencies**: none

**Estimated prompt size**: ~300 lines

**Included subtasks**:

- [ ] T001 Add red-first unit cases for deterministic lane-cycle detection (WP01)
- [ ] T002 Define immutable structured cycle diagnostic types (WP01)
- [ ] T003 Implement deterministic directed-cycle selection and normalization (WP01)
- [ ] T004 Enforce the cycle gate inside `compute_lanes` before depth calculation (WP01)
- [ ] T005 Reconcile legacy cycle-safety coverage and run focused domain gates (WP01)

**Implementation sketch**:

1. Establish red tests for self-loops, multi-lane cycles, lexical selection, normalization, and clean DAGs.
2. Add a typed `LaneComputationError` subclass that owns normalized domain facts but no CLI serialization.
3. Implement a pure sorted DFS helper and prove it preserves directed adjacency while rotating the cycle.
4. Invoke it after the complete `lane_deps` map is built and before `_compute_lane_depths`.
5. Replace the contradictory public permissiveness assertion while retaining direct helper recursion safety.

**Parallel opportunities**: T002 can be drafted alongside T001, but T003–T005 are sequential. After WP01, WP02 and WP03 can run in parallel.

**Risks**: accidental dependence on mapping/set order; incorrect cycle reconstruction; changing clean-DAG manifests; deleting useful low-level stack-safety coverage.

**Prompt**: [tasks/WP01-authoritative-domain-cycle-gate.md](tasks/WP01-authoritative-domain-cycle-gate.md)

## Work Package WP02: Finalization Diagnostics and Persistence Safety

**Goal**: Surface the typed domain rejection identically from mutating and `--validate-only` mission finalization while proving rejected graphs cannot create or replace `lanes.json`.

**Priority**: P0 — completes User Story 1 and the external contract

**Independent test**: Invoke both canonical finalization modes with `--json` on the same cyclic fixture; assert identical cycle fields and nonzero exits, then compare the lane-manifest path before and after.

**Dependencies**: WP01

**Estimated prompt size**: ~310 lines

**Included subtasks**:

- [ ] T006 Add red-first JSON and human diagnostic parity tests (WP02)
- [ ] T007 Add absent/existing `lanes.json` preservation tests (WP02)
- [ ] T008 Render typed cycle failures through the shared finalization boundary (WP02)
- [ ] T009 Verify planning-lane participation and validate-only zero mutation (WP02)
- [ ] T010 Run CLI/finalization regression and quality gates (WP02)

**Implementation sketch**:

1. Build CLI-level fixtures that reach the real `compute_lanes` seam in both modes.
2. Pin the required error envelope and human diagnostic without parsing strings for structured facts.
3. Extend only the common terminal error renderer to recognize the typed exception.
4. Assert the compute-before-write ordering structurally preserves absence and byte identity, including a cycle involving `lane-planning`.
5. Run focused and adjacent finalization tests plus ruff/mypy.

**Parallel opportunities**: T006 and T007 can be authored independently. The entire WP can execute in parallel with WP03 after WP01.

**Risks**: duplicate JSON output; mode-specific catches; mutation during validate-only setup; broadening rollback beyond `lanes.json`; weakening generic error behavior.

**Prompt**: [tasks/WP02-finalization-diagnostics-and-persistence.md](tasks/WP02-finalization-diagnostics-and-persistence.md)

## Work Package WP03: Determinism, Performance, and Regression Proof

**Goal**: Prove the new detector is stable across equivalent input order and process hash seeds, stays inside the performance budget, and preserves valid execution-lane computation.

**Priority**: P1 — release-confidence package

**Independent test**: Run a fixed multi-cycle graph under permuted insertion orders and three `PYTHONHASHSEED` values, compare normalized diagnostics byte-for-byte, then benchmark 100 lanes/500 edges at p95 ≤100 ms.

**Dependencies**: WP01

**Estimated prompt size**: ~290 lines

**Included subtasks**:

- [ ] T011 Lock valid-DAG output compatibility in existing computation tests (WP03)
- [ ] T012 Add insertion-order and multiple-cycle determinism matrices (WP03)
- [ ] T013 Add cross-process hash-seed determinism proof (WP03)
- [ ] T014 Add the fixed 100-lane/500-edge p95 benchmark (WP03)
- [ ] T015 Run broad lane regressions and verify the diagnostic contract (WP03)

**Implementation sketch**:

1. Strengthen existing acyclic fixtures without copying WP01's detector-unit concerns.
2. Exercise equivalent mappings/dependency lists in varied construction orders and compare exception facts.
3. Use controlled subprocesses for hash-seed proof so the environment actually changes.
4. Benchmark the pure detector rather than CLI startup or filesystem work.
5. Validate the checked-in JSON schema against a representative payload and run the broader lane suite.

**Parallel opportunities**: T011, T012, and T014 touch separate files. WP03 can execute in parallel with WP02 after WP01.

**Risks**: flaky wall-clock assertions; subprocesses importing the installed rather than working-tree package; tests that compare timestamps instead of stable fields; duplicating WP01 ownership.

**Prompt**: [tasks/WP03-determinism-performance-and-regression.md](tasks/WP03-determinism-performance-and-regression.md)

## Dependency Graph

```text
WP01 Authoritative domain gate
  ├── WP02 Finalization diagnostics + persistence
  └── WP03 Determinism + performance + regression
```

WP02 and WP03 have no overlapping owned files and may execute concurrently after WP01 is approved.

## MVP Scope

WP01 is the smallest meaningful MVP because it closes the invalid-manifest construction door. Production completion requires WP02 as well so canonical CLI callers receive the governed diagnostic and persistence proof. WP03 supplies the deterministic/performance release evidence required by the specification.
