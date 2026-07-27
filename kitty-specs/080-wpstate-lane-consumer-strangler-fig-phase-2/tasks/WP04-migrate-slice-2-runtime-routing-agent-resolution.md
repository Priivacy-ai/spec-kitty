---
work_package_id: WP04
title: 'Migrate Slice 2: Runtime Routing & Agent Resolution'
dependencies:
- WP01
- WP02
requirement_refs:
- FR-005
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
history: []
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/cli/commands/agent/workflow.py
- tests/specify_cli/next/test_runtime_bridge.py
- tests/specify_cli/cli/commands/agent/test_workflow.py
tags: []
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "55624"
---

# WP04: Migrate Slice 2 — Runtime Routing & Agent Resolution

**Objective**: Migrate two consumers in Slice 2:
- **Part A**: `next/runtime_bridge.py` — Replace lane tuple checks with `state.is_run_affecting`
- **Part B**: `cli/commands/agent/workflow.py` — Replace manual agent coercion with `WPMetadata.resolved_agent()`

---

## Context

**Part A (runtime_bridge.py)**:
Currently uses a hardcoded tuple to decide if a WP affects execution:
```python
RUN_AFFECTING_LANES = (
    Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED, 
    Lane.PLANNED, Lane.CLAIMED
)

if lane in RUN_AFFECTING_LANES:
    return "route_to_implementation"
elif lane in (Lane.DONE, Lane.CANCELED):
    return "accept"  # Terminal
```

By using `state.is_run_affecting`, we eliminate the tuple duplication.

**Part B (workflow.py)**:
Currently manually coerces agent metadata with string/dict/None handling scattered throughout:
```python
if isinstance(wp.agent, str):
    tool = wp.agent
    model = wp.model or "unknown-model"
elif isinstance(wp.agent, dict):
    tool = wp.agent.get("tool", "unknown")
    model = wp.agent.get("model", wp.model or "unknown-model")
    # ... more dict handling ...
else:
    tool = "unknown"
    model = wp.model or "unknown-model"
```

By using `WPMetadata.resolved_agent()`, we centralize this logic and improve testability.

---

## Detailed Guidance

### T009: Migrate next/runtime_bridge.py to Use state.is_run_affecting

**Purpose**: Replace lane tuple checks with the new typed property.

**Steps**:
1. Locate `src/specify_cli/next/runtime_bridge.py`.
2. Find the `RUN_AFFECTING_LANES` tuple definition (or similar).
3. Find all places where it's used, e.g.:
   ```python
   if lane in RUN_AFFECTING_LANES:
       # route to implementation
   elif lane in (Lane.DONE, Lane.CANCELED):
       # accept
   ```
4. Replace with:
   ```python
   from specify_cli.status.models import wp_state_for, Lane
   
   state = wp_state_for(snapshot)
   
   if state.is_run_affecting:
       return "route_to_implementation"
   elif state.lane in (Lane.DONE, Lane.CANCELED):
       return "accept"
   ```
5. Remove the old `RUN_AFFECTING_LANES` tuple definition entirely.
6. Verify no other references to the tuple remain.
7. Check that the function logic is unchanged (same routing decisions, same behavior).

**Validation**: Tuple removed, `is_run_affecting` used, routing logic identical, function still works.

---

### T010: Migrate cli/commands/agent/workflow.py to Use resolved_agent()

**Purpose**: Replace manual agent coercion with `WPMetadata.resolved_agent()`.

**Steps**:
1. Locate `src/specify_cli/cli/commands/agent/workflow.py`.
2. Find the function(s) that handle agent assignment (likely in a command or middleware).
3. Find all places where `wp.agent` is coerced manually:
   - String checks: `isinstance(wp.agent, str)`
   - Dict checks: `isinstance(wp.agent, dict)`
   - Fallback chains: `wp.model or "default"`, `wp.agent.get("model", ...)`
4. Replace with:
   ```python
   from specify_cli.status.models import AgentAssignment
   
   # Assuming wp_metadata is a WPMetadata instance
   assignment = wp_metadata.resolved_agent()
   
   tool = assignment.tool
   model = assignment.model
   profile_id = assignment.profile_id
   role = assignment.role
   ```
5. Remove all manual if-elif chains for agent coercion.
6. Verify no Lane.IN_PROGRESS → "doing" alias remains in consumer code (alias handling stays inside status boundary).
7. Check that the agent assignment logic is unchanged (same fallback behavior, same defaults).

**Validation**: Manual coercion removed, `resolved_agent()` used, agent assignment logic identical, function still works.

---

### T011: Write Integration Tests for Workflow CLI

**Purpose**: Verify workflow end-to-end with both runtime_bridge and agent resolution changes.

**Steps**:
1. Locate or create `tests/specify_cli/cli/commands/agent/test_workflow.py` and `tests/specify_cli/next/test_runtime_bridge.py`.
2. For **runtime_bridge**, write a test verifying `is_run_affecting` produces same routing as old tuple:
   ```python
   def test_is_run_affecting_matches_run_affecting_lanes():
       """Verify is_run_affecting == (lane in RUN_AFFECTING_LANES)."""
       RUN_AFFECTING = ("planned", "claimed", "in_progress", "for_review", 
                        "in_review", "approved")
       
       for lane_str in ["planned", "claimed", "in_progress", "for_review", 
                        "in_review", "approved", "done", "blocked", "canceled"]:
           state = wp_state_for({"lane": lane_str})
           expected = lane_str in RUN_AFFECTING
           assert state.is_run_affecting == expected, f"Lane {lane_str}"
   ```
3. For **workflow**, write tests verifying `resolved_agent()` produces same assignments:
   ```python
   def test_workflow_agent_assignment():
       """Verify resolved_agent() produces correct tool and model."""
       # Test string agent
       metadata1 = WPMetadata(agent="claude", model="claude-opus-4-6")
       assignment1 = metadata1.resolved_agent()
       assert assignment1.tool == "claude"
       assert assignment1.model == "claude-opus-4-6"
       
       # Test dict agent
       metadata2 = WPMetadata(agent={"tool": "copilot", "model": "gpt-4"})
       assignment2 = metadata2.resolved_agent()
       assert assignment2.tool == "copilot"
       assert assignment2.model == "gpt-4"
   ```
4. Run integration test for the workflow CLI command if applicable:
   ```bash
   # Example: test that the workflow command still routes correctly
   spec-kitty agent workflow --feature 080-feature --wp WP01
   ```
5. Verify no regressions in existing workflow tests.

**Validation**: Integration tests pass, routing decisions unchanged, agent assignments correct.

---

## Integration Points

- **Depends on**: WP01 (is_run_affecting available), WP02 (AgentAssignment/resolved_agent available)
- **Does not depend on**: WP03, WP05, WP06 (can run in parallel after WP02 completes)
- **Blocks**: WP07 verification step (final grep pass)

---

## Test Strategy

**Scope**: Regression + integration tests.

**Coverage Target**: 100% of modified logic in both files.

**Test Cases**:
- runtime_bridge.py: All 9 lanes → correct routing decision
- workflow.py: String agent, dict agent, None agent, fallback scenarios
- CLI integration: Workflow command end-to-end (if applicable)

---

## Definition of Done

- [ ] `RUN_AFFECTING_LANES` tuple removed from runtime_bridge.py
- [ ] `state.is_run_affecting` used instead; routing unchanged
- [ ] Manual agent coercion removed from workflow.py
- [ ] `WPMetadata.resolved_agent()` used instead; assignments unchanged
- [ ] All 9 lanes tested in runtime_bridge tests
- [ ] All agent coercion scenarios tested in workflow tests
- [ ] Integration tests pass (CLI workflow command works)
- [ ] All existing tests pass
- [ ] mypy --strict passes on both modified files
- [ ] No performance regression

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Routing regression (is_run_affecting wrong) | Test all 9 lanes; compare old tuple vs new property |
| Agent assignment regression (fallback wrong) | Test string, dict, None, and fallback scenarios |
| Lane.IN_PROGRESS alias leakage to consumer | Code review to ensure alias stays in status boundary |
| Backward compat break | This consumer's API unchanged; only internal logic changed |

---

## Reviewer Guidance

- Verify `RUN_AFFECTING_LANES` tuple is completely removed
- Check that `is_run_affecting` routing is correct for all lanes
- Verify manual agent coercion is completely removed
- Check that `resolved_agent()` is called correctly
- Confirm Lane.IN_PROGRESS alias is not exposed in consumer code
- Verify tests cover all 9 lanes and all agent coercion scenarios
- Check CLI integration test passes

---

## Change Log

- **2026-04-09**: Initial WP for 080-wpstate-lane-consumer-strangler-fig-phase-2

## Activity Log

- 2026-04-09T15:20:43Z – claude:haiku:implementer:implementer – shell_pid=21353 – Started implementation via action command
- 2026-04-09T15:42:15Z – claude:haiku:implementer:implementer – shell_pid=21353 – Ready for review: T009 migrated runtime_bridge._should_advance_wp_step to use WPState.is_run_affecting; T010 migrated workflow.py to use WPMetadata.resolved_agent(); T011 added 53 integration tests. All 184 tests pass.
- 2026-04-09T15:42:39Z – claude:sonnet:reviewer:reviewer – shell_pid=77386 – Started review via action command
- 2026-04-09T15:49:59Z – claude:sonnet:reviewer:reviewer – shell_pid=77386 – Review passed: T009 - RUN_AFFECTING_LANES tuple removed, state.is_run_affecting used correctly with wp_state_for(); T010 - manual isinstance agent coercion replaced by WPMetadata.resolved_agent(), called from live implement path; T011 - 53 tests covering all 9 lanes and all agent coercion scenarios, 331 tests pass with no regressions. Behavioral change for blocked lane aligned with FR-001 semantics.
- 2026-04-09T16:55:56Z – claude:sonnet:implementer:implementer – shell_pid=93567 – Started implementation via action command
- 2026-04-09T17:22:20Z – claude:sonnet:implementer:implementer – shell_pid=93567 – Ready for review: T009 - runtime_bridge._should_advance_wp_step migrated to use WPState.is_run_affecting; T010 - workflow.py doing alias removed, resolved_agent() called from implement path; T011 - 34 tests covering all 9 lanes and all agent coercion scenarios. All 9906 tests pass.
- 2026-04-09T17:22:44Z – claude:sonnet:reviewer:reviewer – shell_pid=55624 – Started review via action command
- 2026-04-09T17:25:07Z – claude:sonnet:reviewer:reviewer – shell_pid=55624 – Review passed: is_run_affecting migration complete, RUN_AFFECTING_LANES tuple removed, doing alias removed from workflow.py, resolved_agent() wired into implement path, 34 live tests covering all 9 lanes and all agent coercion scenarios pass
