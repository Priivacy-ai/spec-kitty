---
work_package_id: WP05
title: 'Migrate Slice 3: Review & Tasks'
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
history: []
authoritative_surface: src/specify_cli/review/
execution_mode: code_change
owned_files:
- src/specify_cli/review/arbiter.py
- src/specify_cli/scripts/tasks/tasks_cli.py
- tests/specify_cli/review/test_arbiter.py
- tests/specify_cli/scripts/tasks/test_tasks_cli.py
tags: []
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "38338"
---

# WP05: Migrate Slice 3 — Review & Tasks

**Objective**: Migrate two consumers in Slice 3:
- **Part A**: `review/arbiter.py` — Replace raw lane string comparisons with typed `Lane` enum via `WPState`
- **Part B**: `scripts/tasks/tasks_cli.py` — Use event log lane access with type handling; delegate display bucketing

---

## Context

**Part A (arbiter.py)**:
Currently uses raw string/enum comparisons for review checks:
```python
latest = wp_events[-1]
if latest.from_lane == Lane.FOR_REVIEW and latest.to_lane == Lane.PLANNED:
    return True  # WP was in for_review, now moved back
```

While this uses the Lane enum, it mixes string and enum comparisons. By fully typing this via WPState, we ensure consistency.

**Part B (tasks_cli.py)**:
Currently manually maps lanes to display strings:
```python
lane = get_lane_from_frontmatter(wp_path)

if lane in ("planned", "claimed"):
    display = "Planned"
elif lane in ("in_progress",):
    display = "In Progress"
elif lane in ("for_review", "in_review"):
    display = "In Review"
```

By using `state.progress_bucket()`, we delegate bucketing to the status module and reduce duplication.

---

## Detailed Guidance

### T012: Migrate review/arbiter.py to Use Typed Lane Enum

**Purpose**: Ensure all lane comparisons are type-safe and consistent.

**Steps**:
1. Locate `src/specify_cli/review/arbiter.py`.
2. Find all places where lane events are compared (likely in review decision logic):
   - String comparisons: `if latest.from_lane == "for_review"`
   - Raw enum comparisons: `if Lane(latest.from_lane) == Lane.FOR_REVIEW`
3. Standardize all comparisons to use typed Lane enum:
   ```python
   from specify_cli.status.models import Lane, wp_state_for
   
   # When comparing lanes from events:
   latest = wp_events[-1]
   
   # Use Lane enum consistently:
   if Lane(latest.from_lane) == Lane.FOR_REVIEW and Lane(latest.to_lane) == Lane.PLANNED:
       return True
   
   # Or, construct state and use state properties:
   state = wp_state_for({"lane": latest.to_lane})
   if state.progress_bucket() == "review":
       # ... review-specific logic
   ```
4. Remove any raw string comparisons like `== "for_review"`.
5. Verify arbiter logic is unchanged (same review decisions).

**Validation**: All lane comparisons use typed Lane enum, no raw strings, arbiter logic unchanged.

---

### T013: Migrate scripts/tasks/tasks_cli.py to Use progress_bucket()

**Purpose**: Replace hardcoded lane bucketing with delegation to status module.

**Steps**:
1. Locate `src/specify_cli/scripts/tasks/tasks_cli.py`.
2. Find all places where lanes are mapped to display strings:
   - Tuples: `if lane in ("planned", "claimed"): display = "Planned"`
   - If-elif chains for bucketing
3. Replace with:
   ```python
   from specify_cli.status.models import wp_state_for
   from specify_cli.status.lane_reader import get_wp_lane
   
   # Get lane from event log (already typed)
   lane_str = str(get_wp_lane(feature_dir, wp_id))
   
   # Construct state and use progress_bucket()
   state = wp_state_for({"lane": lane_str})
   bucket = state.progress_bucket()  # Returns: "not_started", "in_progress", "review", "complete"
   
   # Map bucket to display (if needed)
   display_map = {
       "not_started": "Planned",
       "in_progress": "In Progress",
       "review": "In Review",
       "complete": "Complete",
   }
   display = display_map.get(bucket, "Unknown")
   ```
4. Remove all hardcoded tuples and if-elif chains for lane → display mapping.
5. Verify task script output is unchanged (same display strings for each lane).

**Validation**: Hardcoded bucketing removed, `progress_bucket()` used, display output unchanged.

---

### T014: Write Regression Tests for Arbiter & Tasks

**Purpose**: Verify both consumers produce identical output after migration.

**Steps**:
1. Locate or create `tests/specify_cli/review/test_arbiter.py` and `tests/specify_cli/scripts/tasks/test_tasks_cli.py`.
2. For **arbiter**, write tests verifying review checks still work:
   ```python
   def test_arbiter_review_check():
       """Verify typed Lane enum comparisons work correctly."""
       # Test: WP moved from for_review back to planned
       event = {
           "from_lane": "for_review",
           "to_lane": "planned"
       }
       from_lane = Lane(event["from_lane"])
       to_lane = Lane(event["to_lane"])
       
       assert from_lane == Lane.FOR_REVIEW
       assert to_lane == Lane.PLANNED
       assert from_lane == Lane.FOR_REVIEW and to_lane == Lane.PLANNED
   ```
3. For **tasks_cli**, write regression test verifying display output is unchanged:
   ```python
   def test_tasks_cli_lane_display():
       """Verify progress_bucket() maps to same display as old logic."""
       test_cases = [
           ("planned", "Planned"),
           ("claimed", "Planned"),
           ("in_progress", "In Progress"),
           ("for_review", "In Review"),
           ("in_review", "In Review"),
           ("approved", "In Progress"),  # Approved might map to "In Progress"
           ("done", "Complete"),
           ("canceled", "Complete"),
           ("blocked", "Planned"),  # Or appropriate fallback
       ]
       for lane_str, expected_display in test_cases:
           state = wp_state_for({"lane": lane_str})
           bucket = state.progress_bucket()
           display_map = {
               "not_started": "Planned",
               "in_progress": "In Progress",
               "review": "In Review",
               "complete": "Complete",
           }
           actual_display = display_map.get(bucket, "Unknown")
           assert actual_display == expected_display, f"Lane {lane_str} → {actual_display} != {expected_display}"
   ```
4. Run both test suites locally and verify all pass.

**Validation**: Arbiter tests pass, task display tests pass, output unchanged for all lanes.

---

## Integration Points

- **Depends on**: WP01 (is_run_affecting available, progress_bucket() available)
- **Does not depend on**: WP02, WP04, WP06 (can run in parallel after WP01 completes)
- **Blocks**: WP07 verification step (final grep pass)

---

## Test Strategy

**Scope**: Regression tests only.

**Coverage Target**: 100% of modified logic in both files.

**Test Cases**:
- arbiter.py: Review checks work correctly with typed Lane enum
- tasks_cli.py: All 9 lanes → correct display string
- Edge cases: blocked lane, approved lane (approved should map to "In Progress" per spec, not "complete")

---

## Definition of Done

- [ ] All raw string lane comparisons removed from arbiter.py
- [ ] All lane comparisons use typed Lane enum
- [ ] Arbiter logic verified unchanged (same review decisions)
- [ ] Hardcoded bucketing if-elif chain removed from tasks_cli.py
- [ ] `progress_bucket()` used instead; display output unchanged
- [ ] Regression tests pass for arbiter (typed Lane comparisons)
- [ ] Regression tests pass for tasks (display bucketing for all 9 lanes)
- [ ] All existing tests pass
- [ ] mypy --strict passes on both modified files
- [ ] No performance regression in task script output

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Arbiter review logic regression (wrong check) | Test all comparison scenarios; verify same review decisions |
| Tasks display output regression (wrong bucket) | Test all 9 lanes; compare old vs new display strings |
| Backward compat break | These consumers' APIs unchanged; only internal logic changed |
| Approved lane handling (edge case) | Test explicitly; verify maps to "In Progress" not "Complete" |

---

## Reviewer Guidance

- Verify all raw string lane comparisons are removed from arbiter.py
- Check that all lane comparisons use typed Lane enum
- Confirm arbiter review logic is unchanged
- Verify hardcoded bucketing if-elif chain is removed from tasks_cli.py
- Check that `progress_bucket()` is called correctly
- Confirm regression tests cover all 9 lanes and edge cases (approved, blocked)
- Verify display output is identical for each lane

---

## Change Log

- **2026-04-09**: Initial WP for 080-wpstate-lane-consumer-strangler-fig-phase-2

## Activity Log

- 2026-04-09T15:22:47Z – claude:haiku:implementer:implementer – shell_pid=28913 – Started implementation via action command
- 2026-04-09T15:43:10Z – claude:haiku:implementer:implementer – shell_pid=28913 – Ready for review: migrated arbiter.py to typed Lane enum, tasks_cli.py to event-log lane authority + WPState.display_category(), with 30 regression tests
- 2026-04-09T15:43:33Z – claude:sonnet:reviewer:reviewer – shell_pid=78725 – Started review via action command
- 2026-04-09T15:48:19Z – claude:sonnet:reviewer:reviewer – shell_pid=78725 – Review passed: arbiter.py raw string comparisons replaced with typed Lane enum (Lane.PLANNED, Lane.FOR_REVIEW, Lane.CLAIMED, Lane.APPROVED); tasks_cli.py uses event-log authority via _derive_current_lane() and delegates display bucketing to wp_state_for().display_category(); 30 regression tests added covering all 9 lanes and all comparison scenarios; no raw string comparisons remain; WP05 commit is clean and scoped correctly
- 2026-04-09T17:00:14Z – claude:sonnet:implementer:implementer – shell_pid=1552 – Started implementation via action command
- 2026-04-09T17:15:45Z – claude:sonnet:implementer:implementer – shell_pid=1552 – Ready for review: migrated arbiter.py to typed Lane enum; tasks_cli.py uses event-log authority; 36 regression tests; zero raw string lane comparisons; all 2261 tests pass
- 2026-04-09T17:16:20Z – claude:sonnet:reviewer:reviewer – shell_pid=38338 – Started review via action command
- 2026-04-09T17:17:32Z – claude:sonnet:reviewer:reviewer – shell_pid=38338 – Review passed: full migration, live function tests, zero raw lane strings
