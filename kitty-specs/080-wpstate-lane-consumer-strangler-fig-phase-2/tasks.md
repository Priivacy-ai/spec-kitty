# Work Packages: WPState/Lane Consumer Strangler Fig Migration — Phase 2

**Mission**: 080-wpstate-lane-consumer-strangler-fig-phase-2  
**Plan**: [plan.md](plan.md)  
**Spec**: [spec.md](spec.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Add `WPState.is_run_affecting` property to `src/specify_cli/status/wp_state.py` | WP01 | [P] | [D] | [D] | [D] |
| T002 | Write behavior tests for `is_run_affecting` (all 9 lanes) | WP01 | [D] |
| T003 | Verify `WPState.is_terminal` already exists in current tree | WP01 | [D] |
| T004 | Define `AgentAssignment` frozen dataclass in `src/specify_cli/status/models.py` | WP02 | [D] |
| T005 | Implement `WPMetadata.resolved_agent()` method with legacy coercion | WP02 | [D] |
| T006 | Write behavior tests for `resolved_agent()` (string, dict, None, fallback scenarios) | WP02 | [D] |
| T007 | Migrate `agent_utils/status.py` to use `state.progress_bucket()` | WP03 | [D] |
| T008 | Write regression tests for kanban display (agent_utils/status.py) | WP03 | [D] |
| T009 | Migrate `next/runtime_bridge.py` to use `state.is_run_affecting` | WP04 | [D] |
| T010 | Migrate `cli/commands/agent/workflow.py` to use `resolved_agent()` | WP04 | [D] |
| T011 | Write integration tests for workflow CLI (WP04) | WP04 | [D] |
| T012 | Migrate `review/arbiter.py` to use typed `Lane` enum via `WPState` | WP05 | [D] |
| T013 | Migrate `scripts/tasks/tasks_cli.py` to use event log lane access | WP05 | [D] |
| T014 | Write regression tests for arbiter & task scripts (WP05) | WP05 | [D] |
| T015 | Migrate `cli/commands/merge.py` (explicit approved\|done check, preserve distinction) | WP06 | [D] |
| T016 | Migrate `lanes/recovery.py` to use transition validation | WP06 | [D] |
| T017 | Write integration tests for merge command (WP06) | WP06 | [D] |
| T018 | Grep pass: verify no raw lane-string comparisons remain in 7 consumers | WP07 | [D] |
| T019 | Run mypy --strict on all migrated code | WP07 | [D] |
| T020 | Run full test suite; verify all pass after final integration | WP07 | [D] |

---

## Work Package 1: Introduce WPState.is_run_affecting Property

**Priority**: Foundation (P1 — blocks all consumers)  
**Status**: Pending  
**Goal**: Add typed `is_run_affecting` property to WPState, enabling consumer migrations

### Summary

Introduce `WPState.is_run_affecting` as a first-class property that encapsulates the "active WP" query (planned through approved, excluding done/blocked/canceled). This enables consumers to replace ad-hoc lane tuple checks with a single typed interface.

**Success Criteria**:
- [x] T001 Add `is_run_affecting` property to `src/specify_cli/status/wp_state.py`
- [x] T002 Write behavior tests for all 9 lanes
- [x] T003 Verify `is_terminal` already exists (no new work needed)

**Owned Files**: `src/specify_cli/status/wp_state.py`, `tests/specify_cli/status/test_wp_state.py`

**Execution Mode**: `code_change`

---

## Work Package 2: Introduce AgentAssignment & WPMetadata.resolved_agent()

**Priority**: Foundation (P1 — blocks Slice 2 workflow migration)  
**Status**: Pending  
**Goal**: Add `AgentAssignment` value object and `resolved_agent()` method to unify legacy agent coercion

### Summary

Define `AgentAssignment` as a frozen dataclass and implement `WPMetadata.resolved_agent()` to handle legacy string/dict/None inputs with fallback to model/agent_profile/role fields. This enables workflow.py to migrate away from manual agent coercion logic.

**Success Criteria**:
- [x] T004 Add `AgentAssignment` dataclass with proper fields and documentation
- [x] T005 Implement `resolved_agent()` with full fallback order and defaults
- [x] T006 Write behavior tests for all coercion scenarios (string, dict, None, model fallback, agent_profile fallback, role fallback)

**Owned Files**: `src/specify_cli/status/models.py`, `src/specify_cli/tasks_support.py`, `tests/specify_cli/status/test_agent_assignment.py`

**Execution Mode**: `code_change`

**Dependencies**: WP01

---

## Work Package 3: Migrate Slice 1 — Status Display (agent_utils/status.py)

**Priority**: High (P2 — first consumer migration, validates pattern)  
**Status**: Pending  
**Goal**: Migrate `agent_utils/status.py` to use `state.progress_bucket()` instead of manual lane bucketing

### Summary

Replace hardcoded lane → bucket mapping with delegation to `state.progress_bucket()`. Verify kanban output unchanged. Serve as validation that the pattern works before rolling to other consumers.

**Success Criteria**:
- [x] T007 Replace manual bucketing logic with `state.progress_bucket()` call
- [x] T008 Write regression test verifying display output unchanged for all 9 lanes
- [ ] All existing tests pass post-migration

**Owned Files**: `src/specify_cli/agent_utils/status.py`, `tests/specify_cli/agent_utils/test_status.py`

**Execution Mode**: `code_change`

**Dependencies**: WP01

---

## Work Package 4: Migrate Slice 2 — Runtime Routing & Agent Resolution

**Priority**: High (P2)  
**Status**: Pending  
**Goal**: Migrate `runtime_bridge.py` and `workflow.py` to use typed state properties and agent resolution

### Summary

**Part A (runtime_bridge.py)**: Replace `RUN_AFFECTING_LANES` tuple with `state.is_run_affecting` check.  
**Part B (workflow.py)**: Use `WPMetadata.resolved_agent()` for agent assignment; remove Lane.IN_PROGRESS → "doing" round-trip.

**Success Criteria**:
- [x] T009 Replace lane tuple checks with `state.is_run_affecting` in runtime_bridge.py
- [x] T010 Replace manual agent coercion with `resolved_agent()` in workflow.py
- [x] T011 Write integration tests for workflow CLI (agent assignment, routing)
- [ ] All existing tests pass post-migration

**Owned Files**: `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/cli/commands/agent/workflow.py`, `tests/specify_cli/next/test_runtime_bridge.py`, `tests/specify_cli/cli/commands/agent/test_workflow.py`

**Execution Mode**: `code_change`

**Dependencies**: WP01, WP02

---

## Work Package 5: Migrate Slice 3 — Review & Tasks

**Priority**: Medium (P3)  
**Status**: Pending  
**Goal**: Migrate `arbiter.py` and `tasks_cli.py` to use typed Lane enum and event log lane access

### Summary

**Part A (arbiter.py)**: Replace raw string comparisons with typed Lane enum access via WPState.  
**Part B (tasks_cli.py)**: Use `get_wp_lane()` with proper type handling; delegate display bucketing to `state.progress_bucket()`.

**Success Criteria**:
- [x] T012 Replace string lane comparisons with typed Lane enum in arbiter.py
- [x] T013 Replace hardcoded lane bucketing with `state.progress_bucket()` in tasks_cli.py
- [x] T014 Write regression tests for both consumers (arbiter review checks, task display output)
- [ ] All existing tests pass post-migration

**Owned Files**: `src/specify_cli/review/arbiter.py`, `src/specify_cli/scripts/tasks/tasks_cli.py`, `tests/specify_cli/review/test_arbiter.py`, `tests/specify_cli/scripts/tasks/test_tasks_cli.py`

**Execution Mode**: `code_change`

**Dependencies**: WP01

---

## Work Package 6: Migrate Slice 4 — Merge Validation & Recovery

**Priority**: Medium (P3 — critical for correctness but lower velocity)  
**Status**: Pending  
**Goal**: Migrate `merge.py` and `recovery.py` to use typed Lane enum and transition validation

### Summary

**Part A (merge.py)**: Preserve explicit Lane.DONE | Lane.APPROVED check (NOT delegated to `is_terminal`); use typed Lane enum.  
**Part B (recovery.py)**: Replace hardcoded transition tuples with `validate_transition()` from status module.

**Success Criteria**:
- [x] T015 Replace manual lane string check with typed Lane enum in merge.py (preserve approved|done distinction explicitly)
- [x] T016 Replace hardcoded transition tuples with `validate_transition()` in recovery.py
- [x] T017 Write integration tests for merge command and recovery transitions
- [ ] All existing tests pass post-migration; merge-ready behavior unchanged

**Owned Files**: `src/specify_cli/cli/commands/merge.py`, `src/specify_cli/lanes/recovery.py`, `tests/specify_cli/cli/commands/test_merge.py`, `tests/specify_cli/lanes/test_recovery.py`

**Execution Mode**: `code_change`

**Dependencies**: WP01

---

## Work Package 7: Final Cleanup & Verification

**Priority**: Low (P4 — sign-off phase)  
**Status**: Pending  
**Goal**: Verify completeness of migration and readiness for release

### Summary

Perform final acceptance checks: grep pass (no lane-string comparisons in 7 consumers), mypy --strict compliance, full test suite passing, no regressions.

**Success Criteria**:
- [x] T018 Grep pass: 0 results for lane-string patterns in 7 targeted consumers
- [x] T019 mypy --strict passes on all migrated code
- [x] T020 Full test suite passes (unit + integration + regression tests)
- [ ] No performance regressions in status board rendering or lane lookups

**Owned Files**: (verification only — no new source changes)

**Execution Mode**: `code_change`

**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06

---

## Execution Order & Parallelization

### Sequential Dependencies
1. **WP01** (is_run_affecting) → Foundation for all consumer migrations
2. **WP02** (AgentAssignment) → Required before WP04 (workflow.py migration)
3. **WP03, WP04, WP05, WP06** → Can begin after WP01 completes; WP04 additionally requires WP02
4. **WP07** → Final sign-off after all prior WPs complete

### Parallelization Opportunities
- **WP03, WP05, WP06** can run in parallel once WP01 completes
- **WP04** part A (runtime_bridge.py) can start after WP01; part B (workflow.py) requires WP02
- Suggest execution order: WP01 → [WP02 in parallel with WP03/WP05/WP06 starting] → WP04 → WP07

---

## Testing Strategy

### WP01–WP02 (Foundation)
- Behavior tests only (all 9 lanes, all coercion scenarios)
- No integration tests yet

### WP03–WP06 (Consumer Migrations)
- Regression tests: Compare old vs new output for each consumer
- Integration tests: CLI end-to-end for workflow, merge, recovery
- Target 90%+ coverage for new code

### WP07 (Verification)
- Full suite pass (unit + integration + regression)
- Grep pass on 7 targeted consumers
- mypy --strict compliance

---

## Risk Mitigation

| Risk | Mitigation | Assigned WP |
|------|-----------|-----------|
| Merge validation regression (approved|done handling) | Explicit Lane enum check; NOT delegated to is_terminal; careful testing | WP06 |
| Slice dependencies broken | AgentAssignment in WP02 before WP04; documented in WP prompt | WP02, WP04 |
| is_terminal/approved confusion | Constraint documented; WP06 verification explicit | WP06 |
| Backward compat breaks | Each slice leaves main releasable; full test suite after each | All |
| Type safety regression | mypy --strict enforced; WP07 verification | WP07 |

---

## Change Log

- **2026-04-09**: Initial task set for 7-consumer, 4-slice mission with 7 work packages.
