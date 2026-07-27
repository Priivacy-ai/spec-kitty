# Tasks — Software-Dev Mission Composition Rewrite

**Mission**: `software-dev-composition-rewrite-01KQ26CY`
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)
**Branch contract**: planning base = merge target = `main` (branch_matches_target=true)
**Tracker**: [#503] · [#468] (parent) · [#461] (umbrella)

Three work packages, dependency-ordered. Each WP is contained, ≤7 subtasks, no overlap in `owned_files`. Execution mode: all code_change.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author `tasks.step-contract.yaml` (outline → packages → finalize sub-steps) | WP01 |  | [D] |
| T002 | Extend `_ACTION_PROFILE_DEFAULTS` with `("software-dev","tasks") → "architect-alphonso"` | WP01 |  | [D] |
| T003 | Write `test_software_dev_composition.py` covering all five action contracts | WP01 | [P] (with T001/T002 once written) | [D] |
| T004 | Confirm existing `test_executor.py` and shipped-contract loaders still pass | WP01 |  | [D] |
| T005 | Add composition dispatch helper in `runtime_bridge.py` for `(software-dev, {specify,plan,tasks,implement,review})` | WP02 |  | [D] |
| T006 | Implement collapsed `tasks` post-action guard (replaces `tasks_outline`/`tasks_packages`/`tasks_finalize` triple) | WP02 |  | [D] |
| T007 | Wire post-action guard semantics for the other four composed actions (parity with `_check_step_guards`) | WP02 |  | [D] |
| T008 | Write `test_runtime_bridge_composition.py` (positive dispatch, fall-through, missing-contract error, guard parity) | WP02 | [D] |
| T009 | Confirm existing `test_runtime_bridge.py` and `test_agent_commands_routing.py` still pass | WP02 |  | [D] |
| T010 | Prepend deprecation header comment to `mission-runtime.yaml` | WP03 | [D] |
| T011 | Create `actions/tasks/guidelines.md` mirroring the four sibling action guidelines | WP03 | [D] |
| T012 | Run focused tests + broader sweep; verify NFR-001 (no measurable wall-clock regression) | WP03 |  | [D] |
| T013 | Cross-check no `spec-kitty-events` package or `.kittify/charter/` files were touched (C-007 boundary check) | WP03 |  | [D] |

---

## WP01 — Tasks Step Contract + Executor Profile Extension

**Prompt file**: [tasks/WP01-tasks-step-contract-and-profile-default.md](tasks/WP01-tasks-step-contract-and-profile-default.md)

**Goal**: Make the `(software-dev, tasks)` action loadable through `MissionStepContractRepository` and route-able through `StepContractExecutor` with a sensible default profile. After this WP, the executor can compose all five `software-dev` actions in isolation; the runtime bridge does not yet know about it (that's WP02).

**Priority**: P1 (foundation; everything else depends on this).
**Independent test**: A unit test loads each of the five shipped contracts via the repository, executes them through `StepContractExecutor.execute` against a mocked `ProfileInvocationExecutor`, and asserts profile defaults + invocation_id chain shape.
**Estimated prompt size**: ~280 lines.
**Dependencies**: none (planning artifacts only).

### Included subtasks

- [x] T001 Author `src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml` per the contract in `contracts/tasks-step-contract-schema.md` (WP01)
- [x] T002 Extend `_ACTION_PROFILE_DEFAULTS` in `src/specify_cli/mission_step_contracts/executor.py` with the `tasks` entry (WP01)
- [x] T003 Write `tests/specify_cli/mission_step_contracts/test_software_dev_composition.py` covering all five `(software-dev, action)` contracts via the executor (WP01)
- [x] T004 Run `pytest tests/specify_cli/mission_step_contracts/test_executor.py` and confirm green (WP01)

### Implementation sketch

1. Drop the new YAML file in `src/doctrine/mission_step_contracts/shipped/`.
2. Add one entry to `_ACTION_PROFILE_DEFAULTS`.
3. Author the dedicated test file using the existing `test_executor.py` patterns as reference.
4. Run the focused tests.

### Risks

- New YAML doesn't validate against `MissionStepContract` model → caught immediately by the new test.
- A `delegates_to` candidate isn't in `actions/tasks/index.yaml`'s scope → unresolved candidate; logged but not fatal. Verify in the test.

---

## WP02 — Runtime Bridge Composition Dispatch + Collapsed Tasks Guard

**Prompt file**: [tasks/WP02-runtime-bridge-composition-dispatch.md](tasks/WP02-runtime-bridge-composition-dispatch.md)

**Goal**: Wire the runtime bridge so the live path for `software-dev`'s five public actions runs through `StepContractExecutor.execute`. Collapse the legacy `tasks_outline`/`tasks_packages`/`tasks_finalize` post-step guards into one composed `tasks` guard with equivalent semantics.

**Priority**: P1 (the actual rewrite of the live path).
**Independent test**: An integration test invokes the bridge for each of the five composed actions on a synthetic `software-dev` mission and asserts: composition path was taken (executor called), legacy DAG path was not, post-action guards still fire.
**Estimated prompt size**: ~360 lines.
**Dependencies**: WP01 (needs the `tasks` contract and `(software-dev, tasks)` profile default to exist before bridge dispatches to them).

### Included subtasks

- [x] T005 Add a composition dispatch branch in `src/specify_cli/next/runtime_bridge.py`, guarded on `mission == "software-dev"` and `action ∈ {specify, plan, tasks, implement, review}` (WP02)
- [x] T006 Implement the collapsed `tasks` post-action guard reusing `_has_raw_dependencies_field` (WP02)
- [x] T007 Wire the `specify`/`plan`/`implement`/`review` post-action guards into the composition path with parity to the legacy `_check_step_guards` (WP02)
- [x] T008 Write `tests/specify_cli/next/test_runtime_bridge_composition.py` covering positive dispatch, fall-through for non-software-dev missions, missing-contract → `StepContractExecutionError` → non-zero CLI surface, and guard parity for each action (WP02)
- [x] T009 Run `pytest tests/specify_cli/next/test_runtime_bridge.py tests/specify_cli/runtime/test_agent_commands_routing.py` and confirm green (WP02)

### Implementation sketch

1. Read `runtime_bridge.py` end-to-end; identify the precise insertion point (post `_check_step_guards`, before legacy DAG handler).
2. Add a small helper `_dispatch_via_composition(mission, action, ...) -> bool` that returns `True` if it handled the action.
3. Implement collapsed `tasks` guard by unioning the three legacy `tasks_*` checks.
4. Add the new test file.
5. Run focused tests.

### Risks

- Composition branch fires for non-software-dev missions → guard mission key strictly; assert with negative test.
- Collapsed guard silently weakens validation → enumerate the legacy assertions and verify each negative case still fails (test).
- `StepContractExecutionError` propagates as a Python traceback instead of structured CLI error → wrap callsite and translate.

---

## WP03 — Deprecation, Action Parity, Polish

**Prompt file**: [tasks/WP03-deprecation-parity-polish.md](tasks/WP03-deprecation-parity-polish.md)

**Goal**: Mark the legacy live-path templates deprecated; bring `actions/tasks/` to parity with the four sibling action directories; verify the slice landed cleanly with no regressions and no out-of-scope file touches.

**Priority**: P2 (polish + verification; doesn't change executable behavior on its own).
**Independent test**: `head -10 mission-runtime.yaml` shows the deprecation banner; `actions/tasks/guidelines.md` exists and structurally mirrors `actions/plan/guidelines.md`; full focused test suite green; `git diff --stat main` shows zero files outside the WP01/WP02/WP03 owned set.
**Estimated prompt size**: ~220 lines.
**Dependencies**: WP01 + WP02 (deprecation only meaningful once composition is the live path; the C-007 boundary check is most useful at the end).

### Included subtasks

- [x] T010 Prepend a deprecation header comment block to `src/doctrine/missions/software-dev/mission-runtime.yaml` (WP03)
- [x] T011 Create `src/doctrine/missions/software-dev/actions/tasks/guidelines.md` matching the structure/length of `actions/plan/guidelines.md` and `actions/implement/guidelines.md` (WP03)
- [x] T012 Run `pytest tests/specify_cli/mission_step_contracts/ tests/specify_cli/next/ tests/specify_cli/runtime/` and confirm all green (WP03)
- [x] T013 Verify C-007 boundary: `git diff --stat main` must not list any file under `src/spec_kitty_events/` or `.kittify/charter/` (WP03)

### Implementation sketch

1. Author the deprecation header (pure YAML comments).
2. Read sibling `guidelines.md` files for tone/structure; author the tasks variant.
3. Run the focused test sweep.
4. Audit `git diff --stat main`.

### Risks

- Sibling `guidelines.md` content drifts over time → keep the new file minimal and structurally parallel.
- Touching `mission.yaml` instead of `mission-runtime.yaml` by mistake → only `mission-runtime.yaml` gets the header per D-3.

---

## Dependency Graph

```
WP01 (tasks contract + profile default + executor tests)
   │
   ▼
WP02 (runtime bridge composition dispatch + tests)
   │
   ▼
WP03 (deprecation header + tasks/guidelines.md + final test sweep + boundary check)
```

Strict linear chain. Three execution lanes possible only if WP02 starts before WP01 completes (not recommended — WP02 imports the WP01 outputs implicitly via `MissionStepContractRepository`). Default execution: single-lane, sequential.

## MVP scope

WP01 alone proves the executor can compose all five `software-dev` actions but does not change the live path. WP01 + WP02 = real MVP — operators run the rewrite. WP03 is polish + verification.

## Parallelization

Inside each WP, sub-tasks are largely sequential. Across WPs, strict sequential per dependency graph. No parallel lanes.

## Out-of-scope reaffirmations

- `#505`, `#506`-`#511`, Phase 4/5, `spec-kitty explain`, events package, libraries-vs-charter alignment — not in any WP.
