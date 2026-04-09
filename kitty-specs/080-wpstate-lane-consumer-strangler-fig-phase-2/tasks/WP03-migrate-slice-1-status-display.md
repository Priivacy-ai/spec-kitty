---
work_package_id: WP03
title: 'Migrate Slice 1: Status Display (agent_utils/status.py)'
dependencies:
- WP01
requirement_refs:
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-080-wpstate-lane-consumer-strangler-fig-phase-2
base_commit: efb7680445392afc7d54c898e7075b5a02d36905
created_at: '2026-04-09T14:28:21.148090+00:00'
subtasks:
- T007
- T008
shell_pid: "91418"
history: []
authoritative_surface: src/specify_cli/agent_utils/
execution_mode: code_change
owned_files:
- src/specify_cli/agent_utils/status.py
- tests/specify_cli/agent_utils/test_status.py
tags: []
agent: "claude:sonnet:reviewer:reviewer"
---

# WP03: Migrate Slice 1 — Status Display (agent_utils/status.py)

**Objective**: Migrate `agent_utils/status.py` to use `state.progress_bucket()` instead of manual lane bucketing. This is the first consumer migration, validating that the pattern works before rolling to other consumers.

---

## Context

Currently, `agent_utils/status.py` manually maps WP lanes to progress categories:
```python
lane_str = wp_snapshot.get("lane", "planned")

if lane_str in ("planned", "claimed"):
    progress = "Not Started"
elif lane_str in ("in_progress",):
    progress = "In Progress"
elif lane_str in ("for_review", "in_review"):
    progress = "Review"
elif lane_str in ("approved",):
    progress = "In Progress"
elif lane_str in ("done", "canceled"):
    progress = "Complete"
```

This duplicates bucketing logic. By using `state.progress_bucket()`, we delegate this responsibility to the authoritative status module and reduce coupling.

**Design Decision**: Replace manual if-elif chain with:
```python
state = wp_state_for(wp_snapshot)
bucket = state.progress_bucket()  # Returns: "not_started", "in_progress", "review", "complete"
progress = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "review": "Review",
    "complete": "Complete",
}.get(bucket)
```

---

## Detailed Guidance

### T007: Replace Manual Bucketing Logic with state.progress_bucket()

**Purpose**: Update the display logic in `agent_utils/status.py` to delegate bucketing.

**Steps**:
1. Locate `src/specify_cli/agent_utils/status.py` and find the function(s) that perform kanban display (likely `show_kanban_status()` or similar).
2. Find all places where `lane_str` is checked against hardcoded tuples:
   - `if lane_str in ("planned", "claimed"): ...`
   - `if lane_str in ("in_progress",): ...`
   - `if lane_str in ("for_review", "in_review"): ...`
   - `if lane_str in ("approved",): ...`
   - `if lane_str in ("done", "canceled"): ...`
3. Replace with:
   ```python
   from specify_cli.status.models import wp_state_for
   
   state = wp_state_for(wp_snapshot)
   bucket = state.progress_bucket()  # Returns one of: "not_started", "in_progress", "review", "complete"
   
   # Map bucket to display string (if needed)
   display_map = {
       "not_started": "Not Started",
       "in_progress": "In Progress",
       "review": "Review",
       "complete": "Complete",
   }
   progress = display_map.get(bucket)
   ```
4. Remove the old hardcoded if-elif chain entirely.
5. Verify the function still compiles and no other references to manual lane bucketing remain.
6. Check for any `Lane.IN_PROGRESS` references that may have been used as aliases (e.g., `"doing"` → `Lane.IN_PROGRESS`) and ensure alias resolution remains inside the status boundary (not exposed to this consumer).

**Validation**: All manual bucketing replaced, function still works, old if-elif chain removed, imports added.

---

### T008: Write Regression Tests for Kanban Display

**Purpose**: Verify display output is identical before and after migration.

**Steps**:
1. Locate or create `tests/specify_cli/agent_utils/test_status.py`.
2. Write a regression test that verifies `progress_bucket()` produces the same display output as the old logic:
   ```python
   from specify_cli.agent_utils.status import show_kanban_status
   from specify_cli.status.models import wp_state_for
   
   def test_kanban_progress_bucket_unchanged():
       """Verify progress_bucket() maps lanes same as old manual logic."""
       test_cases = [
           ("planned", "Not Started"),
           ("claimed", "Not Started"),
           ("in_progress", "In Progress"),
           ("for_review", "Review"),
           ("in_review", "Review"),
           ("approved", "In Progress"),
           ("done", "Complete"),
           ("canceled", "Complete"),
           ("blocked", "Not Started"),  # Blocked should map to not_started
       ]
       for lane_str, expected_display in test_cases:
           state = wp_state_for({"lane": lane_str})
           bucket = state.progress_bucket()
           # Verify bucket maps to expected display
           display_map = {
               "not_started": "Not Started",
               "in_progress": "In Progress",
               "review": "Review",
               "complete": "Complete",
           }
           actual_display = display_map.get(bucket)
           assert actual_display == expected_display, f"Lane {lane_str} → bucket {bucket} → display {actual_display} != {expected_display}"
   ```
3. Run the test locally and verify it passes for all 9 lanes.
4. If any test fails, it indicates a regression—investigate and fix the bucketing logic.

**Validation**: All 9 lanes tested, regression test passes, old and new output match.

---

## Integration Points

- **Depends on**: `WPState.is_run_affecting` (WP01) is available, `state.progress_bucket()` already exists in status module
- **Does not depend on**: WP02, WP04, WP05, WP06 (can run in parallel)
- **Blocks**: WP07 verification step (final grep pass)

---

## Test Strategy

**Scope**: Regression tests only. No behavior tests needed for this consumer (progress_bucket() is tested in WP01).

**Coverage Target**: 100% of the display logic (all 9 lanes mapped).

**Test Cases**:
- All 9 lanes: planned, claimed, in_progress, for_review, in_review, approved, done, blocked, canceled
- Display output unchanged for each lane
- Blocked lane maps to "Not Started" (important edge case)

---

## Definition of Done

- [ ] Manual bucketing if-elif chain removed from `agent_utils/status.py`
- [ ] `state.progress_bucket()` used instead
- [ ] Regression test verifies display output unchanged for all 9 lanes
- [ ] No hardcoded Lane tuples remain in the file
- [ ] All existing tests pass
- [ ] mypy --strict passes on modified file
- [ ] No performance regression in kanban rendering

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Display output regression (bucket mapping wrong) | Regression test covers all 9 lanes; compares old vs new output |
| Blocked lane handling (edge case) | Test explicitly includes blocked lane; verify maps to "not_started" |
| Backward compat break | This consumer's API unchanged; only internal logic changed |

---

## Reviewer Guidance

- Verify old if-elif chain is completely removed
- Check that `progress_bucket()` is called correctly
- Confirm regression test covers all 9 lanes and passes
- Ensure no Lane tuple constants remain (other than Lane enum imports)
- Verify Blocked lane maps to "not_started" (important for completeness)
- Check that alias handling (if any) stays inside status boundary

---

## Change Log

- **2026-04-09**: Initial WP for 080-wpstate-lane-consumer-strangler-fig-phase-2

## Activity Log

- 2026-04-09T14:28:21Z – claude:haiku:implementer:implementer – shell_pid=44087 – Assigned agent via action command
- 2026-04-09T14:35:25Z – claude:haiku:implementer:implementer – shell_pid=44087 – Ready for review
- 2026-04-09T14:35:47Z – claude:haiku:reviewer:reviewer – shell_pid=77858 – Started review via action command
- 2026-04-09T14:37:34Z – claude:haiku:reviewer:reviewer – shell_pid=77858 – Moved to planned
- 2026-04-09T14:40:05Z – claude:haiku:reviewer:reviewer – shell_pid=77858 – Fixed: _get_progress_display now called from _display_status_board (line 339). Integration verified via grep and new code path test. All 5 tests pass.
- 2026-04-09T14:40:32Z – claude:haiku:reviewer:reviewer – shell_pid=579 – Started review via action command
- 2026-04-09T14:42:39Z – claude:haiku:reviewer:reviewer – shell_pid=579 – Review cycle 2 passed: Dead code integration completed. Function defined at line 28, called from _display_status_board() at line 339. All 5 tests passing including integration test test_display_board_uses_progress_display which verifies live code path.
- 2026-04-09T16:34:10Z – claude:sonnet:implementer:implementer – shell_pid=21064 – Started implementation via action command
- 2026-04-09T16:44:37Z – claude:sonnet:implementer:implementer – shell_pid=21064 – Complete migration: all raw lane-string comparisons replaced with Lane enum keys and wp_state_for().progress_bucket() calls. Zero raw strings in grep check. 16 tests passing including show_kanban_status() integration test.
- 2026-04-09T16:45:48Z – claude:sonnet:implementer:implementer – shell_pid=52172 – Started implementation via action command
- 2026-04-09T16:50:59Z – claude:sonnet:implementer:implementer – shell_pid=52172 – Ready for review: full migration complete - Lane enum grouping, wp_state_for() in all live code paths (show_kanban_status, _analyze_parallelization, metrics calculations). Zero raw lane string matches. 16 tests passing including 2 live show_kanban_status integration tests. 2277 total tests green.
- 2026-04-09T16:54:09Z – claude:sonnet:reviewer:reviewer – shell_pid=91418 – Started review via action command
- 2026-04-09T16:55:38Z – claude:sonnet:reviewer:reviewer – shell_pid=91418 – Review passed: full migration, live integration tests, zero raw lane strings
