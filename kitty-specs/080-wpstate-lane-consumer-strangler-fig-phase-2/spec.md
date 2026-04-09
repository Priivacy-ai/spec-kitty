# WPState/Lane Consumer Strangler Fig Migration — Phase 2

## Overview

Complete the migration of WP lane consumers away from raw lane-string comparisons toward typed lane semantics and state properties. This is phase 2 of the Strangler Fig pattern from #405, targeting **7 verified consumer sites** (scope reduced from an initial survey of 15 candidates — see Change Log) that currently leak lane-string logic into feature code. Preserve backward compatibility after each consumer slice until migration is complete.

## Problem Statement

Lane semantics are currently scattered across several consumer sites rather than encapsulated in the status/state module. Each consumer reimplements lane buckets (e.g., "not started" = {planned}, "in_flight" = {claimed, in_progress, blocked}, "review" = {for_review, in_review, approved}) and carries stale lane-string assumptions. This creates maintenance burden, makes it harder to evolve lane transitions, and couples feature code to status implementation details.

## Desired Outcome

Lane semantics live exclusively behind `WPState`, `Lane`, and typed metadata boundaries. Consumers delegate to state properties (`is_run_affecting`, `is_terminal`, `progress_bucket()`, `display_category()`, `resolved_agent`) instead of reimplementing lane logic.

---

## User Scenarios

### Scenario 1: Agent Reviewing Status Board
An agent calls `show_kanban_status()` to display work package progress.  
**Current**: Reimplements lane bucketing internally ("review" = {for_review, in_review}, custom in_review folding).  
**After**: Uses `state.progress_bucket()` and `state.display_category()` directly.

### Scenario 2: Runtime Bridge Deciding Next Step
The runtime bridge evaluates WP lane state to decide whether to route to implement/review.  
**Current**: Raw tuples like `(Lane.IN_PROGRESS, Lane.FOR_REVIEW)` for lane membership tests.  
**After**: Uses `state.is_run_affecting`, `state.is_terminal`, or typed state comparisons.

### Scenario 3: Recovery Mode Advancing WPs
Recovery mode advances stalled WPs through lanes (planned → claimed → in_progress).  
**Current**: Direct `Lane.IN_PROGRESS` enum matching and manual transition lists.  
**After**: Uses state-level lane access and transition validation from status module.

### Scenario 4: Workflow Handling Agent Assignment
Workflow resolves agent, model, and role metadata.  
**Current**: String/dict coercion with manual fallback to `model` and `agent_profile` fields; removes Lane.IN_PROGRESS → "doing" alias before passing to runtime.  
**After**: Uses `WPMetadata.resolved_agent` for unified coercion; keeps alias handling inside state boundary.

### Scenario 5: Merge Gates Checking WP Readiness
Merge validation checks if WPs are in terminal lanes (done, approved).  
**Current**: Direct `Lane.DONE | Lane.APPROVED` comparisons.  
**After**: Uses `state.is_terminal` property.

---

## Scope & Boundaries

### In Scope
- Add `WPState.is_run_affecting` property (returns True for active WPs: planned, claimed, in_progress, for_review, in_review, approved)
- Introduce `AgentAssignment` value object with `tool`, `model`, `profile_id`, `role`
- Add `WPMetadata.resolved_agent` returning `AgentAssignment`, absorbing legacy string/dict coercion plus model/agent_profile/role fallback behavior
- Migrate 7 verified WP lane consumers in sequential slices (Strangler Fig):
  1. **Slice 1**: `agent_utils/status.py` (display/kanban)
  2. **Slice 2**: `next/runtime_bridge.py`, `cli/commands/agent/workflow.py` (runtime routing + agent resolution)
  3. **Slice 3**: `review/arbiter.py`, `scripts/tasks/tasks_cli.py` (review arbiter + task scripts)
  4. **Slice 4**: `cli/commands/merge.py`, `lanes/recovery.py` (merge validation + recovery mode)
- Preserve strict backward compatibility after each slice

### Out of Scope (Scope Reduction from Initial Spec)
- **Broadened consumers from initial spec (follow-up missions)**:
  - `dashboard/scanner.py` (requires separate design to preserve approved/for_review distinction)
  - `cli/commands/agent/tasks.py` (already uses typed Lane enums; not a lane-string leak)
  - `policy/merge_gates.py` (approved/done distinction requires explicit handling, not is_terminal)
  - `cli/commands/implement.py`, `acceptance.py`, `core/worktree_topology.py`, `orchestrator_api/commands.py`, `mission_v1/guards.py` (separate follow-up scope)
- Subtask checkbox statuses ("done", "pending") that are not WP lane semantics
- Migration-only compatibility code (intentional during transition)
- Unrelated lane-string usage outside WP state consumers

### Exclusions (Verified)
- `src/specify_cli/next/decision.py` line 403 (`state == "done"`): mission-state routing, not WP lane leak
- `src/specify_cli/status/` (status module itself): authority source, not a consumer
- `WPState.is_terminal` property: Exists in current tree; this mission does NOT introduce it. Only is_run_affecting is added.
- Merge validation using approved|done: preserved as explicit Lane check, NOT delegated to is_terminal (which is only for cleanup logic: done/canceled)
- Legacy lane-string usage in migration code (intentional until final cutover)

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Add `WPState.is_run_affecting` property returning `bool` (True for planned, claimed, in_progress, for_review, in_review, approved; False for done, blocked, canceled) | pending |
| FR-002 | Introduce `AgentAssignment` value object with typed fields: `tool`, `model`, `profile_id`, `role` | pending |
| FR-003 | Add `WPMetadata.resolved_agent()` method returning `AgentAssignment`, absorbing legacy string/dict coercion plus model/agent_profile/role fallback behavior | pending |
| FR-004 | Migrate `agent_utils/status.py` to use `state.progress_bucket()` instead of manual lane bucketing | pending |
| FR-005 | Migrate `next/runtime_bridge.py` to use `state.is_run_affecting` instead of raw lane tuple checks | pending |
| FR-006 | Migrate `cli/commands/agent/workflow.py` to use `WPMetadata.resolved_agent()` for agent assignment; remove Lane.IN_PROGRESS → "doing" round-trip from consumer | pending |
| FR-007 | Migrate `review/arbiter.py` to use typed `Lane` enum via `WPState` instead of raw string comparisons | pending |
| FR-008 | Migrate `scripts/tasks/tasks_cli.py` to use event log lane access via `get_wp_lane()` with proper type handling | pending |
| FR-009 | Migrate `cli/commands/merge.py` to use typed Lane enum for approved/done distinction; preserve explicit merge-ready check | pending |
| FR-010 | Migrate `lanes/recovery.py` to use transition validation from status module instead of hardcoded lane transition tuples | pending |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage for new `WPState` properties and methods | 90%+ | pending |
| NFR-002 | Test coverage for `AgentAssignment` value object (string input, dict input, None, model fallback) | 90%+ | pending |
| NFR-003 | Test coverage for `WPMetadata.resolved_agent()` method | 90%+ | pending |
| NFR-004 | Type safety: mypy --strict passes after migration | 100% compliance | pending |
| NFR-005 | Backward compatibility: all existing tests pass after each consumer slice | 100% passing | pending |
| NFR-006 | Performance: no regression in status board rendering or lane lookups | Baseline unchanged | pending |

---

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Use Strangler Fig pattern: migrate 7 verified consumers sequentially in 4 slices; maintain strict backward compatibility after each slice until final cutover | pending |
| C-002 | `AgentAssignment` must support legacy string, dict, and None inputs for backward compatibility; fallback to model/agent_profile/role fields as needed | pending |
| C-003 | Lane alias resolution (`"doing" → Lane.IN_PROGRESS`) must remain inside the state/status boundary; not exposed at consumer layer | pending |
| C-004 | Merge validation preserved: approved + done are merge-ready; NOT delegated to is_terminal (which is cleanup logic: done/canceled only) | pending |
| C-005 | No changes to `decision.py` or mission-state routing; only WP lane consumers in scope | pending |
| C-006 | Preserve existing CLI and agent API contracts; changes are internal only | pending |

---

## Success Criteria

1. **Lane Semantics Encapsulation**: No raw lane-string comparisons remain in the 7 targeted consumer files; all lane logic delegated to `WPState`, `Lane`, or progress/phase APIs
2. **Complete Migration**: All 7 verified consumers migrated to typed/state semantics in 4 sequential slices with full backward compatibility
3. **Test Coverage**: 90%+ coverage for `WPState.is_run_affecting`, `AgentAssignment`, and `WPMetadata.resolved_agent`; mypy --strict passes
4. **Acceptance Tests**: Full existing test suites pass after each slice and final cutover; no regressions in functionality
5. **Documentation**: Type hints and docstrings for new properties/methods; design decisions captured in plan
6. **Merge Validation Preserved**: Approved + done distinction maintained explicitly; is_run_affecting and is_terminal used correctly without conflation

---

## Assumptions

1. **Lane enum and status module are authoritative**: All lane logic lives in `src/specify_cli/status/`, and consumers delegate to it
2. **Backward compatibility is required**: No breaking changes to CLI or agent APIs during migration; Strangler Fig allows safe incremental rollout
3. **Legacy fallback behavior is documented**: `AgentAssignment` resolution will have clear documented fallback order (direct assignment → model field → agent_profile field → role field)
4. **Sequential slicing is feasible**: The 4 amended slices can be implemented independently with compatibility maintained after each; tight coupling between slices is minimal
5. **Test suites are comprehensive**: Existing tests will catch regressions if a slice is incomplete or breaks a consumer

---

## Key Entities

### WPState
- **Properties**: `lane` (str), `is_run_affecting` (bool), `is_terminal` (bool), `progress_bucket()` → str, `display_category()` → str
- **Responsibility**: Encapsulate lane semantics and state-derived queries
- **Sourced from**: Status event log via `reduce()`

### AgentAssignment
- **Fields**: `tool` (str), `model` (str), `profile_id` (Optional[str])`, `role` (Optional[str])`
- **Responsibility**: Represent resolved agent assignment with all context
- **Usage**: Returned by `WPMetadata.resolved_agent()`

### WPMetadata
- **New method**: `resolved_agent()` → `AgentAssignment`
- **Responsibility**: Unify legacy string/dict coercion and fallback resolution
- **Fallback order**: Direct assignment → model → agent_profile → role (each with safe defaults)

---

## Open Decisions & Clarifications

None. Discovery and user input have resolved all critical decisions.

---

## Related Issues & PRs

- **#405**: Original Strangler Fig pattern introduction (phase 1)
- **#537**: This mission (phase 2 — follow-up)
- **Commit**: `45e92b4abc5e3e73e216cbc23ca572b51af4b70b` (current main source of truth as of 2026-04-09)

---

## Change Log

- **2026-04-09 (Initial)**: Initial specification created from discovery. 15 consumer sites identified and organized into 6 sequential slices. AgentAssignment and WPState property additions scoped.
- **2026-04-09 (Amendment)**: Scope reduction to 7 verified consumers (Path A). Removed broadened consumers from initial spec (dashboard/scanner.py, tasks.py, merge_gates.py, implement.py, acceptance.py, worktree_topology.py, orchestrator_api/commands.py, mission_v1/guards.py). Fixed FR/NFR/constraint misalignments. Clarified is_terminal vs merge-ready distinction. Confirmed WPState.is_terminal already exists; only is_run_affecting is new. Reorganized into 4 slices and 7 WPs instead of 6 slices and 9 WPs.
